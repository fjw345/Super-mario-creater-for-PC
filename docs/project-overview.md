# 项目概况

Super Mario Creater for PC 是基于 Python 和 Pygame CE 的桌面游戏，包含经典 1-1、自定义关卡编辑器和关卡列表，支持中英文切换。

## 项目结构

| 路径 | 职责 |
| --- | --- |
| [mario_open.py](../mario_open.py)、[data/main.py](../data/main.py) | 游戏入口和状态注册。 |
| [data/tools.py](../data/tools.py)、[data/setup.py](../data/setup.py) | 游戏循环、输入分发、状态切换，以及窗口、字体、图像和音频的初始化。 |
| [data/states/](../data/states/) | 主菜单、加载等过场界面、经典关卡、编辑器、关卡列表和自定义关卡运行逻辑。 |
| [data/components/](../data/components/)、[data/game_sound.py](../data/game_sound.py) | Mario、敌人、道具、砖块等精灵，以及 HUD、计分和游戏音效。 |
| [data/constants.py](../data/constants.py) | 状态名、游戏参数、语言标识、存档使用的方块 ID，以及编辑器网格常量 `TILE_SIZE`、`EDITOR_TOP`、`GRID_HEIGHT`。 |
| [data/storage.py](../data/storage.py) | 存档目录、列出、加载校验、原子保存、删除和旧存档迁移，不依赖 pygame。 |
| [data/tiles.py](../data/tiles.py) | 编辑器方块表：槽位顺序、中英文名称、图标和锚点。 |
| [tests/](../tests/)、[scripts/smoke.py](../scripts/smoke.py) | 存档模块的 pytest 测试，以及无窗口的冒烟和行为检查。 |
| [resources/](../resources/)、[levels/](../levels/)、[custom_levels/](../custom_levels/) | 游戏素材、仓库内的关卡 JSON 和玩家创建的关卡目录。 |
| [mario_open.spec](../mario_open.spec)、[RELEASE_v1.0.md](../RELEASE_v1.0.md) | PyInstaller 打包配置和 v1.0 发布说明。 |

## 主要流程

- `mario_open.py` 调用 `data.main.main()` 注册状态，从主菜单进入游戏循环。`Control` 每帧处理输入和绘制，在状态切换时把 `cleanup()` 返回的 `persist` 传给下一状态的 `startup()`。
- 经典模式从主菜单经加载界面进入 [Level1](../data/states/level1.py)。地图布局、敌人和检查点由代码初始化。
- [LevelEditor](../data/states/level_editor.py) 在地图有旗杆时保存 UTF-8 JSON，包含 `name`、`width`、`height`、`tile_size` 和二维 `tiles`。编辑器测试和 [LevelSelect](../data/states/level_select.py) 都把文件路径传给 [CustomLevel](../data/states/custom_level.py)。后者依据方块 ID 创建地图对象，并根据入口设置返回界面。
- PyInstaller 配置将 `resources/` 和 `levels/` 随程序打包。当前 Windows ZIP 解压后应保留 `mario_open.exe` 和同级的 `_internal/`。

## 已知问题与优化方向

具体的修复步骤、实施顺序、验证方法和已确认的决定见 [修复方案](repair-plan.md)，各阶段的完成情况见其中的“完成情况”。

| 问题 | 状态 |
| --- | --- |
| 1 存档逻辑分散 | 已解决，见 `data/storage.py`。 |
| 2 两种关卡重复实现玩法 | 自定义关卡已对齐 1-1（P1），共用代码尚未抽取（P2）。 |
| 3 编辑器的方块信息分散 | 已集中到 `data/tiles.py`，待提交（P3）。 |
| 4 发布产物和说明需要对齐 | 已移出跟踪并更新说明，v1.0.1 尚未发布。 |

下面的描述是修复前的原始记录。

1. **存档逻辑分散。** 编辑器和列表分别用 `__file__` 推导 `custom_levels/` 路径，保存、列出、删除、加载又分布在三个状态。打包后这个路径可能落到 `_internal/`，替换程序目录时容易连同存档一起替换。发布前优先考虑统一存档路径与文件操作，明确打包版的可写位置，并兼容已有 JSON。验证时从新解压的包启动，保存、退出、重启并加载，再检查删除流程。
2. **两种关卡重复实现玩法。** `level1.py` 和 `custom_level.py` 各自处理敌人、龟壳、蘑菇和火球的运动与碰撞。可从蘑菇碰撞响应等行为边界清楚的部分小步抽取。地图初始化、经典模式的检查点和各自的通关流程仍由对应状态管理。每次提取后验证两种关卡的受影响行为。
3. **编辑器的方块信息分散。** `level_editor.py` 同时处理键鼠输入、网格、渲染、帮助面板和命名弹窗。新增方块要核对槽位顺序、预览图、中英文名称和自定义关卡的对象创建逻辑。可以先集中编辑器里的方块配置，继续沿用存档中的方块 ID。
4. **发布产物和说明需要对齐。** Git 当前跟踪 `build/`、`dist/`、Windows ZIP 和部分旧字节码。后续可将生成物从 Git 跟踪中移出，应用包通过 GitHub Release 附件分发。v1.0 说明中的 EXE 名称与现有 ZIP 不一致，也列出了仓库没有提供的 macOS DMG。更新发布说明时以最终附件为准。公开分发前确认上游代码和随包素材的再分发许可。
