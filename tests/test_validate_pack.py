import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class PackValidationTests(unittest.TestCase):
    def test_pack_validator_passes(self):
        result = subprocess.run([sys.executable, str(ROOT / "tools" / "validate_pack.py")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)
        self.assertIn("5 schemas", result.stdout)
        self.assertIn("not polymath-os", result.stdout)

if __name__ == "__main__":
    unittest.main()
