from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def executable(name: str) -> str:
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        suffix = ".exe" if os.name == "nt" else ""
        return str(Path(java_home) / "bin" / (name + suffix))
    return name


def hardware() -> dict:
    result = {"platform": platform.platform(), "processor": platform.processor()}
    if os.name == "nt":
        command = (
            "$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1; "
            "$system = Get-CimInstance Win32_ComputerSystem; "
            "@{cpu=$cpu.Name; logical_processors=$system.NumberOfLogicalProcessors; "
            "ram_bytes=$system.TotalPhysicalMemory} | ConvertTo-Json -Compress"
        )
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True, text=True, timeout=30,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            result.update(json.loads(proc.stdout))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="tests/student/benchmark_results.json")
    args = parser.parse_args()
    build = ROOT / "Java" / "build" / "benchmark"
    build.mkdir(parents=True, exist_ok=True)
    compile_command = [
        executable("javac"), "--release", "17", "-encoding", "UTF-8", "-d", str(build),
        str(ROOT / "Java/source/Algorithms.java"),
        str(ROOT / "Java/source/Json.java"),
        str(ROOT / "tests/student/SearchBenchmark.java"),
    ]
    subprocess.run(compile_command, check=True, timeout=60)
    run_command = [executable("java"), "-Xmx384m", "-cp", str(build), "SearchBenchmark"]
    run = subprocess.run(run_command, capture_output=True, text=True, encoding="utf-8", check=True, timeout=120)
    result = json.loads(run.stdout)
    result["recorded_at_utc"] = datetime.now(timezone.utc).isoformat()
    result["hardware"] = hardware()
    result["reproduce"] = "python tests/student/run_benchmark.py"
    result["java_options"] = "-Xmx384m (default tiered JIT)"
    result["algorithms_sha256"] = hashlib.sha256((ROOT / "Java/source/Algorithms.java").read_bytes()).hexdigest()
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: all benchmark inputs and collision/overlap/empty-pattern checks; {len(result['rows'])} measured rows")
    print("Times: microseconds per call (each run averages 200 calls).")
    for row in result["rows"]:
        raw = ", ".join(f"{value:.3f}" for value in row["microseconds_per_call"])
        print(f"{row['case']:10} n={row['n']:4} m={row['m']:3} {row['algorithm']:5} [{raw}], median={row['median_microseconds_per_call']:.3f}")
    print(f"Saved: {output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
