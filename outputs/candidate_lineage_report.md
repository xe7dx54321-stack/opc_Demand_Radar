# Candidate Lineage Report

## Summary

- lineage_baseline_quality: partial
- Before candidates: 5
- After candidates: 5
- Candidate lineages: 5
- Strong matches: 0
- Weak matches: 5
- Split candidates: 0
- Merged candidates: 0
- Unmatched before: 0
- Missing baseline (new after): 0
- Generated at: 2026-06-15 13:07 UTC

## Lineage Details

### 1. 运营在企业知识工作流中遇到的「知识文档分散、检索困难、依赖人工问询」问题

**Before:**
- Group ID: `ai_cluster_group_000003`
- Title: 运营在企业知识工作流中遇到的「知识文档分散、检索困难、依赖人工问询」问题
- Score: 62.0 [medium]
- Next Action: needs_more_evidence

**After:**
- Group ID: `ai_cluster_group_000003`
- Title: 运营在企业知识工作流中遇到的「文档分散、检索困难、人工整理低效」问题
- Score: 66.4 [medium]
- Next Action: needs_more_evidence

**Match:**
- Match Score: 0.550
- Match Strength: weak
- Match Reasons: group_id 完全匹配 ai_cluster_group_000003; 标题相似度 0.80; 定向信号重叠 0.10
- Targeted Signals: 10 total, 1 matched, 9 unmatched

**Lineage Summary:** 弱匹配（[]）：before score=62.0 → after score=66.4

---

### 2. 研究员追踪AI公司动态时遭遇的「信息分散、手动表格整理低效耗时」问题

**Before:**
- Group ID: `ai_cluster_group_000002`
- Title: 研究员追踪AI公司动态时遭遇的「信息分散、手动表格整理低效耗时」问题
- Score: 55.0 [medium]
- Next Action: needs_more_evidence

**After:**
- Group ID: `ai_cluster_group_000002`
- Title: 研究员追踪AI公司动态时遭遇的「信息分散、人工整理低效耗时」问题
- Score: 46.6 [weak]
- Next Action: keep_watch

**Match:**
- Match Score: 0.550
- Match Strength: weak
- Match Reasons: group_id 完全匹配 ai_cluster_group_000002; 标题相似度 0.80

**Lineage Summary:** 弱匹配（[]）：before score=55.0 → after score=46.6

---

### 3. 投资人在AI产业跟踪中多渠道信息人工收集整理低效问题

**Before:**
- Group ID: `ai_cluster_group_000005`
- Title: 投资人在AI产业跟踪中多渠道信息人工收集整理低效问题
- Score: 51.4 [weak]
- Next Action: keep_watch

**After:**
- Group ID: `ai_cluster_group_000005`
- Title: 开发者在对接工具链/接口时遭遇文档不完整与信息分散问题
- Score: 51.4 [weak]
- Next Action: keep_watch

**Match:**
- Match Score: 0.550
- Match Strength: weak
- Match Reasons: group_id 完全匹配 ai_cluster_group_000005; 标题相似度 0.80
- Drift Flags: group_title_drift
- Targeted Signals: 10 total, 0 matched, 10 unmatched

**Lineage Summary:** 弱匹配（['group_title_drift']）：before score=51.4 → after score=51.4

---

### 4. 运营/研究员在AI智能体工作流中遭遇的「流程不可靠、上下文丢失、人工整理低效」问题

**Before:**
- Group ID: `ai_cluster_group_000004`
- Title: 运营/研究员在AI智能体工作流中遭遇的「流程不可靠、上下文丢失、人工整理低效」问题
- Score: 66.4 [medium]
- Next Action: needs_more_evidence

**After:**
- Group ID: `ai_cluster_group_000004`
- Title: 投资人在AI产业跟踪中面临的多渠道信息人工收集整理低效问题
- Score: 66.4 [medium]
- Next Action: needs_more_evidence

**Match:**
- Match Score: 0.550
- Match Strength: weak
- Match Reasons: group_id 完全匹配 ai_cluster_group_000004; 标题相似度 0.80
- Drift Flags: group_title_drift
- Targeted Signals: 10 total, 0 matched, 10 unmatched

**Lineage Summary:** 弱匹配（['group_title_drift']）：before score=66.4 → after score=66.4

---

### 5. 内容团队在内容选题收集与管理中遇到的「信息分散、人工整理低效」问题

**Before:**
- Group ID: `ai_cluster_group_000001`
- Title: 内容团队在内容选题收集与管理中遇到的「信息分散、人工整理低效」问题
- Score: 74.4 [medium]
- Next Action: needs_more_evidence

**After:**
- Group ID: `ai_cluster_group_000001`
- Title: 内容团队在选题生产中面临的信息分散与人工整理低效问题
- Score: 70.4 [medium]
- Next Action: needs_more_evidence

**Match:**
- Match Score: 0.550
- Match Strength: weak
- Match Reasons: group_id 完全匹配 ai_cluster_group_000001; 标题相似度 0.80; 定向信号重叠 0.40
- Targeted Signals: 10 total, 4 matched, 6 unmatched

**Lineage Summary:** 弱匹配（[]）：before score=74.4 → after score=70.4

---
