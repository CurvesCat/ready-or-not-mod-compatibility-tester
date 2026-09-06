using System.Text;
using System.Text.Json;

namespace RoNCT.Core.Reporting;

public static class ReportWriter
{
    public static string ReportPath(string baseDir, string prefix, string extension)
    {
        Directory.CreateDirectory(baseDir);
        return Path.Combine(baseDir, $"{prefix}_{DateTime.Now:yyyyMMdd-HHmmss}.{extension}");
    }

    public static string WriteJson<T>(string baseDir, string prefix, T data)
    {
        var path = ReportPath(baseDir, prefix, "json");
        File.WriteAllText(
            path,
            JsonSerializer.Serialize(data, new JsonSerializerOptions { WriteIndented = true }));
        return path;
    }

    public static string WriteCsv(
        string baseDir,
        string prefix,
        IReadOnlyList<IReadOnlyList<string>> rows)
    {
        var path = ReportPath(baseDir, prefix, "csv");
        var builder = new StringBuilder();
        foreach (var row in rows)
        {
            builder.AppendLine(string.Join(",", row.Select(EscapeCsvField)));
        }
        File.WriteAllText(path, builder.ToString());
        return path;
    }

    private static string EscapeCsvField(string value)
    {
        if (value.Contains(',') || value.Contains('"') || value.Contains('\n'))
        {
            return $"\"{value.Replace("\"", "\"\"")}\"";
        }
        return value;
    }
}
