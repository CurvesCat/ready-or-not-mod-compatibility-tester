# RoNCT — Ready or Not Mod Compatibility Tester

RoNCT (Ready or Not Mod Compatibility Tester) is a Windows desktop tool that
tests Ready or Not `.pak` mods for compatibility without manually swapping
files or reading engine logs.

The current release is a C# / WinUI 3 rewrite. It is portable (no installer),
keeps all runtime data next to the executable, and does not write to your
Documents folder.

## Features

- One-click compatibility tests with per-mod isolation and automatic grouping
- Dependency-aware group planning from in-process asset analysis
- Safe backup, rollback, quarantine, and restore
- Nexus Mods identification, confirm/ignore history, and requirement checks
- Startup-time calibration with result caching and OCR-based menu detection
- Cancellable runs without UI freezes
- Bilingual interface (English / 中文) with instant language switching
- System / light / dark themes

## System requirements

- Windows 10 or Windows 11 (64-bit)
- Ready or Not installed through Steam (default path recommended)

## Download

Download the portable ZIP from the
[Releases](https://github.com/CurvesCat/ready-or-not-mod-compatibility-tester/releases)
page. Extract it anywhere and run `RoNCT.App.exe`.

The program stores reports, backups, quarantine, cache, and logs in its own
folder. Do not place it inside a protected folder such as `Program Files`.

## Quick start

1. Start the app.
2. Click **Auto detect** to load the installed Ready or Not mods, or select a
   mod folder / individual `.pak` files.
3. Click **Analyze dependencies only** to inspect conflicts without launching
   the game.
4. Click **One-click test** to run the game and produce a report.
5. Use **Stop** to cancel a run safely at any time.

Use the **Help** button in the title bar for the full built-in guide.

## Nexus Mods API

Nexus features require your personal Nexus API key:

1. Open <https://www.nexusmods.com/settings/api-keys> and scroll to the bottom.
2. Generate and copy the **Personal API Key**.
3. Paste it into the Nexus page inside RoNCT and click **Save key**.

Your key stays in the local `config.json` next to the executable and is never
shared with the app's servers.

## Building from source

See [BUILD.md](BUILD.md).

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md).

## License

[PolyForm Noncommercial 1.0.0](LICENSE)

## Contact

- Developer: CurvesCat
- Email: ronct.dev@icloud.com
- Nexus Mods: <https://www.nexusmods.com/readyornot/mods/8575>

When reporting a bug, open the **Debug** page, click **Copy diagnostics**, and
include the copied text in your message.
