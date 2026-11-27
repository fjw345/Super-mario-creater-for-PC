# 修复方案

本文针对 [项目概况](project-overview.md) 中“已知问题与优化方向”的四项，给出具体的修复步骤、验证方法和已确认的决定。文中的行号以 2026-11-27 的源码为准，修改代码后请以函数名为准重新定位。

## 已确认的决定

| 问题 | 决定 |
| --- | --- |
| 打包版的存档位置 | 放在用户数据目录，Windows 上为 `%APPDATA%\SuperMarioCreater\custom_levels`。源码运行时仍使用仓库内的 `custom_levels/`。 |
| `levels/custom_level.json` | 保留，作为只读的内置示例关卡显示在关卡列表中。 |
| EXE 名称 | 修改 `mario_open.spec`，产物改名为 `Super Mario Creater.exe`，与发布说明一致。 |
| 自定义关卡的玩法 | 完全忠于经典 1-1。以 `level1.py` 的行为为准，自定义关卡中与之不同的地方都视为待修复项。 |

## 完成情况

更新于 2026-11-27。

| 阶段 | 状态 | 提交 | 说明 |
| --- | --- | --- | --- |
| P0 存档模块、加载校验、发布产物与说明 | 已完成 | `bd4eb13` | 手动验证清单（打包、迁移、删除、编辑器往返）已由用户确认。 |
| P1 自定义关卡对齐 1-1 | 已完成，待人工手感对比 | `7dc7866` | 下表所有条目都已实现。headless 检查通过，没有在窗口里逐项对照 1-1 的手感。 |
| P3 集中编辑器方块配置 | 已完成 | `a0904c3` | 编辑器画面与修改前逐像素一致，现有关卡和内置示例都能加载。 |
| P2 抽取共用玩法 | 未开始 | 无 | 按本文顺序分 6 步，每步单独提交和验证。 |

### 与方案不同的地方

- **敌人被砖块和问号砖侧向阻挡。** P1 按 `level1.py` 让敌人 x 方向只检测地面、台阶和管道。自定义关卡可以把砖块放在行走高度，敌人因此爬到高一格的方块上。`custom_level.py` 的 `check_enemy_x_collisions` 现在把砖块和问号砖也算作阻挡。这是自定义关卡与 1-1 的有意差异，原因是 1-1 的地图里没有这种布局。P2 抽取敌人碰撞时必须保留这一点。
- **死亡后重开靠 `resume_custom_level` 标记。** 死亡时 `CustomLevel` 在 `persist` 中写入这个标记，加载界面读到后把下一状态设为 `CUSTOM_LEVEL`。标记在 `CustomLevel.startup` 中清除。
- **旗杆高度写入 Mario 和旗子。** `Mario.flag_pole_ground`、`Flag.ground_y` 默认取 `c.GROUND_HEIGHT`，自定义关卡按旗杆底部设置。1-1 的数值不变。

### 尚未完成

- 发布 v1.0.1：构建、打标签、上传 GitHub Release 附件。
- P1 的人工手感对比：准备包含全部 10 种方块的关卡，与 1-1 的同类操作逐项对照，尤其是踩龟壳、顶砖块击杀敌人、龟壳连撞和星星弹跳。
- 自定义关卡没有星星来源，星星相关的移植没有实际触发过。
- 内置示例 `levels/custom_level.json` 没有旗杆，不能通关。需要决定补旗杆还是保持原样。
- 公开分发前确认上游代码、贴图和音乐的再分发许可。
- 缩小 Git 历史需要重写历史并强制推送，本方案不包含这一步。

### “忠于 1-1”的执行规则

- 参照对象是本仓库的 `level1.py`，不是任天堂原版游戏。
- 自定义关卡和 1-1 的差异，默认改自定义关卡去对齐 1-1。
- `level1.py` 自身的明显错误（见 P1 末尾）在两种关卡中一起修正，修正后两边的行为仍保持一致。
- 只保留由关卡来源决定的差异：地图由 JSON 生成、旗杆后自动生成城堡、从编辑器测试时死亡或通关后返回编辑器。

## 现状要点

以下是动手前的状态，P0、P1、P3 已处理的条目见上面的“完成情况”。

- `level_editor.py:83` 和 `level_select.py:65` 从 `__file__` 向上推三层目录定位 `custom_levels/`。打包后这个位置落在 `_internal/custom_levels`，替换程序目录会连同存档一起替换。
- `level_editor.py:911` 写文件时没有异常处理，也不是原子写入，同名保存会直接覆盖。
- `custom_level.py:133` 读取 JSON 时不做校验。文件损坏、行数不足、`tile_size` 为 0 或 `width` 过大都会导致崩溃；无法识别的方块 ID 会被直接丢弃。
- 代码没有读取 `levels/custom_level.json`，它只是被 spec 打进了发布包。
- Git 跟踪了 `build/`、`dist/`、`release_assets/` 中的 Windows ZIP，以及 24 个 Python 3.6 的 `.pyc`。
- `RELEASE_v1.0.md` 写的 EXE 名称与实际产物 `mario_open.exe` 不一致，并列出了不存在的 macOS DMG。
- 仓库没有自动化测试。设置 `SDL_VIDEODRIVER=dummy` 后可以在无窗口模式下导入并启动全部状态。

## 实施顺序

1. P0 第 1、2 项，同时加入存档测试。
2. P0 第 3 项，发布 v1.0.1。
3. P1：自定义关卡对齐 1-1 的就地修复。
4. P3：集中编辑器方块配置。
5. P2：抽取两种关卡共用的玩法代码。

P3 排在 P2 之前，因为它只涉及编辑器和方块创建，不影响 1-1。P1 先让两边行为一致，P2 的抽取才能做到不改变任何一方的玩法。

## P0：发布前必须完成

### 1. 统一存档模块

新建 `data/storage.py`，集中处理存档路径和全部文件操作。

**存档目录**

- 源码运行：仓库根目录下的 `custom_levels/`。
- 打包运行（`sys.frozen` 为真）：`%APPDATA%\SuperMarioCreater\custom_levels`。取不到 `APPDATA` 时退回 `~/.supermariocreater/custom_levels`。
- 目录不存在时自动创建。

**接口**

| 函数 | 说明 |
| --- | --- |
| `levels_dir()` | 返回存档目录。 |
| `builtin_levels()` | 返回内置示例关卡，来自资源目录下的 `levels/`，只读。 |
| `list_levels()` | 返回 `(path, name, ok, builtin)` 列表。损坏的文件也列出，标记为损坏。 |
| `load_level(path)` | 读取并校验、规范化（见第 2 项）。失败时抛出 `LevelLoadError`。 |
| `save_level(name, tiles)` | 先写临时文件，再用 `os.replace` 替换。失败时抛出 `LevelSaveError`。 |
| `delete_level(path)` | 只允许删除存档目录中的文件，拒绝删除内置关卡。 |
| `sanitize_name(raw)` | 去掉非法字符，拦截 `CON`、`PRN`、`AUX`、`NUL`、`COM1` 到 `COM9`、`LPT1` 到 `LPT9` 等 Windows 保留名。截断到 32 个字符后再去一次首尾空格和点。 |
| `level_exists(name)` | 供覆盖确认使用。 |

**资源路径**

`setup.py` 的 `BASE_DIR` 在打包后指向 `_internal/`，这对只读资源是正确的。内置关卡沿用这个路径，玩家存档则一律通过 `levels_dir()` 获取。

**旧存档迁移**

打包版首次启动时，把下面两个位置的 JSON 复制到新目录：

- `_internal/custom_levels/`
- EXE 同级的 `custom_levels/`

新目录中已有同名文件时跳过。旧文件只复制，不删除。迁移完成后写入标记文件，避免重复迁移。

**接入点**

- `LevelEditor`：删除 `levels_dir` 的推导，`save_level` 改为调用 `storage.save_level`。保存失败时在 `ui_message` 中显示原因，不再崩溃。
- 同名保存：在命名弹窗中提示“已存在，再按 Enter 覆盖”。自动保存的“上次测试的关卡”直接覆盖，不提示。
- 命名弹窗中的提示 “自动保存到 custom_levels” 改为显示实际目录。
- `LevelSelect`：改为调用 `list_levels` 和 `delete_level`。内置示例显示“示例”标记，不能删除。损坏的文件显示“无法读取”，可以删除，但不能游玩。
- `CustomLevel`：`load_level` 改为调用 `storage.load_level`。

**JSON 兼容性**

保留 `name`、`width`、`height`、`tile_size`、`tiles` 五个字段，方块 ID 仍使用 `constants.py` 中的字符串。新增可选字段 `"version": 1`，没有该字段的文件按版本 1 处理。

### 2. 加载时校验和规范化

`storage.load_level` 统一执行下面的规则：

- `tiles` 必须是二维列表，否则视为加载失败。
- 以 `tiles` 的实际尺寸为准，不信任 `width` 和 `height` 字段。行数补齐或裁剪到 13 行，每行补齐到同一宽度，宽度限制在 1 到 1000 之间。
- 当前布局写死了 43 像素方块、70 像素顶部偏移和 83x82 的管道，所以 `tile_size` 不是 43 时一律按 43 处理。编辑器本身只会写入 43。
- 无法识别的方块 ID 转为 `empty`，并记录数量，便于排查。
- 加载失败时，`CustomLevel` 不再退回一张无旗杆、无法通关的空地图，而是带着错误信息回到来源界面，由关卡列表或编辑器显示。

### 3. 发布产物与说明

- 执行 `git rm -r --cached build dist release_assets`，并移除所有被跟踪的 `__pycache__`。本地文件保留。
- 在 `.gitignore` 中加入 `build/`、`dist/`、`release_assets/`。
- 安装包通过 GitHub Release 附件分发。移出跟踪不会缩小已有的 Git 历史；缩小历史需要重写历史并强制推送，本方案不包含这一步。
- 修改 `mario_open.spec`：`EXE` 和 `COLLECT` 的 `name` 都改为 `Super Mario Creater`。保留 `datas` 中的 `levels`，因为它现在提供内置示例。
- 更新 `RELEASE_v1.0.md`，或新增 v1.0.1 的发布说明：EXE 名称以最终附件为准，删除 macOS DMG 一行，写明存档位置和旧存档迁移规则。
- README 中的“编辑器保存规则”同步更新存档位置。
- 公开分发前确认上游代码的许可，以及随包贴图和音乐的再分发许可。

### P0 验证

1. 运行 `tests/test_storage.py`。
2. 用 `mario_open.spec` 构建，解压到一个新目录后启动。
3. 保存一个关卡，退出，重启，在列表中加载并游玩。
4. 把程序目录整个替换为新解压的版本，确认存档仍在。
5. 在旧版目录的 `_internal/custom_levels/` 放入 JSON，启动新版，确认已迁移。
6. 删除一个关卡，确认内置示例无法删除。
7. 加载 `custom_levels/` 中现有的三个 JSON 和内置示例。
8. 在编辑器中保存、测试游玩、返回编辑器，确认编辑内容保留。

## P1：自定义关卡对齐 1-1

以下修改都在 `custom_level.py` 中就地进行，不涉及代码抽取。L 表示 `level1.py`，C 表示 `custom_level.py`。

### 方块交互

| 差异 | 位置 | 修复 |
| --- | --- | --- |
| 问号砖顶出金币时不加金币数，也不加 200 分 | C:570-587 | 照搬 L:743-764 的计分。 |
| 顶砖块、问号砖没有 `bump`、`brick_smash` 音效 | C:549-587 | 按 L:757、772、789、796 补上。 |
| Mario 中心线在方块外时直接 `return`，导致从方块角穿入 | C:551、572 | 改用 L 的判定 `mario.rect.y > block.rect.y`。 |
| 头顶同时有两个方块时总是砖块优先 | C:503-534 | 移植 L:725-740 的 `prevent_collision_conflict`。 |
| 顶方块不能击杀站在上面的敌人 | C 缺失 | 移植 L:807-827 的 `check_if_enemy_on_brick`，以及 L:979-1017 中敌人碰到弹起方块被击杀的分支。 |
| `y_vel == 0` 时不处理重叠 | C:511、522 | 按 L 的 y 方向碰撞流程重写 `check_mario_y_collisions`。 |

### 敌人、龟壳与道具

| 差异 | 位置 | 修复 |
| --- | --- | --- |
| 踩敌人和龟壳只在 x 方向检测，晚一帧生效 | C:483-489 | 移植 L 的 `adjust_mario_for_y_enemy_collisions` 和 `adjust_mario_for_y_shell_collisions`（L:872-911）。 |
| 踩停滑行的龟壳后 Mario 没有移到龟壳顶部，下一帧会再踢一次 | C:673-680 | 与 L 一致，设置 `mario.rect.bottom = shell.rect.top`。 |
| 龟壳会撞砖块和问号砖反弹 | C:836-886 | 去掉，与 L:1044-1082 一致。 |
| 无敌状态击杀敌人没有音效和分数 | C:617-621、667-671 | 按 L:541-549 和 L:670-676 补上。 |
| Mario 的 x 方向碰撞各项独立判断 | C:468-491 | 改为 L:522-609 的互斥 `elif` 顺序。 |
| 掉出屏幕的敌人、龟壳、蘑菇永不清除 | C:771、827、902 | 调用 `delete_if_off_screen`，与 L 一致。 |
| 所有敌人和放置的蘑菇从第一帧就开始活动 | C:236-271 | 1-1 通过检查点在镜头接近时生成敌人。自定义关卡改为敌人进入镜头右侧一屏范围内才加入活动组，效果与 1-1 一致。 |
| 星星没有重力和碰撞 | C:893-897 | 移植 L:1160-1193。目前自定义关卡没有星星来源，这一项是预防性修复。 |

### 镜头、死亡与计分

| 差异 | 位置 | 修复 |
| --- | --- | --- |
| 镜头跟随规则不同，没有 1-1 的半速区 | C:1056-1067 | 改为 L:1368-1378 的规则。 |
| 掉坑死亡后关卡不冻结，3 秒内仍可操作 | C:1105 | 与 L:1321-1322 一致，设置 `x_vel = 0` 和 `state = FROZEN`。 |
| 死亡音乐流程不同 | C:1103-1124 | 移植 L 的 `play_death_song`。 |
| 死亡后回到主菜单 | C:1116-1124 | 与 L 的 `set_game_info_values` 一致：扣一条命后经加载界面重开当前自定义关卡，生命为 0 时进入 Game Over，超时进入 Time Out。从编辑器测试时仍返回编辑器。 |
| 死亡和通关时不更新 `TOP_SCORE` | C 缺失 | 按 L:1339 补上。 |
| 旗杆分数用世界坐标创建，却画在屏幕表面上，旗杆在 800 像素以外时看不到 | C:1188 | 与 L:1416 一致，画到 `self.level` 上。 |
| 旗杆计分和旗子下滑终点按地面高度写死，旗杆放在高台上时会出错 | C:419-439 | 计分阈值和下滑终点改为相对旗杆底部计算。放在地面上时与 1-1 结果相同。 |
| 状态实例复用时，`hasattr(self, 'flag')` 可能读到上一关的旗杆 | C:1071 | 在 `startup` 中重置 `self.flag = None`。 |
| 运行时读取 1-1 的 `CAMERA_START_X` | C:161 | 自定义关卡固定从 0 开始。 |

### 性能与绘制

| 问题 | 位置 | 修复 |
| --- | --- | --- |
| 每帧为每个可见地面格新建 Surface 并缩放，已缓存的 `ground_tile_image` 没有使用 | C:1221-1225 | 使用缓存图像。 |
| 管道按锚点列裁剪，离开左边缘前约 40 像素就消失 | C:1207 | 可见范围向左多取一列。 |
| 敌人同时属于两个绘制组，每帧画两次 | C:1178、1182 | 去掉 `enemy_group` 的单独绘制。 |

### 两种关卡一起修正的 1-1 错误

| 问题 | 位置 | 修复 |
| --- | --- | --- |
| `self.mario.state == c.STAND` 是无效的比较 | L:455 | 改为赋值。 |
| 已经变大的 Mario 吃蘑菇还会播放变大动画 | L:581 | 已变大时只加分。 |
| y 方向吃到星星不加分，x 方向吃到星星没有音效 | L:566、716-720 | 两个方向都加分并播放音效。 |

### P1 验证

- 1-1：走到旗杆，过程中吃蘑菇、吃火焰花、发射火球、踢龟壳、顶砖块，确认手感与修改前一致。
- 自定义关卡：准备一张包含全部 10 种方块的测试关卡，逐项核对上表中的行为，并与 1-1 中的同类操作对比。
- 死亡流程：从关卡列表进入时，死亡后重开当前关卡，生命用完进入 Game Over；从编辑器测试时，死亡后返回编辑器。

## P2：抽取共用玩法

新建 `data/states/level_common.py`，写一个 mixin，由 `Level1` 和 `CustomLevel` 共同继承。两个类中相关属性的名称完全一致，例如 `ground_step_pipe_group`、`brick_group`、`viewport`、`moving_score_list`、`game_info`，mixin 可以直接使用。

按风险从低到高逐步进行，每一步单独提交、单独验证：

1. 火球：`adjust_fireball_position`、`bounce_fireball`、`check_fireball_x/y_collisions`、`fireball_kill`、`delete_if_off_screen`。两边完全相同。
2. 问号砖内容切换：`convert_mushrooms_to_fireflowers`、`convert_fireflowers_to_mushrooms`。两边完全相同。
3. 蘑菇和星星的运动与碰撞。先把 C:589 中签名不同的 `check_if_falling` 改名，避免和共用的同名方法冲突。
4. Mario 主循环框架：`handle_states`、`adjust_sprite_positions`、`adjust_mario_position`、`adjust_mario_for_x_collisions`、`test_if_mario_is_falling`、`check_if_mario_in_transition_state`。
5. 完成 P1 后，龟壳、敌人、Mario 碰撞、镜头和死亡流程两边已经一致，再依次抽取。
6. 旗杆计分：把旗杆位置作为参数，两边共用。

保留在各自类中的部分：地图初始化、1-1 的检查点和敌人生成、自定义关卡的方块创建和城堡生成、各自的通关流程。

每一步完成后验证 1-1 和至少一个自定义关卡中受影响的行为。

## P3：集中编辑器方块配置

- 新建 `data/tiles.py`，按槽位顺序列出每种方块的 ID、中英文名称、调色板图标、世界图像和锚点偏移（管道、乌龟、旗杆需要）。
- 编辑器的调色板、预览、绘制和 `get_tile_display_name` 都从这张表读取。数字键 1 到 0 的 10 个 `elif` 改为循环。
- `custom_level.create_tile` 改为按 ID 查表创建对象。存档中的字符串 ID 保持不变。
- 在 `constants.py` 中加入 `TILE_SIZE = 43`、`EDITOR_TOP = 70`、`GRID_HEIGHT = 13`，编辑器和运行时共用，去掉两边散落的固定数字。

新增方块的流程因此变为：在 `constants.py` 加 ID，在 `tiles.py` 加一行配置，在 `create_tile` 的表中加一个创建函数。

### P3 验证

- 截图对比编辑器的调色板和预览，确认与修改前一致。
- 保存、重新加载、测试游玩、返回编辑器。
- 现有 JSON 和内置示例正常加载。

## 验证工具

- `tests/test_storage.py`：用 pytest 和临时目录测试名称清理、原子保存、规范化、旧存档迁移和删除边界。这些是纯函数，不需要窗口。pytest 写入 `requirements-dev.txt`，不进入发布包。
- `scripts/smoke.py`：在 `SDL_VIDEODRIVER=dummy` 下依次启动各个状态，再用几份测试 JSON 运行 `CustomLevel` 数百帧，覆盖正常文件、损坏文件、行数不足和未知方块 ID，确认没有异常。

两者与 P0 一起加入，此后每个阶段都先跑一遍。
