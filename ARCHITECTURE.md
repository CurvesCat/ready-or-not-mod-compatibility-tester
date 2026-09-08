# Architecture

RoNCT is a C# / WinUI 3 desktop application organized into:

- `src/RoNCT.App` — WinUI shell, pages, and Windows/game integration services
- `src/RoNCT.Core` — configuration, planning, backup, and pure logic
- `src/RoNCT.Analysis` — in-process Unreal Engine pak and asset analysis
- `tests/RoNCT.Tests` — automated tests for planning and configuration logic

## Key flows

1. **Selection** resolves a folder or individual `.pak` files.
2. **Analysis** reads paks in-process, builds a dependency graph, and plans
   isolated test groups.
3. **Test runner** backs up the mod folder, deploys one group at a time,
   launches the game, watches for crashes/errors, then restores the folder.
4. **Nexus** uses MD5/filename matching plus the user's API key to identify
   mods and check requirements.
5. **Calibration** measures game startup once and caches the result.

All user data is stored next to the executable and never written to the user's
Documents or AppData by default.

See `docs/ARCHITECTURE-v1.md` for the detailed design history.
