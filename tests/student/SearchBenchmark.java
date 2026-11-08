import java.util.*;


public final class SearchBenchmark {
    private static final long SEED = 20261108L;
    private static final int WARMUP = 300;
    private static final int ITERATIONS = 200;
    private static final int RUNS = 5;

    private static volatile Object sink;
    private static final String[] METHODS = {"naive", "kmp", "rk"};

    private static Map<String, Object> search(String method, Map<String, Object> input) {
        return switch (method) {
            case "naive" -> Algorithms.naive(input);
            case "kmp" -> Algorithms.kmp(input);
            case "rk" -> Algorithms.rk(input);
            default -> throw new IllegalArgumentException(method);
        };
    }


    private static List<Integer> oracle(String text, String pattern) {
        List<Integer> positions = new ArrayList<>();
        for (int i = 0; i <= text.length() - pattern.length(); i++) {
            if (text.startsWith(pattern, i)) positions.add(i);
        }
        return positions;
    }

    private static void verify(Map<String, Object> input, List<Integer> expected) {
        for (String method : METHODS) {
            Object actual = search(method, input).get("positions");

            if (!Json.write(actual).equals(Json.write(expected))) {
                throw new AssertionError(method + " disagrees with the independent oracle");
            }
        }
    }

    private static Map<String, Object> input(String text, String pattern) {
        return Map.of("text", text, "pattern", pattern);
    }

    public static void main(String[] args) {
        verify(input("abdj", "ab"), List.of(0));
        verify(input("aaaaa", "aaa"), List.of(0, 1, 2));
        verify(input("abc", ""), List.of(0, 1, 2, 3));
        List<Map<String, Object>> cases = new ArrayList<>();
        List<Map<String, Object>> inputs = new ArrayList<>();
        for (String kind : List.of("random", "repetitive")) {
            for (int n : new int[]{500, 1500, 3000}) {
                int m = n / 10;
                String text;
                String pattern;
                if (kind.equals("random")) {
                    Random random = new Random(SEED + n);
                    StringBuilder builder = new StringBuilder(n);
                    for (int i = 0; i < n; i++) builder.append((char) ('a' + random.nextInt(26)));
                    text = builder.toString();
                    pattern = text.substring(n / 3, n / 3 + m);
                } else {
                    text = "a".repeat(n);
                    pattern = "a".repeat(m);
                }
                Map<String, Object> input = input(text, pattern);
                List<Integer> expected = oracle(text, pattern);
                verify(input, expected);
                Map<String, Object> metadata = new LinkedHashMap<>();
                metadata.put("case", kind);
                metadata.put("n", n);
                metadata.put("m", m);
                metadata.put("seed", kind.equals("random") ? SEED + n : null);
                metadata.put("matches", expected.size());
                metadata.put("correct_outputs_checked", true);
                cases.add(metadata);
                inputs.add(input);
            }
        }


        for (Map<String, Object> input : inputs) {
            for (String method : METHODS) {
                for (int repeat = 0; repeat < WARMUP; repeat++) sink = search(method, input);
            }
        }
        List<Map<String, Object>> rows = new ArrayList<>();
        for (int c = 0; c < cases.size(); c++) {
            double[][] elapsed = new double[METHODS.length][RUNS];

            for (int run = 0; run < RUNS; run++) {
                for (int offset = 0; offset < METHODS.length; offset++) {
                    int methodIndex = (run + offset) % METHODS.length;
                    String method = METHODS[methodIndex];
                    Map<String, Object> input = inputs.get(c);
                    long start = System.nanoTime();
                    for (int repeat = 0; repeat < ITERATIONS; repeat++) sink = search(method, input);
                    elapsed[methodIndex][run] = (System.nanoTime() - start) / (1000.0 * ITERATIONS);
                }
            }
            for (int methodIndex = 0; methodIndex < METHODS.length; methodIndex++) {
                Map<String, Object> row = new LinkedHashMap<>(cases.get(c));
                row.put("algorithm", METHODS[methodIndex]);
                row.put("microseconds_per_call", elapsed[methodIndex]);
                double[] sorted = elapsed[methodIndex].clone();
                Arrays.sort(sorted);
                row.put("median_microseconds_per_call", sorted[RUNS / 2]);
                rows.add(row);
            }
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("java_version", System.getProperty("java.version"));
        result.put("java_vm", System.getProperty("java.vm.name"));
        result.put("java_vendor", System.getProperty("java.vendor"));
        result.put("os", System.getProperty("os.name") + " " + System.getProperty("os.version"));
        result.put("architecture", System.getProperty("os.arch"));
        result.put("available_processors", Runtime.getRuntime().availableProcessors());
        result.put("seed_base", SEED);
        result.put("warmup_calls_per_method_case", WARMUP);
        result.put("measured_runs", RUNS);
        result.put("calls_per_measured_run", ITERATIONS);
        result.put("timing_scope", "Search method including output allocation, dispatch and volatile result assignment; excludes generation, correctness oracle, JSON, process startup and compilation.");
        result.put("jit_policy", "One JVM with normal tiered JIT. All cases/methods warm up before measurement. Method order rotates per run. No claim that JIT or GC is fully stabilized.");
        result.put("collision_test", Map.of("text", "abdj", "pattern", "ab", "expected_positions", List.of(0), "all_methods_passed", true));
        result.put("rows", rows);
        System.out.println(Json.write(result));
    }
}
