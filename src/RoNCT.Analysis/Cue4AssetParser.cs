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
        var package = new Package(
            archive,
            (FArchive?) null,
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

    private static bool IsGameReference(string value) =>
        value.StartsWith("/Game", StringComparison.Ordinal) ||
        value.StartsWith("/ReadyOrNot", StringComparison.Ordinal);

    private static DefaultFileProvider CreateProvider()
    {
        // The directory is never initialized. CUE4Parse only needs a
        // non-null IFileProvider with mappings for the cooked-package
        // CanDeserialize check; exports stay lazy and are never serialized.
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
