import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IMPORT_SCRIPT = REPO_ROOT / "cli" / "import-audio.sh"


class ImportAudioTests(unittest.TestCase):
    def test_local_input_invokes_ffmpeg_and_returns_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "bin"
            out_dir = Path(tmpdir) / "out"
            source = Path(tmpdir) / "recording.wav"
            log = Path(tmpdir) / "ffmpeg.log"
            bin_dir.mkdir()
            source.write_bytes(b"fake")
            (bin_dir / "ffmpeg").write_text(
                "#!/usr/bin/env bash\nprintf '%s\\n' \"$@\" > \"$FFMPEG_LOG\"\n",
                encoding="utf-8",
            )
            os.chmod(bin_dir / "ffmpeg", 0o755)

            env = os.environ.copy()
            env["PATH"] = f"{bin_dir}:{env['PATH']}"
            env["FFMPEG_LOG"] = str(log)
            result = subprocess.run(
                [
                    str(IMPORT_SCRIPT),
                    "--input",
                    str(source),
                    "--output-dir",
                    str(out_dir),
                    "--base-name",
                    "capture",
                    "--format",
                    "m4a",
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), str(out_dir / "capture.m4a"))
            argv = log.read_text(encoding="utf-8")
            self.assertIn(str(source), argv)
            self.assertIn(str(out_dir / "capture.m4a"), argv)

    def test_local_input_same_output_path_is_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "bin"
            source = Path(tmpdir) / "recording.m4a"
            bin_dir.mkdir()
            source.write_bytes(b"fake")
            (bin_dir / "ffmpeg").write_text(
                "#!/usr/bin/env bash\necho 'ffmpeg should not run' >&2\nexit 99\n",
                encoding="utf-8",
            )
            os.chmod(bin_dir / "ffmpeg", 0o755)

            env = os.environ.copy()
            env["PATH"] = f"{bin_dir}:{env['PATH']}"
            result = subprocess.run(
                [
                    str(IMPORT_SCRIPT),
                    "--input",
                    str(source),
                    "--output-dir",
                    tmpdir,
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), str(source))
            self.assertEqual(result.stderr, "")

    def test_local_input_surfaces_ffmpeg_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "bin"
            out_dir = Path(tmpdir) / "out"
            source = Path(tmpdir) / "recording.wav"
            bin_dir.mkdir()
            source.write_bytes(b"fake")
            (bin_dir / "ffmpeg").write_text(
                "#!/usr/bin/env bash\necho 'mock ffmpeg failure' >&2\nexit 42\n",
                encoding="utf-8",
            )
            os.chmod(bin_dir / "ffmpeg", 0o755)

            env = os.environ.copy()
            env["PATH"] = f"{bin_dir}:{env['PATH']}"
            result = subprocess.run(
                [
                    str(IMPORT_SCRIPT),
                    "--input",
                    str(source),
                    "--output-dir",
                    str(out_dir),
                    "--base-name",
                    "capture",
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("mock ffmpeg failure", result.stderr)

    def test_rejects_base_name_with_parent_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "recording.wav"
            source.write_bytes(b"fake")
            result = subprocess.run(
                [
                    str(IMPORT_SCRIPT),
                    "--input",
                    str(source),
                    "--output-dir",
                    str(Path(tmpdir) / "out"),
                    "--base-name",
                    "../escape",
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--base-name must be a filename stem", result.stderr)

    def test_rejects_base_name_with_nested_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [
                    str(IMPORT_SCRIPT),
                    "--url",
                    "https://example.com/video",
                    "--output-dir",
                    str(Path(tmpdir) / "out"),
                    "--base-name",
                    "nested/clip",
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--base-name must be a filename stem", result.stderr)

    def test_url_mode_uses_no_playlist_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "bin"
            out_dir = Path(tmpdir) / "out"
            log = Path(tmpdir) / "argv.log"
            bin_dir.mkdir()
            (bin_dir / "ffmpeg").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            (bin_dir / "yt-dlp").write_text(
                "#!/usr/bin/env bash\nprintf '%s\\n' \"$@\" > \"$ARGV_LOG\"\nprintf '%s\\n' \"$YTDLP_OUTPUT\"\n",
                encoding="utf-8",
            )
            os.chmod(bin_dir / "ffmpeg", 0o755)
            os.chmod(bin_dir / "yt-dlp", 0o755)

            env = os.environ.copy()
            env["PATH"] = f"{bin_dir}:{env['PATH']}"
            env["ARGV_LOG"] = str(log)
            env["YTDLP_OUTPUT"] = str(out_dir / "clip.m4a")
            result = subprocess.run(
                [
                    str(IMPORT_SCRIPT),
                    "--url",
                    "https://example.com/video",
                    "--output-dir",
                    str(out_dir),
                    "--base-name",
                    "clip",
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), str(out_dir / "clip.m4a"))
            argv = log.read_text(encoding="utf-8")
            self.assertIn("--quiet", argv)
            self.assertIn("--no-warnings", argv)
            self.assertIn("--print", argv)
            self.assertIn("after_move:filepath", argv)
            self.assertIn("--no-playlist", argv)
            self.assertIn("clip.%(ext)s", argv)


if __name__ == "__main__":
    unittest.main()
