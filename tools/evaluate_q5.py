"""Reproducible Q5 semantic, offline and bounded stress gates (nonzero on failure)."""
import argparse
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from tools.evaluate_quality import peak_memory
from tools.q5_corpus import FORMATS, build, check

CASES = (*FORMATS, "stress-txt", "stress-csv", "stress-xlsx", "stress-pdf")


def evaluate(case):
    from document_converter.services.offline import install_network_guard
    attempts = install_network_guard()
    from document_converter.core.router import ConverterRouter
    with TemporaryDirectory(prefix="hybrid-q5-") as folder:
        root = Path(folder)
        source, options, oracle = build(root, case)
        start = perf_counter()
        result = ConverterRouter(options=options).convert(source)
        seconds = perf_counter() - start
        checks = check(result, oracle, root)
        # urllib3 probes IPv6 availability by binding ::1 during import. The
        # guard denies that too, but it is not an outbound request or DNS lookup.
        checks["no_outbound_python_network_attempts"] = not [event for event in attempts if event != "socket.bind"]
        return {"case": case, "checks": checks, "seconds": round(seconds, 6),
                "input_bytes": source.stat().st_size, "output_bytes": len(result.markdown.encode("utf-8")),
                "process_peak_bytes": peak_memory(), "warning_count": len(result.warnings),
                "blocked_local_bind_probes": attempts.count("socket.bind")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=CASES)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error("--repeat must be positive")
    if args.case:
        row = evaluate(args.case)
        print(json.dumps(row))
        return 0 if all(row["checks"].values()) else 1
    rows = []
    for case in CASES:
        for repeat in range(args.repeat):
            try:
                completed = subprocess.run([sys.executable, __file__, "--case", case],
                                           capture_output=True, text=True, timeout=120)
                row = json.loads(completed.stdout)
                row["checks"]["child_exit_success"] = completed.returncode == 0
            except (subprocess.TimeoutExpired, json.JSONDecodeError):
                row = {"case": case, "checks": {"child_completed_with_report": False}}
            row["run"] = repeat + 1
            rows.append(row)
    summaries = []
    for case in CASES:
        measured = [r for r in rows if r["case"] == case and "seconds" in r]
        if measured:
            summaries.append({"case": case, "runs": len(measured),
                              "median_seconds": round(statistics.median(r["seconds"] for r in measured), 6),
                              "max_peak_bytes": max(r["process_peak_bytes"] for r in measured)})
    report = {"python": platform.python_version(), "platform": platform.platform(),
              "method": "Independent generated sources; checked-in semantic goldens; fresh process per case/run. Timing excludes fixture generation, includes router/import/conversion. Peak includes generation, conversion and asset validation. Python socket guard is not an OS sandbox. No general accuracy percentage.",
              "passed": all(all(r["checks"].values()) for r in rows),
              "results": rows, "summary": summaries}
    output = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    print(output)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
