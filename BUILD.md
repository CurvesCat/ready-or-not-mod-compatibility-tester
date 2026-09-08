# Building a release

## Prerequisites

- Windows 10/11
- .NET SDK 10 or newer
- Ready or Not installed (needed for runtime tests only)

## Build

```powershell
dotnet build RoNCT.sln -c Release
```

## Run tests

```powershell
dotnet test RoNCT.sln -c Release
```

## Publish a portable release

```powershell
dotnet publish src/RoNCT.App/RoNCT.App.csproj `
  -c Release `
  -p:Platform=x64 `
  -p:RuntimeIdentifier=win-x64 `
  -p:PublishDir=artifacts/release
```

The output is self-contained and does not require a separate .NET runtime.

## Release ZIP layout

```text
RoNCT.App.exe
Assets\
... (self-contained runtime and WinUI files)
```

Packaging copies the published output plus `README.md`, `LICENSE`, and
`THIRD_PARTY_NOTICES.txt`. No source tree, user configuration, backups, logs,
or reports are included.

Runtime folders (`logs`, `reports`, `backup`, `quarantine`, `cache`) and
`config.json` are created next to the executable on first use.
