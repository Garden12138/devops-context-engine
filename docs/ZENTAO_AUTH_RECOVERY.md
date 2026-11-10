# V1.1.1 禅道 v1 认证恢复契约

实施边界：仅 DCE 基础设施；不扩大 Bug/Project/Product scope，不改业务项目、远程权限、CI 或部署，不推送。本地 scope 与上游认证是两个独立关卡。实际 Cursor 启动范围的私有核对结果只放 `.local/auth-refresh-v1.1.1/`，公开文档/fixtures 使用合成身份。

## 先行诊断

旧 bug_context 在 McpApplication.dispatch 检查 Bug allowlist，失败直接 PERMISSION_DENIED；事实工具在 Reader 创建前检查 instance 与 FactScope。此类失败不经过 HTTP，不能归因于 Token。旧 local_settings 在进程启动时一次登录并把 Token 放入 SecretStr，后续每个 Reader 复用这个固定值，没有刷新逻辑；NETWORK_UNAVAILABLE 单独表示网络异常，历史失败不能推定为过期。

官方 v1 Entry 未登录返回 HTTP401 + JSON `error=Unauthorized`，方法权限返回 HTTP403 + `error=Access not allowed`。tokens POST 错误密码/锁定可返回 HTTP400，成功201仅返回 token，未提供可信有效期。这是官方接口依据，不冒充当前实例所有版本事实。

来源：[Entry认证/权限](https://github.com/easysoft/zentaopms/blob/main/framework/api/entry.class.php)、[tokens登录](https://github.com/easysoft/zentaopms/blob/main/api/v1/entries/tokens.php)。不复制第三方源码。

## 生命周期与错误

- 复用 credential_environment / local_settings 的既有显式本机凭证来源。默认 dce 不增加隐式 dotenv 加载；地址优先级、HTTP放行、文件0600与字面解析保持。
- local_settings 只建立绑定 instance+base_url 的进程内 Manager，不登录；已授权操作第一次 GET 才登录。Token、账号密码仅存 SecretStr/私有运行属性，不序列化凭证到项目/报告。没有可信期限就不猜测 TTL、不解码 Token 猜有效期。
- 同一 Settings 连接共享 Manager；锁保护首次获取、失效刷新和失败熔断；generation防止旧失败覆盖新Token。独立进程各自登录，无磁盘/跨进程共享。
- 仅严格JSON认证错误允许刷新：401的 `Unauthorized`，以及401/403的明确Token失效代码/固定消息。普通401、业务403、404、HTML、跳转、网络错误不据此猜测过期。
- 每次授权操作最多重放一次原始GET，路径/参数/范围不变；不重放业务POST。登录POST不做网络/状态重试；登录失败按实例锁存，修正配置后重启才能重新尝试。刷新后的Token仍被拒绝也熔断，不无限登录。
- 现有 MCP error.code / error_code / message / retryable 结构保持。AUTH_EXPIRED、AUTH_REFRESH_FAILED是内部原因，外部仍使用AUTH_FAILED并在固定message中标原因；网络错误继续NETWORK_UNAVAILABLE，权限PERMISSION_DENIED，404 NOT_FOUND。无上游正文、凭证、Cookie透传。
- 禅道传输诊断内容整体省略，阻止HTTP debug中的Set-Cookie等泄漏；业务输出还使用本次Reader已用凭证与Manager当前秘密脱敏。

## 错误分类（外部 MCP 枚举不变）

| 实际关卡/响应 | 内部语义 | 对外 code | 恢复行为 |
|---|---|---|---|
| 本地 Bug/资源/instance scope 拒绝 | 授权拒绝 | PERMISSION_DENIED | 无网络、无登录 |
| 401 JSON error=Unauthorized；401/403 严格 Token 失效代码/消息 | AUTH_EXPIRED | AUTH_FAILED（恢复成功时不暴露错误） | 一次 single-flight 登录，再重放原 GET 一次 |
| 普通 403（包括 Access not allowed） | 业务权限不足 | PERMISSION_DENIED | 不刷新、不重试权限 |
| 非明确认证过期的 401 | AUTH_FAILED | AUTH_FAILED | 不推测失效、不刷新 |
| 登录拒绝、密码错误、锁定、登录响应无有效 Token | AUTH_FAILED | AUTH_FAILED | 单次密码提交，进程内熔断 |
| 刷新登录失败 | AUTH_REFRESH_FAILED | AUTH_FAILED；网络故障仍 NETWORK_UNAVAILABLE | 熔断；固定 message 标明刷新失败 |
| 刷新后 GET 仍明确认证失败 | AUTH_EXPIRED | AUTH_FAILED | 不再登录；当前 generation 熔断 |
| 404 | 资源不存在 | NOT_FOUND | 不刷新 |
| 请求超时/断网 | 网络故障 | NETWORK_UNAVAILABLE | GET 原有有界网络重试；登录 POST 不重试 |
| HTML/跳转 | 非预期 JSON / 禁止跳转 | INVALID_PAYLOAD（JSON读取）/UNSAFE_URL | 不据此刷新；图片保留既有格式错误分类 |

精确失效代码为 TOKEN_EXPIRED、INVALID_TOKEN、AUTH_EXPIRED；精确 error 消息为 Token expired、Token has expired、Invalid token、Token is invalid。只处理 401/403 JSON 顶层字段，不扫描资源文本或任意 message。仅对16KiB以内的完整错误正文做JSON认证分类，读取超出解析预算就关闭并按HTTP状态分类，不能从不完整JSON推断过期。它们是保守支持集合；当前实例未观察的变体仍 not_verified。

## 验收

合成测试覆盖懒登录、缓存复用、401/403严格分类、原GET重放、二次失效停止、账号错误/锁定/网络登录失败熔断、并发single-flight/迟到失败、无scope网络零调用、跨实例保护、图片/九工具/service_logs回归与秘密不泄漏。完整回归使用合成HTTP，不调用公司平台。

真实验收仅在现有已授权Bug中选择一个，通过既有入口读取；不查询被本地拒绝的新Bug。不为了测试撤销/过期会话或等待失效；刷新通过Mock验证。进程重启检查只验证新进程首次授权访问可登录。真实HTTP分类只报告实际看到的状态；未见的失效变体保留not_verified。

2026-11-06：完整合成回归357 passed，97.62%，strict mypy53文件、ruff通过；标准SDK stdio合成平台覆盖首次登录和过期恢复。真实既有授权资源：无Token有界GET返回401并命中严格JSON认证规则，登录201、缓存复用两次GET200；独立新进程登录201/GET200。只输出状态/计数，不保存正文、图片、Token或Cookie。真实过期后恢复与真实并发未主动制造，仍 not_verified，Mock验证通过。实际Cursor旧子进程尚未重载。详见 [本轮验收](../harness/zentao-auth-v1.1.1-acceptance.md)。

## 限制与合法扩权

Manager绑定一个 Settings 中的单个禅道连接，锁仅在当前进程共享；多进程不共享 Token。没有可信有效期元数据就按明确失效响应恢复；不猜测服务端TTL或主动刷新。登录失败（含网络不确定性）锁存到进程重启，以避免密码多次提交；这比无限恢复保守。只有直接Token时没有密码可重新登录。

精确 Bug allowlist 与 Project/Product 查询 scope 独立。新Bug被精确入口拒绝时，由人工核对业务归属和授权后，给现有启动配置追加经过批准的精确 --zentao-bug 值并重启；不直接扩大Project/Product、不修改远程权限或project.yaml。当前修复不自动应用扩权建议。
