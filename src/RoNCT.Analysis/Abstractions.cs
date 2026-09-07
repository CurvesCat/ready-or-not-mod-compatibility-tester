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
