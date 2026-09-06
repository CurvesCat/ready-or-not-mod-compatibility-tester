using RoNCT.Core.Plan;
using Xunit;

namespace RoNCT.Tests.Plan;

public sealed class DeploymentPlannerTests
{
    [Fact]
    public void Build_UnionsDependencyAndIsolatesConflictMod()
    {
        var plan = DeploymentPlanner.Build(
            new[] { "A.pak", "B.pak", "C.pak" },
            new List<IReadOnlyList<string>> { new[] { "A.pak", "B.pak" } },
            new[] { new DependencyEdge("A.pak", "C.pak") });

        // A depends on C -> grouped together; B is isolated by the conflict.
        var groupWithC = plan.Groups.Single(g => g.Mods.Contains("A.pak"));
        Assert.True(groupWithC.Mods.Contains("C.pak"));
        Assert.Equal("dependency", groupWithC.Reason);
        Assert.Contains("A.pak requires C.pak", groupWithC.Evidence);

        var isolatedB = plan.Groups.Single(g => g.Mods.Count == 1 && g.Mods[0] == "B.pak");
        Assert.Equal("isolated", isolatedB.Reason);
    }

    [Fact]
    public void Build_HonorsUserGroups()
    {
        var rules = new PlannerRules();
        rules.Groups.Add(new List<string> { "X.pak", "Y.pak" });

        var plan = DeploymentPlanner.Build(
            new[] { "X.pak", "Y.pak" },
            Array.Empty<IReadOnlyList<string>>(),
            Array.Empty<DependencyEdge>(),
            rules);

        var group = plan.Groups.Single(g => g.Mods.Contains("X.pak"));
        Assert.Contains("Y.pak", group.Mods);
        Assert.Equal("user_group", group.Reason);
    }
}
