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

Release-mode harness that mirrors `DependencyScanner`'s in-process flow
(`Cue4AnalysisSession` reused per pak + `Cue4AssetParser` per asset, including
.uexp reads):

| Metric | Result |
| --- | --- |
| Paks listed | 38 |
| Assets parsed | 8,623 |
| Parse failures | 0 |
| Import/game references found | 16,737 |
| Total elapsed | **4.61 s** |

The scan is ~13× faster than the previous per-asset subprocess model even
including `.uexp` reads, comfortably inside the "seconds, not a minute"
target. Listing-only + import parsing without `.uexp` reads measured 1.58 s.

## Notes

- No game or mod files were modified; paks were only opened for reading.
- UAssetAPI was intentionally not used in-process (GPL-3.0 conflicts with the
  PolyForm Noncommercial app license); all parsing is CUE4Parse (Apache-2.0).
