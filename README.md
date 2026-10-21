# idea

个人使用的跨行业副业研究库，重点关注 AI 带来的变化与机会。约束：每天两小时，启动预算一万元以内。

工作顺序：交流网站收录 → 讨论采样与需求核验 → 机会评分 → 小规模验证。

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

已配置当前聊天循环任务：每天北京时间 21:00。任务会核验、去重并推送研究文档；没有有效机会时允许零新增。

先集中收集，再增量更新；重质量和行业覆盖，不按数量凑目标。本机只读研究看板已可运行；收藏、忽略和准备验证仍待私人状态接口接入。

提交说明、变更记录及收集内容统一使用中文，专有名词除外；历史资料同样修正。原始链接、稳定 ID 和技术字段保持准确，详见 [中文书写约定](AGENTS.md#中文书写约定)。

## 可视化看板

在仓库根目录启动：

```bash
cd /data/code/idea
PYTHONPATH=src python3 -m local_web --root . --host 127.0.0.1 --port 8765
```

浏览器打开 `http://127.0.0.1:8765/`。需要同一局域网的其他设备访问时，改用 `--host 0.0.0.0`，再访问 `http://电脑局域网IP:8765/`。当前没有登录保护，只应在可信局域网使用；页面只读，不提供公网部署。

看板直接读取 `sources/`、`trends/`、`ideas/` 和 `research/STATE.md`，支持搜索、类型/证据/状态筛选和详情查看。修改 Markdown 后刷新页面即可看到新内容，不生成第二份数据副本。详细说明见 [本机看板操作说明](docs/local-web.md)。

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
