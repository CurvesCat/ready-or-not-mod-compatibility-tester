using RoNCT.Core.Scan;
using RoNCT.Core.Selection;

namespace RoNCT.Core.Plan;

public sealed class TestGroup
{
    public TestGroup(IReadOnlyList<string> modPaths, bool isolated)
    {
        ModPaths = modPaths;
        Isolated = isolated;
    }

    public IReadOnlyList<string> ModPaths { get; }
    public bool Isolated { get; }
}

public sealed class TestPlan
{
    public TestPlan(IReadOnlyList<TestGroup> groups, int conflictCount)
    {
        Groups = groups;
        ConflictCount = conflictCount;
    }

    public IReadOnlyList<TestGroup> Groups { get; }
    public int ConflictCount { get; }
}

public static class TestPlanner
{
    public static TestPlan Build(
        IReadOnlyList<ModItem> items,
        IReadOnlyList<ConflictPair> conflicts)
    {
        var isolatedPaths = conflicts
            .SelectMany(conflict => new[] { conflict.A.FilePath, conflict.B.FilePath })
            .ToHashSet(StringComparer.OrdinalIgnoreCase);

        var groups = new List<TestGroup>();
        var shared = items
            .Where(item => !isolatedPaths.Contains(item.FilePath))
            .Select(item => item.FilePath)
            .ToList();

        if (shared.Count > 0)
        {
            groups.Add(new TestGroup(shared, isolated: false));
        }

        foreach (var item in items.Where(item => isolatedPaths.Contains(item.FilePath)))
        {
            groups.Add(new TestGroup(new[] { item.FilePath }, isolated: true));
        }

        return new TestPlan(groups, conflicts.Count);
    }
}
