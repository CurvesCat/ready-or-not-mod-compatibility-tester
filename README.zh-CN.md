# 严阵以待 Mod 兼容性测试器

**作者：** CurvesCat

**N 网页面：** <https://www.nexusmods.com/readyornot/mods/8575>

这是一个 Windows 桌面工具，用于在《严阵以待》（Ready or Not）更新后自动逐个检测
`.pak` Mod 是否仍然兼容。它会逐个把 Mod 放进游戏目录、启动游戏并观察窗口和进程是否稳定，
输出 CSV / JSON 报告，并可把不可用 Mod 隔离、禁用或删除。

> 本工具只能判断“启动 / 进入主菜单阶段”是否崩溃。如果某个 Mod 是在进入游戏后
> （例如装备武器、进入任务）才失效，而启动阶段一切正常，工具无法自动发现，
> 需要你手动进游戏验证，因为《严阵以待》不会输出标准的 Unreal Engine 日志。

## 功能

- 两种测试来源：
  - **候选文件夹**：测试某个文件夹（或手动挑选）里的 `.pak` Mod。
  - **游戏目录内已安装**：测试已经放进游戏 `Paks` 目录的 Mod。
- 可单独添加 `.pak` 文件、排除指定文件、或清空选择。
- 两种策略：
  - **标准隔离**：逐个 Mod 测试，适合日常排查。
  - **严格深度**：逐个 Mod 测试并观察更久，适合重要 Mod 的最终确认。
- 自动检测游戏根目录、游戏程序和 Mod 安装目录。
- **自动测时**：先启动一次游戏测量启动时间，并给出稳定观察秒数建议。
- 游戏窗口打开时自动点击跳过开场动画。
- 通过进程退出、错误弹窗、`Saved\Crashes` 崩溃目录和可用游戏日志检测崩溃。
- 测试前记录 Mod 目录状态并可选复制备份，支持一键**还原备份**。
- 自动排除 `pakchunk*-Windows.pak` 等游戏系统文件。
- 不可用 Mod 可选：移入隔离区 / 重命名为 `.disabled` 禁用 / 删除 / 仅记录。
- 生成 CSV / JSON 报告，以及 `usable_mods.txt` / `unusable_mods.txt`。
- 中英文界面：首次启动时选择语言，之后可在界面里随时切换。
- 可配置备份目录与备份大小上限。

## 系统要求

- Windows 10 / 11
- 已安装 Steam 版《严阵以待》
- Steam 已登录

使用打包好的 EXE 不需要 Python。从源码运行时需要 Python 3.10+ 和 `psutil`。

## 快速开始（图形界面）

1. 双击运行 `ReadyOrNot-ModCompatTester.exe`。
2. 选择界面语言。
3. 选择测试来源：
   - *候选文件夹*：选择存放 `.pak` 文件的文件夹，或点击“添加 .pak 文件…”。
   - *游戏目录内已安装*：直接测试已安装进游戏 `Paks` 的 Mod。
4. 点击“自动检测”，确认游戏目录、游戏程序和 Mod 安装目录。
5. 可选：点击“自动测时”，测量启动时间。
6. 选择测试策略、稳定观察秒数和不可用 Mod 的处理方式。
7. 点击“开始测试”。

测试期间请不要手动操作游戏。

## 命令行（CLI）

```powershell
ReadyOrNot-ModCompatTester-cli.exe --mods "D:\Mods\RoN" --mode isolated
ReadyOrNot-ModCompatTester-cli.exe --source installed --mode strict
```

常用参数：

| 参数 | 说明 | 默认值 |
| --- | --- | --- |
| `--mods` | 候选文件夹里的 `.pak` Mod | 无 |
| `--files` | 单独指定要测试的 `.pak` 文件 | 无 |
| `--exclude` | 排除这些文件，不参与测试 | 无 |
| `--source` | `folder` / `installed` | `folder` |
| `--mode` | `isolated` / `strict` | `isolated` |
| `--disposition` | `quarantine` / `disable` / `delete` / `record` | `quarantine` |
| `--yes-delete` | 确认使用 `--disposition delete`（否则拒绝执行） | 关闭 |
| `--game` | 游戏根目录 | 自动检测 |
| `--exe` | 游戏可执行文件完整路径 | 自动检测 |
| `--mod-dir` | Mod 安装目录 | 自动检测 |
| `--report-dir` | 报告输出目录 | 见下方说明 |
| `--stable` | 游戏主窗口出现后的稳定观察秒数 | 35 |
| `--startup-timeout` | 等待游戏主窗口出现的超时秒数 | 120 |
| `--menu-hold` | 检测到主菜单标记后再观察的秒数 | 6 |
| `--warmup` | 正式测试前先不带 Mod 启动一次 | 关闭 |
| `--no-close` | 测试前不自动关闭已运行的游戏 | 关闭 |
| `--no-backup` | 只记录状态，不复制备份 | 关闭 |
| `--backup-dir` | 备份目录 | 程序旁的 `backup` |
| `--backup-max-file-mb` | 单个文件超过该大小则不复制备份（MB） | 1500 |
| `--backup-max-total-mb` | 备份总大小上限（MB） | 10000 |
| `--extra-args` | 附加游戏启动参数 | `-windowed -nosplash` |

报告默认输出位置：

- `folder` 来源：候选文件夹旁的 `*_test_reports`。
- `installed` 来源：游戏目录旁的 `RoN_ModCompat_Reports`。

## 从源码运行

```powershell
python -m pip install psutil
python -m ron_mod_tester                       # 图形界面
python -m ron_mod_tester --mods "D:\Mods\RoN" --mode isolated   # 命令行
```

## 构建可执行文件

参见 [BUILD.md](BUILD.md)。

## 免责声明

本工具会反复启动游戏，并可能根据你的设置移动、重命名或删除 Mod 文件。
请先备份存档和 Mod，使用风险自负。自动化结果只是启动阶段的冒烟测试。
