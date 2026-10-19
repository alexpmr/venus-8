#define MyAppName "Venus-8"
#ifndef MyAppVersion
#define MyAppVersion "0.1.0"
#endif
[Setup]
AppId={{E73A1CD2-734F-4B71-A35F-5A4BA8F38D11}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\Venus-8
DefaultGroupName=Venus-8
OutputDir=..\dist
OutputBaseFilename=Venus-8-v{#MyAppVersion}-Windows-Setup
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern
SetupIconFile=..\assets\venus-8.ico
UninstallDisplayIcon={app}\Venus-8.exe
[Files]
Source: "..\dist\Venus-8\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
[Icons]
Name: "{group}\Venus-8"; Filename: "{app}\Venus-8.exe"
Name: "{autodesktop}\Venus-8"; Filename: "{app}\Venus-8.exe"; Tasks: desktopicon
[Tasks]
Name: "desktopicon"; Description: "Criar atalho na Área de Trabalho"; GroupDescription: "Atalhos:"
[Run]
; No skipifsilent: the in-app update runs Setup with /SILENT and must reopen
; Venus-8 afterwards. postinstall entries run as the original (non-admin) user.
Filename: "{app}\Venus-8.exe"; Description: "Abrir Venus-8"; Flags: nowait postinstall
