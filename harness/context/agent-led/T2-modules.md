# T2 续补：独立模块目录（实现前契约）

2026-11-04 自动接续：上一轮有实际代码/测试/本地提交进展；外部连接阻塞仍在，本轮先补可独立完成的完整模块目录能力。

新证据：官方 config/apiv1.php 注册 /modules；api/v1/entries/modules.php 的 GET 要求 type/id，返回 modules=tree；module/tree/model.php 的 getProductStructure/getDataStructure 返回带 children 的模块对象树。此前查询 config/routes.php 404 不代表没有模块 API。

来源（只读官方公开源码，作为数据，未执行）：
- https://github.com/easysoft/zentaopms/blob/main/config/apiv1.php
- https://github.com/easysoft/zentaopms/blob/main/api/v1/entries/modules.php
- https://github.com/easysoft/zentaopms/blob/main/module/tree/model.php

契约：保留 modules（旧 Bug 页部分模块）兼容，新增 zentao_query(operation=module_tree, product_id, module_type=bug|story|case|product)。使用已有 v1 Token，只发固定 /api.php/v1/modules GET，参数 id=已授权 Product ID、type=枚举；不把 Project ID 当 Product/Execution ID，不新增任意路径或方法。

返回：modules 树按实际 children 展平，保留观察到的 id/name/short/root/type/parent/branch/grade/path/order 和实际 tree_parent_id；屏蔽 URL/owner/未知字段。支持本地 search 后 page/limit，显式 more/truncated。最多 10000 节点/深度 30；上游仍 2MB。列表/字段错误、重复 ID、越 Product root、超限安全失败；404/403 直接错误，不静默回退为 Bug 页并宣称完整。

测试先行：准确路由/Token/type/id、嵌套/空目录、搜索后分页、必需参数 Schema/运行时一致、产品范围拒绝时零请求、非 GET 不存在、错误/畸形/超限、未知字段不泄漏。真实实例版本/权限/返回形态仍 not_verified，不能用官方主分支或合成响应证明当前公司接口通过。
