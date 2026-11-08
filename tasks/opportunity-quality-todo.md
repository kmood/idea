# 任务清单：副业机会质量、落地与探索升级

依据：[实施计划](opportunity-quality-plan.md)。

## 第一阶段：只读质量审计

- [x] OQ-01：升级点子质量审计器，输出证据、时效、商业信号和行动缺口。
  - 验收：现有 85 条不被改写；每条可得到可解释的缺口和建议 `readinessStatus`。
  - 验证：`PYTHONPATH=src python3 -m unittest tests.research.test_idea_quality -v`。
  - 文件：`src/research/idea_quality.py`、`tests/research/test_idea_quality.py`。

- [x] OQ-02：修复索引证据等级识别并补回归。
  - 验收：`E3历史`、`E3付费意向` 可识别；`E30`、`XE3` 不被误识别。
  - 验证：研究质量测试和 `git diff --check`。
  - 文件：同 OQ-01。

## 检查点一

- [x] records、research、local-web 测试通过。
- [x] 新审计没有写入 85 条点子正文、用户状态或公开导出。

## 后续任务

- [ ] OQ-03：生成批量复核清单，优先国内非技术行业和线下小企业。
- [ ] OQ-04：持久化正式质量字段和历史事件。
- [ ] OQ-05：实现私人获客路径、探索计划和反馈。
- [ ] OQ-06：实现看板质量筛选和最多三条候选比较。
- [ ] OQ-07：完成正式入口切换演练后再评估切换。
