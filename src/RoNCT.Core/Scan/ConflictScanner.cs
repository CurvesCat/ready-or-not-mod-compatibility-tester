using RoNCT.Core.Selection;

namespace RoNCT.Core.Scan;

public enum ConflictKind
{
    DuplicateName,
}

public sealed record ConflictPair(ModItem A, ModItem B, ConflictKind Kind);

public static class ConflictScanner
{
    public static IReadOnlyList<ConflictPair> FindConflicts(IEnumerable<ModItem> items)
    {
        var array = items as ModItem[] ?? items.ToArray();
        var conflicts = new List<ConflictPair>();

        for (var i = 0; i < array.Length; i++)
        {
            for (var j = i + 1; j < array.Length; j++)
            {
                if (string.Equals(
                    array[i].FileName, array[j].FileName, StringComparison.OrdinalIgnoreCase))
                {
                    conflicts.Add(new ConflictPair(array[i], array[j], ConflictKind.DuplicateName));
                }
            }
        }

        return conflicts;
    }
}
