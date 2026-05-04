import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RENDER_SCRIPT = REPO_ROOT / "cli" / "render-listening-note.py"


class RenderListeningNoteTests(unittest.TestCase):
    def render_sample(self, sample_name: str, language: str) -> str:
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "note.md"
            transcript = REPO_ROOT / "examples" / sample_name
            result = subprocess.run(
                [
                    sys.executable,
                    str(RENDER_SCRIPT),
                    "--audio-path",
                    str(Path(tmpdir) / "sample.m4a"),
                    "--transcript-json",
                    str(transcript),
                    "--title",
                    "Sample Note",
                    "--language",
                    language,
                    "--output",
                    str(output),
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            return output.read_text(encoding="utf-8")

    def test_renders_required_sections_for_japanese(self) -> None:
        rendered = self.render_sample("sample-transcript-ja.json", "Japanese")
        for heading in [
            "# Sample Note",
            "## Source",
            "## Transcript",
            "## Listening Focus",
            "## Useful Expressions",
            "## Study Plan",
        ]:
            self.assertIn(heading, rendered)
        self.assertIn("今日は駅の近くにある小さな喫茶店", rendered)
        self.assertIn("Locale: `ja-JP`", rendered)

    def test_renders_required_sections_for_english(self) -> None:
        rendered = self.render_sample("sample-transcript-en.json", "English")
        self.assertIn("Today I want to talk about a small library", rendered)
        self.assertIn("Locale: `en-US`", rendered)

    def test_rejects_missing_required_transcript_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_json = Path(tmpdir) / "bad.json"
            bad_json.write_text(json.dumps({"engine": "apple"}), encoding="utf-8")
            output = Path(tmpdir) / "note.md"
            result = subprocess.run(
                [
                    sys.executable,
                    str(RENDER_SCRIPT),
                    "--audio-path",
                    str(Path(tmpdir) / "sample.m4a"),
                    "--transcript-json",
                    str(bad_json),
                    "--title",
                    "Bad",
                    "--language",
                    "English",
                    "--output",
                    str(output),
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing required keys", result.stderr)

    def test_rejects_transcript_error_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_json = Path(tmpdir) / "error.json"
            output = Path(tmpdir) / "note.md"
            bad_json.write_text(
                json.dumps(
                    {
                        "error": {"type": "mock_error", "message": "transcription failed"},
                        "engine": "faster-whisper",
                        "locale": "ja-JP",
                        "full_text": "",
                        "segments": [],
                        "timing_complete": False,
                    }
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(RENDER_SCRIPT),
                    "--audio-path",
                    str(Path(tmpdir) / "sample.m4a"),
                    "--transcript-json",
                    str(bad_json),
                    "--title",
                    "Bad",
                    "--language",
                    "Japanese",
                    "--output",
                    str(output),
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Transcript JSON contains ASR error", result.stderr)
            self.assertIn("mock_error", result.stderr)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
