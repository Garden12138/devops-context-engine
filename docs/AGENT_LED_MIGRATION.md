# 从全局 Catalog 迁移至项目关系

新架构以 Host 当前业务工作区的 `.dce/project.yaml` 为关系记录。现有 Catalog 保留为资源缓存和历史数据；旧消费者可继续使用原六 MCP 工具与 mapping CLI，不自动删除表、关系、人工审批或证据。

迁移前停止访问同一数据库的旧 DCE 进程，确认数据库位于安全私有目录。第一次以新版本打开旧 Catalog 并升级至 head 时，先通过 SQLite online backup 在库旁 `backups/catalog-*.sqlite3` 创建 0600 备份，目录 0700；quick_check 成功后才运行 0003。备份失败则升级停止。迁移仅新增 catalog_metadata，role=resource_cache_and_history、relationship_authority=host_project_context；原 Entity/Edge/Evidence/Approval/History 保留原值。新库直接建立该角色。不要把真实库放进 Git。

已实现命令：`dce --catalog <private-cache> catalog status` 查看角色，`dce --catalog <private-cache> catalog backup` 额外备份（注意任何首次打开旧库的命令都会先触发上述安全迁移）。升级不承诺两个进程同时迁移同一个库；应先停用该 MCP 连接再升级。

Host 对旧库只做按项目范围取证：读取旧资源与边、保存来源实例/历史 revision/observed_at 和证据位置；人工确认也只视为历史审批。Host 必须核对当前 workspace、重新读取必要平台事实，生成 proposed/unresolved/stale/conflicted，再按当前用户确认写入项目文件。DCE 不自动把全局关系复制到任意业务目录，不把全局 confirmed 自动升级为项目 confirmed。

默认 `init`/`discover` 不再生成业务语义候选。旧自动化若确实依赖旧规则候选，可显式使用 `init --legacy-mapping` 或既有 `mapping suggest --offline`；这是历史兼容入口。确定性技术事实仍保留。旧六工具本轮不移除，未来弃用需独立版本变更和验收。

回滚：停止使用该库的所有进程，保留迁移后副本，在安全本地目录用升级前备份恢复到独立库，再用旧版本指向恢复库。不要覆盖唯一备份或一边运行 MCP 一边替换 SQLite；若启用 WAL，需使用 SQLite backup API，不能仅复制正在写入的主文件。数据库 downgrade 命令不执行删表回退。

本轮迁移完整性由合成旧库测试证明，未选择/改动用户真实 Catalog。已有真实验收报告按其原版本/采集时间保留，不能当作新版真实平台/Host 成功证据。
