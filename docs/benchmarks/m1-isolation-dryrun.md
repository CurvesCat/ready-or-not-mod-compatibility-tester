# M1 Isolation Pipeline — Dry-Run Record & Manual E2E Checklist

**Date:** 2026-09-07

## Headless dry-run (real 38-pak folder, no game launch, no file mutation)

The scanner + planner combination was run through the real
`DependencyScanner.ScanGraphAsync` and `DeploymentPlanner.Build` code paths:

| Metric | Result |
| --- | --- |
| Mod paks scanned | 38 |
| Assets parsed | 8,623 |
| Cross-mod dependency edges | 27 |
| Overwrite conflict pairs | 6 |
| Unresolved references | 9,409 |
| Planned test groups | 21 (dependency-linked mods share a group) |
| Elapsed (scan + plan) | 12.21 s |

Example grouping: 3 groups shared by dependency (largest groups contain the
ExsaitX asset/blueprint chains), and remaining independent mods are isolated
singletons. No game or mod files were changed during the dry run.

## Manual E2E checklist (user at the computer)

1. Enable automatic backup in Advanced options; confirm the game is closed.
2. Select a small set (for example 3-4 mods, ideally one known-good and one
   known-bad) and click "One-click test".
3. Verify logs show: dependency analysis -> planned N group(s) -> per-group
   "Parked X other installed mod(s)" -> one game launch per group.
4. After the run, verify:
   - JSON/CSV reports exist under the report directory;
   - the Mod folder is back to its pre-run state (unless the disposition
     option intentionally moved/removed failed installed mods);
   - a failing multi-mod group was retried one-by-one and each mod got its own
     verdict.
5. Repeat once with cancellation pressed mid-run; confirm the parked mods are
   restored and no game process remains.
