# Batch Summary Report

## Overall Summary

- Raw signals: 80
- Normalized signals: 80
- Pain points: 72
- Quarantined items: 8
- Demand clusters: 70
- Singleton clusters: 68
- Merge candidates: 102
- Reviewed groups: 0
- Calibration reviews: 9
- Cluster reviews: 0
- Merge reviews: 0
- Generated at: 2026-06-10T16:21:09Z

## Batch Breakdown

### batch_stage26_agent_workflow

- Raw signals: 12
- Pain points: 11
- Quarantine rate: 8.3%
- Demand clusters: 10
- Singleton clusters: 9
- Merge candidates: 14
- Reviewed groups: 0

Extraction Quality:
- Good: 0
- Weak: 0
- False positive: 0
- Bad quote: 1
- Should quarantine: 0

Observations:
- 抽取产出率：91.7%；单证据主题比例：90.0%；合并建议密度：140.0%。

### batch_stage26_ai_research

- Raw signals: 15
- Pain points: 13
- Quarantine rate: 13.3%
- Demand clusters: 13
- Singleton clusters: 13
- Merge candidates: 29
- Reviewed groups: 0

Extraction Quality:
- Good: 2
- Weak: 0
- False positive: 0
- Bad quote: 0
- Should quarantine: 0

Observations:
- 抽取产出率：86.7%；单证据主题比例：100.0%；合并建议密度：223.1%。

### batch_stage26_content_workflow

- Raw signals: 12
- Pain points: 12
- Quarantine rate: 0.0%
- Demand clusters: 11
- Singleton clusters: 10
- Merge candidates: 24
- Reviewed groups: 0

Extraction Quality:
- Good: 1
- Weak: 0
- False positive: 0
- Bad quote: 0
- Should quarantine: 1

Observations:
- 抽取产出率：100.0%；单证据主题比例：90.9%；合并建议密度：218.2%。

### batch_stage26_devtools

- Raw signals: 12
- Pain points: 11
- Quarantine rate: 8.3%
- Demand clusters: 11
- Singleton clusters: 11
- Merge candidates: 19
- Reviewed groups: 0

Extraction Quality:
- Good: 1
- Weak: 0
- False positive: 0
- Bad quote: 0
- Should quarantine: 0

Observations:
- 抽取产出率：91.7%；单证据主题比例：100.0%；合并建议密度：172.7%。

### batch_stage26_enterprise_knowledge

- Raw signals: 16
- Pain points: 16
- Quarantine rate: 0.0%
- Demand clusters: 16
- Singleton clusters: 16
- Merge candidates: 29
- Reviewed groups: 0

Extraction Quality:
- Good: 3
- Weak: 0
- False positive: 0
- Bad quote: 0
- Should quarantine: 0

Observations:
- 抽取产出率：100.0%；单证据主题比例：100.0%；合并建议密度：181.2%。

### batch_stage26_noise

- Raw signals: 13
- Pain points: 9
- Quarantine rate: 30.8%
- Demand clusters: 9
- Singleton clusters: 9
- Merge candidates: 16
- Reviewed groups: 0

Extraction Quality:
- Good: 0
- Weak: 0
- False positive: 0
- Bad quote: 0
- Should quarantine: 0

Observations:
- 抽取产出率：69.2%；单证据主题比例：100.0%；合并建议密度：177.8%。

## Quality Matrix

| Batch | Raw | Pain Points | Quarantine Rate | Clusters | Singleton Rate | Merge Candidates | Reviewed Groups | Notes |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| batch_stage26_agent_workflow | 12 | 11 | 8.3% | 10 | 90.0% | 14 | 0 | 主题仍偏分散 |
| batch_stage26_ai_research | 15 | 13 | 13.3% | 13 | 100.0% | 29 | 0 | 主题仍偏分散 |
| batch_stage26_content_workflow | 12 | 12 | 0.0% | 11 | 90.9% | 24 | 0 | 主题仍偏分散 |
| batch_stage26_devtools | 12 | 11 | 8.3% | 11 | 100.0% | 19 | 0 | 主题仍偏分散 |
| batch_stage26_enterprise_knowledge | 16 | 16 | 0.0% | 16 | 100.0% | 29 | 0 | 主题仍偏分散 |
| batch_stage26_noise | 13 | 9 | 30.8% | 9 | 100.0% | 16 | 0 | 隔离比例偏高，建议复核样本质量 |

## Stage 3 Readiness

- Is sample size sufficient? yes
- Is extraction quality acceptable? yes
- Are clusters sufficiently converging? no
- Are reviewed groups enough? no
- ready_for_truth_scoring: partial
- Recommendation: 已有部分基础，但建议继续补充人工审核或调校聚类/合并建议后再进入真值评分。
