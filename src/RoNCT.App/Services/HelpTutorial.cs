namespace RoNCT.App.Services;

/// <summary>
/// Detailed bilingual guide shown from the Help button in the title bar.
/// </summary>
public static class HelpTutorial
{
    public static string For(string language) =>
        language == Localizer.Chinese ? Chinese : English;

    private const string Chinese = """
        1. 选择要测试的 Mod
        「选择文件夹」：加入整个 Mod 文件夹，软件会自动过滤出其中的 .pak。
        「选择 Mod 文件」：只加入一个或多个 .pak。
        「自动检测」：自动定位游戏默认的 Mod 目录，适合刚安装游戏时使用。
        「清除」：清空当前选择。

        2. 一键测试
        点「一键测试」后，软件会自动备份 Mod 目录，按计划把待测 Mod 放入游戏，
        启动 Ready or Not，用计时与日志判断结果，测试后恢复目录并生成报告。
        如果「测试前分析依赖」已开启，会先按依赖自动分组再开始测试。
        被判不可用的 Mod 会按高级选项的设置移到隔离区或直接删除。

        3. 仅分析依赖
        不启动游戏，先分析各 Mod 之间的资产引用和冲突，结果分为四个页签：
        依赖关系、未解析引用、解析错误、测试分组。确认分组没问题后，
        点「按分组开始一键测试」即可按分析结果测试。

        4. Nexus 识别与前置检查
        先在 Nexus 页填入你的 API Key 并保存，再点「识别当前 Mod」。
        无法精确匹配时会给出候选，选中后点「确认这个」，以后不会再问。
        已确认的 Mod 可以点「检查依赖」，列出缺失或已安装的前置；
        若本机可以组成依赖分组，还能直接按分组开始一键测试。

        5. 备份、还原与隔离区
        「备份与还原」页可以创建备份、还原并回滚，或删除旧备份。
        测试中被判不可用的 Mod 会出现在「隔离区」，可打开目录查看，
        确认无用后再删除或清空。

        6. 调试与反馈
        如果软件出现问题，请到「调试区」点「复制诊断信息」，
        把它连同截图一起发给开发者，能大大加快修复速度。

        7. 高级选项
        「游戏」里可修改游戏根目录、启动程序和额外参数；
        「计时」区可以调整稳定判定、启动超时和主菜单保持秒数。
        点「立即进行启动时长测试」会启动游戏实测一次，
        并把建议的数值自动填回。
        repak、dotnet、UAssetCLI 的路径在正式发行包中已经带好，
        通常不需要手动修改。

        8. 联系开发者
        邮箱：ronct.dev@icloud.com
        反馈 Bug 时请附上「调试区」复制的诊断信息。
        """;

    private const string English = """
        1. Choose the mods you want to test
        "Select folder" adds a whole mod folder; the app only keeps real .pak files.
        "Select .pak files" adds one or more individual files.
        "Auto detect" finds the default Ready or Not mod folder for you.
        "Clear" empties the current selection.

        2. One-click test
        Clicking "One-click test" backs up the mod folder, deploys the selected mods,
        launches Ready or Not, decides the result from timing and the game log, then
        restores the folder and writes a report.
        If "Analyze dependencies" is enabled, mods are grouped by dependency first.
        Mods judged unusable are moved to quarantine or deleted according to the
        Advanced options.

        3. Analyze dependencies only
        This runs without launching the game. The results are shown in four tabs:
        Dependencies, Unresolved, Errors, and Test groups. Once the groups look
        right, click "Start one-click test with these groups" to test by them.

        4. Nexus identification and requirements
        On the Nexus page, enter and save your API key, then click "Identify current
        mods". If there is no exact match, candidates are offered; choose one and
        click "Confirm this" so it is remembered.
        For confirmed mods, click "Check dependencies" to see missing or installed
        requirements. When enough local mods exist, you can also start a test run
        grouped by dependencies.

        5. Backup, restore, and quarantine
        The "Backup" page can create a backup, restore and roll back, or delete old
        backups. Unusable mods moved out of the game folder appear in "Quarantine",
        where you can open the folder, delete selected files, or empty it.

        6. Debugging and feedback
        If something goes wrong, open the "Debug" page and click "Copy diagnostics",
        then send that text together with a screenshot to the developers.

        7. Advanced options
        Under "Game" you can change the game root, executable, and extra launch
        arguments. Under "Timing" you can adjust stable seconds, the startup
        timeout, and the main-menu hold time. Click "Calibrate startup timing now"
        to launch the game once and auto-fill recommended values.
        The repak, dotnet, and UAssetCLI paths ship with the release package and
        usually do not need to be changed.

        8. Contact
        Email: ronct.dev@icloud.com
        When reporting a bug, please include the diagnostics text from the Debug page.
        """;
}
