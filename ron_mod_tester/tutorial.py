TUTORIAL_TEXT = """\
《严阵以待》Mod 兼容性测试器 v0.2.1 - 详细使用教程
作者：CurvesCat

────────────────────────────
一、这个工具是做什么的
────────────────────────────
游戏每次更新后，一些旧 .pak Mod 会导致启动崩溃或进游戏后失效。本工具会逐个把 Mod
放进游戏目录，启动游戏并自动观察：游戏主窗口是否出现、进程是否稳定、是否崩溃/弹错。
最终生成 CSV / JSON 报告，并把不可用 Mod 隔离、禁用或删除。

推荐用法：点顶部“一键测试”，工具会自动完成静态体检 → 分析 Mod 依赖 →
按依赖/冲突自动分组启动游戏 → 生成最终报告。普通用户不需要调整任何高级选项；
需要微调观察时间、备份或处理方式时，再点“展开高级选项”。

注意：本工具只能判断“启动 / 进主菜单阶段会不会崩”。如果某个 Mod 是进游戏后选武器、
进地图才失效，而启动阶段正常，工具无法自动发现，需要你手动进游戏验证。

────────────────────────────
二、语言与界面
────────────────────────────
· 首次启动会询问选择中文或 English，之后可在顶部“语言 / Language”按钮随时切换。
· 界面使用苹果风浅色主题；如果窗口被屏幕截断，可以拖大，程序会保留更大默认尺寸。

────────────────────────────
三、开始前的准备
────────────────────────────
1. 确保 Steam 已登录，且《严阵以待》已安装。
2. 关闭正在运行的游戏（或勾选“测试前关闭已运行的游戏”）。
3. 备份你的存档和 Mod。工具本身也会做目录状态清单和备份，但重要数据请自行再备份一份。

────────────────────────────
四、测试来源怎么选
────────────────────────────
· 候选文件夹：测试你自己准备的一批 .pak 文件。
  - 可以直接选一个文件夹（会递归查找里面的 .pak）。
  - 也可以点“添加 .pak 文件…”单独选几个文件。
  - 用“排除文件…”可以把不想测的文件排除掉。
  - “清空选择”会清掉手动添加和排除的文件。

· 游戏目录内已安装：直接测试当前已经装进游戏 Paks 目录的 Mod。
  - 工具会先把这些 Mod 移到临时区，逐个测完后再恢复/处理，系统 pakchunk-Windows 不会碰。

────────────────────────────
五、自动检测与自动测时
────────────────────────────
1. 点“自动检测”会自动找到游戏根目录、可执行文件（ReadyOrNotSteam-Win64-Shipping.exe）
   和 Mod 安装目录（一般是 ReadyOrNot\\Content\\Paks）；检测不到就手动“浏览…”选择。
2. 建议先点“自动测时”：它会启动一次游戏、自动点击跳过开场动画，并测量“主窗口出现耗时”
   与“到主菜单（空闲）耗时”，然后把建议的“稳定观察”自动填好并保存。

────────────────────────────
六、测试策略
────────────────────────────
· 标准隔离（默认）：逐个 Mod 测试，适合日常排查。
· 严格深度：逐个测试，观察更久、不提前结束，适合重要 Mod 最终确认。

────────────────────────────
七、关键设置说明
────────────────────────────
· 稳定观察：游戏主窗口出现后，保持稳定多少秒就判“可用”。默认 35 秒。
· 启动超时：等待游戏主窗口出现的最大时间，超过则判“错误 / 卡住”。
· 主菜单确认：如果日志里检测到主菜单标记，再观察多少秒（此游戏一般不写日志，可忽略）。
· 附加启动参数：默认 -windowed -nosplash，让游戏以窗口模式启动、跳过启动画面。
· 测试前预热一次：先不带 Mod 启动一次，验证游戏本体能正常启动，并暖缓存。
· 备份设置：可设置“测试前备份 Mod 目录”、自定义备份目录、单文件大小上限和总大小上限。

────────────────────────────
八、备份与还原
────────────────────────────
· 备份默认放在软件所在目录的 backup 文件夹（未自定义时），每次测试覆盖为最新状态。
· “打开备份目录”可以直接查看备份；“还原备份”可以把备份里的非系统 Mod 还原回游戏目录。
· “还原备份”支持勾选“完全还原”：同时移除备份后新增的非系统 Mod，做到真正回滚。

────────────────────────────
九、不可用 Mod 怎么处理
────────────────────────────
· 移入隔离区（默认）：把不可用 Mod 移到报告目录的 quarantine 文件夹。
· 禁用：把文件重命名为 xxx.pak.disabled，游戏不会再加载，但文件保留。
· 删除：永久删除源文件（开始前会二次确认）。
· 仅记录：只写报告，不移动/删除。

────────────────────────────
十、判定逻辑
────────────────────────────
1. 复制候选 .pak 到游戏 Mod 目录。
2. 启动游戏，等待游戏主窗口（UnrealWindow）出现。
3. 主窗口出现后自动持续点击，尽量跳过开场动画，直到本轮观察结束。
4. 主窗口出现后观察“稳定观察”秒；期间崩溃/退出/弹错/生成崩溃报告就判“不可用”。
5. 稳定时间内不退出，判“可用”。
6. 每次测完都会关闭游戏，并移除本工具刚添加的文件。

────────────────────────────
十一、报告与日志在哪
────────────────────────────
默认报告输出到 Mod 文件夹旁边的 *_test_reports 目录：
· mod_compat_report_*.csv / json
· 可用_mods.txt / 不可用_mods.txt
· quarantine/（隔离的 Mod）
· logs/（每次启动的日志）

调试日志：软件会自动把“用户操作 + 异常堆栈”写入：
%APPDATA%\\RoNModCompatTester\\debug.log
日志按 1MB 轮转、保留 3 份历史，自动删除最旧，不会无限占空间。
遇到 bug 时点“打开日志”，把 debug.log 的内容发给作者即可排查。

────────────────────────────
十二、注意事项与已知限制
────────────────────────────
· 反复启动游戏会持续读写游戏大文件，SSD 占用较高，建议分批测试。
· 游戏不写标准 UE 日志，无法据此判断“进游戏后失效”的 Mod。
· 主菜单标记可能识别不到，此时自动回退到固定稳定观察。
· 请自行备份重要数据，使用风险自负。
"""

TUTORIAL_TEXT_EN = """\
Ready or Not Mod Compatibility Tester v0.2.1 - Detailed Tutorial
Author: CurvesCat

------------------------------------------------------------
1. What this tool does
------------------------------------------------------------
After each game update, some old .pak mods may crash at startup or break
in-game. This tool copies each mod into the game folder one by one, launches
the game, and watches whether the game window appears, stays stable, or
crashes. It then writes CSV / JSON reports and quarantines, disables, or
deletes unusable mods.

Recommended usage: click "One-click test" at the top. The tool will run a static
scan, analyze mod dependencies, group dependent/conflicting mods, launch the
game per group, and write a final report. Normal users do not need to touch the
advanced options; expand them only when you want to fine-tune timing, backups,
or how unusable mods are handled.

Note: it can only detect "startup / main-menu stage crashes". If a mod only
breaks after entering a mission or equipping a weapon, this tool cannot detect
that automatically; you need to test it manually in-game.

------------------------------------------------------------
2. Language and UI
------------------------------------------------------------
The language is asked on first launch and can be switched any time from the
"Language / 语言" button at the top. The UI uses a clean Apple-style theme;
if your screen clips the window, enlarge it - the default window is already
sized to show the progress bar and lower panels.

------------------------------------------------------------
3. Before you start
------------------------------------------------------------
1. Make sure Steam is logged in and Ready or Not is installed.
2. Close any running game (or enable "Close running game before testing").
3. Back up your saves and mods. The tool also creates a manifest and backup.

------------------------------------------------------------
4. Test source
------------------------------------------------------------
Candidate folder: test a batch of .pak files you prepared.
  - Choose a folder (it searches subfolders for .pak files).
  - Or click "Add .pak files..." to select individual files.
  - Use "Exclude files..." to skip files you do not want to test.
  - "Clear selection" resets the added/excluded files.

Installed in game folder: test mods already placed in the game Paks folder.
  - The tool moves them to a temporary area, tests them, then restores or
    handles them. System pakchunk-Windows files are never touched.

------------------------------------------------------------
5. Auto detect and Auto timing
------------------------------------------------------------
1. Click "Auto detect" to find the game root, executable, and Mod folder
   (usually ReadyOrNot\\Content\\Paks). If detection fails, pick them manually.
2. It is recommended to click "Auto timing" first: it launches the game once,
   auto-clicks to skip the intro, measures the window-appearance time and the
   time until the menu (idle) is reached, then fills and saves the suggested
   "Stable watch" value.

------------------------------------------------------------
6. Test strategy
------------------------------------------------------------
Standard isolated (default): test one mod at a time.
Strict deep: test one mod at a time with a longer observation window.

------------------------------------------------------------
7. Key settings
------------------------------------------------------------
Stable watch: how long the game window must stay stable to be "usable" (35 s).
Startup timeout: how long to wait for the game window before "error".
Menu confirm: extra seconds after a menu marker is detected (rarely used).
Extra launch args: default -windowed -nosplash.
Warm up once: launch once without mods to verify the base game and warm caches.
Backup settings: enable pre-test backup, choose the backup folder, and set
the single-file / total size limits.

------------------------------------------------------------
8. Backup and restore
------------------------------------------------------------
By default the backup is stored in a "backup" folder next to the executable
(or your custom folder) and is overwritten on each run. "Open backup folder"
shows the backup; "Restore backup" copies the non-system mods back to the game
folder. Check "Full restore" to also remove non-system mods added after the
backup for a true rollback.

------------------------------------------------------------
9. Handling unusable mods
------------------------------------------------------------
Move to quarantine (default), Disable (.disabled rename), Delete, or Record only.

------------------------------------------------------------
10. Verdict logic
------------------------------------------------------------
1. Copy a candidate .pak into the game Mod folder.
2. Launch the game and wait for its main window (UnrealWindow).
3. The tool keeps clicking to skip the intro until the observation ends.
4. Observe for "Stable watch" seconds; crash / exit / error dialog / new crash
   report = unusable.
5. If it stays stable, it is marked usable.
6. The game is closed and the tool's added file is removed after each test.

------------------------------------------------------------
11. Reports and logs
------------------------------------------------------------
Reports go to *_test_reports next to the Mod folder by default:
mod_compat_report_*.csv/json, usable_mods.txt, unusable_mods.txt,
quarantine/, logs/.

Debug log: the program automatically records user actions and exception
stack traces to:
%APPDATA%\\RoNModCompatTester\\debug.log
The log rotates at 1 MB and keeps 3 old files, automatically deleting the
oldest, so it never grows without bound. When reporting a bug, click
"Open log" and send the debug.log content to the author.

------------------------------------------------------------
12. Notes and limitations
------------------------------------------------------------
Repeated game launches read large game files (high SSD usage); test in batches.
The game does not write a standard UE log, so in-game breakage cannot be seen.
Menu markers may not be detected; the tool falls back to the stable window.
Back up important data; use at your own risk.
"""
