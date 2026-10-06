#!/usr/bin/env python3
"""make-msix-assets — render the MSIX/Store logo PNGs required by
packaging/appxmanifest.xml into build/msix-assets/.

Placeholder art: dark rounded square, disk-usage treemap motif, "DO"
monogram. Replace with real branded art before Store submission.
"""
import os
import sys

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QApplication

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   os.pardir, "build", "msix-assets")

# name -> (px, unplated?)  MSIX requires these three referenced in manifest
ASSETS = {
    "StoreLogo.png": 50,
    "Square44x44Logo.png": 44,
    "Square150x150Logo.png": 150,
    # extras for Store listing quality (scale-200 equivalents)
    "Square150x150Logo.scale-200.png": 300,
    "Square44x44Logo.scale-200.png": 88,
    "StoreLogo.scale-200.png": 100,
}

TILES = [  # treemap motif: (x, y, w, h, color) in unit-square coords
    (0.06, 0.06, 0.55, 0.55, "#4e9aef"),
    (0.65, 0.06, 0.29, 0.35, "#76c7c0"),
    (0.65, 0.45, 0.29, 0.49, "#f2c94c"),
    (0.06, 0.65, 0.35, 0.29, "#eb5757"),
    (0.45, 0.65, 0.16, 0.29, "#9b51e0"),
]


def render(size: int, path: str) -> None:
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)

    bg = QPainterPath()
    r = size * 0.12
    bg.addRoundedRect(QRectF(0, 0, size, size), r, r)
    p.fillPath(bg, QColor("#1d2023"))

    p.setPen(QPen(QColor("#1d2023"), max(1.0, size * 0.02)))
    for x, y, w, h, c in TILES:
        p.fillRect(QRectF(x * size, y * size, w * size, h * size), QColor(c))
        p.drawRect(QRectF(x * size, y * size, w * size, h * size))

    if size >= 100:
        f = QFont("Segoe UI", int(size * 0.16))
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor("#ffffff"))
        p.drawText(QRectF(0.07 * size, 0.07 * size, 0.53 * size,
                          0.53 * size),
                   Qt.AlignCenter, "DO")
    p.end()
    img.save(path)


def main() -> int:
    app = QApplication(sys.argv)
    os.makedirs(OUT, exist_ok=True)
    for name, size in ASSETS.items():
        dest = os.path.join(OUT, name)
        render(size, dest)
        print(f"wrote {dest} ({size}x{size})")
    app.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
