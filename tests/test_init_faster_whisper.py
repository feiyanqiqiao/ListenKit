import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INIT_SCRIPT = REPO_ROOT / "cli" / "init-faster-whisper.sh"
PYTHON314 = Path("/opt/homebrew/bin/python3.14")


class InitFasterWhisperTests(unittest.TestCase):
    def test_existing_python314_venv_is_supported(self) -> None:
        if not PYTHON314.is_file():
            self.skipTest("Homebrew Python 3.14 is not installed")
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo = root / "ListenKit"
            script = repo / "cli" / "init-faster-whisper.sh"
            venv_python = repo / ".venv" / "bin" / "python"
            module_dir = root / "modules"
            script.parent.mkdir(parents=True)
            venv_python.parent.mkdir(parents=True)
            module_dir.mkdir()
            script.write_text(INIT_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
            script.chmod(0o755)
            venv_python.symlink_to(PYTHON314)
            (module_dir / "faster_whisper.py").write_text("READY = True\n", encoding="utf-8")
            env = os.environ.copy()
            env["PYTHONPATH"] = str(module_dir)

            result = subprocess.run(
                [str(script)],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), str(venv_python))

    def test_import_health_check_times_out(self) -> None:
        if not PYTHON314.is_file():
            self.skipTest("Homebrew Python 3.14 is not installed")
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo = root / "ListenKit"
            script = repo / "cli" / "init-faster-whisper.sh"
            venv_python = repo / ".venv" / "bin" / "python"
            module_dir = root / "modules"
            script.parent.mkdir(parents=True)
            venv_python.parent.mkdir(parents=True)
            module_dir.mkdir()
            script.write_text(INIT_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
            script.chmod(0o755)
            venv_python.symlink_to(PYTHON314)
            (module_dir / "faster_whisper.py").write_text(
                "import time\ntime.sleep(3)\n",
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["PYTHONPATH"] = str(module_dir)
            env["LISTENKIT_FASTER_WHISPER_IMPORT_TIMEOUT_SECONDS"] = "1"

            result = subprocess.run(
                [str(script)],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                timeout=8,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("timed out after 1 seconds", result.stderr)


if __name__ == "__main__":
    unittest.main()
