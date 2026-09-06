namespace RoNCT.Core.Analysis;

public static class RepakListParser
{
    public static IReadOnlyList<string> Parse(string output)
    {
        return output
            .Split('\n', StringSplitOptions.RemoveEmptyEntries)
            .Select(line => line.Trim())
            .Where(line => line.Length > 0)
            .ToArray();
    }
}
