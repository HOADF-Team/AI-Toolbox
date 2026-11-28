# External AI runtime benchmark integration

## Purpose

This bridge lets a separately hosted AI planner receive benchmark tasks and return Skill-selection proposals that can be scored against the offline gold annotations. It is a transport and evaluation contract, not an AI runtime implementation.

The Toolbox does **not** call an LLM, host a model, load model credentials, or execute Skills. The external host owns model invocation, trusted manifest loading, identity, policy enforcement, and logging.

## Two-step exchange

Pin the exact Personal-AI-Library commit used by the runtime (40-character lowercase Git SHA). Create a unique run ID.

### 1. Export requests

```bash
python scripts/skill_selection_runtime_eval.py prepare \
  --skills-revision <PERSONAL-AI-LIBRARY-COMMIT-SHA> \
  --run-id planner-build-2026-11-28-a \
  --output /tmp/skill-selection-requests.json
```

The exported bundle contains 33 synthetic task requests, candidate Skill IDs, and immutable canonical manifest URLs. It deliberately omits required/acceptable/excluded Skills, expected decisions, annotation rationales, and human-review labels. Do not send `TESTS/selection-benchmark/benchmark.json` or the gold annotations to the planner.

The host should resolve manifests from a trusted checkout at the pinned SHA, read the canonical Markdown, and ask its planner to choose only from the provided Skill IDs. A manifest URL is a reference, not proof that the host fetched or verified it.

### 2. Collect planner responses

The host writes a response JSON file using this schema:

```json
{
  "schema_version": "1.0",
  "run": {
    "run_id": "planner-build-2026-11-28-a",
    "skills_revision": "<same 40-character SHA>",
    "planner_contract_version": "1.0"
  },
  "runtime": {
    "name": "your-host-runtime",
    "planner_version": "git-sha-or-release",
    "model": "optional-model-identifier"
  },
  "responses": [
    {
      "case_id": "single-01",
      "decision": "select",
      "selected_skills": ["automation-vps"],
      "rationale": "The task explicitly requests server automation."
    }
  ]
}
```

Every exported `case_id` must appear exactly once. Allowed decisions are `select`, `abstain`, and `clarify`. Every selected ID must exist in the current Skill map; duplicate and unknown IDs are rejected. Keep the same run ID, manifest revision, and planner contract version. Do not include credentials, user data, hidden chain-of-thought, or sensitive runtime logs. A concise decision rationale is sufficient.

### 3. Score the runtime output

```bash
python scripts/skill_selection_runtime_eval.py score \
  --requests /tmp/skill-selection-requests.json \
  --responses /tmp/skill-selection-responses.json \
  --output /tmp/skill-selection-report.json
```

The report records caller-supplied runtime identity/version, pinned Skill revision, response coverage, micro/macro metrics, per-Skill metrics, abstention and order scores, and limitations.

## Host adapter responsibilities

The host integration should implement these steps without giving the model access to gold annotations:

1. Verify the trusted Personal-AI-Library checkout is exactly the pinned commit.
2. Load canonical `skills/<skill-id>/SKILL.md` files from that checkout; fail closed if any requested manifest cannot be read.
3. Give the planner the task and candidate Skills. The planner emits the strict response object; the host validates schema and Skill IDs before writing it.
4. Store runtime/model/build metadata separately from secrets. Never serialize API keys, passwords, private keys, approval tokens, or customer data into the exchange.
5. Keep benchmark scoring offline and separate from any operational workflow. Benchmark proposals do not authorize tool use or side effects.
6. Retain the raw response bundle and report with access controls appropriate to the task. Runtime identity fields are self-reported unless the host independently attests them.

## Safety and evaluation limits

- No network, installation, VPS, exchange, production, or account action is performed by either CLI.
- The prepare command exports only synthetic tasks and manifest references; the score command reads local JSON.
- The evaluator does not invoke or authenticate the external runtime, and cannot prove that the model read the referenced manifests.
- The model's rationale is scored for presence only; correctness requires human review.
- Synthetic manually curated cases are not a substitute for live user tasks, adversarial evaluation, or independent annotation.
- Human-review cases are omitted from planner requests and aggregate scores until adjudicated.
- A high score is a regression signal, not proof of safe autonomous operation or permission to act.

This bridge makes real planner evaluation possible once an actual host supplies its responses. Until then, unit tests use deterministic synthetic responses and do not represent measured LLM quality.
