# Skill tool preflight

This is a machine-readable companion to [SKILL-MAP.md](../CATALOG/SKILL-MAP.md). It maps the 23 real Skills to stable AI-Toolbox tool IDs without copying their procedures.

## Run

```bash
python3 scripts/inventory.py --pretty > inventory.json
python3 scripts/match_inventory.py --inventory inventory.json --pretty > matches.json
python3 scripts/check_skill_tools.py --matches matches.json --pretty
# Check only selected Skills:
python3 scripts/check_skill_tools.py --skill web-development --skill seo-audit --matches matches.json --pretty
```

## Result meanings

- `ready`: every declared prerequisite group has at least one detected available tool. This is a preflight result, not a functional test.
- `blocked`: at least one prerequisite group has all alternatives explicitly detected as missing.
- `unknown`: no prerequisite alternative was detected as available, and at least one alternative was not probed or has no inventory evidence.
- `recommended_tools`: advisory only; their absence never blocks a Skill.

In `required_any`, each inner array is an OR group; all groups must be satisfied. An empty list means no mandatory external prerequisite is asserted for that Skill. Do not turn a convenient recommendation into a hard dependency without reviewing the Skill.

Always run inventory in the actual execution target. A GitHub Actions result describes the runner, not a user's workstation, VPS, or another runtime. After preflight, inspect the selected Skill and the relevant TOOL.md records, then perform task-specific checks. A detected executable/module is not proof of working credentials, network access, compatibility, or correct behavior.
