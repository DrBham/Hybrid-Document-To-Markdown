"""Q5 process lifecycle, source-backed corpus and failure recovery acceptance."""
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

import pytest

from document_converter.core.options import ConversionOptions
from document_converter.core.router import ConverterRouter
from document_converter.services.batch_converter import BatchConverter
from document_converter.services.process_converter import (
    ProcessConverter, ConversionCancelled, ConversionTimedOut, ConversionProcessError,
)

ROOT = Path(__file__).resolve().parents[1]
FORMATS = ("txt", "csv", "json", "xml", "html", "htm", "docx", "pptx", "xlsx", "pdf")


@pytest.mark.parametrize("case", (*FORMATS, "stress-txt", "stress-csv", "stress-xlsx", "stress-pdf"))
def test_source_oracles_under_network_guard(case):
    completed = subprocess.run([sys.executable, str(ROOT / "tools/evaluate_q5.py"), "--case", case],
                               capture_output=True, text=True, timeout=120)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    report = json.loads(completed.stdout)
    assert report["checks"] and all(report["checks"].values()), report


@pytest.mark.parametrize("extension", FORMATS)
def test_production_worker_preserves_corpus_results(tmp_path, extension):
    from tools.q5_corpus import build, check
    source, options, oracle = build(tmp_path, extension)
    result = ProcessConverter(options).convert(source)
    checks = check(result, oracle, tmp_path)
    assert checks and all(checks.values()), checks
    assert result.source_path == source and result.source_format == extension


def worker_script(tmp_path, body):
    script = tmp_path / "worker.py"
    script.write_text(body, encoding="utf-8")
    return script


def test_cancel_active_worker_cleans_scratch_and_allows_restart(tmp_path, monkeypatch):
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    ready = tmp_path / "ready"
    script = worker_script(tmp_path, "import pathlib, sys, time\npathlib.Path(sys.argv[1]).write_text('ready')\ntime.sleep(60)\n")
    service = ProcessConverter(scratch_root=scratch, timeout_seconds=30)
    source = tmp_path / "source.txt"
    source.write_bytes(b"original\r\n  end  ")
    real_command = service._command
    monkeypatch.setattr(service, "_command", lambda request: [sys.executable, str(script), str(ready)])
    cancelled, errors = threading.Event(), []
    def convert():
        try:
            service.convert(source, cancelled=cancelled)
        except Exception as exc:
            errors.append(exc)
    thread = threading.Thread(target=convert)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not ready.exists() and time.monotonic() < deadline:
            time.sleep(.01)
        assert ready.exists(), "worker did not reach active parsing simulation"
        cancelled.set()
        thread.join(5)
        assert not thread.is_alive()
        assert len(errors) == 1 and isinstance(errors[0], ConversionCancelled)
        assert list(scratch.iterdir()) == []
    finally:
        cancelled.set()
        thread.join(5)
    monkeypatch.setattr(service, "_command", real_command)
    assert service.convert(source).markdown == "original\r\n  end  "
    assert list(scratch.iterdir()) == []


def test_timeout_terminates_child_and_removes_partial_scratch(tmp_path, monkeypatch):
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    script = worker_script(tmp_path, "import pathlib, sys, time\n(pathlib.Path(sys.argv[1]).parent / 'partial.tmp').write_text('partial')\ntime.sleep(60)\n")
    service = ProcessConverter(timeout_seconds=.4, scratch_root=scratch)
    monkeypatch.setattr(service, "_command", lambda request: [sys.executable, str(script), str(request)])
    with pytest.raises(ConversionTimedOut):
        service.convert(tmp_path / "source.txt")
    assert list(scratch.iterdir()) == []


@pytest.mark.parametrize("body", ["import os; os._exit(9)", "pass"])
def test_crash_or_missing_result_is_file_failure(tmp_path, monkeypatch, body):
    script = worker_script(tmp_path, body)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    service = ProcessConverter(scratch_root=scratch)
    monkeypatch.setattr(service, "_command", lambda request: [sys.executable, str(script)])
    with pytest.raises(ConversionProcessError):
        service.convert(tmp_path / "source.txt")
    assert list(scratch.iterdir()) == []


def test_failed_file_does_not_break_following_real_process(tmp_path):
    paths = [tmp_path / name for name in ("good.txt", "broken.txt", "after.txt")]
    for path, content in zip(paths, [b"first", b"\xffPRIVATE_CONTENT", b"last"]):
        path.write_bytes(content)
    result = BatchConverter().convert(paths)
    assert [r.result.markdown for r in result.successful] == ["first", "last"]
    assert len(result.failed) == 1
    assert "UnicodeDecodeError" in result.failed[0].error
    assert "PRIVATE_CONTENT" not in result.failed[0].error


def test_worker_enforces_output_budget(tmp_path):
    source = tmp_path / "large.txt"
    source.write_text("0123456789")
    with pytest.raises(ConversionProcessError, match="resource limits"):
        ProcessConverter(ConversionOptions(max_output_bytes=5)).convert(source)
    assert source.read_text() == "0123456789"


def test_timeout_keeps_batch_running_for_next_file(tmp_path, monkeypatch):
    script = worker_script(tmp_path, "import time\ntime.sleep(60)\n")
    first, second = tmp_path / "slow.txt", tmp_path / "next.txt"
    first.write_text("slow")
    second.write_text("next")
    batch = BatchConverter(timeout_seconds=2)
    original = batch._process._command
    def command(request):
        source = json.loads(request.read_text())["source"]
        return [sys.executable, str(script)] if source.endswith("slow.txt") else original(request)
    monkeypatch.setattr(batch._process, "_command", command)
    outcomes = batch.convert([first, second]).outcomes
    assert "ConversionTimedOut" in outcomes[0].error
    assert outcomes[1].result.markdown == "next"


def test_cancel_batch_keeps_completed_results_and_skips_remaining(tmp_path, monkeypatch):
    ready = tmp_path / "ready"
    script = worker_script(tmp_path, "import pathlib, sys, time\npathlib.Path(sys.argv[1]).write_text('ready')\ntime.sleep(60)\n")
    paths = [tmp_path / name for name in ("first.txt", "slow.txt", "remaining.txt")]
    for path in paths:
        path.write_text(path.stem)
    batch, results = BatchConverter(), []
    original = batch._process._command
    def command(request):
        source = json.loads(request.read_text())["source"]
        return [sys.executable, str(script), str(ready)] if source.endswith("slow.txt") else original(request)
    monkeypatch.setattr(batch._process, "_command", command)
    thread = threading.Thread(target=lambda: results.append(batch.convert(paths)))
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not ready.exists() and time.monotonic() < deadline:
            time.sleep(.01)
        assert ready.exists()
        batch.cancel()
        thread.join(5)
        assert not thread.is_alive()
        outcomes = results[0].outcomes
        assert outcomes[0].result.markdown == "first"
        assert "Cancelled during" in outcomes[1].error
        assert "Cancelled before" in outcomes[2].error
    finally:
        batch.cancel()
        thread.join(5)


def test_worker_missing_dependency_has_actionable_private_error(tmp_path):
    request = tmp_path / "request.json"
    request.write_text(json.dumps({"source": str(tmp_path / "source.docx"), "options": {}}))
    script = worker_script(tmp_path, '''import importlib.abc, sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'document_converter.core.router':
            raise ModuleNotFoundError('PRIVATE_DEPENDENCY_DETAILS')
sys.meta_path.insert(0, Block())
from document_converter.services.conversion_worker import main
main(sys.argv[1])
''')
    subprocess.run([sys.executable, str(script), str(request)],
                   env=dict(os.environ, PYTHONPATH=str(ROOT / "src")), check=True, timeout=15)
    error = json.loads((tmp_path / "response.json").read_text())["error"]
    assert "reinstall" in error and "PRIVATE_DEPENDENCY_DETAILS" not in error


@pytest.mark.parametrize("extension", ["docx", "pptx", "xlsx", "pdf"])
def test_valid_empty_office_or_pdf_has_no_invented_content(tmp_path, extension):
    source = tmp_path / ("empty." + extension)
    if extension == "docx":
        from docx import Document
        Document().save(source)
    elif extension == "pptx":
        from pptx import Presentation
        Presentation().save(source)
    elif extension == "xlsx":
        from openpyxl import Workbook
        book = Workbook()
        book.save(source)
        book.close()
    else:
        import pypdfium2
        document = pypdfium2.PdfDocument.new()
        page = document.new_page(100, 100)
        document.save(str(source))
        page.close()
        document.close()
    result = ConverterRouter(options=ConversionOptions(pdf_mode="text")).convert(source)
    assert result.source_format == extension
    assert "00123" not in result.markdown and "base64" not in result.markdown
    if extension == "pdf":
        assert any("text layer" in warning for warning in result.warnings)


def test_malformed_csv_fails_and_structured_source_is_preserved(tmp_path):
    source = tmp_path / "bad.csv"
    source.write_text('id,note\n00123,"unclosed')
    with pytest.raises(Exception, match="unexpected end"):
        ConverterRouter().convert(source)
    for extension, content in [("json", '{"broken":'), ("xml", "<unclosed>")]:
        path = source.with_suffix("." + extension)
        path.write_text(content)
        assert content in ConverterRouter().convert(path).markdown


def test_missing_office_dependency_does_not_disable_text(tmp_path):
    script = worker_script(tmp_path, '''import importlib.abc, sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'markitdown', 'pypdfium2', 'openpyxl', 'mammoth'}:
            raise ModuleNotFoundError('dependency deliberately unavailable')
sys.meta_path.insert(0, Block())
from pathlib import Path
from document_converter.core.router import ConverterRouter
assert ConverterRouter().convert(Path(sys.argv[1])).markdown == 'exact'
assert 'markitdown' not in sys.modules
''')
    source = tmp_path / "source.txt"
    source.write_text("exact")
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    subprocess.run([sys.executable, str(script), str(source)], env=env, check=True, timeout=15)


def test_network_guard_denies_dns_connect_and_udp_without_leaking_address(tmp_path):
    script = worker_script(tmp_path, '''import socket
from document_converter.services.offline import install_network_guard, NetworkAccessBlocked
attempts = install_network_guard()
for operation in [lambda: socket.getaddrinfo('invalid.example', 443),
                  lambda: socket.socket().connect(('127.0.0.1', 9)),
                  lambda: socket.socket(socket.AF_INET, socket.SOCK_DGRAM).sendto(b'x', ('127.0.0.1', 9))]:
    try:
        operation()
    except NetworkAccessBlocked as exc:
        assert 'invalid.example' not in str(exc)
    else:
        raise AssertionError('network operation was not blocked')
assert len(attempts) == 3
''')
    subprocess.run([sys.executable, str(script)], env=dict(os.environ, PYTHONPATH=str(ROOT / "src")), check=True, timeout=15)


@pytest.mark.parametrize("extension", ["docx", "pptx", "xlsx", "pdf"])
def test_malformed_binary_files_fail_explicitly(tmp_path, extension):
    source = tmp_path / ("broken." + extension)
    source.write_bytes(b"invalid document")
    with pytest.raises(Exception):
        ConverterRouter().convert(source)


@pytest.mark.parametrize("extension", ["txt", "csv", "json", "xml", "html", "htm"])
def test_empty_text_documents_have_explicit_output_policy(tmp_path, extension):
    source = tmp_path / ("empty." + extension)
    source.write_bytes(b"")
    result = ConverterRouter().convert(source)
    assert result.source_format == extension
    if extension in {"txt", "html", "htm"}:
        assert result.markdown == ""
    elif extension in {"json", "xml"}:
        assert result.markdown == f"```{extension}\n\n```\n"
    else:
        assert "## Original CSV" in result.markdown


@pytest.mark.parametrize("seconds", [0, -1, float("nan"), float("inf")])
def test_deadline_configuration_is_bounded(seconds):
    with pytest.raises(ValueError):
        ProcessConverter(timeout_seconds=seconds)
