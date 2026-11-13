# Gate B 临时精确日志授权与预检契约

本文件定义预检阶段边界：预检时真实日志调用必须为零，不重跑Gate A、不改其他平台scope。后续独立执行阶段已完成一次获准读取并撤销，最终结论见[脱敏验收摘要](../harness/v1.1-final-acceptance.md)。企业身份和临时授权文件仅在忽略的本地受保护目录；公开fixtures全部合成。

## 原语义与最小扩展

单独--portainer-log-scope ENDPOINT:STACK是Stack级日志授权，会允许该Stack内任意服务，不满足精确单服务的一次性授权。保留原参数兼容，仅为本轮增加--portainer-log-policy ABSOLUTE_FILE，且同时要求原Endpoint/Stack元数据及日志pair授权。CLI与本地凭证入口加载同一策略；请求不能选择或关闭策略。

策略固定Portainer来源实例、Endpoint、Stack ID/真实Name、Swarm ID、namespace、完整Service ID、Compose key及完整Swarm Service Name。名称输入仅接受精确Compose key；ID输入仅接受钉住的完整ID。其他选择器在创建Reader前拒绝。远程元数据解析后再次比对实际Stack/Service/Swarm/标签/精确身份，不能只依赖名称前缀；被重建或换名的Service不继承授权。

## 服务器约束

临时策略最多存活1小时、max_uses固定1。每次请求检查私有文件内容、权限、有效期和已用标记；撤销/改动文件立即使旧进程失效。真正日志GET之前，以同一目录中与grant_id绑定的O_EXCL文件原子预占额度，同一配置文件的多个进程/窗口/重启共用。失败、超时或中断也消耗唯一尝试；不删除标记重试。文件系统错误一律拒绝，无开放回退。

窗口最长300秒，必须显式带时区。超过300秒拒绝；对合法窗口与执行时最近300秒求交集，未来或无交集窗口拒绝。额度预占前再次按服务器当前时间收紧，避免元数据读取延迟导致越界。行数最多20，原始字节默认16384/上限65536，完整输出最多8192字节，日志GET总超时最多10秒；可更严格。follow参数仍不开放，任意follow输入由Schema拒绝，Docker GET始终follow=false且不重试。

临时授权的Docker整数since向上取整，不多读窗口之前的不足1秒；可能少取窗口开头不足1秒。Docker API未提供until，仍沿用有限tail/原始字节/总流超时，再在内存中按精确半开时间窗口过滤，不能视为完整历史检索。原始字节限制约束保留和解析的payload；传输层缓冲存在有限开销，不等于精确的网卡字节计量。

## 配置格式（全部合成）

两个启动入口都支持以下组合，真实文件仅在受保护本地目录：

```text
--portainer-log-scope 1:7
--portainer-log-policy /absolute/private/service-log-grant.json
```

策略为UTF-8 JSON，父目录0700、文件0600、当前用户所有，拒绝直接symlink、重复key、未知字段及超过8192字节的文件。完整字段和严格类型见 `GrantSpec`；实际身份由授权元数据核对后写入，不能猜测Service ID或Swarm ID。

```json
{
  "version": 1,
  "grant_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "source_instance": "unit",
  "endpoint_id": "1",
  "stack_id": "7",
  "stack_name": "demo",
  "namespace": "demo",
  "swarm_id": "swarm1",
  "service_id": "svc1",
  "compose_service": "template",
  "service_name": "demo_template",
  "issued_at": "2026-11-01T02:00:00Z",
  "expires_at": "2026-11-01T03:00:00Z",
  "max_uses": 1,
  "follow": false,
  "max_window_seconds": 300,
  "max_lines": 20,
  "max_bytes": 16384,
  "max_output_bytes": 8192,
  "timeout_seconds": 10.0
}
```

该示例已经过期，只定义格式，不是可用授权。真实策略的source、Endpoint/Stack/Service身份全部精确匹配；不把用户输入的完整Swarm名称当Compose key接受。无策略的旧Stack级配置保持兼容，因此临时授权必须同时附带策略，不能仅使用pair参数。

## 预检与撤销

仅允许本地配置检查、Mock、真实目标元数据GET、实际STDIO握手/tools/list；预检不调用service_logs、不预占真实额度。真实服务元数据只能从当前授权Portainer代理获取，过滤精确name与namespace，再读取唯一完整ID核对；不输出/保存Env、Header、Token或原始响应。

READY要求精确策略与pair同时生效、单次标记未使用、未过期、元数据身份一致、安全负例全部通过、其他MCP/平台授权保持。否则BLOCKED，不用宽Stack grant代替。日志权限/保留期最终结果仍需唯一真实请求观察，不能预先伪报成功。

Cursor重载正确的新进程后，只能对授权目标执行一次本次窗口查询。完成后立即撤销策略文件并删除此次新增的两个启动参数、重载dce；保留已用标记作为消费证据，不把预算重置当作重试。旧进程因文件撤销立即拒绝日志。Gate B是否通过由后续实际验收记录，READY仅代表安全准备就绪。

已消费或到期但格式合法的策略不阻止其他八个工具或Portainer元数据运行；日志操作为blocked。撤销文件后先移除启动参数再重载，否则启动明确失败，不能静默退回宽Stack权限。一次性保证适用于同一受保护策略文件/本机文件系统；有权修改本地授权文件的管理员不是MCP调用者，不能把删除标记或签发新文件当作获准重试。
