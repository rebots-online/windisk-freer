; NSIS installer — Disk Occupancy
; Build: makensis installer.nsi   (run from packaging\ dir)
; Produces: ..\dist\windisk-freer-v<version.txt>-win64-nsis.exe
!define APPNAME "Disk Occupancy"
; Stamped output — version comes from version.txt (written by
; scripts/update-version.ps1 during build-release.ps1); never hand-edit.
!ifndef APPVERSION
  !define /file APPVERSION "..\version.txt"
!endif
!define PUBLISHER "Robin L. M. Cheung, MBA"
!define APPEXE "DiskOccupancy.exe"

Unicode true
Name "${APPNAME}"
; AD-6 slug-first release naming, flat in dist\: windisk-freer-v<ver>-win64-nsis.exe
OutFile "..\dist\windisk-freer-v${APPVERSION}-win64-nsis.exe"
InstallDir "$LOCALAPPDATA\Programs\${APPNAME}"
RequestExecutionLevel user          ; per-user install — no UAC prompt
SetCompressor /SOLID lzma

!include "MUI2.nsh"
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APPEXE}"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Section "Install"
    SetOutPath "$INSTDIR"
    File "..\build\onefile\${APPEXE}"
    ; LGPL/Qt notices + product license ship alongside the binary
    File /nonfatal "..\LICENSE.txt"
    File /nonfatal "..\LICENSE-Qt-LGPL.txt"

    WriteUninstaller "$INSTDIR\uninstall.exe"
    CreateShortcut "$DESKTOP\${APPNAME}.lnk" "$INSTDIR\${APPEXE}"
    CreateDirectory "$SMPROGRAMS\${APPNAME}"
    CreateShortcut "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk" "$INSTDIR\${APPEXE}"
    CreateShortcut "$SMPROGRAMS\${APPNAME}\Uninstall.lnk" "$INSTDIR\uninstall.exe"

    ; Add/Remove Programs registration
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" \
        "DisplayName" "${APPNAME}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" \
        "DisplayVersion" "${APPVERSION}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" \
        "Publisher" "${PUBLISHER}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" \
        "UninstallString" "$INSTDIR\uninstall.exe"
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" \
        "NoModify" 1
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" \
        "NoRepair" 1
SectionEnd

Section "Uninstall"
    ; License is per-user data in HKCU\Software\DiskOccupancy — kept on
    ; uninstall so reinstall stays activated (standard shareware behavior)
    Delete "$INSTDIR\${APPEXE}"
    Delete "$INSTDIR\LICENSE*.txt"
    Delete "$INSTDIR\uninstall.exe"
    RMDir "$INSTDIR"
    Delete "$DESKTOP\${APPNAME}.lnk"
    RMDir /r "$SMPROGRAMS\${APPNAME}"
    DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}"
SectionEnd
