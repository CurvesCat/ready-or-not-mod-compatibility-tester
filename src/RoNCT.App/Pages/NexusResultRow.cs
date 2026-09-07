using System.ComponentModel;
using System.Runtime.CompilerServices;
using RoNCT.App.Services;

namespace RoNCT.App.Pages;

public sealed class NexusResultRow : INotifyPropertyChanged
{
    public NexusResultRow(
        string fileName,
        string md5,
        long? modId,
        string status,
        string detail,
        string author,
        string url,
        IReadOnlyList<NexusModInfo>? candidates = null)
    {
        FileName = fileName;
        Md5 = md5;
        ModId = modId;
        _status = status;
        _detail = detail;
        _author = author;
        _url = url;
        Candidates = candidates ?? Array.Empty<NexusModInfo>();
    }

    public string FileName { get; }
    public string Md5 { get; }
    public long? ModId { get; }
    public IReadOnlyList<NexusModInfo> Candidates { get; }

    private string _status;
    private string _detail;
    private string _author;
    private string _url;

    public string Status
    {
        get => _status;
        set => SetField(ref _status, value);
    }

    public string Detail
    {
        get => _detail;
        set => SetField(ref _detail, value);
    }

    public string Author
    {
        get => _author;
        set => SetField(ref _author, value);
    }

    public string Url
    {
        get => _url;
        set => SetField(ref _url, value);
    }

    public event PropertyChangedEventHandler? PropertyChanged;

    private void SetField<T>(
        ref T field,
        T value,
        [CallerMemberName] string? propertyName = null)
    {
        if (EqualityComparer<T>.Default.Equals(field, value))
        {
            return;
        }
        field = value;
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
    }
}
