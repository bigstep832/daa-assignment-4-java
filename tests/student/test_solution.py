from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
import hashlib
from itertools import product
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
SEED = 4102026


@dataclass
class Case:
    request: dict
    expected: object
    name: str
    record: bool = False


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def integer(value):
    return type(value) is int


def integers(value):
    return isinstance(value, list) and all(integer(x) for x in value)


def subsequence(candidate, text):
    position = 0
    for character in text:
        if position < len(candidate) and candidate[position] == character:
            position += 1
    return position == len(candidate)


def lcs_oracle(a, b):
    if len(a) > len(b):
        a, b = b, a
    best = 0
    for mask in range(1 << len(a)):
        if mask.bit_count() > best:
            sequence = ''.join(c for i, c in enumerate(a) if mask & (1 << i))
            if subsequence(sequence, b):
                best = len(sequence)
    return best


@lru_cache(maxsize=None)
def merge_oracle(sizes):

    if len(sizes) < 2:
        return 0
    return min(sizes[i] + sizes[i + 1] +
               merge_oracle(sizes[:i] + (sizes[i] + sizes[i + 1],) + sizes[i + 2:])
               for i in range(len(sizes) - 1))


def tree_oracle(weights, edges):
    best = 0
    for mask in range(1 << len(weights)):
        if all(not ((mask >> u) & 1 and (mask >> v) & 1) for u, v in edges):
            best = max(best, sum(w for i, w in enumerate(weights) if (mask >> i) & 1))
    return best


def matches(text, pattern):
    return [i for i in range(len(text) - len(pattern) + 1)
            if text[i:i + len(pattern)] == pattern]


def suffix_oracle(text):
    sa = sorted(range(len(text)), key=lambda i: text[i:])
    lcp = [0] * len(text)
    for i in range(1, len(text)):
        left, right = sa[i - 1], sa[i]
        while left + lcp[i] < len(text) and right + lcp[i] < len(text):
            if text[left + lcp[i]] != text[right + lcp[i]]:
                break
            lcp[i] += 1
    return {'sa': sa, 'lcp': lcp}


def validate(case, answer):
    request, expected = case.request, case.expected
    require(isinstance(answer, dict), 'result must be an object')
    task = request['task']
    if task == 'lcs':
        length, sequence = answer.get('length'), answer.get('sequence')
        require(integer(length) and isinstance(sequence, str), 'LCS schema')
        require(length == expected == len(sequence), 'LCS optimum/length')
        require(subsequence(sequence, request['a']) and subsequence(sequence, request['b']), 'LCS witness')
    elif task == 'merge':
        cost, plan = answer.get('cost'), answer.get('plan')
        require(integer(cost) and isinstance(plan, list), 'merge schema')
        sizes = request['sizes']
        require(cost == expected, 'merge optimum')
        require(len(plan) == max(0, len(sizes) - 1), 'merge plan length')
        blocks = {i: (i, size) for i, size in enumerate(sizes)}
        total = 0
        for step in plan:
            require(integers(step) and len(step) == 3, 'merge step schema')
            left, split, right = step
            require(0 <= left <= split < right < len(sizes), 'merge indices')
            require(left in blocks and blocks[left][0] == split, 'left block not ready')
            require(split + 1 in blocks and blocks[split + 1][0] == right, 'right block not ready/adjacent')
            size = blocks[left][1] + blocks[split + 1][1]
            total += size
            blocks[left] = (right, size)
            del blocks[split + 1]
        require(total == cost, 'merge witness cost')
        require(not sizes or blocks == {0: (len(sizes) - 1, sum(sizes))}, 'final merge block')
    elif task == 'tree':
        weight, selected = answer.get('weight'), answer.get('selected')
        require(integer(weight) and integers(selected), 'tree schema')
        chosen = set(selected)
        require(len(chosen) == len(selected), 'duplicate selected vertices')
        require(all(0 <= v < request['n'] for v in chosen), 'tree vertex bounds')
        require(all(u not in chosen or v not in chosen for u, v in request['edges']), 'selected adjacent vertices')
        require(weight == expected == sum(request['weights'][v] for v in chosen), 'tree optimum/witness')
    elif task in ('naive', 'kmp', 'rk'):
        positions = answer.get('positions')
        require(integers(positions), 'search schema')
        require(positions == expected, 'search positions/overlaps/order')
    elif task == 'suffix':
        sa, lcp, repeated = answer.get('sa'), answer.get('lcp'), answer.get('repeated')
        require(integers(sa) and integers(lcp) and isinstance(repeated, str), 'suffix schema')
        require(sa == expected['sa'] and lcp == expected['lcp'], 'suffix order/LCP')
        require(len(repeated) == max(lcp, default=0), 'longest repeat length')
        if repeated:
            first = request['text'].find(repeated)
            require(first >= 0 and request['text'].find(repeated, first + 1) >= 0, 'repeat requires two starts')
    elif task == 'aho':
        counts = answer.get('counts')
        require(isinstance(counts, list) and all(integers(row) for row in counts), 'Aho schema')
        require(counts == expected, 'Aho counts/order/reset')
    else:
        raise AssertionError('Unknown test task ' + task)


def small_cases():
    rng, cases = random.Random(SEED), []
    def add(task, expected, name, record=False, **kwargs):
        cases.append(Case({'task': task, **kwargs}, expected, name, record))
    binary = [''.join(chars) for n in range(5) for chars in product('ab', repeat=n)]
    for a in binary:
        for b in binary:
            add('lcs', lcs_oracle(a, b), 'lcs exhaustive binary', a=a, b=b)
    for a, b in [('tea_time', 'team'), ('ABCBDAB', 'BDCABA'), ('', '~!'), ('a a~"\\', ' a"\\'), ('zzzzzz', 'zz')]:
        add('lcs', lcs_oracle(a, b), 'lcs example ' + repr((a, b)), True, a=a, b=b)
    for _ in range(100):
        a = ''.join(rng.choices('ab A~', k=rng.randrange(10)))
        b = ''.join(rng.choices('ab A~', k=rng.randrange(10)))
        add('lcs', lcs_oracle(a, b), 'lcs seeded random', a=a, b=b)
    for n in range(6):
        for sizes in product((0, 1, 3), repeat=n):
            add('merge', merge_oracle(sizes), 'merge exhaustive next-operation', sizes=list(sizes))
    for sizes in [[], [0], [1, 100, 1], [0, 0, 0, 0], [10**9] * 4, [2, 3, 4]]:
        add('merge', merge_oracle(tuple(sizes)), 'merge example ' + repr(sizes), True, sizes=sizes)
    for _ in range(60):
        sizes = tuple(rng.randrange(20) for _ in range(rng.randrange(8)))
        add('merge', merge_oracle(sizes), 'merge seeded random', sizes=list(sizes))
    for weights, edges in [([], []), ([-1], []), ([0], []), ([7], []), ([-9, -2, -1], [[0, 1], [1, 2]]),
                           ([4, 9, 6], [[0, 1], [1, 2]]), ([0, 0, 0], [[0, 1], [1, 2]])]:
        add('tree', tree_oracle(weights, edges), 'tree boundary ' + repr(weights), True,
            n=len(weights), weights=weights, edges=edges)
    for _ in range(100):
        n = rng.randrange(1, 13)
        weights = [rng.randrange(-8, 10) for _ in range(n)]
        edges = [[i, rng.randrange(i)] for i in range(1, n)]
        expected = tree_oracle(weights, edges)
        add('tree', expected, 'tree exhaustive subset oracle', n=n, weights=weights, edges=edges)
        permutation = list(range(n))
        rng.shuffle(permutation)
        new_weights = [0] * n
        for old, new in enumerate(permutation):
            new_weights[new] = weights[old]
        new_edges = [[permutation[v], permutation[u]] for u, v in reversed(edges)]
        add('tree', expected, 'tree relabelling/root invariant', n=n, weights=new_weights, edges=new_edges)
    pairs = [(text, pattern) for text in binary for pattern in binary]
    pairs += [('abdj', 'ab'), ('zab', 'ab'), ('aaaaa', 'aaa'), ('abababa', 'aba'), ('', ''), ('a', ''),
              ('a', 'aaa'), ('A a A~"\\', 'A'), ('~! ~!', '~!'), (' \\"~ \\"~', '\\"')]
    for _ in range(180):
        text = ''.join(rng.choices('abAB ~"\\', k=rng.randrange(50)))
        pattern = ''.join(rng.choices('abAB ~"\\', k=rng.randrange(14)))
        pairs.append((text, pattern))
    for text, pattern in pairs:
        expected = matches(text, pattern)
        for task in ('naive', 'kmp', 'rk'):
            record = (text, pattern) in [('abdj', 'ab'), ('zab', 'ab'), ('aaaaa', 'aaa'), ('a', '')]
            add(task, expected, task + ' direct oracle ' + repr((text, pattern)), record, text=text, pattern=pattern)
    texts = [''.join(chars) for n in range(7) for chars in product('ab', repeat=n)]
    texts += ['', 'x', 'banana', '$', ''.join(chr(i) for i in range(32, 127)),
              'abcxabcydefydef', 'abXabYcdZcd', ' a~ a~', 'mississippi']
    texts += [''.join(rng.choices('abc ABC~$', k=rng.randrange(60))) for _ in range(180)]
    for text in texts:
        add('suffix', suffix_oracle(text), 'suffix direct oracle ' + repr(text),
            text in ('banana', '$', 'abcxabcydefydef', 'abXabYcdZcd'), text=text)
    dictionaries = [([], []), ([], ['', 'abc']), (['a'], []), (['a'], ['']),
                    (['a', 'aa', 'a'], ['aaa', '', 'aaa']),
                    (['he', 'she', 'hers', 'he'], ['ushershe', 'ushershe', '']),
                    ([chr(i) for i in range(32, 127)], [''.join(map(chr, range(32, 127))) * 2])]
    for _ in range(180):
        patterns = [''.join(rng.choices('ab A~', k=rng.randrange(1, 7))) for _ in range(rng.randrange(12))]
        if patterns:
            patterns += patterns[:rng.randrange(min(4, len(patterns)) + 1)]
        texts = [''.join(rng.choices('ab A~', k=rng.randrange(50))) for _ in range(rng.randrange(7))]
        dictionaries.append((patterns, texts))
    for patterns, texts in dictionaries:
        expected = [[len(matches(text, pattern)) for pattern in patterns] for text in texts]
        add('aho', expected, 'aho independent searches', patterns == ['a', 'aa', 'a'], patterns=patterns, texts=texts)
    representatives = [next(case for case in cases if case.request['task'] == task and case.record)
                       for task in ('lcs', 'merge', 'tree', 'naive', 'kmp', 'rk', 'suffix', 'aho')]
    rng.shuffle(cases)
    cases.extend(representatives + list(reversed(representatives)) + representatives)
    return cases


def stress_batches():
    a = 'a'
    yield 'lcs full domain', [
        Case({'task': 'lcs', 'a': a * 1000, 'b': a * 1000}, 1000, 'identical 1000x1000'),
        Case({'task': 'lcs', 'a': 'ab' * 500, 'b': 'ba' * 500}, 999, 'alternating 1000x1000'),
        Case({'task': 'lcs', 'a': a * 1000, 'b': 'b' * 1000}, 0, 'disjoint 1000x1000'),
        Case({'task': 'lcs', 'a': '', 'b': a * 1000}, 0, 'empty versus maximum')]
    yield 'merge full domain', [
        Case({'task': 'merge', 'sizes': [10**9] * 200}, 1544 * 10**9, 'balanced equal leaves 64-bit'),
        Case({'task': 'merge', 'sizes': [0] * 200}, 0, '200 zero blocks ties'),
        Case({'task': 'merge', 'sizes': [10**9] + [0] * 199}, 10**9, 'one edge nonzero block')]
    n = 100000
    yield 'tree full domain', [
        Case({'task': 'tree', 'n': n, 'weights': [10**9] * n, 'edges': [[i - 1, i] for i in range(1, n)]},
             50000 * 10**9, 'deep chain 64-bit'),
        Case({'task': 'tree', 'n': n, 'weights': [10**9] * n, 'edges': [[0, i] for i in range(1, n)]},
             99999 * 10**9, 'wide star 64-bit'),
        Case({'task': 'tree', 'n': n, 'weights': [-10**9] * n, 'edges': [[i - 1, i] for i in range(1, n)]},
             0, 'negative deep chain')]
    for task, pairs in {
        'naive': [(a * 3000, a * 1500), (a * 3000, ''), (a * 2999, a * 3000), (a * 3000, a * 1499 + 'b')],
        'kmp': [(a * 200000, a * 100000), (a * 200000, ''), (a * 200000, a * 99999 + 'b'), ('', a * 100000)],
        'rk': [(a * 10000, a * 2000), (a * 10000, ''), (a * 2000, a * 10000), (a * 10000, a * 1999 + 'b')]
    }.items():
        batch = []
        for text, pattern in pairs:
            expected = list(range(len(text) - len(pattern) + 1)) if 'b' not in pattern else []
            batch.append(Case({'task': task, 'text': text, 'pattern': pattern}, expected,
                              f'{task} n={len(text)}, m={len(pattern)}'))
        yield task + ' full domain', batch
    n = 50000
    yield 'suffix full domain', [
        Case({'task': 'suffix', 'text': a * n},
             {'sa': list(range(n - 1, -1, -1)), 'lcp': list(range(n))}, '50000 equal characters'),
        Case({'task': 'suffix', 'text': 'ab' * (n // 2)},
             {'sa': list(range(n - 2, -1, -2)) + list(range(n - 1, -1, -2)),
              'lcp': list(range(0, n, 2)) + [0] + list(range(1, n - 2, 2))}, '50000 alternating characters')]
    yield 'aho maximum trie depth', [
        Case({'task': 'aho', 'patterns': [a * 100000], 'texts': [a * 200000]}, [[100001]],
             '100000-state chain and 200000 text'),
        Case({'task': 'aho', 'patterns': [a * 100000], 'texts': [a * 2000] * 100},
             [[0] for _ in range(100)], '100 independent texts and full trie')]
    yield 'aho dense duplicates', [
        Case({'task': 'aho', 'patterns': [a * 10] * 10000, 'texts': [a * 200000]},
             [[199991] * 10000], '10000 duplicates with dense overlaps'),
        Case({'task': 'aho', 'patterns': [a] * 10000, 'texts': [a * 2000] * 100},
             [[2000] * 10000 for _ in range(100)], 'maximum count matrix'),
        Case({'task': 'aho', 'patterns': [], 'texts': [''] * 100}, [[] for _ in range(100)], '100 empty rows')]
    patterns = ['~' + str(i).zfill(8) + '!' for i in range(10000)]
    row = [0] * 10000
    row[4321] = 20000
    yield 'aho wide dictionary', [
        Case({'task': 'aho', 'patterns': patterns, 'texts': [patterns[4321] * 20000]}, [row],
             '10000 distinct patterns total length 100000')]


def execute_batch(command, cases, name, records):
    payload = ''.join(json.dumps(case.request, separators=(',', ':')) + '\n' for case in cases)
    start = time.perf_counter()
    result = subprocess.run(command, input=payload, text=True, encoding='utf-8', capture_output=True, timeout=20, cwd=ROOT)
    elapsed = time.perf_counter() - start
    require(result.returncode == 0, f'{name}: process exit {result.returncode}: {result.stderr[:2000]}')
    output_bytes = len(result.stdout.encode('utf-8'))
    require(output_bytes <= 8 * 1024 * 1024, f'{name}: output exceeds 8 MiB')
    lines = result.stdout.splitlines()
    require(len(lines) == len(cases), f'{name}: expected {len(cases)} lines; received {len(lines)}')
    for case, line in zip(cases, lines):
        answer = json.loads(line)
        try:
            validate(case, answer)
        except AssertionError as error:
            raise AssertionError(f'{name} / {case.name}: {error}') from error
        if case.record:
            records.setdefault(case.name, {'input': case.request, 'expected': case.expected, 'actual': answer, 'passed': True})
    print(f'PASS {name}: {len(cases)} requests ({elapsed:.3f} s)', flush=True)
    return {'name': name, 'requests': len(cases), 'seconds': round(elapsed, 6), 'output_bytes': output_bytes,
            'passed': True, 'case_names': [case.name for case in cases] if len(cases) < 10 else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--java-home', default=os.environ.get('JAVA_HOME'))
    parser.add_argument('--report', type=Path, default=ROOT / 'tests/student/test_results.json')
    args = parser.parse_args()
    def executable(name):
        if args.java_home:
            return str(Path(args.java_home) / 'bin' / (name + ('.exe' if os.name == 'nt' else '')))
        found = shutil.which(name)
        if found is None:
            raise RuntimeError(f'{name} not found; set JAVA_HOME or pass --java-home')
        return found
    build = ROOT / 'Java/build'
    build.mkdir(exist_ok=True)
    sources = sorted((ROOT / 'Java/source').glob('*.java'))
    subprocess.run([executable('javac'), '--release', '17', '-encoding', 'UTF-8', '-d', str(build), *map(str, sources)],
                   check=True, timeout=60)
    command = [executable('java'), '-Xmx384m', '-XX:ActiveProcessorCount=1', '-cp', str(build), 'Main']
    records, batches, counts = {}, [], Counter()
    cases = small_cases()
    for start in range(0, len(cases), 1200):
        chunk = cases[start:start + 1200]
        counts.update(case.request['task'] for case in chunk)
        batches.append(execute_batch(command, chunk, f'mixed oracle batch {start // 1200 + 1}', records))
    for name, cases in stress_batches():
        counts.update(case.request['task'] for case in cases)
        batches.append(execute_batch(command, cases, name, records))
    report = {'seed': SEED, 'java_heap': '384m', 'active_processor_count': 1, 'timeout_seconds_per_batch': 20,
              'total_requests': sum(counts.values()), 'requests_by_task': dict(sorted(counts.items())), 'all_passed': True,
              'source_sha256': {str(path.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(path.read_bytes()).hexdigest()
                                for path in sources},
              'batches': batches, 'representative_expected_actual': list(records.values()),
              'limitation': 'Local checks, not the official hidden tests or a promised grade.'}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(f'PASS all {sum(counts.values())} requests: {dict(sorted(counts.items()))}')
    print('Report: ' + str(args.report.relative_to(ROOT) if args.report.is_relative_to(ROOT) else args.report))


if __name__ == '__main__':
    try:
        main()
    except (AssertionError, OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print('FAIL: ' + str(error), file=sys.stderr)
        sys.exit(1)
