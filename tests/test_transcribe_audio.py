import subprocess
import tempfile
import unittest
import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TRANSCRIBE_SCRIPT = REPO_ROOT / "cli" / "transcribe-audio.sh"


class TranscribeAudioTests(unittest.TestCase):
    def test_default_apple_helper_is_bundled(self) -> None:
        helper = REPO_ROOT / "tools" / "apple-speech-helper" / "run-apple-speech-helper.sh"
        self.assertTrue(helper.is_file())
        self.assertTrue(os.access(helper, os.X_OK))

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

    def test_apple_helper_can_be_used_without_python3_on_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audio = Path(tmpdir) / "sample.m4a"
            helper = Path(tmpdir) / "helper.sh"
            output = Path(tmpdir) / "transcript.json"
            bin_dir = Path(tmpdir) / "bin"
            bin_dir.mkdir()
            audio.write_bytes(b"fake")
            helper.write_text(
                "#!/usr/bin/env bash\n"
                "printf '{\"engine\":\"apple\",\"locale\":\"ja-JP\",\"full_text\":\"ok\",\"segments\":[],\"timing_complete\":true}\\n'\n",
                encoding="utf-8",
            )
            helper.chmod(0o755)
            for name, target in {
                "awk": "/usr/bin/awk",
                "bash": "/bin/bash",
                "cat": "/bin/cat",
                "dirname": "/usr/bin/dirname",
                "mkdir": "/bin/mkdir",
                "mktemp": "/usr/bin/mktemp",
                "mv": "/bin/mv",
                "rm": "/bin/rm",
            }.items():
                (bin_dir / name).symlink_to(target)

            env = {
                "APPLE_SPEECH_HELPER": str(helper),
                "PATH": str(bin_dir),
            }
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

    def test_helper_error_payload_fails_even_with_zero_exit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audio = Path(tmpdir) / "sample.m4a"
            helper = Path(tmpdir) / "helper.sh"
            output = Path(tmpdir) / "transcript.json"
            audio.write_bytes(b"fake")
            helper.write_text(
                "#!/usr/bin/env bash\n"
                "printf '{\"error\":{\"type\":\"mock_error\",\"message\":\"failed\"},\"engine\":\"apple\",\"locale\":\"ja-JP\",\"full_text\":\"\",\"segments\":[],\"timing_complete\":false}\\n'\n",
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
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("ASR backend returned error", result.stderr)
            self.assertIn("mock_error", result.stderr)
            self.assertFalse(output.exists())

    def test_pretty_printed_helper_error_payload_fails_even_with_zero_exit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audio = Path(tmpdir) / "sample.m4a"
            helper = Path(tmpdir) / "helper.sh"
            output = Path(tmpdir) / "transcript.json"
            audio.write_bytes(b"fake")
            helper.write_text(
                "#!/usr/bin/env bash\n"
                "cat <<'EOF'\n"
                "{\n"
                "  \"error\": {\n"
                "    \"type\": \"mock_error\",\n"
                "    \"message\": \"failed\"\n"
                "  },\n"
                "  \"engine\": \"apple\",\n"
                "  \"locale\": \"ja-JP\",\n"
                "  \"full_text\": \"\",\n"
                "  \"segments\": [],\n"
                "  \"timing_complete\": false\n"
                "}\n"
                "EOF\n",
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
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("ASR backend returned error", result.stderr)
            self.assertIn("mock_error", result.stderr)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
