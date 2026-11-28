from __future__ import annotations
import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"scripts"))
from skill_selection_benchmark import score_benchmark,validate_benchmark
class SelectionBenchmarkTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.b=json.loads((ROOT/"TESTS/selection-benchmark/benchmark.json").read_text(encoding="utf-8"));cls.catalog=json.loads((ROOT/"CATALOG/skill-tools.json").read_text(encoding="utf-8"))
 def test_schema_and_coverage(self):self.assertEqual(validate_benchmark(self.b,self.catalog),[])
 def test_all_catalog_skills_covered(self):self.assertEqual({s for c in self.b["cases"] for s in c["required_skills"]},{x["id"] for x in self.catalog["skills"]})
 def test_perfect_proposals(self):
  p={c["case_id"]:{"selected_skills":c["required_skills"],"decision":"abstain" if c["expected_decision"]=="abstain" else "clarify" if c["expected_decision"]=="abstain_or_clarify" else "select","rationale":"reason"} for c in self.b["cases"] if not c["needs_human_review"]};r=score_benchmark(self.b,p,self.catalog);self.assertEqual(r["metrics"]["micro_f1"],1.0);self.assertEqual(r["metrics"]["exact_match_rate"],1.0)
 def test_unnecessary_skill_is_false_positive(self):
  r=score_benchmark(self.b,{"single-01":{"selected_skills":["automation-vps","server-security"]}},self.catalog);x=next(x for x in r["case_results"] if x["case_id"]=="single-01");self.assertEqual(x["unnecessary_skills"],["server-security"])
 def test_missing_required_skill_is_false_negative(self):
  r=score_benchmark(self.b,{"single-01":{"selected_skills":[]}},self.catalog);x=next(x for x in r["case_results"] if x["case_id"]=="single-01");self.assertEqual(x["missing_required"],["automation-vps"])
 def test_ambiguous_clarification(self):self.assertEqual(score_benchmark(self.b,{"ambiguous-01":{"decision":"clarify","selected_skills":[]}},self.catalog)["status"],"scored")
 def test_human_review_excluded(self):self.assertEqual(score_benchmark(self.b,{},self.catalog)["cases_human_review"],1)
 def test_duplicate_case_rejected(self):
  b=json.loads(json.dumps(self.b));b["cases"].append(b["cases"][0]);self.assertTrue(any("duplicate_case_id" in e for e in validate_benchmark(b,self.catalog)))
if __name__=="__main__":unittest.main()
