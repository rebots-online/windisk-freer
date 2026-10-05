#!/usr/bin/env python3
"""Headless verification: licensing gate, registry roundtrip, CC7 UI."""
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import disk_occupancy as D

ver = D.app_version()
assert ver.startswith("v") and ver == "v" + open(
    os.path.join(os.path.dirname(D.__file__), "version.txt")).read().strip(), ver
print('CC7 version string:', ver)

print('free tier (no key saved):', D.LICENSING.is_pro)
assert not D.LICENSING.is_pro

import glob, json
lics = sorted(glob.glob(r'C:\Users\Admin\tools\licensing\issued\*.lic'),
              key=os.path.getmtime)
key = json.loads(open(lics[-1]).read())['key']
print('using issued license:', lics[-1].split(os.sep)[-1])
lic = D.LICENSING.save(key)
print('activated:', lic.email, '| is_pro:', D.LICENSING.is_pro)
assert D.LICENSING.is_pro

try:
    D.LICENSING.save('garbage')
    print('FAIL: bad key saved')
except ValueError as e:
    print('bad key rejected, not stored:', e)

D.LICENSING.clear()
assert not D.LICENSING.is_pro
print('after deactivation, is_pro:', D.LICENSING.is_pro)

from PySide6.QtWidgets import QApplication
app = QApplication([])
w = D.Main()
print('title:', w.windowTitle())
print('tier label:', w.tier_label.text())
menus = [a.text() for a in w.menuBar().actions()]
print('menus:', menus)
assert menus == ['&File', '&Tools', '&Help'], menus
assert ver in w.windowTitle()
print('ALL CHECKS PASSED')
