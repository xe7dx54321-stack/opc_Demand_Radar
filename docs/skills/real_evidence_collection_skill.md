# Real Evidence Collection Skill

## Purpose

Collect real, traceable demand signals for the target direction: **投资人 / 研究员 AI 产业跟踪与项目初筛**.

This skill guides human or AI-assisted evidence collection. Every item collected must have a traceable source (`source_url` or `source_note`). No synthetic or AI-fabricated evidence is allowed.

---

## Target Direction

- **ID**: ai_investment_tracking
- **Title**: 投资人 / 研究员 AI 产业跟踪与项目初筛
- **Target personas**: 投资人, VC/PE 分析师, 产业研究员, AI 行业研究人员, 创业项目筛选人员

---

## Priority Source Types

Collect from these sources, in order of priority:

1. **product_review** — Real user reviews of tools (G2, Capterra, ProductHunt, App Store)
2. **community_discussion** — Reddit, Hacker News, Discord, Slack community threads
3. **github_issue** — GitHub issues describing workflow pain
4. **interview_note** — Anonymized notes from real interviews (must include date, role, context)
5. **case_study** — Customer case studies with workflow details (not just vendor marketing)
6. **pricing_page** — Tool pricing pages (proves paid alternatives exist)
7. **job_posting** — Job descriptions showing investment in manual labor
8. **product_docs** — Tool documentation describing solved use cases
9. **newsletter** — Investment research newsletters mentioning workflow tools
10. **analyst_article** — Industry analyst reports with workflow details
11. **blog_post** — Practitioner blog posts describing personal workflow

---

## Search Queries

### English

```
AI startup tracking workflow pain
VC deal sourcing AI tools review
AI market intelligence workflow investment
investment research information overload tools
startup screening due diligence workflow pain
AI company monitoring tools pricing
VC analyst research automation software
deal sourcing software pricing review
market intelligence platform review G2
portfolio company tracking tools VC
```

### Chinese

```
AI 项目 初筛 投资人 工作流
AI 产业 跟踪 投研 工具
投资人 项目筛选 信息分散 痛点
VC 项目初筛 人工整理 低效
AI 公司动态 监控 工具 价格
投研 自动化 信息源 工具对比
产业研究 多源信息 验证 效率
AI 行业跟踪 投资人 订阅 工具
初筛 尽调 工作流 人力成本
```

---

## Per-Item Checklist

Before collecting each item, confirm all of the following:

1. **Real source?** Is this from a real URL or a real interview?
2. **Who is speaking?** Identify the persona (investor, analyst, researcher, founder, etc.).
3. **What is the scenario?** What task were they doing when they encountered the problem?
4. **What is the pain?** What specific difficulty or inefficiency did they describe?
5. **Current workaround?** How do they solve this today? (manual, spreadsheet, tool X, etc.)
6. **Cost/budget signal?** Did they mention paying for a tool, hiring someone, or spending budget?
7. **Why is this a demand signal?** Not just a trend comment — is there real user friction?

---

## Required Fields

Each collected item must have:

- `source_url` (preferred) OR `source_note` (for interviews)
- `raw_text` >= 80 characters (real quote or faithful summary)
- `source_type` from allowed list
- `persona` (who is speaking)
- `evidence_type` (pain_signal / paid_signal / workaround_signal / business_impact_signal)

---

## Forbidden Practices

- ❌ Do NOT fabricate user feedback with AI
- ❌ Do NOT collect items without a URL or source_note
- ❌ Do NOT use vendor marketing copy as evidence of user pain
- ❌ Do NOT treat trend articles as user pain without direct quotes
- ❌ Do NOT lower quality standards to meet quantity targets
- ❌ Do NOT mark `is_synthetic = true` and submit as real evidence

---

## Quality Bar

Each item should be able to answer: **"Would a skeptical investor accept this as real evidence of pain?"**

If the answer is no — skip it.