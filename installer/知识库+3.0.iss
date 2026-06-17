; 知识库+3.0 安装程序 — Inno Setup 脚本
; 编译: ISCC.exe installer\知识库+3.0.iss

#define MyAppName "知识库+3.0"
#define MyAppVersion "3.0"
#define MyAppPublisher "FileSearchPlus"
#define MyAppExeName "知识库+3.0.exe"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DisableDirPage=yes
OutputDir=..\dist
OutputBaseFilename=知识库+3.0_Installer
SetupIconFile=..\app_icon正式.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma2/max
SolidCompression=yes
LZMAUseSeparateProcess=yes
DisableProgramGroupPage=yes
WizardStyle=modern
ShowLanguageDialog=no
LanguageDetectionMethod=none

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "快捷方式:"; Flags: checkedonce

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\sample_files\知识库文件\*"; DestDir: "{app}\知识库文件"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\知识库+3.0"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\知识库+3.0"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 知识库+3.0"; Flags: nowait postinstall skipifsilent