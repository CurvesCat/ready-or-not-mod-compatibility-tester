using System.Security.Cryptography;
using System.Text;

namespace RoNCT.Core.Analysis;

public enum StaticConflictKind
{
    Duplicate,
    Overwrite,
}

public sealed record ConflictProvider(string PakName, string? Sha256);

public sealed record StaticConflict(
    string InternalPath,
    StaticConflictKind Kind,
    IReadOnlyList<ConflictProvider> Providers);

public static class StaticConflictAnalyzer
{
    public static IReadOnlyList<StaticConflict> Analyze(
        IReadOnlyList<PakInventory> inventories,
        Func<string, string, byte[]> readContent)
    {
        var byPath = new Dictionary<string, List<PakInventory>>(
            StringComparer.OrdinalIgnoreCase);
        foreach (var inventory in inventories)
        {
            foreach (var path in inventory.InternalPaths)
            {
                if (!byPath.TryGetValue(path, out var owners))
                {
                    owners = new List<PakInventory>();
                    byPath[path] = owners;
                }
                owners.Add(inventory);
            }
        }

        var conflicts = new List<StaticConflict>();
        foreach (var path in byPath.Keys.OrderBy(p => p, StringComparer.OrdinalIgnoreCase))
        {
            var owners = byPath[path];
            if (owners.Count < 2)
            {
                continue;
            }

            var providers = new List<ConflictProvider>();
            var hashes = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (var owner in owners)
            {
                byte[]? content = null;
                try
                {
                    content = readContent(owner.PakPath, path);
                }
                catch
                {
                    content = null;
                }
                var sha = content is null ? null : Sha256(content);
                providers.Add(new ConflictProvider(owner.FileName, sha));
                if (sha is not null)
                {
                    hashes.Add(sha);
                }
            }

            var kind = hashes.Count <= 1
                ? StaticConflictKind.Duplicate
                : StaticConflictKind.Overwrite;
            conflicts.Add(new StaticConflict(path, kind, providers));
        }
        return conflicts;
    }

    public static string Sha256(byte[] data) =>
        Convert.ToHexString(SHA256.HashData(data)).ToLowerInvariant();
}
