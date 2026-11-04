# 用户恢复接续：本地凭证入口（实现前契约）

用户已给出业务工作区，选择 Bug 4300 为真实样本，并说明三平台凭证在仓库 .env，禅道以 v1 账号密码获取 Token。仅由本机受控进程处理该明确提供的凭证源；正文、密码、Token 不进入模型上下文/日志/Git。只检查变量名发现 ZEN_USER/ZEN_PASSWORD/GITLAB_TOKEN/PORTAINER_API_KEY；无 URL 配置。已把文件权限从 0644 收紧到 0600。

Host 已只读识别目标的 20 个 Git roots，抽取 manifest/CI/Dockerfile 白名单事实，形成仅在 .local/agent-led/intake 的画像与空关系草稿；Schema 校验通过。业务目录无 project.yaml，尚未写入；具体路径、名称和 remote 只留私有区，不提交。

边界：默认 dce 不自动加载 .env。提供单独、显式指定 credentials-file/config 的本地 MCP 启动入口；live/read-only 必需。仅解析 dotenv 字面值，不 source、不执行、不插值；只接受受保护的常规文件及已知变量，重复/冲突/格式错误安全失败。使用已有 v1 登录 Adapter，认证只请求一次，不附旧 Token、不自动重试账号密码；Token 仅驻留当前进程 Settings，过期返回 AUTH_FAILED，重启连接再登录，不保存 Token。

启动器复用现有 MCP/FactScope/只读工具，不增加平台业务写接口，不把密码传 argv。全局配置默认保持原行为；只为 load_settings 增加可注入环境，避免修改父进程变量。禅道账号和密码必须成对；HTTP 必须显式配置放行，默认拒绝。stdout 仅 MCP，启动失败为 stderr 固定错误。

测试先行：默认不加载、别名映射、无插值/执行、凭证不出日志/返回/argv/持久化、private permissions/symlink/大小/重复 key 拒绝、缺失 URL/HTTP 未授权零请求、v1 一次 POST 后认证 GET、401 不重试、并行进程环境隔离、CLI/stdout/Schema/只读范围。真实调用等待三平台地址和 Host 条件，不以合成测试声称实测成功。
