# M2 Benchmark — In-Process CUE4Parse Analysis

**Date:** 2026-09-07
**Machine:** RoNCT development machine (Windows, local Ready or Not install)
**Data set:** real `ReadyOrNot\Content\Paks` mod folder — 38 mod paks,
8,623 `.uasset` files (excluding base-game `pakchunk\d+-Windows` paks).

## Before (legacy path)

The pre-M2 dependency scanner launched one `dotnet UAssetCLI` subprocess per
parsed `.uasset`. On this machine the scan class was ~1 minute for the default
100-asset scan because each process spawn costs roughly half a second plus
.NET startup; a full 8,000+ asset scan would take many minutes. This matches
the user-reported Python-era scan duration.

## After (in-process path)

Release-mode run of the real `DependencyScanner.RunAsync` service with the
in-process adapters (`Cue4AnalysisSession` + `Cue4AssetParser`, unlimited
asset limit, including .uexp reads and static conflict scanning):

| Metric | Result |
| --- | --- |
| Paks listed | 38 |
| Assets parsed | 8,623 |
| Dependency edges | 27 |
| Unresolved `/Game/Mods/...` references | 9,409 |
| Static conflicts | 6 |
| Total elapsed | **8.00 s** |

A minimal in-process harness (same adapters, no conflict read-back) measured
**4.61 s** for the same dataset, and listing + import parsing without .uexp
reads measured 1.58 s.

Parse-only harness (same in-process adapters, no conflict read-back):

| Metric | Result |
| --- | --- |
| Paks listed | 38 |
| Assets parsed | 8,623 |
| Parse failures | 0 |
| Import/game references found | 16,737 |
| Total elapsed (parse harness) | **4.61 s** |

The full service pipeline (conflict read-back included) runs in 8 s for the
entire 8,623-asset folder, comfortably inside the "seconds, not a minute"
target; the previous per-asset subprocess model would need many minutes for
the same dataset.

## Notes

- No game or mod files were modified; paks were only opened for reading.
- UAssetAPI was intentionally not used in-process (GPL-3.0 conflicts with the
  PolyForm Noncommercial app license); all parsing is CUE4Parse (Apache-2.0).
