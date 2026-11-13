# Cursor Host V1.1.1 集成修复契约

本轮只修启动、配置及工具发现，不改Token Manager、不扩权、不改业务project.yaml。2026-11-07实施阶段保持未提交；2026-11-08用户已确认Gate A PASS并授权工程收尾本地提交，仍不推送。实际公司配置/日志/路径只保存在gitignored私有目录；公开测试全部合成。

## 边界与证据

用户级与项目级MCP定义、Cursor窗口缓存、进程、独立客户端、真实桌面调用分开取证。进程存活/包导入不等于桌面调用成功；独立STDIO成功也不冒充Cursor Agent验收。历史只按argv完全一致筛选会遗漏授权参数不同的旧连接；不据此误杀其他窗口。

保留现有显式本地凭证入口，使用绝对Python/脚本/配置/凭证/Catalog路径。用户级只改dce条目，写前私有0600备份，其他条目与原有资源scope逐项比较保持，不增加新Bug或日志授权。业务工作区若存在覆盖定义，只读报告，不自动修改。

## 启动与失败

启动器增加可重复的 --require-platform（zentao/gitlab/portainer），只要求连接存在，不授予访问范围、不发认证请求。缺失指定平台在STDIO服务启动前输出固定脱敏JSON到stderr并退出；stdout为空，不建Catalog。原来不指定该参数的独立单平台用法兼容。

启动器补齐 --portainer-log-scope，复用CLI的同一校验函数；格式必须ENDPOINT:STACK，且同时已有对应元数据scope。默认空集合，拒绝项在读取凭证前停止；本轮真实配置不增加此grant。不修改时间窗口、日志读取或Token刷新算法。

## 工具发现与运行身份

九工具名称与输入/输出data契约保持。portainer_query枚举和描述必须包含service_logs，契约revision保持2.2。初始化serverInfo.version使用包版本1.1.1，不增加版本查询工具。

在既有Tool._meta.dce及CallToolResult._meta.dce中附加同一运行身份：server_version、process_id、仅对公开输入Schema计算的schema_sha256、configured_platforms（仅平台类别）。不含路径、地址、账号、scope值或Token，不改变业务Schema。完整响应预算包括这些元数据。

响应接近预算时先省略CallToolResult的可选_meta，再执行原有数据/图片裁剪；诊断不能挤占原本可返回的结果。工具发现及stderr仍保留运行身份。

仅显式本地入口启用dce.audit的stderr固定审计：启动版本/PID/Schema摘要/配置平台类别，调用工具白名单名/状态/错误码/PID及既有信封request_id；不记录参数、请求头、上游正文或业务ID。即使Host不转发_meta，也可用JSON文本信封的request_id对照同一stderr审计，从而将具体调用关联到初始化及Schema；缺失历史审计时明确证据缺口。

## 工具目录中的旧Runtime PID

Cursor可将初始化instructions保存为工具目录的INSTRUCTIONS.md。该文件是上次发现时的快照，不代表实时连接；历史说明中的PID因此可能跨连接保留。DCE的runtime只在进程内由os.getpid()创建，不从Catalog或工具目录读取，亦无对应持久化写入。

收尾仅从可缓存的握手说明移除瞬时PID，保留稳定Schema摘要及版本协议；九工具、Schema、工具/结果实时runtime和request_id审计不改。实时进程以最新调用结果的_meta或request_id对应stderr为准。复用同一合成Catalog连续启动两个STDIO进程，说明/Schema保持相同，实时PID和request_id分别更新，防止把快照当作连接状态。不手改Host缓存，不重启已通过验收的业务连接。

## 验收

先用合成测试验证启动缺平台、日志独立grant及越权、任意cwd启动、九工具/描述/Schema、原生图片、配置与版本元数据、stderr审计和stdout协议纯净。再执行完整回归。

真实独立STDIO使用最终Cursor条目的相同command/args/env，三平台配置可发现，握手1.1.1，九工具，service_logs可发现；限定既有授权Bug连续两次读取及既有测试Stack元数据一次。不读真实图片/日志，不调用构建部署。结果只保存状态/计数/身份/Schema摘要，不保存业务正文或凭证。桌面连接重载与实际调用另外验收。

## Cursor重载与复验

1. 在目标业务窗口检查用户级dce条目指向本仓库绝对Python和serve_dce_local.py，包含原有配置/凭证/Catalog路径及全部scope，另有三个--require-platform。不要换回无配置CLI入口。
2. 保存该窗口工作，在MCP面板停用dce，等待该连接断开，再执行Developer: Reload Window；启用dce并新建Agent会话。当前聊天中的旧工具描述不能作为重载结果。
3. 在dce输出中核对新的mcp_start：version=1.1.1、configured=gitlab,portainer,zentao、pid及schema摘要。初始化、九工具_meta.dce.runtime和调用结果应指向同一PID/Schema；若Host隐藏_meta，使用响应文本中已有request_id对应stderr的mcp_call。
4. 重新发现portainer_query：operation枚举含service_logs，契约2.2。仅查询原来已授权的资源一次核对调用PID；不发日志查询。不因为新Bug被scope拒绝而扩权。

共享MCP宿主可能保留其他窗口引用的旧定义。只重载目标窗口，不按“所有Python/DCE进程”批量终止；仅当日志/启动定义/窗口关联均证明是本轮遗留且没有其他窗口引用时，才可单独清理。旧PID仍存活不代表目标窗口仍在使用它，新PID存活也不代表一次桌面调用成功。

日志grant仍需管理员明确确认后单独审批--portainer-log-scope；本轮只补参数解析，没有配置该授权。若要回滚，从私有备份提取并仅恢复dce条目，比较其他条目后操作，不整文件覆盖用户随后对其他MCP的修改。
