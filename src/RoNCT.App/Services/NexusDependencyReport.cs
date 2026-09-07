using RoNCT.Core.Plan;

namespace RoNCT.App.Services;

public sealed class NexusDependencyRow
{
    public NexusDependencyRow(
        string pakName,
        string sourceMod,
        string status,
        string requirement,
        string notes,
        string url)
    {
        PakName = pakName;
        SourceMod = sourceMod;
        Status = status;
        Requirement = requirement;
        Notes = notes;
        Url = url;
    }

    public string PakName { get; }
    public string SourceMod { get; }
    public string Status { get; }
    public string Requirement { get; }
    public string Notes { get; }
    public string Url { get; }
}

public sealed class NexusDependencyReport
{
    public NexusDependencyReport(
        IReadOnlyList<NexusDependencyRow> rows,
        IReadOnlyList<DependencyEdge> dependencyEdges,
        int errors)
    {
        Rows = rows;
        DependencyEdges = dependencyEdges;
        Errors = errors;
    }

    public IReadOnlyList<NexusDependencyRow> Rows { get; }
    public IReadOnlyList<DependencyEdge> DependencyEdges { get; }
    public int Errors { get; }
}

public static class NexusDependencyReportBuilder
{
    public static async Task<NexusDependencyReport> BuildAsync(
        string apiKey,
        IReadOnlyList<NexusModInfo> confirmedMods,
        IReadOnlyList<NexusModInfo> localMods,
        CancellationToken cancellationToken = default)
    {
        var ownedIds = confirmedMods
            .Where(info => info.ModId is not null)
            .Select(info => info.ModId!.Value)
            .ToHashSet();
        var localIds = new HashSet<long>(ownedIds);
        foreach (var local in localMods)
        {
            if (local.ModId is not null)
            {
                localIds.Add(local.ModId.Value);
            }
        }

        var localPakByModId = new Dictionary<long, string>();
        foreach (var info in confirmedMods.Concat(localMods))
        {
            if (info.ModId is not null &&
                !string.IsNullOrWhiteSpace(info.PakName) &&
                !localPakByModId.ContainsKey(info.ModId.Value))
            {
                localPakByModId[info.ModId.Value] = info.PakName;
            }
        }

        var rows = new List<NexusDependencyRow>();
        var edges = new List<DependencyEdge>();
        var errors = 0;

        foreach (var source in confirmedMods
                     .Where(info => info.ModId is not null)
                     .DistinctBy(info => info.ModId))
        {
            if (source.ModId is null)
            {
                continue;
            }

            NexusModRequirements requirements;
            try
            {
                requirements = await NexusClient.GetModRequirementsAsync(
                    apiKey, source.ModId.Value, cancellationToken);
            }
            catch (Exception exc)
            {
                errors++;
                rows.Add(new NexusDependencyRow(
                    source.PakName ?? string.Empty,
                    source.Name ?? string.Empty,
                    "error",
                    exc.Message,
                    string.Empty,
                    string.Empty));
                continue;
            }

            foreach (var requirement in requirements.Items)
            {
                string status;
                if (requirement.IsDlc)
                {
                    status = "dlc";
                }
                else if (requirement.External)
                {
                    status = "external";
                }
                else if (requirement.ModId is not null &&
                         ownedIds.Contains(requirement.ModId.Value))
                {
                    status = "installed";
                }
                else if (requirement.ModId is not null &&
                         localIds.Contains(requirement.ModId.Value))
                {
                    status = "local_candidate";
                }
                else
                {
                    status = "missing";
                }

                rows.Add(new NexusDependencyRow(
                    source.PakName ?? string.Empty,
                    source.Name ?? string.Empty,
                    status,
                    requirement.Name ?? string.Empty,
                    requirement.Notes ?? string.Empty,
                    requirement.Url ?? string.Empty));

                if (requirement.ModId is not null &&
                    localPakByModId.TryGetValue(requirement.ModId.Value, out var targetPak) &&
                    !string.IsNullOrWhiteSpace(source.PakName) &&
                    !string.Equals(source.PakName, targetPak, StringComparison.OrdinalIgnoreCase))
                {
                    edges.Add(new DependencyEdge(
                        source.PakName.ToLowerInvariant(),
                        targetPak.ToLowerInvariant()));
                }
            }
        }

        return new NexusDependencyReport(rows, edges, errors);
    }
}
