using System.Text.Json;
using RoNCT.Core.Reporting;
using Xunit;

namespace RoNCT.Tests.Reporting;

public sealed class ReportWriterTests : IDisposable
{
    private readonly string _dir = Path.Combine(
        Path.GetTempPath(), "ronct-report-tests-" + Guid.NewGuid().ToString("N"));

    public void Dispose()
    {
        try { Directory.Delete(_dir, recursive: true); }
        catch { /* best effort */ }
    }

    [Fact]
    public void WriteJson_CreatesTimestampedFile_WithRoundTrippableData()
    {
        var payload = new Dictionary<string, object>
        {
            ["summary"] = "ok",
            ["usable"] = 3,
        };

        var path = ReportWriter.WriteJson(_dir, "mod_compat_report", payload);

        Assert.True(File.Exists(path));
        Assert.Matches(@"mod_compat_report_\d{8}-\d{6}\.json$", Path.GetFileName(path));
        var loaded = JsonSerializer.Deserialize<Dictionary<string, object>>(File.ReadAllText(path));
        Assert.Equal("ok", loaded!["summary"]?.ToString());
    }

    [Fact]
    public void WriteCsv_EscapesFieldsAndWritesRows()
    {
        var rows = new List<IReadOnlyList<string>>
        {
            new[] { "name", "result" },
            new[] { "a.pak", "usable, ok" },
        };

        var path = ReportWriter.WriteCsv(_dir, "report", rows);

        Assert.True(File.Exists(path));
        var text = File.ReadAllText(path);
        Assert.Contains("name,result", text);
        Assert.Contains("\"usable, ok\"", text);
    }
}
