#ifndef MyAppName
#define MyAppName "Logical"
#endif

#ifndef MyAppVersion
#define MyAppVersion "1.0.0"
#endif

#ifndef MyAppPublisher
#define MyAppPublisher "Logical"
#endif

#ifndef MySourceDir
#define MySourceDir "."
#endif

#define MyAppExeName "Logical.exe"

[Setup]
AppId={{A9F6D12D-8E41-4D2F-9D84-3B2B3C6F8A21}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir={#MySourceDir}\installer_output
OutputBaseFilename=LogicalUpdater
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UsePreviousAppDir=yes
CloseApplications=yes
CloseApplicationsFilter=Logical.exe
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "{#MySourceDir}\dist\Logical.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MySourceDir}\logo.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MySourceDir}\Logical Saves\*"; DestDir: "{app}\Logical Saves"; Flags: recursesubdirs createallsubdirs ignoreversion

[Dirs]
Name: "{app}\Logical Saves"
