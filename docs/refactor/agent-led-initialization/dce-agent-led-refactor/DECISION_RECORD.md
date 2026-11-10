# Architecture Decision Record

## ADR-001: Agent owns project relationship reasoning
**Status:** Implemented offline; external acceptance pending

**Decision:** 跨平台业务关系推理和项目初始化由目标项目中的 Agent Host 执行。DCE 只提供安全只读平台能力和证据。

**Consequences:** DCE 模型无关；每个项目有独立关系文件；不再有公司级业务关系全局真相；人工审核仍是模糊关系的必要环节。

## ADR-002: Project context is stored per workspace
**Status:** Implemented offline; external acceptance pending

**Decision:** 使用 `.dce/project.yaml` 保存项目关系，按公司数据策略决定是否提交。凭证永不保存其中。

## ADR-003: Keep DCE V1 read-only
**Status:** Accepted for this refactor

**Decision:** 本次不增加平台写操作、CI 触发、构建、部署或删除工具。后续需单独设计审批和风险控制。

实施证据：[本轮验收](../../../../harness/agent-led-acceptance.md)。当前实际业务工作区/真实 Host/完整模块目录和真实图片仍未通过验收；本地实现不等于整体目标完成。
