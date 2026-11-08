# idea

个人使用的跨行业副业研究库，重点关注 AI 带来的变化与机会。约束：每天两小时，启动预算一万元以内。

当前研究方式（2026-10-27起）：原始材料复核 → 关键假设与反证 → 交易/交付/回款追踪 → 完整投入 → 私人验证方案。详见[深度研究任务书](docs/intent/deep-opportunity-research.md)。

探索不设固定“两周”期限。默认建议周期为 4–6 周：简单服务型方向可安排 2–4 周，涉及获客、交付、合规或持续维护的方向可安排 6–12 周或更久；每个方向都要写明阶段目标、投入上限、继续条件和暂停条件。

- [已确认需求意图](docs/intent/personal-opportunity-library.md)
- [已确认能力划分](CAPABILITY-MAP.md)
- [资料与历史规格（已批准）](SPEC-records-history.md)
- [来源采集与研究规格（已批准）](SPEC-source-research.md)
- [资料与历史技术计划（已完成归档）](tasks/records-history/plan.md)
- [来源采集技术计划（已批准）](tasks/plan.md)
- [当前来源采集任务清单](tasks/todo.md)
- [项目检验与优化建议（2026-10-21）](docs/project-optimization-review-2026-10-21.md)
- [趋势与灵感](trends/INDEX.md)
- [网站目录](sources/INDEX.md)
- [Agent 工作规范](AGENTS.md)
- [研究执行手册](docs/agent/RESEARCH-WORKFLOW.md)
- [机会索引](ideas/INDEX.md)
- [运行状态](research/STATE.md)

当前聊天循环任务沿用每10分钟一次的心跳，执行深度尽调；实际以自动化配置为准。每轮保留断点和零新增记录，无重要变化保持安静。同步须通过资料检查并遵守工作区边界。

历史集中收集转为深度尽调，原200条目标仅为历史覆盖参照；以关键不确定性是否减少判断进展。看板功能状态与研究结论分开验收，私人操作以实际数据库接口为准。

提交说明、变更记录及收集内容统一使用中文，专有名词除外；历史资料同样修正。原始链接、稳定 ID 和技术字段保持准确，详见 [中文书写约定](AGENTS.md#中文书写约定)。

## 可视化看板

在仓库根目录启动：

```bash
cd /data/code/idea
PYTHONPATH=src python3 -m local_web --root . --host 127.0.0.1 --port 8765
```

浏览器打开 `http://127.0.0.1:8765/`。需要同一局域网的其他设备访问时，改用 `--host 0.0.0.0`，再访问 `http://电脑局域网IP:8765/`。当前没有登录保护，只应在可信局域网使用；页面只读，不提供公网部署。

看板直接读取 `sources/`、`trends/`、`ideas/` 和 `research/STATE.md`，支持搜索、类型/证据/状态筛选和详情查看。修改 Markdown 后刷新页面即可看到新内容，不生成第二份数据副本。需要使用“标记本人不适用”时，追加 `--db .local/records.sqlite3` 指向已迁移的本机 records 数据库；该操作只写私人状态，不修改公开资料。详细说明见 [本机看板操作说明](docs/local-web.md)。

初始化、迁移、后台启动、停止、检查和备份命令见 [部署与运行说明](docs/deployment.md)。

## 资料模块

Python 3.14 标准库实现，无第三方依赖。正式研究仍写 Markdown；数据库迁移尚未切换。

```bash
PYTHONPATH=src python3 -m records --help
PYTHONPATH=src python3 -m unittest discover -s tests/records -p 'test_*.py' -v
python3 -m compileall -q src/records
```

命令支持 init、status、request（JSON 文件）、export/import、backup/restore、legacy-preview/legacy-apply。
私人状态使用 `request --scope personal`；研究入口拒绝私人字段。`.local/` 和 SQLite 文件默认不入 Git。

资料与历史模块的 13 项任务已完成，来源采集模块 R01–R19 已完成。最新检查范围与结果见 [项目检验](docs/project-optimization-review-2026-10-21.md)，后续进度以任务清单为准。接口、迁移、同步和恢复操作见 [操作说明](docs/records-operations.md)。
