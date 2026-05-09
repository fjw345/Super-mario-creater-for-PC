# Super Mario Creater for PC v1.0

发布日期：2026-05-09

这是 Super Mario Creater for PC 的首个正式版本。v1.0 提供可直接游玩的经典 1-1 关卡、自定义关卡编辑器、自定义关卡游玩流程，以及基础的中英文界面切换支持。

## 下载即玩

> 以下链接指向 GitHub Releases 的 v1.0 发布资产。发布时请将安装包文件名与表格中的文件名保持一致。

| 系统 | 架构 | 下载链接 | 使用方式 |
|---|---|---|---|
| Windows | x64 | [Super-Mario-Creater-v1.0-windows-x64.zip](https://github.com/fjw345/Super-mario-creater-for-PC/releases/download/v1.0/Super-Mario-Creater-v1.0-windows-x64.zip) | 解压后运行 `Super Mario Creater.exe` |
| macOS | Apple Silicon / Intel | [Super-Mario-Creater-v1.0-macos-universal.dmg](https://github.com/fjw345/Super-mario-creater-for-PC/releases/download/v1.0/Super-Mario-Creater-v1.0-macos-universal.dmg) | 打开 DMG 后将应用拖入 Applications |

备用入口：[GitHub v1.0 Release 页面](https://github.com/fjw345/Super-mario-creater-for-PC/releases/tag/v1.0)

## v1.0 内容

- 经典 Mario 1-1 关卡游玩。
- 主菜单、关卡选择、自定义关卡编辑器。
- 自定义关卡创建、保存、删除和测试游玩。
- 支持地面、砖块、问号砖、管道、敌人、旗杆、蘑菇、火焰花等编辑元素。
- 自定义关卡通关时自动生成城堡，并播放夺旗后的自动通关演出。
- 支持中英文界面切换。
- 提供 `requirements.txt`，源码运行时可一键安装 Python 依赖。

## 操作说明

### Mario

| 操作 | 按键 |
|---|---|
| 左移 | A |
| 右移 | D |
| 跳跃 | K |
| 冲刺 / 动作 | J |
| 下蹲 | S |
| 返回 / 退出当前自定义关卡 | ESC |

### 编辑器

| 操作 | 按键 / 鼠标 |
|---|---|
| 移动画面 | A / D 或 Left / Right |
| 选择方块槽位 | 1-9, 0 |
| 切换方块 | Q / E |
| 放置方块 | 鼠标左键 |
| 擦除方块 | 鼠标右键 |
| 保存关卡 | Ctrl + S |
| 测试关卡 | T |
| 重置关卡 | C |
| 折叠 / 展开帮助面板 | H |
| 切换语言 | L |

## 源码运行

如果你下载的是源码版本，需要先安装 Python 3.10+，然后在项目目录中执行：

```powershell
python -m pip install -r requirements.txt
python mario_open.py
```

## 已知说明

- Windows 首次运行可能会出现安全提示，请选择“仍要运行”。
- macOS 首次运行如遇到 Gatekeeper 阻止，可右键应用并选择“打开”。
- 自定义关卡文件保存在 `custom_levels` 目录中。

## 反馈

如果发现问题或希望提交改进，请前往：

https://github.com/fjw345/Super-mario-creater-for-PC/issues
