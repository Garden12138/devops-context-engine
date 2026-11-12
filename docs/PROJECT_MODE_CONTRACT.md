# Project mode 1.2 契约

T0→T7实施：先状态/失败/授权契约，再本机确认、发现、持久化、入口、STDIO与完整验收。

`--mode project`为显式新模式，启动不绑定业务ID或工作区、不探测平台；旧模式默认legacy，九工具契约兼容。项目模式十工具，增加project_initialize，project_context读取当前工作区文件与状态。工作区优先取Host Roots，多root须显式选择；无Roots时先通过用户确认绑定，不能把Agent的路径参数视为读权限。每个STDIO实例一次绑定一个工作区，roots改变后拒绝查询，需新会话。

只有用户明确提出初始化/刷新时Host才调用begin；新会话、查询Bug和project_context都不能自动初始化。begin需要用户真实确认临时发现范围；30分钟TTL，每平台目录页最多3页，每页20项。仅配置来源，GitLab精确remote对应项目，ZenTao以Bug/关键词定位，Portainer以部署仓库/关键词匹配元数据；未匹配资源不得展开。无分页目录只读一次有界响应，不保证完整。未知、失败、超限如实返回，日志不在发现授权内。

审批优先MCP form elicitation；能力缺失时开启127.0.0.1随机端口本机确认页。10分钟TTL、一次性标识、POST/Origin/CSRF检查，完整展示工作区、提案和资源范围；无截断批准。accept+approve+非空审核人/原因才同意；decline/cancel/timeout均不生效。Agent的confirmed字段不能授权。威胁边界为不可信平台数据/MCP调用者；能够控制本机文件或模拟Host用户交互的操作系统管理员不由本机制认证。

review严格校验ProjectContext、实例、发现资源范围，候选关系保持proposed；用户可单独选择确认关系ID。审批后返回规范文档和随机receipt。Host保存.dce/project.yaml，complete复读规范hash相同才以0700目录/0600文件原子激活私有授权；DCE不写业务目录。cancel/会话重启使未完成receipt失效。已有初始化begin不覆盖，显式refresh才重新发现。既有项目也必须本轮真实审批，不信任文件自带approved_by。

授权绑定规范路径、workspace ID、来源配置身份；每次请求重新读取策略，撤销跨进程生效；project.yaml改变不扩权，context报告changed_pending_review。每workspace独立Catalog/图片目录，旧全局库不导入项目。新资源授权只能来自审批过的发现集合，缺失平台可部分完成。

项目模式Bug查询按项目/产品归属授权，不需固定Bug白名单；同时配置两者必须同时命中。响应ID、归属缺失/冲突拒绝，Execution不当Project。Bug/列表/附件/图片/legacy资源均共享检查，归属校验前不解析正文、不下载图片、不落盘。服务日志默认关闭，项目模式仅接受独立--portainer-log-policy文件并复核其属于已审核项目，不接受宽Stack pair；legacy日志入口保持兼容。

验收：无主动初始化零外部请求；合成Roots/elicitation与本机页面正负例；完整begin→发现→review→Host保存→complete→跨会话两Bug→撤销；双工作区、TOCTOU/篡改/实例变化、部分失败及九工具legacy回归。真实公司平台和真实Cursor UI未运行保持not_verified。完整runner、lint、strict mypy、Wheel、STDIO与GitHub CI据实记录。
