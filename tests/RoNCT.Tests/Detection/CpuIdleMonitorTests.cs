using RoNCT.Core.Detection;

namespace RoNCT.Tests.Detection;

public sealed class CpuIdleMonitorTests
{
    [Fact]
    public void ConfirmsMenuOnlyAfterLowCpuPersistsLongEnough()
    {
        var monitor = new CpuIdleMonitor(
            thresholdPercent: 8,
            requiredConsecutiveSamples: 3,
            confirmAfter: TimeSpan.FromSeconds(3));
        var start = new DateTime(2026, 9, 7, 0, 0, 0, DateTimeKind.Utc);

        for (var second = 1; second <= 5; second++)
        {
            monitor.Sample(cpuPercent: 2.0, timestamp: start.AddSeconds(second));
        }

        Assert.False(monitor.MenuConfirmed);

        monitor.Sample(cpuPercent: 2.0, timestamp: start.AddSeconds(6));

        Assert.True(monitor.MenuConfirmed);
    }

    [Fact]
    public void BusySampleResetsIdleConfirmation()
    {
        var monitor = new CpuIdleMonitor(
            thresholdPercent: 8,
            requiredConsecutiveSamples: 3,
            confirmAfter: TimeSpan.FromSeconds(3));
        var start = new DateTime(2026, 9, 7, 0, 0, 0, DateTimeKind.Utc);

        monitor.Sample(2.0, start.AddSeconds(1));
        monitor.Sample(2.0, start.AddSeconds(2));
        monitor.Sample(2.0, start.AddSeconds(3));
        monitor.Sample(2.0, start.AddSeconds(4));
        monitor.Sample(90.0, start.AddSeconds(5));

        Assert.False(monitor.MenuConfirmed);

        monitor.Sample(2.0, start.AddSeconds(6));
        monitor.Sample(2.0, start.AddSeconds(7));
        monitor.Sample(2.0, start.AddSeconds(8));

        Assert.False(monitor.MenuConfirmed);

        monitor.Sample(2.0, start.AddSeconds(9));
        monitor.Sample(2.0, start.AddSeconds(10));
        monitor.Sample(2.0, start.AddSeconds(11));

        Assert.True(monitor.MenuConfirmed);
    }
}
