namespace RoNCT.Core.Plan;

public sealed record DependencyEdge(string FromMod, string ToMod);

public sealed class PlannerModRule
{
    public List<string> Requires { get; } = new();
    public List<string> GroupWith { get; } = new();
}

public sealed class PlannerRules
{
    public Dictionary<string, PlannerModRule> Mods { get; } = new(
        StringComparer.OrdinalIgnoreCase);
    public List<List<string>> Groups { get; } = new();
}

public sealed class DeployGroup
{
    public DeployGroup(string groupId, IReadOnlyList<string> mods, string reason, List<string> evidence)
    {
        GroupId = groupId;
        Mods = mods;
        Reason = reason;
        Evidence = evidence;
    }

    public string GroupId { get; }
    public IReadOnlyList<string> Mods { get; }
    public string Reason { get; }
    public List<string> Evidence { get; }
}

public sealed class DeployPlan
{
    public DeployPlan(
        IReadOnlyList<DeployGroup> groups,
        IReadOnlyList<IReadOnlyList<string>> conflictPairs,
        IReadOnlyList<string> warnings)
    {
        Groups = groups;
        ConflictPairs = conflictPairs;
        Warnings = warnings;
    }

    public IReadOnlyList<DeployGroup> Groups { get; }
    public IReadOnlyList<IReadOnlyList<string>> ConflictPairs { get; }
    public IReadOnlyList<string> Warnings { get; }
}

public static class DeploymentPlanner
{
    public static DeployPlan Build(
        IReadOnlyList<string> scannedMods,
        IReadOnlyList<IReadOnlyList<string>> conflictPairs,
        IReadOnlyList<DependencyEdge> dependencyEdges,
        PlannerRules? rules = null)
    {
        rules ??= new PlannerRules();
        var scanned = scannedMods.ToHashSet(StringComparer.OrdinalIgnoreCase);

        // Keep conflicts whose both mods were scanned.
        var parsedConflictPairs = conflictPairs
            .Select(pair => pair.Where(scanned.Contains).ToList())
            .Where(pair => pair.Count >= 2)
            .ToList();
        var conflictModSet = parsedConflictPairs
            .SelectMany(pair => pair)
            .ToHashSet(StringComparer.OrdinalIgnoreCase);

        var requires = new Dictionary<string, List<string>>(StringComparer.OrdinalIgnoreCase);
        var names = scanned.ToList();
        names.Sort(StringComparer.OrdinalIgnoreCase);

        foreach (var edge in dependencyEdges)
        {
            if (scanned.Contains(edge.FromMod) && scanned.Contains(edge.ToMod))
            {
                if (!requires.TryGetValue(edge.FromMod, out var list))
                {
                    list = new List<string>();
                    requires[edge.FromMod] = list;
                }
                if (!list.Contains(edge.ToMod, StringComparer.OrdinalIgnoreCase))
                {
                    list.Add(edge.ToMod);
                }
            }
        }

        foreach (var (mod, rule) in rules.Mods)
        {
            foreach (var req in rule.Requires)
            {
                if (scanned.Contains(mod) && scanned.Contains(req))
                {
                    if (!requires.TryGetValue(mod, out var list))
                    {
                        list = new List<string>();
                        requires[mod] = list;
                    }
                    if (!list.Contains(req, StringComparer.OrdinalIgnoreCase))
                    {
                        list.Add(req);
                    }
                }
            }
        }

        var parent = names.ToDictionary(name => name, name => name, StringComparer.OrdinalIgnoreCase);

        string Find(string item)
        {
            var root = item;
            while (parent[root] != root)
            {
                root = parent[root];
            }
            while (parent[item] != root)
            {
                var next = parent[item];
                parent[item] = root;
                item = next;
            }
            return root;
        }

        void Union(string a, string b)
        {
            var ra = Find(a);
            var rb = Find(b);
            if (ra != rb)
            {
                parent[rb] = ra;
            }
        }

        foreach (var (source, targets) in requires)
        {
            foreach (var target in targets)
            {
                Union(source, target);
            }
        }

        foreach (var group in rules.Groups)
        {
            var present = group.Where(scanned.Contains).ToList();
            for (var i = 1; i < present.Count; i++)
            {
                Union(present[0], present[i]);
            }
        }
        foreach (var (mod, rule) in rules.Mods)
        {
            var present = new[] { mod }.Concat(rule.GroupWith).Where(scanned.Contains).ToList();
            for (var i = 1; i < present.Count; i++)
            {
                Union(present[0], present[i]);
            }
        }

        var components = new Dictionary<string, List<string>>(StringComparer.OrdinalIgnoreCase);
        foreach (var name in names)
        {
            var root = Find(name);
            if (!components.TryGetValue(root, out var list))
            {
                list = new List<string>();
                components[root] = list;
            }
            list.Add(name);
        }
        var orderedComponents = components.Values
            .Select(c => c.OrderBy(n => n, StringComparer.OrdinalIgnoreCase).ToList())
            .OrderBy(c => c[0], StringComparer.OrdinalIgnoreCase)
            .ThenBy(c => c.Count)
            .ToList();

        var warnings = new List<string>();
        var groups = new List<DeployGroup>();
        for (var index = 0; index < orderedComponents.Count; index++)
        {
            var component = orderedComponents[index];
            string reason;
            var evidence = new List<string>();

            if (component.Count == 1)
            {
                reason = "isolated";
            }
            else
            {
                var reasons = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                foreach (var source in component)
                {
                    if (requires.ContainsKey(source))
                    {
                        reasons.Add("dependency");
                    }
                }
                foreach (var group in rules.Groups)
                {
                    if (group.Where(scanned.Contains).Count(n => component.Contains(n, StringComparer.OrdinalIgnoreCase)) > 1)
                    {
                        reasons.Add("user_group");
                    }
                }
                foreach (var (mod, rule) in rules.Mods)
                {
                    if (rule.GroupWith.Any(g =>
                            component.Contains(mod, StringComparer.OrdinalIgnoreCase) &&
                            component.Contains(g, StringComparer.OrdinalIgnoreCase)))
                    {
                        reasons.Add("user_group");
                    }
                }
                reason = reasons.Contains("user_group")
                    ? "user_group"
                    : reasons.Contains("dependency") ? "dependency" : "strong_dependency";

                foreach (var source in component)
                {
                    if (requires.TryGetValue(source, out var targets))
                    {
                        evidence.AddRange(
                            targets
                                .Where(component.Contains)
                                .Select(target => $"{source} requires {target}"));
                    }
                }
            }

            groups.Add(new DeployGroup($"g{index + 1}", component, reason, evidence));
        }

        return new DeployPlan(groups, parsedConflictPairs, warnings);
    }
}
