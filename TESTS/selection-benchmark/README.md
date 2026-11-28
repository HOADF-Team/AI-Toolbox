# Semantic Skill-selection benchmark

Offline benchmark of manually curated synthetic tasks against explicit planner proposal JSON. It covers every Skill in the current 25-entry catalog: single-Skill, multi-Skill, ambiguous and out-of-scope cases. One deliberately underspecified case is marked needs_human_review and excluded from aggregate metrics.

## Run

```bash
python scripts/skill_selection_benchmark.py --proposals path/to/proposals.json --pretty
python scripts/skill_selection_benchmark.py --proposals path/to/proposals.json --output report.json
```

Proposal format:

```json
{
  "single-01": {"decision":"select", "selected_skills":["automation-vps"], "rationale":"The request explicitly asks for API integration and webhook automation."},
  "ambiguous-01": {"decision":"clarify", "selected_skills":[], "rationale":"The requested crypto analysis type is unspecified."}
}
```

Allowed decisions: select, abstain, clarify. Missing proposal entries are scored as empty selections. The validator checks case schema, known Skill IDs, duplicate IDs and coverage of all catalog Skills.

## Metrics

- Micro precision/recall/F1 over required Skills; acceptable alternatives are permitted but do not increase recall.
- Exact set match; unnecessary and missed Skills per case.
- Ordered-chain accuracy for strict expected order; advisory order is not penalized.
- Abstention accuracy and per-Skill recall.
- Rationale presence only; factual correctness is not automatically judged.

These metrics are signals, not a complete measure of semantic reasoning. Gold labels are manually curated and synthetic and may need expert review. Cases marked needs_human_review are excluded until adjudicated. The benchmark does not call an LLM, select Skills, load manifests, install tools, access networks, or execute workflows. Real LLM evaluation begins only when outputs from an actual connected runtime are supplied.

## Annotation policy

required_skills are necessary; acceptable_skills are plausible but nonessential alternatives; excluded_skills identify clearly irrelevant choices. expected_order is enforced as an ordered subsequence unless order_is_advisory is true. Tool prerequisites in CATALOG/skill-tools.json are not semantic Skill dependencies.

## Safety

Offline and read-only. No package installation, external service, production system, VPS, exchange, account, or credential is touched.
