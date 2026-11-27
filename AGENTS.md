# AGENTS.md

- 开始修改前，先读 [项目概况](docs/project-overview.md)，按功能定位入口、相关模块和验证流程。
- 处理已知问题时，按 [修复方案](docs/repair-plan.md) 的顺序和已确认决定进行。自定义关卡的玩法以 `level1.py` 为准。
- 从仓库根目录运行 `python -m pip install -r requirements.txt` 安装依赖，运行 `python mario_open.py` 启动游戏。玩家操作见 [README](README.md)。
- 修改共用玩法时，验证经典 1-1 和自定义关卡。修改编辑器或存档时，验证保存、重新加载、测试游玩和返回编辑器，并保留旧关卡 JSON 的兼容性。
- 发布包通过 `mario_open.spec` 构建。功能改动以源码为准，无需手工编辑 `build/` 和 `dist/` 中的产物。
