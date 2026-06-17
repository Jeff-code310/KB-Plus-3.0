; Inno Setup Script - 文件搜索+ 安装包
; 编码：ANSI

#define MyAppName "文件搜索+"
#define MyAppVersion "1.0"
#define MyAppPublisher "文件搜索+"
#define MyAppExeName "FileSearchPlus.exe"

[Setup]
AppId={{B9A2D3E1-4F5C-4A6B-8C7D-9E0F1A2B3C4D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\installer_output
OutputBaseFilename=文件搜索+_setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "C:\Users\Administrator\.qclaw\workspace\file_search_assistant\dist\FileSearchPlus.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Administrator\.qclaw\workspace\file_search_assistant\dist\config.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Administrator\.qclaw\workspace\file_search_assistant\dist\logs\*"; DestDir: "{app}\logs"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "C:\Users\Administrator\.qclaw\workspace\file_search_assistant\sample_files\*"; DestDir: "{app}\sample_files"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
