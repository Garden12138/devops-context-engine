# 本地产品验收契约

本轮沿用 T0→T7：基线和依赖 → Adapter → 发现 → Catalog → 关系审核 → CLI → MCP → 产品验收。新增的是验收编排，不改变业务授权、九工具或版本 1.1.1。

`uv run --offline python scripts/run_acceptance.py` 是完整离线入口。首次安装先运行 `uv sync --locked --dev` 填充依赖缓存。验收使用独立临时目录、合成 fixtures/HTTP 服务和清除业务配置的子进程环境；Python 子进程仅允许 loopback 连接，uv 强制 offline。不会打开用户凭证、真实项目、`.local` 或 `.dce`。

阶段独立记录命令、退出码、耗时、状态和受控诊断：Python/锁一致性、锁定安装、Ruff、strict Mypy、完整 pytest/coverage、当前索引安全检查、工作树敏感路径检查、Wheel、锁定运行依赖隔离安装、CLI 和 Wheel MCP STDIO。完整测试只运行一次；功能分类直接从本次 JUnit 用例派生，不用历史摘要补结果。

PASS 表示命令成功且必需产物有效；FAIL 表示代码、断言或契约错误；BLOCKED 表示命令不可用、超时或离线依赖缺失；NOT_RUN 表示依赖阶段失败或外部现场项。任何必需阶段非 PASS，整体退出非零。不隐藏失败、跳过或降低既有覆盖率门槛。测试总数包括 skipped/errors，每个用例只计一次；分类可重叠且不相加。

每轮新建临时目录，禁止读取旧 XML/coverage。机器摘要与 Markdown 报告覆盖为本次结果，保存 Git HEAD、dirty 状态、被测实现摘要、Python/依赖版本、失败 node ID 和有界合成断言原因、分类与外部未验证项。运行日志仅驻本轮临时目录，结束自动清除；报告不嵌入原始 stdout/stderr 或环境变量值。报告 HEAD 指向执行时提交，报告自身随后提交不会被伪称已测试；实现摘要用于核对代码一致性。

Host 初始化验收是合成 Host harness：仓库/模块发现、关系候选、证据、proposed、人工审核元数据校验、project.yaml 保存/复读/跨工作区隔离、增量 stale/conflict。它不能证明模型推理正确或真实人已审批。DCE 不写业务工作区。

Cursor SDK STDIO 测试覆盖真实本地子进程、握手、九工具/Schema、多次调用、参数/错误、版本/PID/request_id、stdout 协议和 stderr 隔离。Cursor 桌面 UI 重载、模型可见图片、本轮真实平台读取、真实 Token 过期恢复均为 NOT_RUN / not_verified。旧 Gate A/B 仅是带原时间的历史证据。

新增编排器必须测试失败命令、超时清理、缺失/损坏测试产物与跳过处理，防止“执行失败但报告通过”。

CI 缓存边界：允许继承非秘密 `UV_CACHE_DIR`，确保离线子进程使用依赖准备阶段实际填充的同一缓存；仍剔除 DCE/业务凭证、代理和其他 UV 配置，不回退联网或复制现有 site-packages。回归测试必须让子进程实际从自定义缓存读取合成准备标记，同时确认业务凭证未继承。GitHub CI 的本轮报告输出到独立 runner.temp 目录，只上传本轮生成的两份摘要，不能上传 checkout 中的旧报告冒充本次结果。
