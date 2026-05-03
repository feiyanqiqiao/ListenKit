import subprocess
import tempfile
import unittest
import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TRANSCRIBE_SCRIPT = REPO_ROOT / "cli" / "transcribe-audio.sh"


class TranscribeAudioTests(unittest.TestCase):
    def test_rejects_unsupported_engine(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audio = Path(tmpdir) / "sample.m4a"
            audio.write_bytes(b"fake")
            result = subprocess.run(
                [
                    str(TRANSCRIBE_SCRIPT),
                    "--audio-path",
                    str(audio),
                    "--locale",
                    "ja-JP",
                    "--engine",
                    "whisper",
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Unsupported engine", result.stderr)

    def test_missing_faster_whisper_python_returns_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audio = Path(tmpdir) / "sample.m4a"
            audio.write_bytes(b"fake")
            env = os.environ.copy()
            env.pop("FASTER_WHISPER_PYTHON", None)
            result = subprocess.run(
                [
                    str(TRANSCRIBE_SCRIPT),
                    "--audio-path",
                    str(audio),
                    "--locale",
                    "ja-JP",
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("FASTER_WHISPER_PYTHON is required", result.stderr)

    def test_default_faster_whisper_helper_can_be_mocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audio = Path(tmpdir) / "sample.m4a"
            helper = Path(tmpdir) / "helper.sh"
            output = Path(tmpdir) / "transcript.json"
            audio.write_bytes(b"fake")
            helper.write_text(
                "#!/usr/bin/env bash\n"
                "printf '{\"engine\":\"faster-whisper\",\"model\":\"small\",\"compute_type\":\"int8\",\"locale\":\"ja-JP\",\"language\":\"ja\",\"full_text\":\"ok\",\"segments\":[],\"timing_complete\":true}\\n'\n",
                encoding="utf-8",
            )
            helper.chmod(0o755)
            env = os.environ.copy()
            env["FASTER_WHISPER_PYTHON"] = "/bin/sh"
            env["LISTENKIT_FASTER_WHISPER_HELPER"] = str(helper)
            result = subprocess.run(
                [
                    str(TRANSCRIBE_SCRIPT),
                    "--audio-path",
                    str(audio),
                    "--locale",
                    "ja-JP",
                    "--output",
                    str(output),
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), str(output))
            rendered = output.read_text(encoding="utf-8")
            self.assertIn('"engine":"faster-whisper"', rendered)
            self.assertIn('"compute_type":"int8"', rendered)

    def test_apple_helper_can_be_used(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audio = Path(tmpdir) / "sample.m4a"
            helper = Path(tmpdir) / "helper.sh"
            output = Path(tmpdir) / "transcript.json"
            audio.write_bytes(b"fake")
            helper.write_text(
                "#!/usr/bin/env bash\n"
                "printf '{\"engine\":\"apple\",\"locale\":\"ja-JP\",\"full_text\":\"ok\",\"segments\":[],\"timing_complete\":true}\\n'\n",
                encoding="utf-8",
            )
            helper.chmod(0o755)
            env = os.environ.copy()
            env["APPLE_SPEECH_HELPER"] = str(helper)
            result = subprocess.run(
                [
                    str(TRANSCRIBE_SCRIPT),
                    "--audio-path",
                    str(audio),
                    "--locale",
                    "ja-JP",
                    "--engine",
                    "apple",
                    "--output",
                    str(output),
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), str(output))
            self.assertIn('"full_text":"ok"', output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
