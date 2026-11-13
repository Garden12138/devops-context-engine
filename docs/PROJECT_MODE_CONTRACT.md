# Project mode 1.2 契约

T0→T7实施：先状态/失败/授权契约，再本机确认、发现、持久化、入口、STDIO与完整验收。

`--mode project`为显式新模式，启动不绑定业务ID或工作区、不探测平台；旧模式默认legacy，九工具契约兼容。项目模式十工具，增加project_initialize，project_context读取当前工作区文件与状态。工作区优先取Host Roots，多root须显式选择；无Roots时先通过用户确认绑定，不能把Agent的路径参数视为读权限。每个STDIO实例一次绑定一个工作区，roots改变后拒绝查询，需新会话。

只有用户明确提出初始化/刷新时Host才调用begin；新会话、查询Bug和project_context都不能自动初始化。begin需要用户真实确认临时发现范围；30分钟TTL，每平台目录页最多3页，每页20项。仅配置来源，GitLab精确remote对应项目，ZenTao以Bug/关键词定位，Portainer以部署仓库/关键词匹配元数据；未匹配资源不得展开。无分页目录只读一次有界响应，不保证完整。未知、失败、超限如实返回，日志不在发现授权内。

审批优先MCP form elicitation；能力缺失时开启127.0.0.1随机端口本机确认页。10分钟TTL、一次性标识、POST/Origin/CSRF检查，完整展示工作区、提案和资源范围；无截断批准。accept+approve+非空审核人/原因才同意；decline/cancel/timeout均不生效。Agent的confirmed字段不能授权。威胁边界为不可信平台数据/MCP调用者；能够控制本机文件或模拟Host用户交互的操作系统管理员不由本机制认证。

review严格校验ProjectContext、实例、发现资源范围，候选关系保持proposed；用户可单独选择确认关系ID。审批后返回规范文档和随机receipt。Host保存.dce/project.yaml，complete复读规范hash相同才以0700目录/0600文件原子激活私有授权；DCE不写业务目录。cancel/会话重启使未完成receipt失效。已有初始化begin不覆盖，显式refresh才重新发现。既有项目也必须本轮真实审批，不信任文件自带approved_by。

授权绑定规范路径、workspace ID、来源配置身份；每次请求重新读取策略，撤销跨进程生效；project.yaml改变不扩权，context报告changed_pending_review。每workspace独立Catalog/图片目录，旧全局库不导入项目。新资源授权只能来自审批过的发现集合，缺失平台可部分完成。

项目模式Bug查询按项目/产品归属授权，不需固定Bug白名单；同时配置两者必须同时命中。响应ID、归属缺失/冲突拒绝，Execution不当Project。Bug/列表/附件/图片/legacy资源均共享检查，归属校验前不解析正文、不下载图片、不落盘。服务日志默认关闭，项目模式仅接受独立--portainer-log-policy文件并复核其属于已审核项目，不接受宽Stack pair；legacy日志入口保持兼容。

验收：无主动初始化零外部请求；合成Roots/elicitation与本机页面正负例；完整begin→发现→review→Host保存→complete→跨会话两Bug→撤销；双工作区、TOCTOU/篡改/实例变化、部分失败及九工具legacy回归。真实公司平台和真实Cursor UI未运行保持not_verified。完整runner、lint、strict mypy、Wheel、STDIO与GitHub CI据实记录。

## Host Roots 兼容与失败契约（2026-11-13）

首次绑定前，Host宣告Roots但请求超时、响应无法通过SDK校验或方法不支持时，不把该失败当作工作区授权：本会话记录固定warning，改为用户明确指定绝对路径并亲自确认绑定；已有私有授权也不能跳过这次确认。不指定路径返回workspace_selection_required，未确认不得读取项目文件、初始化或访问平台。手动绑定后固定本会话工作区，不反复请求失效的Roots；新MCP会话重新协商。

已经通过有效Host Roots绑定的会话，后续Roots丢失/超时/解析失败必须拒绝当前请求，不静默降为手动授权。有效Roots中请求范围不符、非本机URI和Host明确请求失败仍拒绝。未选择的Root已删除，不应阻止显式选择另一个有效Root；选定路径不存在时返回明确NOT_FOUND。

错误诊断仅记录固定阶段、异常类型及固定原因码，不记录异常正文、根路径、凭证或上游返回。工具结果保留同一个request_id用于关联审计。验收必须覆盖真实STDIO的错误Roots响应、人工确认前零文件读取，以及绑定后的失败不扩权。

项目控制响应只保留本进程审批Broker签发且仍有效的本机approval_url，以及通过完整项目校验和已配置凭证检查的canonical document；普通平台/日志响应仍使用原脱敏器。不能将审核文档中的合法无凭证remote URL改成占位符，否则Host保存后无法通过receipt/hash校验。任何已知凭证出现在项目文档中必须先拒绝，不能通过控制响应绕过凭证边界。
