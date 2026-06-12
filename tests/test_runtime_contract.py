import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECK_RUNTIME = REPO_ROOT / "cli" / "check-runtime.sh"
FASTER_WHISPER_HELPER = REPO_ROOT / "tools" / "faster-whisper" / "transcribe.py"
APPLE_HELPER_SOURCE = REPO_ROOT / "tools" / "apple-speech-helper" / "SpeechPermissionApp" / "main.swift"


class RuntimeContractTests(unittest.TestCase):
    def test_runtime_check_reports_python_and_faster_whisper_versions(self) -> None:
        result = subprocess.run(
            [str(CHECK_RUNTIME)],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("python_version=3.14.", result.stdout)
        self.assertIn("faster_whisper_version=1.2.1", result.stdout)

    def test_faster_whisper_error_payload_has_schema_version(self) -> None:
        result = subprocess.run(
            [str(REPO_ROOT / ".venv" / "bin" / "python"), str(FASTER_WHISPER_HELPER), "/missing/audio.mp3"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["schema_version"], 1)

    def test_runtime_check_rejects_unpinned_faster_whisper_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_python = Path(tmpdir) / "python"
            fake_python.write_text(
                "#!/usr/bin/env bash\n"
                "if [[ \"$1\" == \"-\" ]]; then\n"
                "  printf 'python_executable=%s\\npython_version=3.14.3\\nabi_tag=cpython-314\\nfaster_whisper_version=9.9.9\\n' \"$0\"\n"
                "  exit 0\n"
                "fi\n"
                "if [[ \"$1\" == \"-c\" ]]; then exit 0; fi\n"
                "exit 1\n",
                encoding="utf-8",
            )
            os.chmod(fake_python, 0o755)

            result = subprocess.run(
                [str(CHECK_RUNTIME), "--python", str(fake_python)],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("requires faster-whisper 1.2.1", result.stderr)

    def test_apple_helper_declares_schema_version(self) -> None:
        source = APPLE_HELPER_SOURCE.read_text(encoding="utf-8")

        self.assertIn("let schemaVersion: Int", source)
        self.assertIn('case schemaVersion = "schema_version"', source)


if __name__ == "__main__":
    unittest.main()
