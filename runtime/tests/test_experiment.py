import subprocess, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ["docs/EXPERIMENT_RESULTS.md", "experiments/results.csv", "prototype/replay_data.js"]


class ExperimentTests(unittest.TestCase):
    def test_generated_artifacts_are_fresh_and_deterministic(self):
        before = {p: (ROOT / p).read_bytes() for p in GENERATED}
        r = subprocess.run([sys.executable, str(ROOT / "experiments" / "ablation.py")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        for p in GENERATED:
            self.assertEqual(before[p], (ROOT / p).read_bytes(), f"{p} was stale or non-deterministic")

    def test_eir_regression_guard_on_scenario_matrix(self):
        sys.path.insert(0, str(ROOT / "experiments"))
        import ablation
        for sc in ablation.SCENARIOS:
            j = ablation.judge(sc, ablation.run_eir(sc))
            self.assertTrue(j["safe"], f"{sc.sid} unsafe: {j}")

    def test_each_ablation_link_is_load_bearing(self):
        """Removing a link must make at least one scenario unsafe; otherwise the link proves nothing."""
        sys.path.insert(0, str(ROOT / "experiments"))
        import ablation
        def unsafe(fn):
            return {sc.sid for sc in ablation.SCENARIOS if not ablation.judge(sc, fn(sc))["safe"]}
        b0, b1, b2, b3 = (unsafe(lambda s, a=a: ablation.run_baseline(s, *a))
                          for a in [(0, 0, 0), (1, 0, 0), (1, 1, 0), (1, 1, 1)])
        eir = unsafe(ablation.run_eir)
        self.assertTrue(b0 > b1 > b2 > b3 > eir, (b0, b1, b2, b3, eir))   # strict set inclusion chain


class DocsTests(unittest.TestCase):
    def test_required_documents_exist(self):
        need = ["README.md", "docs/TECHNICAL_SPEC.md", "docs/ROADMAP.md", "docs/AUDIT_POLYMATH.md",
                "docs/RUNBOOK_HARDENED.md", "docs/RESEARCH.md", "docs/THREAT_MODEL.md", "docs/DECISIONS.md",
                "docs/EXPERIMENT_PLAN.md", "docs/IMPLEMENTATION_GUIDE.md", "docs/LIMITATIONS.md"]
        for n in need:
            self.assertTrue((ROOT / n).is_file(), n)


if __name__ == "__main__":
    unittest.main()
