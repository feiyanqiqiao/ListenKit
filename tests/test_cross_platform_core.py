import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path, PureWindowsPath
from unittest import mock

from listenkit_cli.asr_device import (
    CudaDevice,
    CudaProbe,
    cuda_retry_compute_type,
    is_cuda_runtime_failure,
    probe_cuda_devices,
    select_asr_device,
)
from listenkit_cli.errors import ListenKitError, RuntimeHealthError
from listenkit_cli.health import can_import_faster_whisper, import_timeout_seconds
from listenkit_cli.errors import RuntimeImportTimeout
from listenkit_cli.media import import_audio, validate_base_name
from listenkit_cli.platform_paths import (
    default_runtime_dir,
    huggingface_hub_cache_dir,
    runtime_python_path,
)
from listenkit_cli.process import run_command
from listenkit_cli.rendering import render_transcript
from listenkit_cli.subtitles import extract_subtitles, parse_vtt
from listenkit_cli.transcription import transcribe_audio
from listenkit_cli.workflow import generate_markdown, locale_from_language


class PlatformPathTests(unittest.TestCase):
    def test_windows_runtime_uses_local_app_data(self) -> None:
        path = default_runtime_dir(
            platform="win32", environment={"LOCALAPPDATA": r"C:\Users\Test\AppData\Local"}
        )
        self.assertEqual(
            PureWindowsPath(path),
            PureWindowsPath(r"C:\Users\Test\AppData\Local\ListenKit\venvs\cpython-314"),
        )

    def test_windows_requires_local_app_data(self) -> None:
        with self.assertRaisesRegex(ValueError, "LOCALAPPDATA"):
            default_runtime_dir(platform="win32", environment={})

    def test_unix_contract_remains_library_caches(self) -> None:
        home = Path("/home/test")
        expected = home / "Library/Caches/ListenKit/venvs/cpython-314"
        self.assertEqual(default_runtime_dir(platform="linux", environment={}, home=home), expected)
        self.assertEqual(default_runtime_dir(platform="darwin", environment={}, home=home), expected)

    def test_runtime_override_wins_on_every_platform(self) -> None:
        expected = Path("custom/runtime")
        for platform in ("win32", "darwin", "linux"):
            with self.subTest(platform=platform):
                self.assertEqual(
                    default_runtime_dir(
                        platform=platform,
                        environment={"LISTENKIT_FASTER_WHISPER_VENV_DIR": str(expected)},
                    ),
                    expected,
                )

    def test_python_layout_is_platform_specific(self) -> None:
        root = Path("runtime")
        self.assertEqual(runtime_python_path(root, platform="win32"), root / "Scripts/python.exe")
        self.assertEqual(runtime_python_path(root, platform="linux"), root / "bin/python")

    def test_huggingface_cache_precedence(self) -> None:
        self.assertEqual(
            huggingface_hub_cache_dir(
                environment={"HF_HUB_CACHE": "direct", "HF_HOME": "home"}
            ),
            Path("direct"),
        )
        self.assertEqual(
            huggingface_hub_cache_dir(environment={"HF_HOME": "home"}),
            Path("home/hub"),
        )


class HealthContractTests(unittest.TestCase):
    def test_import_timeout_is_positive_integer(self) -> None:
        self.assertEqual(import_timeout_seconds({}), 60)
        self.assertEqual(
            import_timeout_seconds(
                {"LISTENKIT_FASTER_WHISPER_IMPORT_TIMEOUT_SECONDS": "7"}
            ),
            7,
        )
        for value in ("0", "-1", "abc", "1.5"):
            with self.subTest(value=value), self.assertRaises(RuntimeHealthError):
                import_timeout_seconds(
                    {"LISTENKIT_FASTER_WHISPER_IMPORT_TIMEOUT_SECONDS": value}
                )

    def test_run_command_preserves_unicode_and_spaces(self) -> None:
        result = run_command(
            [sys.executable, "-c", "import sys; print(sys.argv[1])", "路径 with spaces"]
        )
        self.assertEqual(result.stdout.strip(), "路径 with spaces")

    def test_faster_whisper_import_is_bounded(self) -> None:
        if sys.version_info[:2] < (3, 10):
            self.skipTest("requires venv-capable Python")
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            subprocess_python = root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            run_command([sys.executable, "-m", "venv", root], capture=True)
            site_packages = Path(
                run_command(
                    [subprocess_python, "-c", "import site; print(site.getsitepackages()[0])"]
                ).stdout.strip()
            )
            package = site_packages / "faster_whisper"
            package.mkdir()
            (package / "__init__.py").write_text(
                "import time\ntime.sleep(10)\n", encoding="utf-8"
            )
            started = time.monotonic()
            with self.assertRaises(RuntimeImportTimeout):
                can_import_faster_whisper(
                    subprocess_python,
                    environment={
                        **os.environ,
                        "LISTENKIT_FASTER_WHISPER_IMPORT_TIMEOUT_SECONDS": "1",
                    },
                )
            self.assertLess(time.monotonic() - started, 5)


class AsrDevicePolicyTests(unittest.TestCase):
    def test_modern_nvidia_with_headroom_uses_float16(self) -> None:
        selection = select_asr_device(
            CudaProbe(
                (
                    CudaDevice(
                        index=0,
                        name="NVIDIA GeForce RTX 4070",
                        compute_capability=8.9,
                        free_memory_mib=8192,
                        supported_compute_types=frozenset(
                            {"float16", "int8_float16", "float32"}
                        ),
                    ),
                )
            )
        )
        self.assertEqual(selection.device, "cuda")
        self.assertEqual(selection.compute_type, "float16")
        self.assertEqual(selection.device_name, "NVIDIA GeForce RTX 4070")

    def test_memory_constrained_modern_nvidia_uses_int8_float16(self) -> None:
        selection = select_asr_device(
            CudaProbe(
                (
                    CudaDevice(
                        index=0,
                        compute_capability=8.6,
                        free_memory_mib=2500,
                        supported_compute_types=frozenset(
                            {"float16", "int8_float16", "float32"}
                        ),
                    ),
                )
            )
        )
        self.assertEqual(selection.device, "cuda")
        self.assertEqual(selection.compute_type, "int8_float16")

    def test_low_memory_or_legacy_nvidia_stays_on_cpu_in_auto_mode(self) -> None:
        cases = (
            CudaDevice(
                index=0,
                compute_capability=8.6,
                free_memory_mib=1024,
                supported_compute_types=frozenset({"float16", "int8_float16"}),
            ),
            CudaDevice(
                index=0,
                compute_capability=6.1,
                free_memory_mib=8192,
                supported_compute_types=frozenset({"int8_float32", "float32"}),
            ),
        )
        for device in cases:
            with self.subTest(device=device):
                selection = select_asr_device(CudaProbe((device,)))
                self.assertEqual(selection.device, "cpu")
                self.assertEqual(selection.compute_type, "int8")

    def test_explicit_pascal_cuda_uses_supported_int8_float32(self) -> None:
        selection = select_asr_device(
            CudaProbe(
                (
                    CudaDevice(
                        index=0,
                        compute_capability=6.1,
                        free_memory_mib=8192,
                        supported_compute_types=frozenset({"int8_float32", "float32"}),
                    ),
                )
            ),
            requested_device="cuda",
        )
        self.assertEqual(selection.device, "cuda")
        self.assertEqual(selection.compute_type, "int8_float32")

    def test_auto_selects_cuda_device_with_most_free_memory(self) -> None:
        selection = select_asr_device(
            CudaProbe(
                (
                    CudaDevice(
                        index=0,
                        free_memory_mib=4096,
                        compute_capability=8.6,
                        supported_compute_types=frozenset({"float16"}),
                    ),
                    CudaDevice(
                        index=1,
                        name="NVIDIA RTX A5000",
                        free_memory_mib=16000,
                        compute_capability=8.6,
                        supported_compute_types=frozenset({"float16"}),
                    ),
                )
            )
        )
        self.assertEqual(selection.device_index, 1)
        self.assertEqual(selection.device_name, "NVIDIA RTX A5000")

    def test_no_cuda_means_cpu_but_explicit_cuda_is_an_error(self) -> None:
        selection = select_asr_device(CudaProbe((), "CUDA libraries unavailable"))
        self.assertEqual(selection.device, "cpu")
        with self.assertRaisesRegex(ListenKitError, "no usable CUDA device"):
            select_asr_device(
                CudaProbe((), "CUDA libraries unavailable"),
                requested_device="cuda",
            )

    def test_cpu_rejects_irrelevant_device_index(self) -> None:
        with self.assertRaisesRegex(ListenKitError, "only valid with auto or cuda"):
            select_asr_device(
                CudaProbe(()), requested_device="cpu", requested_device_index=1
            )

    def test_cuda_probe_merges_runtime_capabilities_and_nvidia_memory(self) -> None:
        runtime_result = mock.Mock(
            returncode=0,
            stdout=json.dumps(
                {
                    "devices": [
                        {
                            "index": 0,
                            "supported_compute_types": ["float16", "int8_float16"],
                        }
                    ],
                    "libraries": {"cublas64_12.dll": True, "cudnn64_9.dll": False},
                }
            ),
            stderr="",
        )
        with mock.patch(
            "listenkit_cli.asr_device.run_command", return_value=runtime_result
        ), mock.patch(
            "listenkit_cli.asr_device._query_nvidia_smi",
            return_value={
                0: {
                    "name": "NVIDIA GeForce RTX 5090",
                    "uuid": "GPU-test",
                    "total_memory_mib": "32768",
                    "free_memory_mib": "30000",
                    "compute_capability": "12.0",
                }
            },
        ):
            probe = probe_cuda_devices(Path("runtime-python"), environment={})
        self.assertEqual(len(probe.devices), 1)
        self.assertEqual(probe.devices[0].name, "NVIDIA GeForce RTX 5090")
        self.assertEqual(probe.devices[0].free_memory_mib, 30000)
        self.assertEqual(probe.devices[0].compute_capability, 12.0)
        self.assertIn("float16", probe.devices[0].supported_compute_types)
        self.assertIn(("cublas64_12.dll", True), probe.libraries)
        self.assertIn(("cudnn64_9.dll", False), probe.libraries)

    def test_missing_cuda_runtime_libraries_force_auto_cpu(self) -> None:
        probe = CudaProbe(
            (
                CudaDevice(
                    index=0,
                    compute_capability=8.9,
                    free_memory_mib=8192,
                    supported_compute_types=frozenset({"float16"}),
                ),
            ),
            "Required CUDA libraries are not loadable: cublas64_12.dll",
            (("cublas64_12.dll", False),),
        )
        selection = select_asr_device(probe)
        self.assertEqual(selection.device, "cpu")
        self.assertIn("cublas64_12.dll", selection.reason)
        with self.assertRaisesRegex(ListenKitError, "CUDA runtime is not ready"):
            select_asr_device(probe, requested_device="cuda")

    def test_cuda_retry_and_error_classification(self) -> None:
        selection = select_asr_device(
            CudaProbe(
                (
                    CudaDevice(
                        index=0,
                        free_memory_mib=8192,
                        compute_capability=8.6,
                        supported_compute_types=frozenset(
                            {"float16", "int8_float16"}
                        ),
                    ),
                )
            )
        )
        self.assertEqual(cuda_retry_compute_type(selection), "int8_float16")
        self.assertTrue(is_cuda_runtime_failure("cuBLAS failed: out of memory"))
        self.assertFalse(is_cuda_runtime_failure("Audio file is corrupt"))

    def test_transcription_retries_cuda_then_records_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            audio = root / "输入.wav"
            audio.write_bytes(b"audio")
            helper = root / "helper.py"
            helper.write_text("# fake", encoding="utf-8")
            probe = CudaProbe(
                (
                    CudaDevice(
                        index=0,
                        name="NVIDIA RTX 4070",
                        free_memory_mib=8192,
                        compute_capability=8.9,
                        supported_compute_types=frozenset(
                            {"float16", "int8_float16"}
                        ),
                    ),
                )
            )
            failure = mock.Mock(
                returncode=1,
                stdout=json.dumps(
                    {
                        "schema_version": 1,
                        "error": {"type": "RuntimeError", "message": "CUDA out of memory"},
                    }
                ),
                stderr="faster-whisper failed: CUDA out of memory",
            )
            success = mock.Mock(
                returncode=0,
                stdout=json.dumps(
                    {
                        "schema_version": 1,
                        "engine": "faster-whisper",
                        "model": "small",
                        "full_text": "ok",
                        "segments": [],
                        "timing_complete": True,
                    }
                ),
                stderr="",
            )
            with mock.patch(
                "listenkit_cli.transcription._managed_runtime_python",
                return_value=Path(sys.executable),
            ), mock.patch(
                "listenkit_cli.transcription.can_import_faster_whisper", return_value=True
            ), mock.patch(
                "listenkit_cli.transcription.probe_cuda_devices", return_value=probe
            ), mock.patch(
                "listenkit_cli.transcription.run_command", side_effect=[failure, success]
            ) as runner:
                rendered = transcribe_audio(
                    audio_path=audio,
                    locale="en-US",
                    device="auto",
                    environment={
                        **os.environ,
                        "LISTENKIT_FASTER_WHISPER_HELPER": str(helper),
                    },
                )
            payload = json.loads(rendered)
            self.assertEqual(payload["device"], "cuda")
            self.assertEqual(payload["compute_type"], "int8_float16")
            self.assertEqual(payload["fallback_from"], ["cuda/float16"])
            self.assertIn("CUDA out of memory", payload["fallback_reason"])
            first_args = runner.call_args_list[0].args[0]
            second_args = runner.call_args_list[1].args[0]
            self.assertEqual(first_args[first_args.index("--compute-type") + 1], "float16")
            self.assertEqual(
                second_args[second_args.index("--compute-type") + 1], "int8_float16"
            )

    def test_auto_transcription_falls_back_to_cpu_after_cuda_retries(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            audio = root / "audio.wav"
            audio.write_bytes(b"audio")
            helper = root / "helper.py"
            helper.write_text("# fake", encoding="utf-8")
            probe = CudaProbe(
                (
                    CudaDevice(
                        index=0,
                        free_memory_mib=8192,
                        compute_capability=8.6,
                        supported_compute_types=frozenset(
                            {"float16", "int8_float16"}
                        ),
                    ),
                )
            )
            cuda_failure = mock.Mock(
                returncode=1,
                stdout=json.dumps(
                    {
                        "schema_version": 1,
                        "error": {"type": "RuntimeError", "message": "cuDNN DLL missing"},
                    }
                ),
                stderr="CUDA cuDNN DLL missing",
            )
            cpu_success = mock.Mock(
                returncode=0,
                stdout=json.dumps(
                    {
                        "schema_version": 1,
                        "engine": "faster-whisper",
                        "model": "small",
                        "full_text": "cpu ok",
                        "segments": [],
                        "timing_complete": True,
                    }
                ),
                stderr="",
            )
            with mock.patch(
                "listenkit_cli.transcription._managed_runtime_python",
                return_value=Path(sys.executable),
            ), mock.patch(
                "listenkit_cli.transcription.can_import_faster_whisper", return_value=True
            ), mock.patch(
                "listenkit_cli.transcription.probe_cuda_devices", return_value=probe
            ), mock.patch(
                "listenkit_cli.transcription.run_command",
                side_effect=[cuda_failure, cuda_failure, cpu_success],
            ) as runner:
                rendered = transcribe_audio(
                    audio_path=audio,
                    locale="en-US",
                    device="auto",
                    environment={
                        **os.environ,
                        "LISTENKIT_FASTER_WHISPER_HELPER": str(helper),
                    },
                )
            payload = json.loads(rendered)
            self.assertEqual(payload["device"], "cpu")
            self.assertEqual(payload["compute_type"], "int8")
            self.assertEqual(
                payload["fallback_from"],
                ["cuda/float16", "cuda/int8_float16"],
            )
            third_args = runner.call_args_list[2].args[0]
            self.assertEqual(third_args[third_args.index("--device") + 1], "cpu")


class MediaCoreTests(unittest.TestCase):
    def test_windows_reserved_base_names_are_rejected(self) -> None:
        for value in ("CON", "CON.txt", "nul", "COM1", "LPT9"):
            with self.subTest(value=value), self.assertRaises(ListenKitError):
                validate_base_name(value)

    def test_windows_invalid_filename_characters_are_rejected(self) -> None:
        for value in ("bad:name", "bad*name", "bad?name", 'bad"name'):
            with self.subTest(value=value), self.assertRaises(ListenKitError):
                validate_base_name(value)

    def test_nested_base_names_are_rejected_on_every_platform(self) -> None:
        for value in ("../audio", r"folder\audio", "folder/audio"):
            with self.subTest(value=value), self.assertRaises(ListenKitError):
                validate_base_name(value)

    def test_same_local_input_is_a_noop_without_ffmpeg(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "音声 with spaces.m4a"
            source.write_bytes(b"audio")
            with mock.patch("listenkit_cli.media.require_command") as require:
                result = import_audio(
                    input_path=source,
                    output_dir=root,
                    base_name=source.stem,
                    audio_format="m4a",
                )
            self.assertEqual(result, [source])
            require.assert_not_called()

    def test_vtt_parser_accepts_utf8_bom_and_entities(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "字幕.vtt"
            path.write_text(
                "\ufeffWEBVTT\n\n00:00.000 --> 00:01.500\n<c>hello &amp; world</c>\n",
                encoding="utf-8",
            )
            self.assertEqual(
                parse_vtt(path),
                [{"start": 0.0, "end": 1.5, "text": "hello & world"}],
            )

    def test_subtitle_extraction_prefers_manual(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "out.json"

            def fake_run(args, **kwargs):
                work_dir = Path(args[args.index("--paths") + 1])
                (work_dir / "subtitle.ja.vtt").write_text(
                    "WEBVTT\n\n00:00.000 --> 00:01.000\nmanual\n", encoding="utf-8"
                )
                return mock.Mock(returncode=0, stdout="", stderr="")

            with mock.patch("listenkit_cli.subtitles.require_command", return_value="yt-dlp"), mock.patch(
                "listenkit_cli.subtitles.run_command", side_effect=fake_run
            ):
                extract_subtitles("https://example.test/video", locale="ja-JP", output=output)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["subtitle_kind"], "manual")
            self.assertEqual(payload["full_text"], "manual")


class WorkflowCoreTests(unittest.TestCase):
    def test_locale_mapping_is_cross_platform(self) -> None:
        self.assertEqual(locale_from_language("日本語"), "ja-JP")
        self.assertEqual(locale_from_language("English"), "en-US")
        self.assertEqual(locale_from_language("中文"), "zh-CN")
        self.assertEqual(locale_from_language("한국어"), "ko-KR")

    def test_render_writes_utf8_markdown_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            payload = root / "payload.json"
            output = root / "目录 with spaces" / "结果.md"
            payload.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "engine": "test",
                        "locale": "ja-JP",
                        "full_text": "こんにちは",
                        "segments": [],
                        "timing_complete": True,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            render_transcript(
                source_ref=r"C:\Media\音声.m4a",
                transcript_json=payload,
                title="日本語 title",
                language="Japanese",
                output=output,
            )
            rendered = output.read_text(encoding="utf-8")
            self.assertIn("# 日本語 title", rendered)
            self.assertIn("こんにちは", rendered)

    def test_local_end_to_end_orchestration_produces_same_stem_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "输入 audio.wav"
            source.write_bytes(b"source")
            output = root / "输出 folder" / "note.md"
            imported = output.parent / "audio" / "note.m4a"

            def fake_import_audio(**kwargs):
                imported.parent.mkdir(parents=True, exist_ok=True)
                imported.write_bytes(b"converted")
                return [imported]

            def fake_transcribe_audio(**kwargs):
                target = kwargs["output"]
                target.write_text(
                    json.dumps(
                        {
                            "schema_version": 1,
                            "engine": "faster-whisper",
                            "locale": kwargs["locale"],
                            "full_text": "ok",
                            "segments": [],
                            "timing_complete": True,
                        }
                    ),
                    encoding="utf-8",
                )
                return target

            with mock.patch("listenkit_cli.workflow.import_audio", side_effect=fake_import_audio), mock.patch(
                "listenkit_cli.workflow.transcribe_audio", side_effect=fake_transcribe_audio
            ):
                result = generate_markdown(
                    input_path=source,
                    output=output,
                    language="Japanese",
                    auto_init=True,
                )
            self.assertEqual(result, output)
            self.assertTrue(output.is_file())
            self.assertTrue(output.with_suffix(".json").is_file())
            self.assertIn("ok", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
