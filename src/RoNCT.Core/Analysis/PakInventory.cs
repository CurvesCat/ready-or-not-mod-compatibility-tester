namespace RoNCT.Core.Analysis;

public sealed class PakInventory
{
    public PakInventory(string pakPath, string fileName, IReadOnlyList<string> internalPaths)
    {
        PakPath = pakPath;
        FileName = fileName;
        InternalPaths = internalPaths;
    }

    public string PakPath { get; }
    public string FileName { get; }
    public IReadOnlyList<string> InternalPaths { get; }
}
