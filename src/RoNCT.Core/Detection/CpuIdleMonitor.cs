namespace RoNCT.Core.Detection;

/// <summary>
/// Treats a sustained low-CPU period as "the game reached an idle screen
/// such as the main menu". Log markers can be missing or delayed, so the
/// calibration and test loops use this as a second detection signal.
/// </summary>
public sealed class CpuIdleMonitor
{
    private readonly double _thresholdPercent;
    private readonly int _requiredConsecutiveSamples;
    private readonly TimeSpan _confirmAfter;
    private int _lowCpuStreak;
    private DateTime? _idleSince;

    public CpuIdleMonitor(
        double thresholdPercent = 8,
        int requiredConsecutiveSamples = 3,
        TimeSpan? confirmAfter = null)
    {
        _thresholdPercent = thresholdPercent;
        _requiredConsecutiveSamples = requiredConsecutiveSamples;
        _confirmAfter = confirmAfter ?? TimeSpan.FromSeconds(3);
    }

    public bool MenuConfirmed { get; private set; }

    public void Sample(double cpuPercent, DateTime timestamp)
    {
        if (MenuConfirmed)
        {
            return;
        }

        if (cpuPercent < _thresholdPercent)
        {
            _lowCpuStreak++;
            if (_lowCpuStreak >= _requiredConsecutiveSamples)
            {
                _idleSince ??= timestamp;
                if (timestamp - _idleSince.Value >= _confirmAfter)
                {
                    MenuConfirmed = true;
                }
            }
        }
        else
        {
            _lowCpuStreak = 0;
            _idleSince = null;
        }
    }
}
