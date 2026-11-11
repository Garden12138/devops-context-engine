# 本地凭证入口：历史实现前契约（公开脱敏版）

本文保留显式本地凭证入口的历史实现边界。真实缺陷编号、业务工作区画像、凭证文件状态及逐次采集记录只保留在用户本地受保护证据中，不在公开文档复述。公开测试使用合成账号、地址和资源身份。

项目画像仅抽取manifest、CI、Dockerfile等白名单事实；具体业务路径、名称、remote及关系草稿不进入公共仓库。是否写入业务project.yaml由Host展示diff并取得人工审核，DCE本身不写业务目录。

下文属于认证恢复实现之前的行为契约，当前Token生命周期以[认证恢复边界](../../../docs/ZENTAO_AUTH_RECOVERY.md)为准；本次脱敏不更改历史实现的成功或失败结论。

边界：默认 dce 不自动加载 .env。提供单独、显式指定 credentials-file/config 的本地 MCP 启动入口；live/read-only 必需。仅解析 dotenv 字面值，不 source、不执行、不插值；只接受受保护的常规文件及已知变量，重复/冲突/格式错误安全失败。使用已有 v1 登录 Adapter，认证只请求一次，不附旧 Token、不自动重试账号密码；Token 仅驻留当前进程 Settings，过期返回 AUTH_FAILED，重启连接再登录，不保存 Token。

启动器复用现有 MCP/FactScope/只读工具，不增加平台业务写接口，不把密码传 argv。全局配置默认保持原行为；只为 load_settings 增加可注入环境，避免修改父进程变量。禅道账号和密码必须成对；HTTP 必须显式配置放行，默认拒绝。stdout 仅 MCP，启动失败为 stderr 固定错误。

测试先行：默认不加载、别名映射、无插值/执行、凭证不出日志/返回/argv/持久化、private permissions/symlink/大小/重复 key 拒绝、缺失 URL/HTTP 未授权零请求、v1 一次 POST 后认证 GET、401 不重试、并行进程环境隔离、CLI/stdout/Schema/只读范围。真实调用等待三平台地址和 Host 条件，不以合成测试声称实测成功。
