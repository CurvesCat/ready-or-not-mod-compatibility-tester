namespace RoNCT.App.Pages;

public sealed class NexusResultRow
{
    public NexusResultRow(
        string fileName,
        string status,
        string detail,
        string author,
        string url)
    {
        FileName = fileName;
        Status = status;
        Detail = detail;
        Author = author;
        Url = url;
    }

    public string FileName { get; }
    public string Status { get; }
    public string Detail { get; }
    public string Author { get; }
    public string Url { get; }
}
