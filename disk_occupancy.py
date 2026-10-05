#!/usr/bin/env python3
"""disk_occupancy — per-disk, per-folder space occupancy with select-to-delete.

WinDirStat-style PySide6 GUI: drive buttons for every fixed disk, a
size-sorted folder tree (size / % of parent / file count), a squarified
treemap, and delete-to-Recycle-Bin with permanent-delete fallback.

Scanning uses os.scandir (no admin needed). Reparse points / junctions are
counted as zero-size leaves to avoid double-counting and loops.
"""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                os.pardir, "licensing"))
import rlmc_license

from PySide6.QtCore import (QAbstractItemModel, QModelIndex, QObject, Qt,
                            QThread, Signal)
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QApplication, QDialog, QHBoxLayout,
                               QHeaderView, QLabel, QLineEdit, QMainWindow,
                               QMenu, QMessageBox, QProgressBar,
                               QPushButton, QSplashScreen, QSplitter,
                               QStyle, QToolBar, QTreeView, QVBoxLayout,
                               QWidget)

PRODUCT_ID = "diskoccupancy"
APP_NAME = "Disk Occupancy"
PUBLIC_KEY_B64 = "xzgVxIR3q1r2GsivntH-50U2Z9VlcDwIzoENuVNybVI"
LICENSING = rlmc_license.Licensing(PRODUCT_ID, PUBLIC_KEY_B64,
                                   reg_key=r"Software\DiskOccupancy")


def app_version() -> str:
    """CC7: user-facing version is exactly v<version.txt> — nothing else."""
    for base in (getattr(sys, "_MEIPASS", ""),
                 os.path.dirname(os.path.abspath(__file__))):
        try:
            with open(os.path.join(base, "version.txt")) as f:
                return "v" + f.read().strip()
        except OSError:
            continue
    return "v0.0.00000"

HIDDEN = {"system volume information", "$recycle.bin", "recovery"}


# ---------------------------------------------------------------- model data
@dataclass
class Node:
    name: str
    path: str
    is_dir: bool
    size: int = 0
    nfiles: int = 0
    children: list = field(default_factory=list)
    parent: object = None
    denied: bool = False

    def row(self):
        return self.parent.children.index(self) if self.parent else 0


def human(n: int) -> str:
    for u in ("B", "KB", "MB", "GB", "TB", "PB"):
        if n < 1024 or u == "PB":
            return f"{n:.1f} {u}" if u != "B" else f"{n} B"
        n /= 1024


# -------------------------------------------------------------------- scan
class Scanner(QThread):
    progress = Signal(str, int, int)          # current path, files, bytes
    finished_scan = Signal(object, int)        # root Node, denied count

    def __init__(self, root_path: str):
        super().__init__()
        self.root_path = root_path
        self._stop = False

    def run(self):
        root = Node(os.path.basename(self.root_path.rstrip("\\/")) or self.root_path,
                    self.root_path, True)
        denied = 0
        stack = [(root, None)]          # (node, iterator-holder)
        files = 0
        t_last = time.monotonic()
        while stack and not self._stop:
            node, it = stack[-1]
            if it is None:
                try:
                    it = iter(os.scandir(node.path))
                    stack[-1] = (node, it)
                except OSError:
                    node.denied = True
                    denied += 1
                    stack.pop()
                    self._rollup(node)
                    continue
            try:
                entry = next(it)
            except StopIteration:
                stack.pop()
                self._rollup(node)
                continue
            except OSError:
                denied += 1
                stack.pop()
                self._rollup(node)
                continue
            try:
                is_link = entry.is_symlink() or (entry.stat(follow_symlinks=False).st_file_attributes
                            & 0x400) if os.name == "nt" else entry.is_symlink()
                if entry.is_dir(follow_symlinks=False) and not is_link:
                    child = Node(entry.name, entry.path, True, parent=node)
                    node.children.append(child)
                    stack.append((child, None))
                else:
                    try:
                        sz = entry.stat(follow_symlinks=False).st_size if not is_link else 0
                    except OSError:
                        sz = 0
                    node.children.append(Node(entry.name, entry.path, False,
                                              size=sz, parent=node))
                    files += 1
            except OSError:
                denied += 1
            now = time.monotonic()
            if now - t_last > 0.15:
                t_last = now
                self.progress.emit(entry.path, files, 0)
        self.finished_scan.emit(root, denied)

    @staticmethod
    def _rollup(node):
        node.size = sum(c.size for c in node.children)
        node.nfiles = sum(1 if not c.is_dir else 0 for c in node.children) + \
            sum(c.nfiles for c in node.children if c.is_dir)
        node.children.sort(key=lambda c: c.size, reverse=True)


# ---------------------------------------------------------------- tree model
class TreeModel(QAbstractItemModel):
    COLS = ("Name", "Size", "%", "Files")

    def __init__(self):
        super().__init__()
        self.root = Node("", "", True)

    def set_root(self, root):
        self.beginResetModel()
        self.root = root
        self.endResetModel()

    def remove_subtree(self, node):
        parent, row = node.parent, node.row()
        self.beginRemoveRows(self.index_for(parent), row, row)
        parent.children.remove(node)
        self.endRemoveRows()
        delta_size, delta_files = node.size, node.nfiles + (0 if node.is_dir else 1)
        p = parent
        while p is not None:
            p.size -= delta_size
            p.nfiles -= delta_files
            p = p.parent
        self.layoutChanged.emit()

    def index_for(self, node):
        if node is self.root or node.parent is None:
            return QModelIndex()
        return self.createIndex(node.row(), 0, node)

    # --- required QAbstractItemModel API ---
    def index(self, row, col, parent=QModelIndex()):
        node = parent.internalPointer() if parent.isValid() else self.root
        if 0 <= row < len(node.children):
            return self.createIndex(row, col, node.children[row])
        return QModelIndex()

    def parent(self, idx):
        if not idx.isValid():
            return QModelIndex()
        node = idx.internalPointer()
        if node.parent is None or node.parent is self.root:
            return QModelIndex()
        return self.createIndex(node.parent.row(), 0, node.parent)

    def rowCount(self, parent=QModelIndex()):
        node = parent.internalPointer() if parent.isValid() else self.root
        return len(node.children)

    def columnCount(self, parent=QModelIndex()):
        return len(self.COLS)

    def headerData(self, section, orient, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orient == Qt.Horizontal:
            return self.COLS[section]

    def data(self, idx, role=Qt.DisplayRole):
        if not idx.isValid():
            return None
        n: Node = idx.internalPointer()
        c = idx.column()
        if role == Qt.DecorationRole and c == 0:
            from PySide6.QtWidgets import QFileIconProvider
            from PySide6.QtCore import QFileInfo
            return QFileIconProvider().icon(QFileInfo(n.path))
        if role == Qt.DisplayRole:
            if c == 0:
                return n.name + ("  [denied]" if n.denied else "")
            if c == 1:
                return human(n.size)
            if c == 2:
                if n.parent and n.parent.size:
                    return f"{100.0 * n.size / n.parent.size:.1f}%"
                return "100%" if n.parent else ""
            if c == 3:
                return f"{n.nfiles:,}" if n.is_dir else ""
        if role == Qt.TextAlignmentRole and c in (1, 2, 3):
            return Qt.AlignRight | Qt.AlignVCenter
        if role == Qt.ForegroundRole and n.denied:
            return QColor("#e07070")
        if role == Qt.UserRole:
            return n
        return None


# ------------------------------------------------------------------ treemap
def squarify(children, x, y, w, h, out, depth):
    """Simple slice-and-dice treemap (stable, good enough visually)."""
    total = sum(c.size for c in children)
    if total <= 0 or w <= 2 or h <= 2:
        return
    vertical = w >= h
    pos = 0.0
    frame = []
    for c in children:
        frac = c.size / total
        if vertical:
            rect = (c, x + pos, y, w * frac, h, depth)
            pos += w * frac
        else:
            rect = (c, x, y + pos, w, h * frac, depth)
            pos += h * frac
        out.append(rect)
        frame.append(rect)
    if depth < 3:
        for c, cx, cy, cw, ch, _d in frame:
            if c.is_dir and c.children:
                squarify(c.children[:25], cx + 1, cy + 1, cw - 2, ch - 2, out, depth + 1)


PALETTE = ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f",
           "#edc948", "#b07aa1", "#ff9da7", "#9c755f", "#bab0ac"]


class Treemap(QWidget):
    clicked = Signal(object)

    def __init__(self):
        super().__init__()
        self.root = None
        self.rects = []
        self.selected = None
        self.setMinimumHeight(220)

    def set_root(self, root):
        self.root = root
        self.update()

    def set_selected(self, node):
        self.selected = node
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#1b1b1b"))
        if not self.root or not self.root.children:
            p.setPen(QColor("#888"))
            p.drawText(self.rect(), Qt.AlignCenter, "No scan data")
            return
        self.rects.clear()
        top = self.root.children[:200]
        items = []
        squarify(top, 0, 0, self.width(), self.height(), items, 0)
        for i, (node, x, y, w, h, depth) in enumerate(items):
            ancestor = node
            while ancestor.parent and ancestor.parent.parent is not None:
                ancestor = ancestor.parent
            base = QColor(PALETTE[top.index(ancestor) % len(PALETTE)] if ancestor in top else "#555")
            color = base.darker(100 + depth * 18)
            p.fillRect(int(x), int(y), max(1, int(w)), max(1, int(h)), color)
            p.setPen(QPen(QColor("#101010"), 1))
            p.drawRect(int(x), int(y), max(1, int(w)), max(1, int(h)))
            self.rects.append((x, y, w, h, node))
            if node is self.selected:
                p.setPen(QPen(QColor("#ffffff"), 2))
                p.drawRect(int(x) + 1, int(y) + 1, max(1, int(w)) - 2, max(1, int(h)) - 2)
            if w > 60 and h > 16:
                p.setPen(QColor("#f0f0f0"))
                label = f"{node.name}  {human(node.size)}"
                p.drawText(int(x) + 4, int(y) + 2, int(w) - 8, int(h) - 4,
                           Qt.AlignLeft | Qt.AlignTop, label)
        p.end()

    def mousePressEvent(self, e):
        for x, y, w, h, node in reversed(self.rects):
            if x <= e.position().x() < x + w and y <= e.position().y() < y + h:
                self.clicked.emit(node)
                return


# --------------------------------------------------------------- main window
def fixed_drives():
    drives = []
    if os.name == "nt":
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for i in range(26):
            if bitmask & (1 << i):
                d = f"{chr(65 + i)}:\\"
                if ctypes.windll.kernel32.GetDriveTypeW(d) == 3:  # DRIVE_FIXED
                    drives.append(d)
    return drives or ["C:\\"]


class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {app_version()}")
        self.resize(1200, 780)
        self.model = TreeModel()
        self.scanner = None
        self._build_ui()

    def _build_ui(self):
        self._build_menus()
        tb = QToolBar()
        tb.setMovable(False)
        for d in fixed_drives():
            b = QPushButton(d)
            b.setCheckable(True)
            b.clicked.connect(lambda _=False, p=d: self.scan(p))
            tb.addWidget(b)
        tb.addSeparator()
        for label, fn in (("Scan folder…", self.pick_folder),
                          ("Rescan", self.rescan),
                          ("Stop", self.stop)):
            b = QPushButton(label)
            b.clicked.connect(fn)
            tb.addWidget(b)
        self.addToolBar(tb)

        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setSortingEnabled(False)
        self.tree.setUniformRowHeights(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._menu)
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        for i, w in ((1, 110), (2, 70), (3, 90)):
            self.tree.setColumnWidth(i, w)
        self.tree.selectionModel().selectionChanged.connect(self._tree_sel)

        self.map = Treemap()
        self.map.clicked.connect(self._map_sel)

        split = QSplitter(Qt.Vertical)
        split.addWidget(self.tree)
        split.addWidget(self.map)
        split.setSizes([520, 240])
        self.setCentralWidget(split)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.status = QLabel("Pick a drive to scan.")
        bar = QWidget()
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(6, 2, 6, 2)
        lay.addWidget(self.status, 1)
        lay.addWidget(self.progress)
        self.tier_label = QLabel()
        lay.addWidget(self.tier_label)
        self.statusBar().addWidget(bar, 1)
        self._path = None
        self._update_tier()

    # ----------------------------------------------------------- menus
    def _build_menus(self):
        mb = self.menuBar()
        m_file = mb.addMenu("&File")
        m_file.addAction("Scan folder…", self.pick_folder)
        m_file.addAction("Rescan", self.rescan)
        m_file.addSeparator()
        m_file.addAction("Exit", self.close)
        m_tools = mb.addMenu("&Tools")
        m_tools.addAction("License…", self._license_dialog)
        m_help = mb.addMenu("&Help")
        m_help.addAction(f"About {APP_NAME}", self._about)

    def _about(self):
        from PySide6.QtCore import qVersion
        lic = LICENSING.load()
        rows = [
            f"<h3>{APP_NAME} {app_version()}</h3>",
            "<p>Per-disk, per-folder space occupancy — select to delete.</p>",
            f"<p>Tier: <b>{'Pro — ' + lic.email if lic else 'Free'}</b></p>",
            f"<p>Qt (UI framework): {qVersion()}</p>",
            "<p>(c) 2026 Robin L. M. Cheung, MBA. All rights reserved.</p>",
        ]
        QMessageBox.about(self, f"About {APP_NAME}", "".join(rows))

    # ----------------------------------------------------------- licensing
    def _update_tier(self):
        lic = LICENSING.load()
        self.tier_label.setText(
            f"Pro — {lic.email}" if lic else "Free — activate Pro to delete")

    def _license_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("License")
        lay = QVBoxLayout(dlg)
        lic = LICENSING.load()
        status = (f"Active: Pro — {lic.email}  "
                  + ("perpetual" if lic.perpetual else "expires "
                     + time.strftime("%Y-%m-%d",
                                     time.localtime(lic.expires)))
                  if lic else "No license active — Free tier")
        lay.addWidget(QLabel(status))
        mh = rlmc_license.machine_hash(PRODUCT_ID)
        row = QHBoxLayout()
        row.addWidget(QLabel(f"Machine ID: {mh}  (send with purchase "
                             f"for machine-bound licenses)"))
        copy = QPushButton("Copy")
        copy.clicked.connect(
            lambda: QApplication.clipboard().setText(mh))
        row.addWidget(copy)
        lay.addLayout(row)
        entry = QLineEdit()
        entry.setPlaceholderText("RLMC1.… license key")
        lay.addWidget(entry)
        btn_row = QHBoxLayout()
        act = QPushButton("Activate")
        act.clicked.connect(lambda: self._activate(dlg, entry.text()))
        deact = QPushButton("Deactivate")
        deact.clicked.connect(lambda: (LICENSING.clear(),
                                       self._update_tier(), dlg.reject()))
        close = QPushButton("Close")
        close.clicked.connect(dlg.reject)
        for b in (act, deact, close):
            btn_row.addWidget(b)
        lay.addLayout(btn_row)
        dlg.exec()

    def _activate(self, dlg, key):
        try:
            lic = LICENSING.save(key)
        except ValueError as e:
            QMessageBox.warning(self, "License", str(e))
            return
        self._update_tier()
        QMessageBox.information(self, "License",
                                f"Pro activated for {lic.email}")
        dlg.accept()

    # ------------------------------------------------------------- actions
    def scan(self, path):
        self.stop()
        self._path = path
        self.progress.setVisible(True)
        self.status.setText(f"Scanning {path} …")
        self.scanner = Scanner(path)
        self.scanner.progress.connect(
            lambda p, f, b: self.status.setText(f"Scanning {p}   ({f:,} files)"))
        self.scanner.finished_scan.connect(self._scanned)
        self.scanner.start()

    def stop(self):
        if self.scanner and self.scanner.isRunning():
            self.scanner._stop = True
            self.scanner.wait(3000)

    def rescan(self):
        if self._path:
            self.scan(self._path)

    def pick_folder(self):
        from PySide6.QtWidgets import QFileDialog
        d = QFileDialog.getExistingDirectory(self, "Scan folder", "C:\\")
        if d:
            self.scan(d)

    def _scanned(self, root, denied):
        self.progress.setVisible(False)
        self.model.set_root(root)
        self.map.set_root(root)
        self.tree.expand(self.model.index(0, 0))
        msg = f"{human(root.size)} in {root.nfiles:,} files under {root.path}"
        if denied:
            msg += f"   ({denied} items denied — run as admin for full scan)"
        self.status.setText(msg)

    def _menu(self, pos):
        idx = self.tree.indexAt(pos)
        if not idx.isValid():
            return
        node = idx.internalPointer()
        menu = QMenu(self)
        menu.addAction("Open in Explorer", lambda: self._open(node))
        menu.addAction("Copy path", lambda: QApplication.clipboard().setText(node.path))
        menu.addSeparator()
        menu.addAction(self.style().standardIcon(QStyle.SP_TrashIcon),
                       "Delete (Recycle Bin)", lambda: self._delete(node))
        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def _open(self, node):
        target = node.path if node.is_dir else os.path.dirname(node.path)
        subprocess.Popen(["explorer", target])

    def _tree_sel(self, sel, _):
        idxs = sel.indexes()
        if idxs:
            self.map.set_selected(idxs[0].internalPointer())

    def _map_sel(self, node):
        chain = []
        p = node
        while p and p.parent is not None:
            chain.append(p)
            p = p.parent
        for n in reversed(chain[:-1]):
            self.tree.expand(self.model.index_for(n))
        idx = self.model.index_for(node)
        self.tree.selectionModel().select(
            idx, self.tree.selectionModel().SelectionFlag.ClearAndSelect |
            self.tree.selectionModel().SelectionFlag.Rows)
        self.tree.scrollTo(idx)
        self.map.set_selected(node)

    def _delete(self, node):
        if node.parent is None:
            return
        if not LICENSING.is_pro:
            box = QMessageBox(self)
            box.setWindowTitle("Pro feature")
            box.setText("Deleting files requires Disk Occupancy Pro.\n\n"
                        "Enter a license key to unlock.")
            activate = box.addButton("Activate…", QMessageBox.AcceptRole)
            box.addButton(QMessageBox.Cancel)
            box.exec()
            if box.clickedButton() is activate:
                self._license_dialog()
            return
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("Delete")
        box.setText(f"Send to Recycle Bin?\n\n{node.path}\n\n{human(node.size)}"
                    + (f", {node.nfiles:,} files" if node.is_dir else ""))
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        if box.exec() != QMessageBox.Yes:
            return
        try:
            from send2trash import send2trash
            send2trash(node.path)
        except Exception as exc:
            box2 = QMessageBox(self)
            box2.setIcon(QMessageBox.Critical)
            box2.setWindowTitle("Recycle failed")
            box2.setText(f"Recycle Bin refused:\n{exc}\n\nDelete PERMANENTLY instead?")
            box2.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            if box2.exec() != QMessageBox.Yes:
                return
            try:
                if node.is_dir:
                    import shutil
                    shutil.rmtree(node.path)
                else:
                    os.remove(node.path)
            except OSError as e2:
                QMessageBox.critical(self, "Delete failed", str(e2))
                return
        self.status.setText(f"Deleted {node.path} ({human(node.size)})")
        self.model.remove_subtree(node)
        self.map.set_root(self.model.root)


DARK_STYLE = """
QMainWindow, QWidget { background: #1d2023; color: #e8e8e8; }
QTreeView { background: #1d2023; alternate-background-color: #26292d;
            color: #e8e8e8; border: none; show-decoration-selected: 1; }
QTreeView::item { padding: 7px 6px; }
QTreeView::item:selected { background: #3a5f8a; color: #fff; }
QTreeView::item:hover { background: #2e3339; }
QHeaderView::section { padding: 7px 8px; background: #26292d; color: #cfcfcf;
                       border: none; border-bottom: 1px solid #3a3d42; }
QToolBar { background: #232629; border: none; spacing: 6px; padding: 4px; }
QPushButton { background: #2e3339; color: #e8e8e8; border: 1px solid #3a3d42;
              border-radius: 4px; padding: 5px 12px; }
QPushButton:hover { background: #3a4149; }
QPushButton:checked { background: #3a5f8a; border-color: #4a6f9a; }
QStatusBar { background: #232629; color: #cfcfcf; }
QProgressBar { border: 1px solid #3a3d42; border-radius: 3px;
               background: #1d2023; height: 10px; text-align: center; }
QProgressBar::chunk { background: #3a5f8a; }
QSplitter::handle { background: #232629; }
QMenu { background: #26292d; color: #e8e8e8; border: 1px solid #3a3d42; }
QMenu::item:selected { background: #3a5f8a; }
QMenuBar { background: #232629; color: #e8e8e8; }
QMenuBar::item:selected { background: #3a5f8a; }
QDialog, QLineEdit { background: #1d2023; color: #e8e8e8; }
QLineEdit { border: 1px solid #3a3d42; border-radius: 4px; padding: 5px; }
"""


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_STYLE)
    pix = QPixmap(400, 180)
    pix.fill(QColor("#1d2023"))
    splash = QSplashScreen(pix)
    splash.showMessage(f"{APP_NAME}\n{app_version()}",
                       Qt.AlignCenter, QColor("#e8e8e8"))
    splash.show()
    app.processEvents()
    w = Main()
    w.show()
    splash.finish(w)
    if len(sys.argv) > 1:
        w.scan(sys.argv[1])
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
