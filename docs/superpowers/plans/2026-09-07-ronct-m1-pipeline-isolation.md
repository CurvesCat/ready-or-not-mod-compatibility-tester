# M1 Wiring: Dependency Grouping + Isolation in One-Click Test

> Executed with superpowers:executing-plans (inline controller style; the repo
> is local-only and commits to main after every green task, as in M1/M2).

**Goal:** Make "One-click test" run the real pipeline: dependency analysis
first, group mods that depend on each other, then launch each group with every
other installed mod parked and restored safely.

**Spec:** ARCHITECTURE-v1.md sections 4-7 and the Python parity inventory
(4.2 rows: static scan, dependency analysis, grouping, per-group launch,
restore/verification, reports).

## Global constraints

- Never touch base-game `pakchunk\d+-Windows*.pak` files.
- Parking/restoring uses only the app-managed session directory; after a
  cancelled or failed run the mod folder must be restored.
- The existing `DependencyScanner.RunAsync` summary API and Analyze button
  behavior stay unchanged.
- Real-game execution is validated manually at the end; automated work covers
  build, unit tests, and a headless dry-run/verification of plan + isolation
  primitives.

---

### Task 1: Harden ModFolderOperator for real-game safety

- Only non-system `.pak` files are parked/restored.
- Add an explicit method to enumerate installed mod names.
- Partial failure during parking rolls back already-moved files.
- Tests: system paks stay untouched, rollback on collision, round-trip
  park/restore.

### Task 2: Expose the dependency graph from the scanner

- Add `DependencyScanGraph` (actual `DependencyEdge`s, overwrite conflict
  pairs, parsed/unresolved counts).
- `RunAsync` delegates to `ScanGraphAsync` and keeps its summary counts.
- TestPage's Analyze summary still works.

### Task 3: Run one-click tests as dependency groups with isolation

- `TestRunner.RunAsync` resolves installed mods in the game Paks folder.
- With `AnalyzeDeps` enabled: `ScanGraphAsync` -> `DeploymentPlanner.Build`
  -> groups; otherwise every mod is its own group.
- Before each group: park installed mods not in the group, deploy any external
  sources, launch once, remove deployed files, restore parked mods.
- A failing multi-mod group falls back to per-mod launches for attribution.
- Optional backup + disposition (quarantine/delete for failed installed mods)
  reuse existing config and BackupService.
- Mod-folder state is verified after the run; JSON/CSV reports include group
  reason and evidence.

### Task 4: Verification

- Full unit suite green (35 + new tests).
- Release build clean; no vulnerable packages.
- Headless dry-run against the real 38-pak folder shows expected groups and
  no file mutations.
- Manual E2E checklist written for the user's confirmation run.
