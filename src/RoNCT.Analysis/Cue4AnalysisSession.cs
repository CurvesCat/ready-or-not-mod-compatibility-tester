using CUE4Parse.UE4.Pak;
using CUE4Parse.UE4.Versions;

namespace RoNCT.Analysis;

/// <summary>
/// Reuses one open CUE4Parse pak reader per pak path so a full dependency
/// scan reads each pak index once instead of once per contained asset.
/// </summary>
public sealed class Cue4AnalysisSession : IPakInspector, IPakFileReader, IDisposable
{
    private static readonly VersionContainer Versions = new(EGame.GAME_UE5_4);
    private readonly Dictionary<string, PakFileReader> _readers =
        new(StringComparer.OrdinalIgnoreCase);

    public IReadOnlyList<string> ListAssets(string pakPath)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(pakPath);
        return GetReader(pakPath).Files.Keys.ToArray();
    }

    public byte[] ReadFile(string pakPath, string internalPath)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(pakPath);
        ArgumentException.ThrowIfNullOrWhiteSpace(internalPath);
        return GetReader(pakPath).Files[internalPath].Read();
    }

    public void Dispose()
    {
        foreach (var reader in _readers.Values)
        {
            reader.Dispose();
        }
        _readers.Clear();
    }

    private PakFileReader GetReader(string pakPath)
    {
        if (_readers.TryGetValue(pakPath, out var existing))
        {
            return existing;
        }

        var reader = new PakFileReader(pakPath, Versions);
        try
        {
            reader.Mount(StringComparer.OrdinalIgnoreCase);
        }
        catch
        {
            reader.Dispose();
            throw;
        }
        _readers[pakPath] = reader;
        return reader;
    }
}
