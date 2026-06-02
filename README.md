# multi-agent-stock-peeling — A股深度分析多智能体系统

> 备份时间: 2026-06-02 23:41 | 分支: backup-20260602

## 包含技能

| 技能 | 角色 | 行数 | 说明 |
|------|------|------|------|
| `stock-deep-peeling` | 核心分析 | — | 九步扒皮法 v3.2，A股深度股票分析 |
| `stock-deep-peeling-team` | Worker成员 | 190 | 团队模式下成员版分析技能 |
| `team-lead` | 调度者 | 173 | Team-Lead角色约束，Agent组调度 |
| `agent-flow` | 流程角色 | 98 | 任务调度/分配/监控/质量门控 |
| `agent-monitor` | 监察角色 | 84 | 质量审核/分类归档/交叉审核 |
| `agent-tech` | 技术角色 | 66 | 基础设施检查/问题发现/方案设计 |

## 系统架构

```
Team-Lead (调度)
  ├── W1-W4: Team_01 (监控模式, T0032-T0460)
  ├── W1-W8: Team_Upgrade (⚫→A 升级, 3601只)
  ├── Alpha_A-D: 快速突击/接力耐久/严格遴选/跨夜马拉松
  └── Agent Roles: flow → monitor → tech
```

## 辅助基础设施

- `config/flow_memory.md` — 跨组共享流程记忆 (v2.35)
- `agent/data/completed/` — 完成报告目录 (650文件)
- `raw/deep_peel/` — 分级产出目录 (A272/B0/C128/D289/⚫3601)

## 质量标准 (v3.0)

- WS ≥ 12 (WebSearch次数)
- 九步 ≥ 10行/步 (零占位符)
- raw > 5KB (完整报告)
- 全球对标 ≥ 7家
- 政策 ≥ 3维
- gp-94 六实测
