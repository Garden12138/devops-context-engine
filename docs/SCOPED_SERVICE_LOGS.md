# V1.1 Scoped Service Logs 契约与验收边界

状态：离线实现与验收通过；真实日志接口 `not_verified`。仅扩展 `portainer_query(operation="service_logs")`；九工具、Project Schema V2、Host 推理职责不变。包版本 1.1.0，Portainer 事实契约 2.2，其他工具 revision 保持。

## 授权与身份

已有 `--live --read-only --portainer-endpoint E --portainer-stack S` 之外，必须显式设置 `--portainer-log-scope E:S`。此参数是日志读取的独立授权声明，只应用于已获授权的测试环境。空授权拒绝请求，不读取凭证文件、不探测日志权限。调用仍需配置的 `instance`。

先 GET Stack（Id、Type=1、EndpointId）、当前 Swarm Cluster.ID，核对 SwarmId；再核对真实 Service.ID、Spec.Name 与 `com.docker.stack.namespace`。`service_name` 为精确 Compose key，按可信 Stack namespace 解析为完整 Swarm 名称，服务端 name/label filters 后仍做精确核对；或提供完整 `service_id`，二者恰好一个。不按 test 名称推断环境。只通过现有 Portainer Docker API proxy GET，不使用 SSH、Socket、容器日志替代接口或远程写操作。

## 输入与限制

新增参数：`start_time`、`end_time`（必须 RFC3339、显式时区、最多纳秒；半开区间 [start,end)，0 < 窗口 <= 900 秒）；`keywords=[]`（最多 8 个非空字面字符串，每个 <=64 字符，大小写不敏感 OR 匹配）；`max_lines=100`（1–500）；`max_bytes=65536`（1024–262144，原始日志 payload 接收上限）；`max_output_bytes=8192`（4096–16384，完整 MCP CallToolResult 双份 JSON 上限，同时受全局 output_budget 限制）；`timeout_seconds=10`（>0，<=15，单次日志 HTTP 请求的总截止时间；元数据请求沿用既有 Reader 的 timeout/有限重试）。全局 output_budget <4096 时拒绝读取。禁止 follow 参数，分页只接受 page=1；通用 limit 不参与日志裁剪。HTTP 库可能预取固定传输缓冲，应用只接收/解析 max_bytes 内的原始 payload；不宣称可精确控制内核收到的网络包字节数。

官方服务日志接口没有 until/关键词过滤，因此只发送 since、tail、follow=false、stdout/stderr、timestamps=true、details=true。需要 API >=1.30；按 /version 协商明确版本。不支持必要过滤参数时停止，不去掉过滤重读。日志 GET 不重试。拒绝压缩流，原始数据只在受限内存处理；到字节/时间上限立即关闭。处理 8 字节 stdcopy 头、跨 chunk/frame UTF-8 与行边界、stdout/stderr、TTY combined、纳秒时间戳和 URL 编码的 Task context；Systemerr 是错误，不能当作普通 stderr。

依据：[Docker service logs](https://docs.docker.com/reference/cli/docker/service/logs/)、[Docker Engine API](https://docs.docker.com/reference/api/engine/version/v1.48/)、[Moby 日志编码](https://github.com/moby/moby/blob/v27.5.1/api/server/httputils/write_log_stream.go)。

## 输出与失败

沿用 FactData 来源、observed_at、revision、evidence 和不可信数据标记。日志记录包含 query、identity、events、summary、outcome、error_type、truncated、限制/遗漏、retention 状态。日志不落盘、无原文引用、无任意自由文本。仅固定词汇的事件/级别/常见异常/HTTP 状态和关联摘要出现在事件中；关联 ID 使用进程内随机密钥 HMAC，可跨服务匹配同一次会话，进程重启后变化。额外 details、URL、请求体、Header、Cookie、Token、密码、个人信息均省略，不依靠正则宣称任意文本已安全脱敏。服务身份来自已验证元数据；Task context 只保留严格格式 ID。摘要是确定性投影，不是根因推断；未知信息返回 omitted/unclassified。

区分：`matched`、`no_match_in_retained_logs`、`empty_retention_unknown`、`truncated`、`error`。空响应不能证明没有权限或已过期；retention 默认 not_verified。只有明确上游过期错误才标 `LOGS_EXPIRED`；明确驱动错误标 `LOG_DRIVER_UNSUPPORTED`；权限/认证、过滤不支持、格式错误、超时、中断分别给出固定 error_type。部分读取即使没有命中也不能报告真正无匹配。达到 tail 数量保守标记可能缺失，不能保证历史完整。输出裁剪保留查询范围与错误，不无声丢弃。service_logs 专属错误允许 status=error 时附 FactData；原操作错误 data=null 不变。error_type 在顶层 error.code 和记录中保持一致；失败不生成成功观测 evidence。

## 预定测试

合成 HTTP / stdio：正常、多 Task、纳秒/时区、分帧/UTF-8/TTY、窗口/行/字节/完整输出预算、Stack/Endpoint/Swarm/label/ID 失败闭合、独立日志授权、401/403、驱动/过期、空/无命中/尾部截断、自由文本/凭证/PII/提示注入不外泄、超时/慢流/取消/中断/Systemerr/无安全降级，以及原九工具契约回归。禁止主动制造审核事件。

当前未取得明确的真实日志读取权限证据，使用 Mock 验收；不读取本机 .env/Token/私有日志或业务目录。真实环境需要管理员确认日志权限后，仅对用户授权测试 Stack 做一次短窗口有限验证。

## 实际 MCP Schema 与 Cursor 使用

完整运行时输入 Schema：[portainer-query.schema.json](../schemas/portainer-query.schema.json)。它由 `PortainerQuery.model_json_schema()` 导出，包含旧操作及条件必填/互斥约束；跨字段时间差由运行时验证。

| 字段 | 类型 / 默认 | service_logs 约束 |
|---|---|---|
| instance | string，必填 | 与现有连接配置完全相同 |
| operation | string，必填 | service_logs |
| endpoint_id / stack_id | string，必填 | 元数据 allowlist 和日志 pair 同时授权 |
| service_name / service_id | string / null | 恰好一个；Compose key / 完整 Docker Service.ID |
| start_time / end_time | string，必填 | 显式时区，半开窗口 <=15 分钟 |
| keywords | string[]，[] | <=8 个；每个 1–64 字符、非空白、无控制符；literal OR |
| max_lines | integer，100 | 1–500，服务端每 Task tail 和输出事件上限 |
| max_bytes | integer，65536 | 1024–262144，原始 payload 上限 |
| max_output_bytes | integer，8192 | 4096–16384，完整双份 MCP JSON 上限 |
| timeout_seconds | number，10 | 0 < 值 <=15，总日志 HTTP 截止时间 |
| page / limit | integer，1 / 20 | page 只能 1；limit 保留兼容，日志用 max_lines |
| namespace | null | 从真实 Stack 与 Service label 校验，不接受覆盖 |

在现有 stdio 启动参数追加已批准的日志 pair，例如合成配置 `--portainer-endpoint 1 --portainer-stack 7 --portainer-log-scope 1:7`；保留已有 `--live --read-only` 与凭证注入方式。先由管理员确认该账号对目标 Environment/Stack 及 Docker service logs 的读取权限。不要将实际 Token 放入 MCP 参数、提示词或本文件。升级使用源码入口的 `.venv` 无需独立服务；若使用已安装 wheel，先安装新 1.1.0 wheel。关闭再开启 Cursor 的 DCE MCP 连接，重新枚举仍为九工具，portainer_query 的 meta.contract_revision=2.2，service_logs.availability 只说明配置状态，不证明上游权限。

下例只用合成身份和时间；在 Cursor 内将 instance、Stack、服务 key 和审核事件时间替换为已经批准的实际值。一个服务一次调用；第二个服务使用相同窗口和审核事件关键词，不自动扩展查询范围。

```json
{
  "instance": "portainer",
  "operation": "service_logs",
  "endpoint_id": "1",
  "stack_id": "7",
  "service_name": "template",
  "start_time": "2026-11-01T10:00:00+08:00",
  "end_time": "2026-11-01T10:01:00+08:00",
  "keywords": ["synthetic-review-event-123"],
  "max_lines": 20,
  "max_bytes": 16384,
  "max_output_bytes": 8192,
  "timeout_seconds": 5
}
```

读取匹配不到时先看 outcome/error_type/truncation_reasons/retention；不能从空结果推断回调未发生。老窗口常被较新的有限 tail 挤出，这是有界降级的已知限制。省略原始错误文本是默认安全契约；如固定摘要不足以定位，只能另行申请人工本地日志审查，不在此能力放开任意原文。
