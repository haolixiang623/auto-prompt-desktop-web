# 测试数据夹具说明

后续扩展带数据回归时，统一放在本目录。

建议结构：

- `workspaces/happy-path/`
- `workspaces/missing-classified-dir/`
- `workspaces/missing-pending-dir/`
- `workspaces/bad-factors-duplicate/`
- `expected/`（期望输出快照）

当前阶段先以内存临时目录测试为主，避免仓库体积快速膨胀。
