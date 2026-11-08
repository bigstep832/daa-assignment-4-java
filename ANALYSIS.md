# Assignment 4 — Java implementation and analysis

## Environment and commands

Language: **Java**, targeting Java 17 (`javac --release 17`). The supplied
`submission.json` already selects Java. Local verification used Python 3.13.2 and
Microsoft OpenJDK 17.0.20.1 (64-bit Server VM) on Windows. Hardware and the exact
benchmark runtime are recorded with the measured results below.

Run these commands from the repository root with Python 3.12+ and JDK 17+ on PATH:

```text
python tools/run.py --setup
python tools/run.py --check
python tools/run.py --input examples/lcs.jsonl
python tests/student/test_solution.py
python tests/student/run_benchmark.py
```

The launcher compiles `Java/source/*.java` to `Java/build`, then runs
`java -Xmx384m -cp Java/build Main`. Equivalently:

```text
javac --release 17 -encoding UTF-8 -d Java/build Java/source/Algorithms.java Java/source/Json.java Java/source/Main.java
java -Xmx384m -cp Java/build Main
```

For the local Windows environment, the session PATH was prefixed with the existing
Microsoft JDK 17 `bin` directory; no machine-wide settings were changed. The
provided JSON transport behaviour is retained. The compiler warning about
unchecked casts is inherited from the template. Setup passed; all 44 public cases
and the repeated 88-request mixed batch passed. Own tests and benchmark results
are recorded below. These checks do not predict the hidden-test grade.

## Algorithm explanations

All input strings are printable ASCII, so Java `char` indices agree with the
specified character positions. The methods allocate fresh request-local state.
No algorithm uses a built-in substring search. Costs, weights, and Aho counts use
`long`; position indices and DP lengths fit in `int`. Complexity below excludes
JSON parsing and distinguishes auxiliary storage from the returned output.

### LCS

`dp[i][j]` is the longest common subsequence length of `a[0..i)` and `b[0..j)`.
The zero row and column are zero. Equal final characters give
`dp[i-1][j-1]+1`; otherwise use `max(dp[i-1][j], dp[i][j-1])`.
Increasing `i`, then `j`, makes all predecessors available.

Correctness follows by induction on prefix lengths. If final characters differ,
a common subsequence must omit at least one of them, so one of the two smaller
states attains the optimum. If they agree, an optimum can end with this shared
character; removing it leaves the diagonal subproblem. Backtracking from `(n,m)`
appends characters on equal-character diagonal moves and otherwise follows a
predecessor with the same optimal value. Ties choose the upper predecessor.
Reversing the collected characters gives a subsequence of both inputs of length
`dp[n][m]`; no lexicographically smallest witness is required.

Time and auxiliary memory are `O((n+1)(m+1))`, including table initialization and
empty inputs; the returned sequence uses `O(min(n,m)+1)` space. `tea_time` versus
`team` gives `team`, detecting confusion between substring and subsequence.

### Ordered adjacent-block merging

`dp[l][r]` is the minimum cost to turn the closed original interval `[l,r]` into
one block. A singleton costs zero. For every last split `l <= k < r`, consider
`dp[l][k] + dp[k+1][r] + prefix[r+1] - prefix[l]`. Fill intervals in increasing
length and retain the first minimizing `k` in `split[l][r]`.

Every legal final merge combines two adjacent intervals with some such `k`.
Replacing a nonoptimal child plan would improve the whole plan, so optimal
substructure holds. Conversely, two optimal child plans followed by that merge
are feasible. Minimizing over all splits therefore gives exactly the optimum.
An explicit postorder stack emits left child, right child, then `[l,k,r]`.
Consequently the two blocks exist when their parent instruction is executed;
the output has exactly `n-1` instructions. Empty/singleton inputs return cost zero
and an empty plan.

For `n>=1`: `O(n^3)` time, `O(n^2)` auxiliary storage, `O(n)` output; empty input
takes `O(1)`. Prefix sums, candidates, and DP values are `long`. `[1,100,1]` costs
203; merging the two ones first would illegally ignore adjacency. Zero sizes
exercise ties without requiring any particular optimal plan.

### Maximum-weight independent set on a tree

Root at vertex zero and build a parent-before-child order iteratively, using a
flat adjacency list (`head`, `to`, `next`). For each vertex `v`, `take[v]` is the
best subtree weight if `v` is selected, and `skip[v]` is the best if it is not:
`take[v] = weight[v] + sum(skip[child])`,
`skip[v] = sum(max(take[child], skip[child]))`.
The reverse order processes all children first. Leaves have `take=weight` and
`skip=0`. The empty tree returns zero and no vertices.

Conditioned on the parent's decision, different child subtrees have no edges
between them. The recurrences exhaust the two possible decisions for each child,
so induction proves optimality. Reconstruction traverses the forward order. A
selected parent forces a child to be skipped; otherwise select the child exactly
when `take>skip`. Ties choose skipping. This reconstructs the same optimum and
never includes both endpoints of an edge. Negative weights do not force any
selection because skipping every vertex is feasible.

Time and auxiliary memory are `O(n+1)`; selected output is `O(n+1)`. Both passes
are iterative, including reconstruction. A 100000-vertex equal-weight chain checks
stack safety; large weights check that the total is not stored in an `int`.

### Naive exact search

Test each start `0..n-m`, comparing characters from `j=0` until a mismatch or
`j=m`. The comparison invariant is that the first `j` pattern characters equal
the corresponding text window. Report precisely the windows with `j=m`. Starts
increase by one, so overlaps are retained and output is sorted. If `m=0`, each
of the `n+1` boundaries succeeds without indexing the pattern; if `m>n`, there
are no candidate starts. For `aaaaa`/`aaa`, the result is `[0,1,2]`.

Time is `O(n*m+n+1)` including output; auxiliary space is `O(1)` and output
space is `O(z+1)` for `z` matches. Input strings are referenced, not copied.

### KMP

`pi[i]` is the longest proper prefix of `pattern[0..i]` that is also its suffix.
Start from `pi[i-1]`, repeatedly fall back to `pi[j-1]` on mismatch, and extend
by one on equality. These are all possible shorter borders, in descending order.
During scanning, `matched` is the length of the longest pattern prefix matching
a suffix of the text already consumed. The same fallback chain preserves all
possible matches without moving the text index backwards.

On reaching `m`, output `i-m+1` and fall back to `pi[m-1]`, rather than zero,
so a suffix of this match can start an overlapping one. Empty patterns are handled
before any pattern indexing. For `abababa`/`aba`, outputs are `[0,2,4]`.
Each successful extension raises the matched length by one; all decreases can
be charged to earlier increases. Thus time is `O(n+m+z+1)`, auxiliary memory
`O(m+1)`, and output memory `O(z+1)`.

### Exact Rabin–Karp

Use ASCII character codes, base `B=31`, modulus `M=101`, and the highest power
for the leftmost character. Let `power=B^(m-1) mod M`. Initially build the pattern
and first window hashes left to right. To slide, remove
`oldCharacter*power`, reduce modulo M, add M if the remainder is negative, then
multiply by B and add the new character modulo M.

The polynomial identity proves that the maintained hash equals the current
window's hash. A true match must have the same hash. Equal hashes only trigger
a fresh character-by-character comparison, so collisions cannot create false
matches. Empty patterns and patterns longer than the text return before hash
construction. The supplied collision `abdj`/`ab` returns only `[0]`: both `ab`
and `dj` hash to 75, but the latter fails verification.

For `1<=m<=n`, time is `O(n+m+c*m)` for `c` equal-hash candidates, including the
possible quadratic case. A bound covering all inputs is `O(n*m+n+m+1)`.
This rolling-window implementation uses `O(1)` auxiliary space and `O(z+1)`
output space. All hash arithmetic uses `long` and normalized residues.

### Suffix array and Kasai LCP

Initially ranks encode single characters as positive integers. In a doubling
round of width `w`, suffix `i` is keyed by `(rank[i], rank[i+w])`, with zero for
an out-of-range second half. Two stable counting-sort passes (second key, then
first) order the pairs. Equal pairs receive the same new positive rank; others
receive increasing ranks. By induction the ranks describe the first `2w`
characters after each round. Once all ranks differ, or the width covers the
text, pair order is full lexicographic suffix order. The zero rank is only a
virtual end marker: the output contains exactly indices `0..n-1`. No suffix
strings are materialized. Empty and singleton inputs are explicit valid cases.

Kasai constructs inverse suffix-array positions, then scans original starts
`i` in increasing order. It compares suffix `i` with its lexicographic predecessor.
After a common prefix of length `h`, the next start can reuse at least `h-1`
characters when it has a predecessor; the lexicographically first suffix resets
the carry to zero. The remaining characters are compared explicitly and the
result is stored at `lcp[inverse[i]]`. Total increments and decrements of the
carry are linear, so this pass is `O(n)`.

Any substring appearing at distinct starts prefixes two suffixes. Suffixes with
that prefix form a contiguous lexicographic interval, hence an adjacent pair
shares at least that many characters. Conversely any positive adjacent LCP is
a repeat. The largest LCP therefore yields a longest repeated substring,
including overlapping occurrences. Ties retain the first maximum encountered
in the original-start scan. The code copies only the final repeated string.

Counting arrays have `O(n+95)` entries, so doubling is `O(n log(n+1))` time;
auxiliary and output memory are `O(n+1)`. Empty input costs `O(1)`. `banana`
has SA `[5,3,1,0,4,2]`, LCP `[0,1,3,0,0,2]`, and repeat `ana`. Tests with the
literal character `$` detect accidental treatment of a real character as sentinel.

### Aho–Corasick

Insert all patterns into one trie. Each node owns a 95-entry transition array;
one terminal-state index is saved for each original dictionary position.
Duplicates share the trie state, but retain separate result columns.
Breadth-first processing creates failure links: a child's failure state is the
transition on the child's character from its parent's failure state. Missing
transitions are filled from that same fallback row. Root's missing transitions
remain root. BFS guarantees that all needed fallback rows are complete first.

While scanning a text, the state denotes the longest suffix of the consumed text
that is a dictionary prefix. Increment that state's visit count once per
character. In reverse BFS order, add each state's visits to its failure parent.
A pattern matches precisely when its terminal state lies on the current state's
failure chain, so this propagation counts suffix patterns and overlaps. It
aggregates states rather than enumerating every dictionary-entry occurrence.
Read terminal visits in original pattern order. Each independent text starts
with state zero and a newly zeroed visit array; each request builds its own
automaton. Empty dictionaries produce one empty row per text, and no texts
produce no rows.

Let L be total pattern length, S the number of states (including root), p the
number of patterns, and q the number of texts. Construction takes
`O(L+95*S+p)` time and `O(95*S+p)` auxiliary space. Query/propagation for one
text takes `O(|text|+S+p)` time and `O(S)` scratch space. Output space is
`O(q*(p+1)+1)`; count values are `long`. For patterns `[a,aa,a]` and texts
`[aaa,"",aaa]`, rows are `[3,2,3]`, `[0,0,0]`, `[3,2,3]`, checking duplicates,
suffixes, overlaps and reset together.

## Own tests

`python tests/student/test_solution.py` passed **5713 requests in 15 batches**.
The complete report is [test_results.json](tests/student/test_results.json),
including actual outputs for representative inputs, batch times and source
SHA-256 hashes. The seed is 4102026. Per-command counts are LCS 1073, merge 436,
tree 213, naive 1158, KMP 1158, RK 1158, suffix 321 and Aho 196.

The independent small-input oracles enumerate subsequences, next adjacent merges
and independent vertex subsets; string oracles use direct comparisons/materialized
short suffixes. Tree relabelling checks root invariance. Validators require all
fields with exact types, accept alternative optimal witnesses, and replay merge
plans against the currently available intervals. Seeded random cases and exhaustive
short binary inputs are shuffled into mixed JSONL batches and repeated across tasks.
The runner does not import the solution or the public validator.

|Command|Input or generated fixture|Expected result|Actual result|Defect detected|
|---|---|---|---|---|
|lcs|`tea_time`, `team`|length 4, witness `team`|4, `team`|Confusing a subsequence with a substring|
|lcs|`ABCBDAB`, `BDCABA`|any common subsequence of length 4|4, `BCBA`|Rejecting a valid alternative optimum|
|merge|`[1,100,1]`|203 with a legal adjacent plan|203, `[[1,1,2],[0,0,2]]`|Illegally merging arbitrary blocks|
|merge|200 blocks of size 10^9|1544000000000, 199 valid merges|PASS, exact cost and replay|32-bit overflow and chronological reconstruction|
|tree|`[4,9,6]`, path edges|weight 10, vertices 0 and 2|10, `[0,2]`|Incorrect parent restrictions|
|tree|100000-vertex chain, all weights 10^9|50000000000000|PASS, optimum and independent witness|Recursion failure and 32-bit overflow|
|tree|100000-vertex star, all weights 10^9|99999000000000|PASS, optimum and independent witness|Wide-tree traversal and total-weight overflow|
|naive/kmp/rk|`aaaaa` / `aaa`|`[0,1,2]`|`[0,1,2]` for each|Discarding overlaps|
|naive/kmp/rk|`a` / empty pattern|`[0,1]`|`[0,1]` for each|Missing the final boundary|
|rk|`abdj` / `ab`|`[0]`|`[0]`|False positives from equal hashes|
|rk|`zab` / `ab`|`[1]`|`[1]`|Failure to normalize a negative rolling remainder|
|suffix|`banana`|SA `[5,3,1,0,4,2]`, LCP `[0,1,3,0,0,2]`, `ana`|Exactly those values|Wrong LCP convention or overlap handling|
|suffix|`$`|SA `[0]`, LCP `[0]`, no repeat|Exactly those values|Dropping a real character as a sentinel|
|suffix|`abXabYcdZcd`|longest repeat length 2, either `ab` or `cd`|length 2, `ab`|Requiring one particular tied optimum|
|suffix|50000 equal characters|SA descending, LCP 0..49999, repeat length 49999|PASS, every array entry checked|Materializing quadratic-size suffix strings|
|aho|`[a,aa,a]`, texts `[aaa,"",aaa]`|`[[3,2,3],[0,0,0],[3,2,3]]`|Exactly that matrix|Duplicates, suffix patterns, overlaps and reset|
|aho|pattern `a^100000`, text `a^200000`|100001 occurrences|PASS, 100001|Deep trie and full pattern/text limits|
|aho|10000 copies of `a`, 100 texts `a^2000`|100 by 10000 matrix of 2000|PASS, every count checked|Per-match enumeration and oversized output handling|

Further generated cases cover empty inputs, all-negative trees, zero/tied merge
costs, all 95 ASCII characters, all maximum search lengths, KMP mismatch fallback,
100 independent texts with a maximum-depth trie, and 10000 distinct patterns
totalling 100000 characters. For equal-size merging with n=200, a minimum-depth
binary merge tree has 56 leaves at depth 7 and 144 at depth 8, giving total
depth 1544; this supplies an independent large-case expected cost.

Each local batch used a 384 MiB Java heap, `-XX:ActiveProcessorCount=1`, a
20-second timeout and an 8 MiB output check. The slowest measured batch took
0.478 seconds; the largest output was 5070541 bytes. This is a local run, not
the official container: the JVM processor setting is not OS-level CPU isolation,
and peak resident memory was not measured. The Java heap limit was enforced.

## Search comparison

Run `python tests/student/run_benchmark.py`. The hardware was an Intel Core
i5-12450HX with 12 logical processors and 16873545728 bytes of RAM, Windows 11
build 26200, Microsoft OpenJDK 17.0.20.1. The complete final measurements and
environment are in [benchmark_results.json](tests/student/benchmark_results.json).

Random cases use `java.util.Random(20261108+n)`, uniformly choosing lowercase
letters from a 26-character alphabet; the pattern is the substring at `n/3`
of length `m=n/10`. The three seeds are 20261608, 20262608 and 20264108.
Repetitive cases use `a^n` and `a^m` at the same sizes. All outputs are checked
against an independent `String.startsWith` oracle before timing, including the
known collision, empty-pattern and overlap cases. Random cases each have one
match; repetitive cases have n-m+1 matches.

One JVM performs 300 warm-up calls per method/input combination, then five
measured batches of 200 calls. Method order rotates between batches. Each value
below is the batch time divided by 200, in **microseconds per call**. Timing
includes method dispatch, algorithm work, output allocation and volatile result
assignment; it excludes generation, the oracle, JSON serialization, compilation
and JVM startup. Default tiered JIT is enabled; complete JIT/GC stabilization is
not assumed. The same boundary is used for all methods.

|Case|n|m|Algorithm|Run 1|Run 2|Run 3|Run 4|Run 5|Median|
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
|random|500|50|naive|0.8935|0.6460|0.7085|0.9485|1.2310|0.8935|
|random|500|50|kmp|0.9240|0.8790|1.0195|0.9020|1.4745|0.9240|
|random|500|50|rk|3.4820|3.3305|3.5955|7.5830|3.7395|3.5955|
|random|1500|150|naive|1.9375|2.1670|1.9630|2.4355|2.2705|2.1670|
|random|1500|150|kmp|2.7910|2.6835|3.1900|3.5840|3.4345|3.1900|
|random|1500|150|rk|10.2925|10.4405|10.3995|11.1425|11.3365|10.4405|
|random|3000|300|naive|4.5040|6.2665|4.0930|3.9230|5.0565|4.5040|
|random|3000|300|kmp|5.4755|6.6870|5.6160|7.0405|5.4225|5.6160|
|random|3000|300|rk|20.4240|22.0695|22.0715|20.7425|21.1375|21.1375|
|repetitive|500|50|naive|27.8125|29.7445|32.9065|26.6475|28.0200|28.0200|
|repetitive|500|50|kmp|3.8175|4.4190|3.9610|5.5455|4.2355|4.2355|
|repetitive|500|50|rk|47.3475|45.6135|49.6200|48.7550|46.2630|47.3475|
|repetitive|1500|150|naive|231.4825|247.1565|222.0430|217.9555|216.3840|222.0430|
|repetitive|1500|150|kmp|11.9850|13.9990|7.0755|7.9600|7.3590|7.9600|
|repetitive|1500|150|rk|355.8755|362.5615|364.9050|351.0930|349.5350|355.8755|
|repetitive|3000|300|naive|1007.8155|928.0635|969.1470|960.5140|1276.2690|969.1470|
|repetitive|3000|300|kmp|28.5855|17.0020|19.1555|14.2870|17.0015|17.0020|
|repetitive|3000|300|rk|1908.9350|1483.4455|1745.9290|1574.8690|1597.5065|1597.5065|

All rows passed the independent correctness check. Naive search had the lowest
median on the random cases; KMP was fastest on the repetitive cases. On
repetitive inputs every window is a genuine match, so exact RK must verify every
candidate. Both naive and exact RK therefore do substantially more work than KMP
on these inputs. With growing n and m, this illustrates the benefit of reusing
prefix information.
Random inputs often stop naive verification on the first character, while RK
still pays hashing costs and verifies occasional collisions. The deliberately
small modulus 101 is a collision laboratory; these results do not represent
every production hash implementation. Timings do not prove asymptotic complexity.

The source hash and runtime are recorded in the result file. OS scheduling,
JIT and GC remain possible sources of timing variability. No timing threshold
is used as a correctness test.

## Sources and AI assistance

- [Official template and README](https://github.com/RZhaniya/daa-assignment-4-archive):
  Java JSON transport, launcher, public checks, repository structure and task.
- [Contracts](docs/guide/CONTRACTS.md), [testing](docs/guide/TESTING.md),
  [rubric](docs/guide/RUBRIC.md), and [algorithm notes](docs/LECTURE_CLARIFICATIONS_EN_RU.md):
  required recurrences, output conventions, limits, hash constants and edge cases.
- [Interactive lesson](https://rzhaniya.github.io/daa-assignment-4-archive/) and its
  repository source `docs/content.js`: conceptual explanations and practice
  material. The lesson's source was inspected when the rendered site was unavailable.
- **OpenAI Codex AI assistance:** helped prepare tests, write the analysis,
  and verify the solution. The verification results are recorded above.
