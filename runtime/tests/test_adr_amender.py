"""runtime/tests/test_adr_amender.py — Tests for Decree-Driven ADR Amendment (ADR-0026)."""
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve()
_SRC = _HERE.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from adr_amender import (
    AdrAmender, AmendmentResult, AdrAmenderError,
    _parse_decree, _format_adr_id,
)


class DecreeParsingTests(unittest.TestCase):
    def test_parse_create(self):
        op, fields = _parse_decree("create ADR-0027 about cell65-llm integration")
        self.assertEqual(op, "create")
        self.assertEqual(fields["adr_num"], 27)
        self.assertEqual(fields["topic"], "cell65-llm integration")

    def test_parse_create_no_leading_zeros(self):
        op, fields = _parse_decree("create ADR 5 about minimal scope")
        self.assertEqual(op, "create")
        self.assertEqual(fields["adr_num"], 5)
        self.assertEqual(fields["topic"], "minimal scope")

    def test_parse_amend(self):
        op, fields = _parse_decree("amend ADR-0016 to require two-party review")
        self.assertEqual(op, "amend")
        self.assertEqual(fields["target_adr_num"], 16)
        self.assertEqual(fields["change"], "require two-party review")

    def test_parse_supersede(self):
        op, fields = _parse_decree("supersede ADR-0008 with ADR-0028")
        self.assertEqual(op, "supersede")
        self.assertEqual(fields["old_adr_num"], 8)
        self.assertEqual(fields["new_adr_num"], 28)

    def test_parse_deprecate(self):
        op, fields = _parse_decree("deprecate ADR-0011")
        self.assertEqual(op, "deprecate")
        self.assertEqual(fields["target_adr_num"], 11)

    def test_parse_no_match_raises(self):
        with self.assertRaises(AdrAmenderError):
            _parse_decree("this is not an amendment decree")
        with self.assertRaises(AdrAmenderError):
            _parse_decree("never use Google DNS")  # prohibition decree, not amendment

    def test_parse_case_insensitive(self):
        op, _ = _parse_decree("CREATE ADR-0050 ABOUT something")
        self.assertEqual(op, "create")
        op, _ = _parse_decree("Amend ADR 16 to require review")
        self.assertEqual(op, "amend")

    def test_format_adr_id(self):
        self.assertEqual(_format_adr_id(1), "ADR-0001")
        self.assertEqual(_format_adr_id(16), "ADR-0016")
        self.assertEqual(_format_adr_id(9999), "ADR-9999")
        with self.assertRaises(AdrAmenderError):
            _format_adr_id(0)
        with self.assertRaises(AdrAmenderError):
            _format_adr_id(10000)


class AdrAmenderCreateTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.adr_dir = Path(self.tmpdir.name) / "adr"
        self.adr_dir.mkdir()
        self.amender = AdrAmender(adr_dir=self.adr_dir)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_create_generates_adr_file(self):
        result = self.amender.process(
            decree_seq=1,
            decree_text="create ADR-0027 about cell65-llm integration",
            timestamp="2026-10-17T08:00:00Z",
        )
        self.assertEqual(result.operation, "create")
        self.assertEqual(result.target_adr, "ADR-0027")
        self.assertEqual(result.topic_or_change, "cell65-llm integration")
        self.assertEqual(result.decree_seq, 1)
        # Verify ADR file was created
        self.assertIsNotNone(result.new_adr_file)
        self.assertTrue(Path(result.new_adr_file).exists())
        # Verify content
        content = Path(result.new_adr_file).read_text()
        self.assertIn("ADR-0027", content)
        self.assertIn("cell65-llm integration", content)
        self.assertIn("Decree #1", content)
        self.assertIn("Proposed", content)

    def test_create_log_entry_format(self):
        result = self.amender.process(
            decree_seq=5,
            decree_text="create ADR-0030 about CRDT-based vault sync",
            timestamp="2026-10-17T08:00:00Z",
        )
        self.assertIn("[2026-10-17T08:00:00Z]", result.log_entry)
        self.assertIn("Decree #5", result.log_entry)
        self.assertIn("(create)", result.log_entry)
        self.assertIn("ADR-0030", result.log_entry)

    def test_create_does_not_overwrite_existing(self):
        # Create an ADR file manually first
        existing_file = self.adr_dir / "0050-test-topic.md"
        existing_file.write_text("# Existing content")
        # Now try to create via amender
        result = self.amender.process(
            decree_seq=1,
            decree_text="create ADR-0050 about test topic",
        )
        self.assertEqual(result.operation, "create")
        self.assertIn("already exists", result.notes[0])
        # Original file unchanged
        self.assertEqual(existing_file.read_text(), "# Existing content")


class AdrAmenderAmendTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.adr_dir = Path(self.tmpdir.name) / "adr"
        self.adr_dir.mkdir()
        self.amender = AdrAmender(adr_dir=self.adr_dir)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_amend_returns_result(self):
        result = self.amender.process(
            decree_seq=8,
            decree_text="amend ADR-0016 to require two-party review",
            timestamp="2026-10-17T08:00:00Z",
        )
        self.assertEqual(result.operation, "amend")
        self.assertEqual(result.target_adr, "ADR-0016")
        self.assertEqual(result.topic_or_change, "require two-party review")
        self.assertEqual(result.decree_seq, 8)

    def test_amend_log_entry(self):
        result = self.amender.process(
            decree_seq=8,
            decree_text="amend ADR-0016 to require two-party review",
            timestamp="2026-10-17T08:00:00Z",
        )
        self.assertIn("[2026-10-17T08:00:00Z]", result.log_entry)
        self.assertIn("Decree #8", result.log_entry)
        self.assertIn("(amend)", result.log_entry)
        self.assertIn("ADR-0016", result.log_entry)
        self.assertIn("require two-party review", result.log_entry)

    def test_amend_does_not_modify_original_adr_file(self):
        # Create an ADR file
        target_file = self.adr_dir / "0016-self-rewriting.md"
        original_content = "# Original ADR-0016\n\nThis is the original."
        target_file.write_text(original_content)

        result = self.amender.process(
            decree_seq=8,
            decree_text="amend ADR-0016 to require two-party review",
        )

        # Original ADR file MUST be unchanged (per ADR-0016 §3 immutability)
        self.assertEqual(target_file.read_text(), original_content)
        self.assertIn("NOT modified", result.notes[1])


class AdrAmenderSupersedeTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.adr_dir = Path(self.tmpdir.name) / "adr"
        self.adr_dir.mkdir()
        self.amender = AdrAmender(adr_dir=self.adr_dir)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_supersede_generates_new_adr(self):
        result = self.amender.process(
            decree_seq=9,
            decree_text="supersede ADR-0008 with ADR-0028",
            timestamp="2026-10-17T08:00:00Z",
        )
        self.assertEqual(result.operation, "supersede")
        self.assertEqual(result.target_adr, "ADR-0008")
        self.assertEqual(result.new_adr, "ADR-0028")
        # New ADR file generated
        self.assertIsNotNone(result.new_adr_file)
        self.assertTrue(Path(result.new_adr_file).exists())
        # Content has Supersedes header
        content = Path(result.new_adr_file).read_text()
        self.assertIn("Supersedes", content)
        self.assertIn("ADR-0008", content)
        self.assertIn("Decree #9", content)

    def test_supersede_log_entry(self):
        result = self.amender.process(
            decree_seq=9,
            decree_text="supersede ADR-0008 with ADR-0028",
            timestamp="2026-10-17T08:00:00Z",
        )
        self.assertIn("Decree #9", result.log_entry)
        self.assertIn("(supersede)", result.log_entry)
        self.assertIn("ADR-0008", result.log_entry)
        self.assertIn("ADR-0028", result.log_entry)


class AdrAmenderDeprecateTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.adr_dir = Path(self.tmpdir.name) / "adr"
        self.adr_dir.mkdir()
        self.amender = AdrAmender(adr_dir=self.adr_dir)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_deprecate_returns_result(self):
        result = self.amender.process(
            decree_seq=10,
            decree_text="deprecate ADR-0011",
            timestamp="2026-10-17T08:00:00Z",
        )
        self.assertEqual(result.operation, "deprecate")
        self.assertEqual(result.target_adr, "ADR-0011")
        self.assertEqual(result.decree_seq, 10)

    def test_deprecate_log_entry(self):
        result = self.amender.process(
            decree_seq=10,
            decree_text="deprecate ADR-0011",
            timestamp="2026-10-17T08:00:00Z",
        )
        self.assertIn("Decree #10", result.log_entry)
        self.assertIn("(deprecate)", result.log_entry)
        self.assertIn("ADR-0011", result.log_entry)


class AdrAmenderLogTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.adr_dir = Path(self.tmpdir.name) / "adr"
        self.adr_dir.mkdir()
        self.amender = AdrAmender(adr_dir=self.adr_dir)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_process_and_log_writes_to_file(self):
        # Initial state: no log file
        self.assertFalse(self.amender.amendments_log_path.exists())
        # Process a decree
        self.amender.process_and_log(
            decree_seq=8,
            decree_text="amend ADR-0016 to require two-party review",
            timestamp="2026-10-17T08:00:00Z",
        )
        # Log file now exists with one entry
        self.assertTrue(self.amender.amendments_log_path.exists())
        entries = self.amender.read_log()
        self.assertEqual(len(entries), 1)
        self.assertIn("Decree #8", entries[0])

    def test_multiple_log_entries_append(self):
        # Process multiple decrees
        self.amender.process_and_log(
            decree_seq=8, decree_text="amend ADR-0016 to require two-party review",
            timestamp="2026-10-17T08:00:00Z",
        )
        self.amender.process_and_log(
            decree_seq=9, decree_text="supersede ADR-0008 with ADR-0028",
            timestamp="2026-10-17T08:05:00Z",
        )
        self.amender.process_and_log(
            decree_seq=10, decree_text="deprecate ADR-0011",
            timestamp="2026-10-17T08:10:00Z",
        )
        entries = self.amender.read_log()
        self.assertEqual(len(entries), 3)
        self.assertIn("Decree #8", entries[0])
        self.assertIn("Decree #9", entries[1])
        self.assertIn("Decree #10", entries[2])

    def test_read_empty_log(self):
        # When log doesn't exist, returns empty list
        self.assertEqual(self.amender.read_log(), [])


class AdrAmenderErrorTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.adr_dir = Path(self.tmpdir.name) / "adr"
        self.adr_dir.mkdir()
        self.amender = AdrAmender(adr_dir=self.adr_dir)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_unrecognized_decree_raises(self):
        with self.assertRaises(AdrAmenderError):
            self.amender.process(
                decree_seq=1,
                decree_text="this doesn't match any pattern",
            )

    def test_prohibition_decree_not_recognized_as_amendment(self):
        # 'never use Google DNS' is a prohibition decree, not an amendment
        with self.assertRaises(AdrAmenderError):
            self.amender.process(
                decree_seq=1,
                decree_text="never use Google DNS",
            )


class AdrAmenderEndToEndTests(unittest.TestCase):
    """End-to-end: simulate processing multiple decrees from a fresh DB."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.adr_dir = Path(self.tmpdir.name) / "adr"
        self.adr_dir.mkdir()
        self.amender = AdrAmender(adr_dir=self.adr_dir)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_full_amendment_workflow(self):
        # 1. Create an ADR
        r1 = self.amender.process_and_log(
            decree_seq=1,
            decree_text="create ADR-0030 about CRDT-based vault sync",
            timestamp="2026-10-17T10:00:00Z",
        )
        self.assertEqual(r1.operation, "create")
        self.assertTrue(Path(r1.new_adr_file).exists())

        # 2. Amend another ADR
        r2 = self.amender.process_and_log(
            decree_seq=2,
            decree_text="amend ADR-0016 to require three-party review for AdrAmender-generated ADRs",
            timestamp="2026-10-17T10:05:00Z",
        )
        self.assertEqual(r2.operation, "amend")

        # 3. Supersede an ADR
        r3 = self.amender.process_and_log(
            decree_seq=3,
            decree_text="supersede ADR-0011 with ADR-0031",
            timestamp="2026-10-17T10:10:00Z",
        )
        self.assertEqual(r3.operation, "supersede")
        self.assertTrue(Path(r3.new_adr_file).exists())

        # 4. Deprecate an ADR
        r4 = self.amender.process_and_log(
            decree_seq=4,
            decree_text="deprecate ADR-0014",
            timestamp="2026-10-17T10:15:00Z",
        )
        self.assertEqual(r4.operation, "deprecate")

        # Verify log has all 4 entries
        entries = self.amender.read_log()
        self.assertEqual(len(entries), 4)
        # Verify each entry has correct decree seq
        self.assertIn("Decree #1", entries[0])
        self.assertIn("Decree #2", entries[1])
        self.assertIn("Decree #3", entries[2])
        self.assertIn("Decree #4", entries[3])
        # Verify each entry has correct operation
        self.assertIn("(create)", entries[0])
        self.assertIn("(amend)", entries[1])
        self.assertIn("(supersede)", entries[2])
        self.assertIn("(deprecate)", entries[3])


if __name__ == "__main__":
    unittest.main()
