TUTORIAL_TEXT = """\
《严阵以待》Mod 兼容性测试器 v0.3.0 - 详细使用教程
作者：CurvesCat

────────────────────────────
一、这个工具是做什么的
────────────────────────────
游戏每次更新后，一些旧 .pak Mod 会导致启动崩溃或进游戏后失效。本工具会逐个把
Mod 放进游戏目录，启动游戏并自动观察：游戏主窗口是否出现、进程是否稳定、是否
崩溃/弹错。最终生成 CSV / JSON 报告，并把不可用 Mod 隔离或禁用。

推荐用法：选好文件夹后点蓝色大按钮“一键测试”。工具会自动完成：
静态体检 → 分析 Mod 依赖 → 按依赖/冲突自动分组启动游戏 → 生成最终报告。
普通用户不需要调整任何高级选项。

注意：本工具只能判断“启动 / 进主菜单阶段会不会崩”。如果某个 Mod 是进游戏后
选武器、进地图才失效，而启动阶段正常，工具无法自动发现，需要你手动进游戏验证。

────────────────────────────
二、界面说明
────────────────────────────
· v0.3 使用 Windows 11 风格的 Fluent 界面，由 Qt/PySide6 编写。
· 界面文字使用内置 MiSans 字体（免费可商用），观感接近苹方/SF。
· 底部状态栏右侧有“浅色 / 深色 / 跟随系统”切换：
  默认跟随 Windows；也可以手动固定浅色或深色，选择会自动保存。
· 左侧导航：一键测试（回到主页）、教程、打开报告目录、运行日志、还原备份、关于；
  底部语言按钮点击一下就会直接切换 中文 / English。
· 页面整体可以上下滚动；高级选项默认收起，需要时再展开。

────────────────────────────
三、开始前的准备
────────────────────────────
1. 确保 Steam 已登录，且《严阵以待》已安装。
2. 关闭正在运行的游戏（高级选项里也默认勾选“测试前关闭已运行的游戏”）。
3. 备份你的存档和 Mod。工具本身会做目录状态清单和备份，但重要数据请自行再备份一份。

────────────────────────────
四、选择要测试的 Mod
────────────────────────────
主页面第一张卡片是“Mod 文件夹”，支持两种用法：

· 候选文件夹：选择你自己准备的一批 .pak 文件所在文件夹（会递归查找子文件夹）。
  测试时文件会被临时放进游戏目录，测完会自动移除，不会残留在游戏里。

· 游戏目录内已安装：如果你直接选择游戏的 Paks 目录
  （一般是 ReadyOrNot\\Content\\Paks），工具会识别出来并显示蓝色提示，
  然后就地测试已安装的 Mod：先移到临时区，测完恢复或按设置处理。
  系统 pakchunk-Windows 文件永远不会被碰。

找不到游戏时，点“自动检测”；仍找不到就在“高级选项”里手动填写游戏根目录。

────────────────────────────
五、一键测试会自动做什么
────────────────────────────
1. 静态扫描：读取每个 .pak，找出重复/覆盖冲突。
2. 依赖分析：解析资源引用，找出“谁依赖谁”。
3. 自动分组：互相依赖的 Mod 合并成一组启动，冲突的 Mod 分开测。
4. 启动游戏并按组实测，自动点击跳过开场动画。
5. 生成报告并把不可用 Mod 移入隔离区（默认）或禁用。

测试过程中会反复弹出游戏窗口，请不要手动操作游戏；想中途停止可点“停止”。

────────────────────────────
六、高级选项说明
────────────────────────────
在“展开高级选项”里可以调整：
· 测试策略：标准隔离（默认）或严格深度（观察更久）。
· 稳定观察：游戏主窗口出现后保持稳定多少秒判“可用”，默认 35 秒。
· 启动超时：等待主窗口出现的最大时间。
· 主菜单确认：日志检测到主菜单后额外观察的秒数。
· 附加启动参数：默认 -windowed -nosplash。
· 不可用 Mod 处理：移入隔离区 / 禁用（.disabled）/ 仅记录。
· 测试前关闭已运行的游戏、测试前备份、预热一次。
· 游戏根目录：自动检测失败时手动选择。

这些设置会在下次测试时生效并自动保存。

────────────────────────────
七、N 网 API Key（可选）
────────────────────────────
主页面下方可以保存 Nexus Mods 的 Personal API Key。Key 只保存在本机配置中，
不会上传；它用于以后的可选联网依赖识别功能。是否填写都不影响一键测试。
点击“如何获取 API Key”会打开 Nexus 的密钥页面。

────────────────────────────
八、备份与还原
────────────────────────────
· 每次测试前会自动记录 Mod 目录状态，并按设置创建备份。
· 左侧导航点“还原备份”可以把备份里的非系统 Mod 还原回游戏目录。
· “完全还原”选项还会移除备份后新增的非系统 Mod，做到真正回滚。
· 测试完成后，“打开报告目录”里能看到隔离区（quarantine）和日志。

────────────────────────────
九、判定逻辑
────────────────────────────
1. 把候选 .pak 放进游戏的 Mod 目录（或就地测试已安装的 Mod）。
2. 启动游戏，等待主窗口（UnrealWindow）出现。
3. 主窗口出现后自动点击，尽量跳过开场动画，直到本轮观察结束。
4. 观察期内崩溃/退出/弹错/生成崩溃报告 → 判“不可用”。
5. 稳定时间内不退出 → 判“可用”。
6. 每组测完关闭游戏，并恢复/移除本工具移动的文件。

────────────────────────────
十、报告与日志在哪
────────────────────────────
默认报告输出到：
· 候选文件夹测试：Mod 文件夹旁边 *_test_reports
· 游戏目录内已安装：游戏目录旁边 RoN_ModCompat_Reports

里面有 mod_compat_report_*.csv / json、可用/不可用列表、
quarantine/（隔离区）和 logs/（每次启动的日志）。

调试日志：%APPDATA%\\RoNModCompatTester\\debug.log
日志按 1MB 轮转、保留 3 份历史，不会无限占空间。遇到 bug 时把 debug.log
内容发给作者即可排查。

────────────────────────────
十一、注意事项与已知限制
────────────────────────────
· 反复启动游戏会持续读写游戏文件，SSD 占用较高，建议分批测试。
· 游戏不写标准 UE 日志，无法判断“进游戏后失效”的 Mod。
· 请自行备份重要数据，使用风险自负。
"""

TUTORIAL_TEXT_EN = """\
Ready or Not Mod Compatibility Tester v0.3.0 - Detailed Tutorial
Author: CurvesCat

------------------------------------------------------------
1. What this tool does
------------------------------------------------------------
After each game update, some old .pak mods may crash at startup or break
in-game. This tool deploys each mod into the game folder, launches the game,
and watches whether the main window appears, the process stays stable, or it
crashes. It then writes CSV / JSON reports and quarantines or disables
unusable mods.

Recommended usage: choose a Mod folder and click the big blue "One-click test"
button. The tool runs a static scan, analyzes dependencies, groups mods by
dependency/conflict, launches the game per group, and writes a final report.
Normal users do not need to touch the advanced options.

Note: it can only detect "startup / main-menu stage crashes". If a mod only
breaks after entering a mission or equipping a weapon, it cannot be detected
automatically; test it manually in-game.

------------------------------------------------------------
2. Interface
------------------------------------------------------------
The v0.3 GUI uses a Windows 11 Fluent-style interface built with Qt/PySide6.
The UI uses the bundled MiSans font (free for commercial use), with a look
close to Apple's PingFang / SF.
The status bar has a Light / Dark / Follow system switcher. By default it
follows Windows automatically; you can also fix light or dark manually.
Left navigation: One-click test (home), Tutorial, Open report folder,
Run log, Restore backup, About. The button at the bottom toggles directly
between Chinese and English. The whole page scrolls; advanced options are
collapsed by default.

------------------------------------------------------------
3. Before you start
------------------------------------------------------------
1. Make sure Steam is logged in and Ready or Not is installed.
2. Close any running game (or keep "Close running game before testing" enabled).
3. Back up your saves and mods. The tool also creates a manifest and backup.

------------------------------------------------------------
4. Choosing the mods to test
------------------------------------------------------------
Candidate folder: choose a folder containing .pak files (subfolders are
searched). Files are temporarily deployed into the game folder during tests
and removed afterwards.

Installed in game folder: if you select the game's Paks folder directly
(usually ReadyOrNot\\Content\\Paks), the tool shows a blue notice and tests
installed mods in place: they are moved to a temporary area, tested, then
restored or handled. System pakchunk-Windows files are never touched.

If the game is not detected, click "Auto detect". If that still fails, set the
game root manually under "Advanced options".

------------------------------------------------------------
5. What one-click testing does
------------------------------------------------------------
1. Static scan: reads every .pak and finds duplicate/overwrite conflicts.
2. Dependency analysis: parses asset references to find "who needs whom".
3. Automatic planning: interdependent mods launch together; conflicts stay
   isolated.
4. Real game launches per group, auto-clicking to skip the intro.
5. Report generation; unusable mods are quarantined (default) or disabled.

The game window opens several times. Do not operate the game manually while
testing. Click "Stop" to cancel.

------------------------------------------------------------
6. Advanced options
------------------------------------------------------------
Under "Advanced options" you can adjust: test strategy (standard isolated or
strict deep), stable watch seconds, startup timeout, menu confirm seconds,
extra launch arguments (default -windowed -nosplash), handling of unusable
mods (quarantine / disable / record only), closing a running game before
testing, pre-test backup, warm-up launch, and the game root folder.
Changes are saved and apply to the next test.

------------------------------------------------------------
7. Nexus API key (optional)
------------------------------------------------------------
You can save a Nexus Mods Personal API key at the bottom of the page. The key
is stored only on this computer and is used by the optional online dependency
feature; whether you fill it in or not, one-click testing works normally.
Click "How to get an API key" to open the Nexus key page.

------------------------------------------------------------
8. Backup and restore
------------------------------------------------------------
The Mod folder state is recorded before each test and a backup is created
according to the settings. "Restore backup" in the left navigation copies the
backed-up non-system mods back to the game folder. "Full restore" also removes
non-system mods added after the backup for a true rollback.

------------------------------------------------------------
9. Verdict logic
------------------------------------------------------------
1. A candidate .pak is deployed into the game Mod folder (or installed mods
   are tested in place).
2. The game is launched and the main window (UnrealWindow) is awaited.
3. The tool auto-clicks to skip the intro until the observation ends.
4. Crash / exit / error dialog / new crash report during the window =
   unusable.
5. Staying stable for the configured time = usable.
6. The game is closed after each group and moved files are restored/removed.

------------------------------------------------------------
10. Reports and logs
------------------------------------------------------------
Default report locations:
- Candidate-folder tests: *_test_reports next to the Mod folder.
- Installed tests: RoN_ModCompat_Reports next to the game directory.

They contain mod_compat_report_*.csv/json, usable/unusable text lists,
quarantine/ and logs/.

Debug log: %APPDATA%\\RoNModCompatTester\\debug.log
The log rotates at 1 MB and keeps 3 old files. When reporting a bug, send the
debug.log content to the author.

------------------------------------------------------------
11. Notes and limitations
------------------------------------------------------------
Repeated game launches read large game files (high SSD usage); test in batches.
The game does not write a standard UE log, so in-game breakage cannot be seen.
Back up important data; use at your own risk.
"""
