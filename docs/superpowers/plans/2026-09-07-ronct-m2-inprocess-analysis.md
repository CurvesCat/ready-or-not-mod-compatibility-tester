# M2: In-Process Asset Analysis (CUE4Parse only) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Replace per-asset `dotnet UAssetCLI` subprocess parsing and per-pak
`repak` subprocesses with one in-process CUE4Parse library so a full dependency
scan drops from ~1 minute to seconds.

**Architecture:** A new pure .NET library `RoNCT.Analysis` exposes
`IPakInspector`, `IPakFileReader`, and `IAssetParser`. The default
implementations use CUE4Parse for the pak index/list/read and for parsing the
cooked `.uasset` import table. The existing repak/UAssetCLI subprocess path is
retained as a fallback behind the same interfaces.

**License ruling (critical):** The app is licensed under PolyForm Noncommercial
1.0.0. UAssetAPI is GPL-3.0; linking it in-process into the distributed
application would create a derivative/combined GPL work and conflict with the
app license. **UAssetAPI is therefore NOT used in-process.** CUE4Parse is
permissively licensed (Apache-2.0 per NuGet) and is compatible. The legacy
UAssetCLI (GPL) helper remains an external, separately launched tool for
fallback/legacy purposes only, exactly as in the Python release.

**Tech Stack:** .NET 10 (`net10.0` library), CUE4Parse `1.2.2.202609`
(verified latest stable on NuGet), `Microsoft.Bcl.Memory` `10.0.4` (direct pin
to clear GHSA-73j8-2gch-69rq / CVE-2026-26127 in the transitive 9.0.0), xUnit.

**Spec:** `../ARCHITECTURE-v1.md` sections 3 and 5.

## Global Constraints

- Repository: `C:\Users\curve\Documents\Codex\2026-09-07\RoNCT`, branch `main`.
- `RoNCT.Analysis` targets `net10.0` only; no WinUI/WinRT references.
- Third-party licenses: CUE4Parse (Apache-2.0 per NuGet, permissive), its
  transitive dependencies are permissive; all are tracked in
  THIRD_PARTY_NOTICES in a later packaging milestone. No GPL-3.0 dependency is
  introduced into `RoNCT.Analysis` or `RoNCT.App`.
- Keep the existing repak/UAssetCLI path working until the in-process path is
  verified against real mods.
- Runtime data stays under the app directory. No game mod files are touched.

## Spike evidence (2026-09-07, this machine)

Release-mode spike against the real Ready or Not Mod folder (38 mod paks,
8,623 `.uasset` files):

- Pak list + per-file read via `CUE4Parse.UE4.Pak.PakFileReader` works without
  any AES key or temporary files.
- Import tables are readable by constructing `CUE4Parse.UE4.Assets.Package`
  over raw bytes with lazy serialization and a stub `ITypeMappingsProvider`
  (needed only because cooked assets are unversioned; exports are never
  serialized). `/Game/...` and `/ReadyOrNot/...` references are exposed
  through `FObjectImport.ObjectName.Text`.
- All 8,623 assets parsed with 0 failures in **1.58 seconds**, which exceeds
  the M2 performance target.

---

### Task 1: Scaffold RoNCT.Analysis and add CUE4Parse

**Files:**
- Create: `src/RoNCT.Analysis/RoNCT.Analysis.csproj`
- Create: `src/RoNCT.Analysis/Abstractions.cs`
- Modify: `RoNCT.sln` (add project)
- Modify: `tests/RoNCT.Tests/RoNCT.Tests.csproj` (reference analysis lib)

**Interfaces:**
- Produces:
  - `interface IPakInspector { IReadOnlyList<string> ListAssets(string pakPath); }`
  - `interface IPakFileReader { byte[] ReadFile(string pakPath, string internalPath); }`
  - `interface IAssetParser { AssetImports Parse(byte[] uasset, byte[]? uexp); }`
  - `sealed record AssetImports(IReadOnlyList<string> ImportNames, IReadOnlyList<string> SoftReferences);`

- [x] **Step 1: Create the project files**

`src/RoNCT.Analysis/RoNCT.Analysis.csproj`:

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net10.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="CUE4Parse" Version="1.2.2.202609" />
    <!-- Direct pin clears CVE-2026-26127 in the transitive 9.0.0 package. -->
    <PackageReference Include="Microsoft.Bcl.Memory" Version="10.0.4" />
  </ItemGroup>
</Project>
```

`src/RoNCT.Analysis/Abstractions.cs`:

```csharp
namespace RoNCT.Analysis;

public interface IPakInspector
{
    IReadOnlyList<string> ListAssets(string pakPath);
}

public interface IPakFileReader
{
    byte[] ReadFile(string pakPath, string internalPath);
}

public interface IAssetParser
{
    AssetImports Parse(byte[] uasset, byte[]? uexp);
}

public sealed record AssetImports(
    IReadOnlyList<string> ImportNames,
    IReadOnlyList<string> SoftReferences);
```

Versions were verified with `dotnet package search` and the NuGet flat
container index (CUE4Parse latest = `1.2.2.202609`; UAssetAPI latest = `1.1.0`
and is intentionally unused).

- [x] **Step 2: Add to solution and reference from tests**

```powershell
dotnet sln RoNCT.sln add src/RoNCT.Analysis/RoNCT.Analysis.csproj
dotnet add tests/RoNCT.Tests/RoNCT.Tests.csproj reference src/RoNCT.Analysis/RoNCT.Analysis.csproj
```

- [x] **Step 3: Build and commit**

```powershell
dotnet build RoNCT.sln
git add -A
git commit -m "feat(analysis): scaffold in-process CUE4Parse analysis library with parser abstractions"
```

### Task 2: Implement CUE4Parse pak inspector/reader

**Files:**
- Create: `src/RoNCT.Analysis/Cue4Pak.cs`
- Test: `tests/RoNCT.Tests/Analysis/Cue4PakTests.cs`

**Interfaces:** consumes Task 1 abstractions; produces
`Cue4PakInspector`, `Cue4PakReader`.

- [x] **Step 1: Write the failing test**

```csharp
using RoNCT.Analysis;
using Xunit;

namespace RoNCT.Tests.Analysis;

public sealed class Cue4PakTests
{
    private static readonly string SamplePak =
        @"C:\Program Files (x86)\Steam\steamapps\common\Ready Or Not\ReadyOrNot\Content\Paks\pakchunk99-noNVGblur_DLC2Updated_P.pak";

    [Fact]
    public void ListsAssets_OnRealSamplePak()
    {
        Skip.IfNot(File.Exists(SamplePak), "Requires the local Ready or Not mod pak fixture.");
        var inspector = new Cue4PakInspector();
        var assets = inspector.ListAssets(SamplePak);
        Assert.Contains(assets, p => p.EndsWith(".uasset", StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void ReadFile_ReturnsSampleUassetBytes()
    {
        Skip.IfNot(File.Exists(SamplePak), "Requires the local Ready or Not mod pak fixture.");
        const string inner =
            "ReadyOrNot/Content/ReadyOrNot/Assets/Advanced/Postprocess/Night_Vision/Instances/MI_NVG_Blur.uasset";
        var bytes = new Cue4PakReader().ReadFile(SamplePak, inner);
        Assert.True(bytes.Length > 100);
    }
}
```

- [x] **Step 2: Run test (expect fail until implemented)**

- [x] **Step 3: Implement**

```csharp
using CUE4Parse.UE4.Pak;
using CUE4Parse.UE4.Versions;

namespace RoNCT.Analysis;

public sealed class Cue4PakInspector : IPakInspector
{
    private static readonly VersionContainer Versions = new(EGame.GAME_UE5_4);

    public IReadOnlyList<string> ListAssets(string pakPath)
    {
        using var reader = new PakFileReader(pakPath, Versions);
        reader.Mount(StringComparer.OrdinalIgnoreCase);
        return reader.Files.Keys.ToArray();
    }
}

public sealed class Cue4PakReader : IPakFileReader
{
    private static readonly VersionContainer Versions = new(EGame.GAME_UE5_4);

    public byte[] ReadFile(string pakPath, string internalPath)
    {
        using var reader = new PakFileReader(pakPath, Versions);
        reader.Mount(StringComparer.OrdinalIgnoreCase);
        return reader.Files[internalPath].Read();
    }
}
```

- [x] **Step 4: Run test (expect pass), then commit**

### Task 3: Implement CUE4Parse in-process asset parser

**Files:**
- Create: `src/RoNCT.Analysis/Cue4AssetParser.cs`
- Test: `tests/RoNCT.Tests/Analysis/Cue4AssetParserTests.cs`

**License note:** no UAssetAPI/UAssetCLI in-process usage. The parser reads the
cooked package header directly (import map + soft object paths) through the
permissive CUE4Parse library; exports stay lazy and are never deserialized.

- [x] **Step 1: Write the failing test**

```csharp
[Fact]
public void ParsesImportTable_OnRealSampleAsset()
{
    Skip.IfNot(File.Exists(SamplePak), "Requires the local Ready or Not mod pak fixture.");
    var pak = SamplePak;
    var inner = "ReadyOrNot/Content/ReadyOrNot/Assets/Advanced/Postprocess/Night_Vision/Instances/MI_NVG_Blur.uasset";
    var uasset = new Cue4PakReader().ReadFile(pak, inner);
    var parser = new Cue4AssetParser();
    var imports = parser.Parse(uasset, uexp: null);
    Assert.Contains(imports.ImportNames, n => n.StartsWith("/Game", StringComparison.Ordinal));
}
```

- [x] **Step 2: Run test (expect fail)**

- [x] **Step 3: Implement**

```csharp
using CUE4Parse.FileProvider;
using CUE4Parse.MappingsProvider;
using CUE4Parse.UE4.Assets;
using CUE4Parse.UE4.Readers;
using CUE4Parse.UE4.Versions;

namespace RoNCT.Analysis;

public sealed class Cue4AssetParser : IAssetParser
{
    private static readonly VersionContainer Versions = new(EGame.GAME_UE5_4);
    private static readonly DefaultFileProvider Provider = CreateProvider();

    public AssetImports Parse(byte[] uasset, byte[]? uexp)
    {
        ArgumentNullException.ThrowIfNull(uasset);
        using var archive = new FByteArchive("asset.uasset", uasset, Versions);
        FArchive? uexpArchive = uexp is null
            ? null
            : new FByteArchive("asset.uexp", uexp, Versions);
        using (uexpArchive)
        {
            // useLazySerialization: imports and summary only; never exports.
            var package = new Package(
                archive,
                uexpArchive,
                (FArchive?) null,
                (FArchive?) null,
                Provider,
                useLazySerialization: true);

            var names = package.ImportMap
                .Select(import => import.ObjectName.Text)
                .Where(IsGameReference)
                .Distinct(StringComparer.Ordinal)
                .ToArray();
            var soft = package.SoftObjectPaths
                .Select(path => path.ToString())
                .Where(IsGameReference)
                .Distinct(StringComparer.Ordinal)
                .ToArray();
            return new AssetImports(names, soft);
        }
    }

    private static bool IsGameReference(string value) =>
        value.StartsWith("/Game", StringComparison.Ordinal) ||
        value.StartsWith("/ReadyOrNot", StringComparison.Ordinal);

    private static DefaultFileProvider CreateProvider()
    {
        // Directory is never initialized; only used to satisfy CUE4Parse's
        // IFileProvider for the non-null mappings check on cooked packages.
        var provider = new DefaultFileProvider(
            Path.GetTempPath(), SearchOption.TopDirectoryOnly, Versions);
        provider.MappingsContainer = new EmptyMappingsProvider();
        return provider;
    }

    private sealed class EmptyMappingsProvider : ITypeMappingsProvider
    {
        public TypeMappings? MappingsForGame => new TypeMappings();

        public void Load(string path, StringComparer? comparer = null) { }

        public void Load(byte[] bytes, StringComparer? comparer = null) { }

        public void Reload() { }
    }
}
```

If the compiler reports a member rename (e.g. `SoftObjectPaths[i]` vs
`ToString()`), adjust to the exact member name reported. Soft references stay
best-effort; import paths are the primary dependency signal.

- [x] **Step 4: Run test (expect pass), then commit**

### Task 4: Wire in-process path into DependencyScanner (App services)

**Files:**
- Modify: `src/RoNCT.App/RoNCT.App.csproj` (add `RoNCT.Analysis` reference)
- Modify: `src/RoNCT.App/Services/DependencyScanner.cs`
- Modify: `src/RoNCT.App/Pages/TestPage.xaml.cs` (use in-process adapters)

- [x] Step 1: Add project reference
- [x] Step 2: Thread `IPakInspector`, `IPakFileReader`, and `IAssetParser`
  through `RunAsync` as optional parameters with null fallback to the
  repak/UAssetCLI subprocess path
- [x] Step 3: In `TestPage`, prefer the in-process adapters when CUE4Parse is
  available and stop requiring configured repak/dotnet/UAssetCLI paths for the
  analyze action
- [x] Step 4: Build, run full tests (target: existing 31+ pass)
- [x] Step 5: Benchmark on the real 38-mod folder: record before/after seconds
- [x] Step 6: Commit

### Task 5: Milestone verification

- [x] Full test suite green.
- [x] Benchmark recorded in `docs/benchmarks/m2-inprocess.md`.
- [x] Architecture docs updated (no GPL in-process dependency; CUE4Parse-only
  wording).
- [x] `git status` clean.
