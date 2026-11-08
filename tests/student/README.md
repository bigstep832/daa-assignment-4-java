# Independent student tests

Run from the repository root with Python 3.12+ and JDK 17+:

```sh
python tests/student/test_solution.py
```

If Java is not on `PATH`, set `JAVA_HOME` or pass `--java-home /path/to/jdk`.
The runner compiles the submitted Java sources, uses a 384 MiB heap and
`-XX:ActiveProcessorCount=1`, enforces 20 seconds per JSONL batch and an 8 MiB
output limit, and writes actual counts, timings, source hashes and representative
expected/actual results to `tests/student/test_results.json`.

Small inputs use independent exhaustive oracles: subsequence enumeration,
all next adjacent merges, all vertex subsets, direct window comparisons,
materialized short suffixes, and independent per-pattern occurrence counts.
Witness validation accepts any optimum and replays merge plans chronologically.
The suite does not import the implementation or the public validator.

Reproducible randomized cases use seed `4102026`. Exhaustive binary strings,
empty inputs, zero/tied optima, printable ASCII, overlaps, the `ab`/`dj` hash
collision, negative rolling remainders, and relabelled trees are included.
Mixed batches repeat requests and interleave different commands.

Large cases exercise every published maximum length/count, 64-bit totals,
100000-vertex chains and stars, 50000-character suffix arrays, 100000-character
dictionary input, 10000 duplicate patterns, 100 independent texts, and dense
Aho matches. Large expected values follow explicit formulas or known structures.
Passing these tests is not a promised grade.

## Reproducible search comparison

```sh
python tests/student/run_benchmark.py
```

This compiles `SearchBenchmark.java` into the ignored `Java/build/benchmark`
directory. The benchmark verifies every input with an independent oracle, then
records five timed batches for each method at three sizes for both random and
repetitive inputs. Raw times, runtime, hardware, method, seed and source hash are
saved to `benchmark_results.json`; `ANALYSIS.md` explains the measurements.
