using CUE4Parse.UE4.Pak;
using CUE4Parse.UE4.Versions;

namespace RoNCT.Analysis;

public sealed class Cue4PakInspector : IPakInspector
{
    private static readonly VersionContainer Versions = new(EGame.GAME_UE5_4);

    public IReadOnlyList<string> ListAssets(string pakPath)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(pakPath);

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
        ArgumentException.ThrowIfNullOrWhiteSpace(pakPath);
        ArgumentException.ThrowIfNullOrWhiteSpace(internalPath);

        using var reader = new PakFileReader(pakPath, Versions);
        reader.Mount(StringComparer.OrdinalIgnoreCase);
        return reader.Files[internalPath].Read();
    }
}
