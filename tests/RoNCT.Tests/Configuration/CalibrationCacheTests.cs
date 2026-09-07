using RoNCT.Core.Configuration;

namespace RoNCT.Tests.Configuration;

public sealed class CalibrationCacheTests
{
    private static readonly DateTime Now =
        new(2026, 9, 7, 12, 0, 0, DateTimeKind.Utc);

    [Fact]
    public void MissingRecordRequiresCalibration()
    {
        var config = new AppConfig();

        Assert.False(CalibrationCache.IsCurrent(
            config,
            @"C:\Game\ReadyOrNot.exe",
            "-windowed",
            Now));
    }

    [Fact]
    public void FreshRecordForSameExeAndArgsSkipsCalibration()
    {
        var config = new AppConfig();
        CalibrationCache.Mark(
            config,
            @"C:\Game\ReadyOrNot.exe",
            "-windowed",
            Now);

        Assert.True(CalibrationCache.IsCurrent(
            config,
            @"C:\Game\ReadyOrNot.exe",
            "-windowed",
            Now.AddHours(1)));
    }

    [Fact]
    public void ChangedExeOrArgsRequiresCalibration()
    {
        var config = new AppConfig();
        CalibrationCache.Mark(
            config,
            @"C:\Game\ReadyOrNot.exe",
            "-windowed",
            Now);

        Assert.False(CalibrationCache.IsCurrent(
            config,
            @"D:\Game\ReadyOrNot.exe",
            "-windowed",
            Now.AddHours(1)));
        Assert.False(CalibrationCache.IsCurrent(
            config,
            @"C:\Game\ReadyOrNot.exe",
            "-fullscreen",
            Now.AddHours(1)));
    }

    [Fact]
    public void RecordOlderThanSevenDaysRequiresCalibration()
    {
        var config = new AppConfig();
        CalibrationCache.Mark(
            config,
            @"C:\Game\ReadyOrNot.exe",
            "-windowed",
            Now);

        Assert.False(CalibrationCache.IsCurrent(
            config,
            @"C:\Game\ReadyOrNot.exe",
            "-windowed",
            Now.AddDays(7)));
    }
}
