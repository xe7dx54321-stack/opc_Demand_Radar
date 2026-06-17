# MVP-D2 Calibrated Query Plan Report

## Summary
- total_queries: 48
- queries_by_seed: {"seed__000001": 12, "seed__000002": 12, "seed__000003": 12, "seed__000004": 12}
- queries_by_connector: {"hacker_news": 44, "rss": 4}
- query_types: {"pain_phrase": 10, "manual_workflow": 15, "complaint_phrase": 5, "spreadsheet_workaround": 8, "workaround_phrase": 6, "buying_intent": 4}

## How V2 Differs From V1
- V2 优先搜索 pain / complaint / workaround / manual workflow，而不是泛泛搜索产品或项目。
- V2 强制保留 seed_id、pain_item_id、query_type 和 source_category，便于后续归因。
- V2 带负向词，减少 recipe、fitness、game、generic chatbot 等域外命中。

## Query Examples
- d2_query_seed__000001__000001 | seed=seed__000001 | hacker_news | pain_phrase | user_discussion | "investment research workflow" "spreadsheet"
- d2_query_seed__000001__000002 | seed=seed__000001 | hacker_news | manual_workflow | workaround_discussion | "investment research workflow" "manual"
- d2_query_seed__000001__000003 | seed=seed__000001 | hacker_news | complaint_phrase | user_discussion | "investment memo" "time consuming"
- d2_query_seed__000001__000004 | seed=seed__000001 | hacker_news | spreadsheet_workaround | workaround_discussion | "VC analyst" "due diligence" "spreadsheet"
- d2_query_seed__000001__000005 | seed=seed__000001 | hacker_news | pain_phrase | user_discussion | "VC analyst" "market research" "pain"
- d2_query_seed__000001__000006 | seed=seed__000001 | hacker_news | complaint_phrase | user_discussion | "portfolio monitoring" "too much information"
- d2_query_seed__000001__000007 | seed=seed__000001 | hacker_news | pain_phrase | user_discussion | "portfolio monitoring" "hard to track"
- d2_query_seed__000001__000008 | seed=seed__000001 | hacker_news | manual_workflow | workaround_discussion | "deal sourcing" "manual research"
- d2_query_seed__000001__000009 | seed=seed__000001 | hacker_news | spreadsheet_workaround | workaround_discussion | "company tracking" "investment analyst" "spreadsheet"
- d2_query_seed__000001__000010 | seed=seed__000001 | hacker_news | manual_workflow | workaround_discussion | "equity research" "data collection" "manual"
- d2_query_seed__000001__000011 | seed=seed__000001 | hacker_news | workaround_phrase | workaround_discussion | "investment analyst" "research workflow" "Notion"
- d2_query_seed__000001__000012 | seed=seed__000001 | rss | buying_intent | comparison_page | "due diligence" "research" "expensive"
- d2_query_seed__000002__000001 | seed=seed__000002 | hacker_news | pain_phrase | user_discussion | "investment research workflow" "spreadsheet"
- d2_query_seed__000002__000002 | seed=seed__000002 | hacker_news | manual_workflow | workaround_discussion | "investment research workflow" "manual"
- d2_query_seed__000002__000003 | seed=seed__000002 | hacker_news | complaint_phrase | user_discussion | "investment memo" "time consuming"
- d2_query_seed__000002__000004 | seed=seed__000002 | hacker_news | spreadsheet_workaround | workaround_discussion | "VC analyst" "due diligence" "spreadsheet"
- d2_query_seed__000002__000005 | seed=seed__000002 | hacker_news | pain_phrase | user_discussion | "VC analyst" "market research" "pain"
- d2_query_seed__000002__000006 | seed=seed__000002 | hacker_news | manual_workflow | workaround_discussion | "deal sourcing" "manual research"
- d2_query_seed__000002__000007 | seed=seed__000002 | hacker_news | workaround_phrase | workaround_discussion | "deal sourcing" "Airtable"
- d2_query_seed__000002__000008 | seed=seed__000002 | hacker_news | spreadsheet_workaround | workaround_discussion | "company tracking" "investment analyst" "spreadsheet"
- d2_query_seed__000002__000009 | seed=seed__000002 | hacker_news | manual_workflow | workaround_discussion | "equity research" "data collection" "manual"
- d2_query_seed__000002__000010 | seed=seed__000002 | hacker_news | workaround_phrase | workaround_discussion | "investment analyst" "research workflow" "Notion"
- d2_query_seed__000002__000011 | seed=seed__000002 | rss | buying_intent | comparison_page | "due diligence" "research" "expensive"
- d2_query_seed__000002__000012 | seed=seed__000002 | hacker_news | manual_workflow | workaround_discussion | "market research" "analyst" "manual"
- d2_query_seed__000003__000001 | seed=seed__000003 | hacker_news | pain_phrase | user_discussion | "investment research workflow" "spreadsheet"
- d2_query_seed__000003__000002 | seed=seed__000003 | hacker_news | manual_workflow | workaround_discussion | "investment research workflow" "manual"
- d2_query_seed__000003__000003 | seed=seed__000003 | hacker_news | complaint_phrase | user_discussion | "investment memo" "time consuming"
- d2_query_seed__000003__000004 | seed=seed__000003 | hacker_news | spreadsheet_workaround | workaround_discussion | "VC analyst" "due diligence" "spreadsheet"
- d2_query_seed__000003__000005 | seed=seed__000003 | hacker_news | pain_phrase | user_discussion | "VC analyst" "market research" "pain"
- d2_query_seed__000003__000006 | seed=seed__000003 | hacker_news | manual_workflow | workaround_discussion | "deal sourcing" "manual research"
- d2_query_seed__000003__000007 | seed=seed__000003 | hacker_news | workaround_phrase | workaround_discussion | "deal sourcing" "Airtable"
- d2_query_seed__000003__000008 | seed=seed__000003 | hacker_news | spreadsheet_workaround | workaround_discussion | "company tracking" "investment analyst" "spreadsheet"
- d2_query_seed__000003__000009 | seed=seed__000003 | hacker_news | manual_workflow | workaround_discussion | "equity research" "data collection" "manual"
- d2_query_seed__000003__000010 | seed=seed__000003 | hacker_news | workaround_phrase | workaround_discussion | "investment analyst" "research workflow" "Notion"
- d2_query_seed__000003__000011 | seed=seed__000003 | rss | buying_intent | comparison_page | "due diligence" "research" "expensive"
- d2_query_seed__000003__000012 | seed=seed__000003 | hacker_news | manual_workflow | workaround_discussion | "market research" "analyst" "manual"
- d2_query_seed__000004__000001 | seed=seed__000004 | hacker_news | pain_phrase | user_discussion | "investment research workflow" "spreadsheet"
- d2_query_seed__000004__000002 | seed=seed__000004 | hacker_news | manual_workflow | workaround_discussion | "investment research workflow" "manual"
- d2_query_seed__000004__000003 | seed=seed__000004 | hacker_news | complaint_phrase | user_discussion | "investment memo" "time consuming"
- d2_query_seed__000004__000004 | seed=seed__000004 | hacker_news | spreadsheet_workaround | workaround_discussion | "VC analyst" "due diligence" "spreadsheet"
