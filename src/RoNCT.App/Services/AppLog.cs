namespace RoNCT.App.Services;

public static class AppLog
{
    private static readonly object Gate = new();

    public static string LogFile =>
        Path.Combine(AppSettings.DataDirectory, "logs", "debug.log");

    public static void Log(string message)
        => Write("INFO", message);

    public static void UserAction(string action)
        => Write("USER_ACTION", action);

    public static void Error(string message)
        => Write("ERROR", message);

    private static void Write(string level, string message)
    {
        try
        {
            lock (Gate)
            {
                Directory.CreateDirectory(Path.GetDirectoryName(LogFile)!);
                var line = $"{DateTime.Now:yyyy-MM-dd HH:mm:ss.fff} {level} {message}{Environment.NewLine}";
                File.AppendAllText(LogFile, line);
            }
        }
        catch
        {
            // Never let logging break the app.
        }
    }
}
