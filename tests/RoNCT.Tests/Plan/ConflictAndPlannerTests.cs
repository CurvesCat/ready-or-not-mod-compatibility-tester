using RoNCT.Core.Plan;
using RoNCT.Core.Scan;
using RoNCT.Core.Selection;
using Xunit;

namespace RoNCT.Tests.Plan;

public sealed class ConflictAndPlannerTests
{
    private static ModItem Mod(string name) =>
        new($"C:/mods/{name}", name, 10);

    [Fact]
    public void FindConflicts_DetectsCaseInsensitiveDuplicateNames()
    {
        var items = new[] { Mod("A.pak"), Mod("a.pak"), Mod("B.pak") };

        var conflicts = ConflictScanner.FindConflicts(items);

        Assert.Single(conflicts);
        Assert.Equal(ConflictKind.DuplicateName, conflicts[0].Kind);
    }

    [Fact]
    public void FindConflicts_NoMatch_ReturnsEmpty()
    {
        var conflicts = ConflictScanner.FindConflicts(new[] { Mod("A.pak"), Mod("B.pak") });
        Assert.Empty(conflicts);
    }

    [Fact]
    public void Build_GroupsSharedTogether_AndIsolatesConflicts()
    {
        var items = new[] { Mod("A.pak"), Mod("B.pak"), Mod("X.pak"), Mod("x.pak") };
        var conflicts = ConflictScanner.FindConflicts(items);

        var plan = TestPlanner.Build(items, conflicts);

        Assert.Equal(3, plan.Groups.Count);
        Assert.Equal(1, plan.ConflictCount);

        var shared = plan.Groups.Single(group => !group.Isolated);
        Assert.Contains("C:/mods/A.pak", shared.ModPaths);
        Assert.Contains("C:/mods/B.pak", shared.ModPaths);
        Assert.Equal(2, shared.ModPaths.Count);

        Assert.Equal(2, plan.Groups.Count(group => group.Isolated));
    }
}
