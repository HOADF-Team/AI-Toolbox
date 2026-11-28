"""Offline semantic Skill-selection benchmark scorer; never invokes an LLM."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK=ROOT/"TESTS"/"selection-benchmark"/"benchmark.json"
def load_json(path:Path)->dict[str,Any]:
 value=json.loads(path.read_text(encoding="utf-8"))
 if not isinstance(value,dict): raise ValueError(f"{path} must contain a JSON object")
 return value
def validate_benchmark(data:dict[str,Any],catalog:dict[str,Any])->list[str]:
 errors=[]; ids={x.get("id") for x in catalog.get("skills",[]) if isinstance(x,dict)}; cases=data.get("cases")
 if not isinstance(cases,list) or not cases:return ["cases_must_be_non_empty_array"]
 seen=set();covered=set()
 for i,c in enumerate(cases):
  if not isinstance(c,dict):errors.append(f"case_{i}_must_be_object");continue
  cid=c.get("case_id")
  if not isinstance(cid,str) or not cid:errors.append(f"case_{i}_missing_case_id")
  elif cid in seen:errors.append(f"duplicate_case_id:{cid}")
  else:seen.add(cid)
  if not isinstance(c.get("task"),str) or not c["task"].strip():errors.append(f"{cid}_missing_task")
  for field in ("required_skills","acceptable_skills","excluded_skills","expected_order"):
   vals=c.get(field)
   if not isinstance(vals,list) or any(not isinstance(x,str) for x in vals):errors.append(f"{cid}_{field}_must_be_string_array");continue
   for skill in vals:
    if skill not in ids:errors.append(f"{cid}_unknown_skill:{skill}")
  if isinstance(c.get("required_skills"),list):covered.update(c["required_skills"])
  if c.get("expected_decision") not in {"select","abstain","abstain_or_clarify","human_review"}:errors.append(f"{cid}_invalid_expected_decision")
  if not isinstance(c.get("needs_human_review"),bool):errors.append(f"{cid}_needs_human_review_must_be_boolean")
 if ids-covered:errors.append("uncovered_skills:"+",".join(sorted(ids-covered)))
 return errors
def score_benchmark(benchmark:dict[str,Any],proposals:dict[str,Any],catalog:dict[str,Any])->dict[str,Any]:
 errors=validate_benchmark(benchmark,catalog)
 if errors:return {"status":"invalid_benchmark","errors":errors}
 rows=[];tp=fp=fn=exact=eligible=checked=ordered=abstain_n=abstain_ok=rationales=0;per_skill={}
 for c in benchmark["cases"]:
  cid=c["case_id"];p=proposals.get(cid,{})
  if not isinstance(p,dict):p={}
  raw=p.get("selected_skills",[]);selected=list(dict.fromkeys(x for x in raw if isinstance(x,str))) if isinstance(raw,list) else []
  decision=p.get("decision","select" if selected else "abstain");required=set(c["required_skills"]);allowed=required|set(c["acceptable_skills"]);chosen=set(selected)
  missing=required-chosen;extra=chosen-allowed;ltp=len(required&chosen);lfp=len(extra);lfn=len(missing)
  if not c["needs_human_review"]:
   tp+=ltp;fp+=lfp;fn+=lfn;eligible+=1
   decision_ok=(c["expected_decision"] not in {"abstain","abstain_or_clarify"} or decision in ({"abstain"} if c["expected_decision"]=="abstain" else {"abstain","clarify"}))
   exact+=int(chosen==required and decision_ok)
   if c["expected_decision"] in {"abstain","abstain_or_clarify"}:
    abstain_n+=1;abstain_ok+=int(decision in ({"abstain"} if c["expected_decision"]=="abstain" else {"abstain","clarify"}))
   if c.get("expected_order") and not c.get("order_is_advisory",False):
    checked+=1;pos=-1;ok=True
    for skill in c["expected_order"]:
     try:pos=selected.index(skill,pos+1)
     except ValueError:ok=False;break
    ordered+=int(ok)
   rationales+=int(isinstance(p.get("rationale"),str) and bool(p["rationale"].strip()))
   for skill in required:
    v=per_skill.setdefault(skill,{"tp":0,"fn":0});v["tp"]+=int(skill in chosen);v["fn"]+=int(skill not in chosen)
  rows.append({"case_id":cid,"kind":c["kind"],"excluded_from_aggregate":c["needs_human_review"],"decision":decision,"selected_skills":selected,"missing_required":sorted(missing),"unnecessary_skills":sorted(extra),"exact_match":chosen==required,"rationale_present":bool(p.get("rationale"))})
 precision=tp/(tp+fp) if tp+fp else (1.0 if tp+fn==0 else 0.0);recall=tp/(tp+fn) if tp+fn else 1.0;f1=2*precision*recall/(precision+recall) if precision+recall else 0.0
 return {"status":"scored","benchmark_id":benchmark.get("benchmark_id"),"cases_total":len(benchmark["cases"]),"cases_scored":eligible,"cases_human_review":sum(bool(c["needs_human_review"]) for c in benchmark["cases"]),"metrics":{"micro_precision":round(precision,4),"micro_recall":round(recall,4),"micro_f1":round(f1,4),"exact_match_rate":round(exact/eligible,4) if eligible else 0.0,"ordered_chain_accuracy":round(ordered/checked,4) if checked else None,"abstention_accuracy":round(abstain_ok/abstain_n,4) if abstain_n else None,"rationale_presence_rate":round(rationales/eligible,4) if eligible else 0.0,"true_positives":tp,"false_positives":fp,"false_negatives":fn},"per_skill_recall":{k:round(v["tp"]/(v["tp"]+v["fn"]),4) if v["tp"]+v["fn"] else 1.0 for k,v in sorted(per_skill.items())},"case_results":rows,"limitations":["Scores proposal JSON only; does not call an LLM or execute Skills.","Rationale metric checks presence, not correctness.","Annotations are manually curated and synthetic; ambiguous cases may need expert revision.","Acceptable Skills are permitted alternatives and do not count as required recall."]}
def main()->int:
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("--benchmark",type=Path,default=DEFAULT_BENCHMARK);p.add_argument("--proposals",type=Path,required=True);p.add_argument("--skill-map",type=Path,default=ROOT/"CATALOG"/"skill-tools.json");p.add_argument("--output",type=Path);p.add_argument("--pretty",action="store_true");a=p.parse_args()
 report=score_benchmark(load_json(a.benchmark),load_json(a.proposals),load_json(a.skill_map));rendered=json.dumps(report,ensure_ascii=False,indent=2 if a.pretty else None)+"\\n"
 if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(rendered,encoding="utf-8")
 else:sys.stdout.write(rendered)
 return 0 if report["status"]=="scored" else 2
if __name__=="__main__":raise SystemExit(main())
