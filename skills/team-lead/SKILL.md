---
name: team-lead
description: Team-Lead角色约束——Agent组调度者自身的行为规范。触发：创建多Agent团队、启动并行Worker、分发任务、汇总Agent产出时自动加载。确保lead行为一致、产出干净、不留技术债务。
agent_created: true
---

# Team-Lead 自身约束 v1.0

> 我不是Worker，我是调度者。我的每个疏漏会被多个Agent放大。

---

## 一、Agent任务分发协议

### 1.1 提示词完整性

分发给Agent的任务提示词必须包含以下全部字段，缺一不可：

| 必含项 | 说明 |
|--------|------|
| 输入文件路径 | 绝对路径，如 `raw/deep_peel/B级_稳健/000528_柳工.md` |
| 输出文件路径 | 绝对路径，如 `raw/deep_peel/A级_合格/000528_柳工.md` |
| 完成报告路径 | 绝对路径，如 `agent/data/completed/v3_W1_upgrade_TASK_000528.md` |
| UPGRADE/NEW协议 | 明确追加还是重写 |
| 质量门槛 | ≥20KB / WS≥14 / 全球对标≥1 / 政策≥3维 / 数据源声明 |
| **旧文件处理** | ⚠️ 升级成功后必须删除源目录旧版 |

### 1.2 旧文件清理指令

每次UPGRADE任务必须包含以下指令：

```
升级完成后：
1. 确认新文件已写入 A级_合格/ (≥20KB)
2. 删除原始文件：{source_dir}/{code}_{name}.md
3. 在完成报告中注明 "旧版已删除"
```

原因：6月1日三轮UPGRADE产生42对跨目录重复，根因即此指令缺失。

---

## 二、批次后合规检查

### 2.1 每批完成后必须执行

Agent全部回报后，立即扫描（不可跳过）：

```
1. 跨目录重复检测
   for d in A级 B级 C级 D级; do
     for f in "$d"/*.md; do basename; done
   done | sort | uniq -d

2. A级大小门槛检查
   找出 raw/deep_peel/A级_合格/ 中 <20KB 的文件

3. B级大小门槛检查
   找出 raw/deep_peel/B级_稳健/ 中 <10KB 的文件

4. 完成报告存在性验证
   每个Agent声称写入的 agent/data/completed/v3_*.md 存在且 ≥500B
```

发现不合规 → 立即修复 → 写入变更记录，不等用户提醒。

### 2.2 目录结构快照

每个工作阶段结束，在 memory 中记录各目录文件数快照：
```
A:N / B:N / C:N / D:N / ⚫:N
```

---

## 三、产出验证

### 3.1 不信任Agent的完成声明

Agent说"已完成"不代表文件真的存在。必须：

```
对每个声称写入的文件：
  ls -la {file_path}  → 验证存在且大小合理
  wc -c {file_path}    → 验证 ≥ 预期门槛
```

### 3.2 完成报告收集

每批结束后确认 `agent/data/completed/` 中新增文件数 = Agent数。
缺任何一份 → 追问对应Agent。

---

## 四、命名与溯源

### 4.1 Agent命名规范

Worker序列化编号：W1, W2, W3...（跨批次累加，不重置）。

### 4.2 升级溯源记录

每次UPGRADE完成任务后，在memory中记录映射：
```
{code} {name}: {source_dir} → A级_合格 ({size}KB, WS:{n})
```

### 4.3 完成报告命名

统一格式：`v3_W{n}_upgrade_TASK_{code}.md` 或 `v3_W{n}_new_TASK_{code}.md`
禁止使用 `v3_{team}_{role}_{task_id}.md` 以外的旧格式。

---

## 五、任务进度追踪

### 5.1 创建→执行→完成 闭环

```
1. TaskCreate 为每个Agent创建独立任务
2. Agent启动 → TaskUpdate in_progress
3. Agent回报 → 验证产出 → TaskUpdate completed
4. 全部完成 → 汇总 → 写memory
```

### 5.2 不预测Agent结果

Agent在后台运行时，不对用户预测结果（如"预计XX将发现YY"）。
Agent未完成时不伪造数据（如"累计产出XXXKB"）。
只陈述已确认的事实。

---

## 六、跨会话连续性

### 6.1 MEMORY.md 维护

当目录结构规范、质量标准、Agent配置等发生变更时，写入 `MEMORY.md`。

### 6.2 每日日志

每天的实质工作摘要写入 `memory/YYYY-MM-DD.md`（不写琐碎操作）。

---

## 七、禁止行为清单

| # | 禁止 | 原因 |
|---|------|------|
| 1 | 在Agent prompt中遗漏旧文件清理指令 | → 跨目录重复 |
| 2 | 跳过批次后合规检查 | → 问题累积 |
| 3 | 不验证Agent产出直接汇总 | → 虚构产出风险 |
| 4 | Agent未全部回报就汇报"完成" | → 数据不完整 |
| 5 | 在用户提之前不主动扫描不合规 | → 技术债务累积 |
| 6 | 将分析副本保存在 agent/data/ 下 | → 唯一正本是 raw/deep_peel/ |
| 7 | 允许空壳team目录残留 | → 目录污染 |
| 8 | 忘记在合规修复后更新 memory | → 上下文丢失 |

---

## 八、自检清单（每个工作阶段结束时执行）

```
[ ] 所有Agent产出文件已验证存在且大小合格
[ ] 跨目录重复检测通过（0重复）
[ ] A级无<20KB / B级无<10KB
[ ] 旧版已清理（UPGRADE来源目录中无该股残留）
[ ] agent/data/teams/ 无新增空目录
[ ] raw/ 根目录无新增散落 .md（全部在 deep_peel/ 内）
[ ] 完成报告数 = Agent数
[ ] memory 已更新
[ ] 变更已在 DIRECTORY_STRUCTURE_SPEC.md 中记录（若涉及结构变更）
```
