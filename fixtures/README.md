# 合成 Fixtures

`synthetic-discovery.json` 是合成数据，不包含公司实际服务名称、内网地址、镜像信息或凭证。它基于架构现象构造验证用例：

- 3 个 Stack 中仅 current Stack 的 Swarm ID 与 Endpoint 匹配；
- Git 当前 Compose 服务数 78，旧 Stack 保存配置 71；
- current Swarm 中业务 Service 78，额外的基础组件 3（总计 81）；
- 78 个业务 Service、73 个不同镜像，5 个镜像分别被两个 Service 复用；
- ZenTao Bug 内嵌两张图片但 files 字段为空；
- GitLab Pipeline 构建报错仅为合成摘要，无真实日志。

实现时可以拆成更精细的 `tests/fixtures/*.json`，但不能把现场环境输出写入这里。
