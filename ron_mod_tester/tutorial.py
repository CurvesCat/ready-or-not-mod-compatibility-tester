TUTORIAL_TEXT = """\
《严阵以待》Mod 兼容性测试器 v0.4.1 - 详细使用教程
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

也可以先点“仅分析资产依赖”单独看分组，确认无误后再点结果窗口里的
“用当前分组开始测试”，不会重复扫描。

注意：本工具只能判断“启动 / 进主菜单阶段会不会崩”。如果某个 Mod 是进游戏后
选武器、进地图才失效，而启动阶段正常，工具无法自动发现，需要你手动进游戏验证。

────────────────────────────
二、界面说明
────────────────────────────
· 使用 Windows 11 风格的 Fluent 界面，由 Qt/PySide6 编写。
· 界面文字跟随 Windows 系统默认字体（Segoe UI / 微软雅黑）。
· 底部状态栏右侧有“浅色 / 深色 / 自动”切换：
  默认跟随 Windows；也可以手动固定浅色或深色，选择会自动保存。
· 左侧导航：一键测试（回到主页）、教程、打开报告目录、打开隔离区、运行日志、
  打开备份目录、还原备份、关于；
  首次打开默认 English；底部语言按钮点击一下就会直接切换 中文 / English。
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
主页面 Mod 文件夹默认留空。点“选择要测试的 Mod ▾”会展开两个选项，都用
Windows 原生窗口：选“文件夹”就测试里面全部 Mod；选“.pak 文件”可一次勾选
一个或多个，只测试选中的这些。点“自动检测”则直接填入游戏已安装的 Mod 目录。

────────────────────────────
五、一键测试会自动做什么
────────────────────────────
1. 静态扫描：读取每个 .pak，找出重复/覆盖冲突。
2. 依赖分析：解析资源引用，找出“谁依赖谁”。
3. 自动分组：互相依赖的 Mod 合并成一组启动，冲突的 Mod 分开测。
4. 启动游戏并按组实测，自动点击跳过开场动画。
5. 生成报告并把不可用 Mod 移入隔离区（默认）或禁用。

测试过程中会反复弹出游戏窗口，请不要手动操作游戏；想中途停止可点“停止”。

高级选项默认开启“测试前自动校准启动时间”：首次一键测试会先启动一次游戏，
测出主窗口/主菜单耗时并自动填好“稳定观察 / 启动超时”的建议值，然后无缝继续
正式测试。也可以点“现在校准一次”手动重测。

────────────────────────────
六、高级选项说明
────────────────────────────
在“展开高级选项”里可以调整：
· 测试策略：标准隔离（默认）或严格深度（观察更久）。
· 稳定观察：游戏主窗口出现后保持稳定多少秒判“可用”，默认 35 秒。
· 启动超时：等待主窗口出现的最大时间。
· 主菜单确认：日志检测到主菜单后额外观察的秒数。
· 附加启动参数：默认 -windowed -nosplash。
· 测试前自动校准启动时间（默认开启）：首次/每 7 天或换了游戏路径时，会在正式
  测试前自动启动游戏测一次时间；也可以随时点“现在校准一次”手动重测。
· 不可用 Mod 处理：隔离 / 禁用（.disabled）/ 删除 / 仅记录。
  选“删除”时，测试开始前会再次弹出确认，被判定不可用的源文件会永久删除。
· 测试前关闭已运行的游戏、测试前备份、预热一次。
· 测试前分析 Mod 间资产依赖（默认开启）：更准确地把互相引用的 Mod 分到一组；
  如果只想快速实测，也可以关掉，随时用“仅分析资产依赖”单独分析。
· 游戏根目录：自动检测失败时手动选择。

改动会自动保存，并应用到下一次测试。

────────────────────────────
七、N 网 Mod 识别（可选）
────────────────────────────
在 N 网卡片里保存 Nexus Mods 的 Personal API Key 后（点击“如何获取”会打开
Nexus 密钥页），可以使用两个新按钮：

· 获取 Key 时注意：密钥页打开后要滚动到“页面最底部”，Personal API Key
  区域在底部，点 Generate/Create 生成并复制。

· “测试连接”：确认 API Key 是否有效。
· “识别当前 Mod 文件夹”：对当前选择的 Mod 文件夹逐个计算文件指纹（MD5），
  到 N 网反查这些 .pak 分别属于哪个 Mod / 哪个版本，并把 N 网页面链接列出来。
查不到的先显示“N 网未找到”，7 天后会自动重新查询。

识别完全在后台进行，期间可以继续看页面；完成后点“查看识别结果”可以看到表格，
双击或选中行点“打开选中页面”直达 N 网。结果会缓存在软件目录的 cache/ 里，
同一个文件不会重复查询。隐私说明：联网只上传文件指纹和你的 API Key（只发给
nexusmods.com），不会上传文件内容。是否填写都不影响本地一键测试；离线时跳过
联网功能即可。

对“可能是”的结果，请人工核对后使用结果窗口里的按钮：
· “确认这个 Mod”：把这个文件对应关系记进 cache/nexus_known_mods.json；
  以后重扫会直接显示“已确认”，不会再猜。
· “其他候选…”：推荐不对时，从候选列表里选正确的那一个再确认。
· “标记为忽略”：这个文件不是 N 网 Mod（或不想管它），以后不再提示。

确认至少一个 Mod 后，点“检查已确认依赖”：软件会读取 N 网页面上的
Requirements（前置需求），和你已确认的 Mod 对比，标出“已安装 / 缺失 / 外部链接 /
需要 DLC / 本地已有（待确认）”，窗口顶部会直接总结“缺哪些前置”。
结果同时写入 reports/nexus_dependencies_*.json 和 .csv。

────────────────────────────
八、备份与还原
────────────────────────────
· 每次测试前会自动记录 Mod 目录状态，并按设置创建备份。
· “高级选项 → 隔离目录”可以自定义隔离区位置；默认放在软件(exe)旁边，
  不再往“我的文档”里堆文件。想改回默认，直接把隔离目录清空即可（留空 = exe 旁）。
· 左侧导航“打开隔离区”可以随时查看被隔离的不可用 Mod；若还没有隔离区，
  会提示隔离区生成的位置（默认在软件目录的 quarantine 文件夹）。
· 左侧导航“打开备份目录”直接打开软件目录的 backup/ 文件夹。
· 左侧导航“还原备份”可以把备份里的非系统 Mod 还原回游戏目录。
  还原前会显示备份时间、备份里有多少个 .pak、将还原到哪个目录；
  如果备份记录里的目录与当前不一致，会先提示你。
· “完全还原”选项还会移除备份后新增的非系统 Mod，做到真正回滚。

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
所有默认输出都放在软件（exe）所在的目录，不会写进“我的文档”或 AppData：
· reports/ —— CSV / JSON 报告、每次启动的日志
· quarantine/ —— 隔离的不可用 Mod
· backup/ —— 测试前自动备份
· cache/ —— N 网识别缓存（MD5 指纹查询结果）
· debug.log —— 调试日志（软件根目录）

只有你在高级选项里手动指定其他位置时，才会写到别处。
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
Ready or Not Mod Compatibility Tester v0.4.1 - Detailed Tutorial
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

You can also run "Analyze asset dependencies only" first to review the planned
groups, then click "Start test with these groups" to launch the real test
without scanning twice.

Note: it can only detect "startup / main-menu stage crashes". If a mod only
breaks after entering a mission or equipping a weapon, it cannot be detected
automatically; test it manually in-game.

------------------------------------------------------------
2. Interface
------------------------------------------------------------
The GUI uses a Windows 11 Fluent-style interface built with Qt/PySide6.
The UI follows the Windows system default font (Segoe UI / Microsoft YaHei).
The status bar has a Light / Dark / Auto switcher. By default it
follows Windows automatically; you can also fix light or dark manually.
Left navigation: One-click test (home), Tutorial, Open report folder,
Open quarantine, Run log, Open backup folder, Restore backup, About. The button
at the bottom toggles directly between Chinese and English (English is the
first-launch default). The whole page scrolls; advanced options are collapsed
by default.

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

The mod-folder field is left empty by default. Click "Select mods ▾" to expand
two native Windows choices: pick a folder to test every mod inside it, or pick
one/multiple .pak files to test only those. "Auto detect" fills the game's
installed mod folder for you.

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

The "Auto-calibrate startup timing before tests" option is enabled by
default: the first one-click test launches the game once, measures how long it
takes to reach the main window/menu, fills in suggested Stable watch /
Startup timeout values, and then continues with the real test seamlessly. You
can also click "Calibrate now" to re-measure at any time.

------------------------------------------------------------
6. Advanced options
------------------------------------------------------------
Under "Advanced options" you can adjust: test strategy (standard isolated or
strict deep), stable watch seconds, startup timeout, menu confirm seconds,
auto-calibrate startup timing (enabled by default; recalibrates on first
use / after 7 days / when the game path changes), extra launch arguments
(default -windowed -nosplash), handling of unusable
mods (quarantine / disable / delete / record only; delete asks for extra
confirmation and permanently removes unusable source files), closing a
running game before testing, pre-test backup, warm-up launch, asset dependency
analysis before tests (enabled by default; disable it for faster runs and use
the standalone analysis button when needed), and the game root folder.
Changes are saved automatically and apply to the next test.

------------------------------------------------------------
7. Nexus mod identification (optional)
------------------------------------------------------------
After saving a Nexus Mods Personal API key in the Nexus card (click "How to
get an API key" to open the key page), two actions become available:
- Important: when the key page opens, scroll all the way to the bottom - the
  Personal API Key section is at the bottom. Use Generate/Create and copy it.
- Test connection: confirms the key is valid.
- Identify current mod folder: fingerprints each .pak in the selected folder
  (MD5) and looks it up on Nexus to see which mod/version it belongs to, with
  a direct page link. Files not found are shown as "Not found on Nexus" and
  are looked up again after 7 days.

Identification runs in the background. When it finishes, click "View
identification results" to open a table; double-click a row or select it and
click "Open selected page" to visit Nexus. Results are cached in the
software's cache/ folder, so the same file is never queried twice. Online
identification uploads only the file fingerprint and your API key (sent to
nexusmods.com only), never file contents. Filling it in is optional and never
required for the local one-click test; when offline, simply skip this feature.

For "Possible (unconfirmed)" rows, verify the match manually, then use the
result window buttons:
- "Confirm this mod": saves the file-to-mod mapping in
  cache/nexus_known_mods.json, so later scans show "Confirmed" instead of
  guessing again.
- "Other candidates...": choose the correct mod from the candidate list when
  the top suggestion is wrong.
- "Mark as ignored": this file is not a Nexus mod (or you do not care about
  it) and should no longer be suggested.

After confirming at least one mod, click "Check confirmed dependencies". RoNCT
reads the Requirements shown on each Nexus page and compares them with your
confirmed mods, marking each as Installed / Missing / External link / DLC
required / Present locally (confirm). The top of the dialog summarizes which
prerequisites are missing. Results are also written to
reports/nexus_dependencies_*.json and .csv.

------------------------------------------------------------
8. Backup and restore
------------------------------------------------------------
The Mod folder state is recorded before each test and a backup is created
according to the settings (backup folder next to the exe). "Open quarantine"
opens the folder where unusable mods are moved (next to the executable by
default; configure it under Advanced options > "Quarantine folder").
"Open backup folder" opens the software's backup directory.
"Restore backup" copies the backed-up non-system mods back to the game folder.
The restore dialog shows the backup time, the number of backed-up .pak files,
and the target directory, and warns you if the recorded directory differs.
"Full restore" also removes non-system mods added after the backup for a true
rollback.

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
All default output stays inside the software (exe) folder - nothing is written
to Documents or AppData unless you choose a custom location:
- reports/ - CSV/JSON reports and per-launch logs
- quarantine/ - unusable mods
- backup/ - automatic pre-test backup
- cache/ - Nexus identification cache (MD5 lookup results)
- debug.log - debug log at the software root

Debug log: debug.log next to the executable (in the release folder).
The log rotates at 1 MB and keeps 3 old files. When reporting a bug, send the
debug.log content to the author.

------------------------------------------------------------
11. Notes and limitations
------------------------------------------------------------
Repeated game launches read large game files (high SSD usage); test in batches.
The game does not write a standard UE log, so in-game breakage cannot be seen.
Back up important data; use at your own risk.
"""
