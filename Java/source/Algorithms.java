import java.util.*;


public final class Algorithms {
    private Algorithms() {}

    static Map<String, Object> lcs(Map<String, Object> input) {
        String a = (String) input.get("a"), b = (String) input.get("b");
        int n = a.length(), m = b.length();
        int[][] dp = new int[n + 1][m + 1];
        for (int i = 1; i <= n; i++) {
            for (int j = 1; j <= m; j++) {
                dp[i][j] = a.charAt(i - 1) == b.charAt(j - 1)
                        ? dp[i - 1][j - 1] + 1 : Math.max(dp[i - 1][j], dp[i][j - 1]);
            }
        }
        StringBuilder reversed = new StringBuilder(dp[n][m]);
        int i = n, j = m;
        while (i > 0 && j > 0) {
            if (a.charAt(i - 1) == b.charAt(j - 1)) {
                reversed.append(a.charAt(--i));
                j--;
            } else if (dp[i - 1][j] >= dp[i][j - 1]) {
                i--;
            } else {
                j--;
            }
        }
        return Map.of("length", dp[n][m], "sequence", reversed.reverse().toString());
    }

    static Map<String, Object> merge(Map<String, Object> input) {
        List<?> sizes = (List<?>) input.get("sizes");
        int n = sizes.size();
        List<int[]> plan = new ArrayList<>();
        if (n < 2) return Map.of("cost", 0L, "plan", plan);
        long[] prefix = new long[n + 1];
        for (int i = 0; i < n; i++) prefix[i + 1] = prefix[i] + number(sizes.get(i));
        long[][] dp = new long[n][n];
        int[][] split = new int[n][n];
        for (int length = 2; length <= n; length++) {
            for (int left = 0; left + length <= n; left++) {
                int right = left + length - 1;
                long sum = prefix[right + 1] - prefix[left];
                dp[left][right] = Long.MAX_VALUE;
                for (int k = left; k < right; k++) {
                    long candidate = dp[left][k] + dp[k + 1][right] + sum;
                    if (candidate < dp[left][right]) {
                        dp[left][right] = candidate;
                        split[left][right] = k;
                    }
                }
            }
        }

        Deque<int[]> stack = new ArrayDeque<>();
        stack.push(new int[]{0, n - 1, 0});
        while (!stack.isEmpty()) {
            int[] frame = stack.pop();
            int left = frame[0], right = frame[1];
            if (left == right) continue;
            int k = split[left][right];
            if (frame[2] == 1) {
                plan.add(new int[]{left, k, right});
            } else {
                stack.push(new int[]{left, right, 1});
                stack.push(new int[]{k + 1, right, 0});
                stack.push(new int[]{left, k, 0});
            }
        }
        return Map.of("cost", dp[0][n - 1], "plan", plan);
    }

    static Map<String, Object> tree(Map<String, Object> input) {
        int n = ((Number) input.get("n")).intValue();
        List<Integer> selected = new ArrayList<>();
        if (n == 0) return Map.of("weight", 0L, "selected", selected);
        List<?> weights = (List<?>) input.get("weights"), edges = (List<?>) input.get("edges");
        int[] head = new int[n], to = new int[2 * edges.size()], next = new int[to.length];
        Arrays.fill(head, -1);
        int edgeIndex = 0;
        for (Object value : edges) {
            List<?> edge = (List<?>) value;
            int u = ((Number) edge.get(0)).intValue(), v = ((Number) edge.get(1)).intValue();
            to[edgeIndex] = v; next[edgeIndex] = head[u]; head[u] = edgeIndex++;
            to[edgeIndex] = u; next[edgeIndex] = head[v]; head[v] = edgeIndex++;
        }

        int[] parent = new int[n], order = new int[n];
        parent[0] = -1;
        int size = 1;
        for (int i = 0; i < size; i++) {
            int v = order[i];
            for (int e = head[v]; e != -1; e = next[e]) {
                int u = to[e];
                if (u != parent[v]) {
                    parent[u] = v;
                    order[size++] = u;
                }
            }
        }
        long[] take = new long[n], skip = new long[n];
        for (int i = n - 1; i >= 0; i--) {
            int v = order[i];
            take[v] += number(weights.get(v));
            if (parent[v] >= 0) {
                take[parent[v]] += skip[v];
                skip[parent[v]] += Math.max(take[v], skip[v]);
            }
        }
        boolean[] chosen = new boolean[n];
        for (int v : order) {
            chosen[v] = (parent[v] < 0 || !chosen[parent[v]]) && take[v] > skip[v];
            if (chosen[v]) selected.add(v);
        }
        return Map.of("weight", Math.max(take[0], skip[0]), "selected", selected);
    }

    static Map<String, Object> naive(Map<String, Object> input) {
        String text = (String) input.get("text"), pattern = (String) input.get("pattern");
        List<Integer> positions = new ArrayList<>();
        int n = text.length(), m = pattern.length();

        for (int start = 0; start <= n - m; start++) {
            int j = 0;
            while (j < m && text.charAt(start + j) == pattern.charAt(j)) j++;
            if (j == m) positions.add(start);
        }
        return Map.of("positions", positions);
    }

    static Map<String, Object> kmp(Map<String, Object> input) {
        String text = (String) input.get("text"), pattern = (String) input.get("pattern");
        int n = text.length(), m = pattern.length();
        if (m == 0) return Map.of("positions", boundaries(n));
        List<Integer> positions = new ArrayList<>();
        if (m > n) return Map.of("positions", positions);
        int[] pi = new int[m];
        for (int i = 1; i < m; i++) {
            int j = pi[i - 1];
            while (j > 0 && pattern.charAt(i) != pattern.charAt(j)) j = pi[j - 1];
            if (pattern.charAt(i) == pattern.charAt(j)) j++;
            pi[i] = j;
        }
        int matched = 0;
        for (int i = 0; i < n; i++) {
            while (matched > 0 && text.charAt(i) != pattern.charAt(matched)) matched = pi[matched - 1];
            if (text.charAt(i) == pattern.charAt(matched)) matched++;
            if (matched == m) {
                positions.add(i - m + 1);
                matched = pi[matched - 1];
            }
        }
        return Map.of("positions", positions);
    }

    static Map<String, Object> rk(Map<String, Object> input) {
        String text = (String) input.get("text"), pattern = (String) input.get("pattern");
        int n = text.length(), m = pattern.length();
        if (m == 0) return Map.of("positions", boundaries(n));
        List<Integer> positions = new ArrayList<>();
        if (m > n) return Map.of("positions", positions);
        final long base = 31, modulus = 101;
        long power = 1, patternHash = 0, windowHash = 0;
        for (int i = 0; i < m; i++) {
            patternHash = (patternHash * base + pattern.charAt(i)) % modulus;
            windowHash = (windowHash * base + text.charAt(i)) % modulus;
            if (i > 0) power = power * base % modulus;
        }
        for (int start = 0; start <= n - m; start++) {
            if (windowHash == patternHash) {
                int j = 0;
                while (j < m && text.charAt(start + j) == pattern.charAt(j)) j++;
                if (j == m) positions.add(start);
            }
            if (start < n - m) {
                long remaining = (windowHash - text.charAt(start) * power) % modulus;
                if (remaining < 0) remaining += modulus;
                windowHash = (remaining * base + text.charAt(start + m)) % modulus;
            }
        }
        return Map.of("positions", positions);
    }

    static Map<String, Object> suffix(Map<String, Object> input) {
        String text = (String) input.get("text");
        int n = text.length();
        int[] sa = new int[n], lcp = new int[n];
        if (n == 0) return Map.of("sa", sa, "lcp", lcp, "repeated", "");
        int[] ranks = new int[n], temporary = new int[n];
        for (int i = 0; i < n; i++) { sa[i] = i; ranks[i] = text.charAt(i) + 1; }
        int maximumRank = 127;
        for (int width = 1; width < n; width *= 2) {

            rankSort(sa, temporary, ranks, width, maximumRank);
            rankSort(temporary, sa, ranks, 0, maximumRank);
            int[] newRanks = new int[n];
            int classes = 1;
            newRanks[sa[0]] = classes;
            for (int i = 1; i < n; i++) {
                int a = sa[i - 1], b = sa[i];
                if (ranks[a] != ranks[b] || rankAt(ranks, a + width) != rankAt(ranks, b + width)) classes++;
                newRanks[b] = classes;
            }
            ranks = newRanks;
            maximumRank = classes;
            if (classes == n) break;
        }
        int[] inverse = new int[n];
        for (int i = 0; i < n; i++) inverse[sa[i]] = i;
        int common = 0, bestLength = 0, bestStart = 0;
        for (int i = 0; i < n; i++) {
            int position = inverse[i];
            if (position == 0) { common = 0; continue; }
            int previous = sa[position - 1];
            while (i + common < n && previous + common < n
                    && text.charAt(i + common) == text.charAt(previous + common)) common++;
            lcp[position] = common;
            if (common > bestLength) { bestLength = common; bestStart = i; }
            if (common > 0) common--;
        }
        return Map.of("sa", sa, "lcp", lcp, "repeated", text.substring(bestStart, bestStart + bestLength));
    }

    private static int rankAt(int[] ranks, int index) {
        return index < ranks.length ? ranks[index] : 0;
    }

    private static void rankSort(int[] input, int[] output, int[] ranks, int offset, int maximumRank) {
        int[] counts = new int[maximumRank + 1];
        for (int index : input) counts[rankAt(ranks, index + offset)]++;
        int total = 0;
        for (int key = 0; key < counts.length; key++) {
            int frequency = counts[key];
            counts[key] = total;
            total += frequency;
        }
        for (int index : input) output[counts[rankAt(ranks, index + offset)]++] = index;
    }

    static Map<String, Object> aho(Map<String, Object> input) {
        List<?> patterns = (List<?>) input.get("patterns"), texts = (List<?>) input.get("texts");
        final int alphabet = 95, firstCharacter = 32;
        List<int[]> transitions = new ArrayList<>();
        transitions.add(new int[alphabet]);
        int[] terminal = new int[patterns.size()];
        for (int i = 0; i < patterns.size(); i++) {
            String pattern = (String) patterns.get(i);
            int state = 0;
            for (int j = 0; j < pattern.length(); j++) {
                int character = pattern.charAt(j) - firstCharacter;
                int[] row = transitions.get(state);
                if (row[character] == 0) {
                    row[character] = transitions.size();
                    transitions.add(new int[alphabet]);
                }
                state = row[character];
            }
            terminal[i] = state;
        }
        int states = transitions.size();
        int[] failure = new int[states], queue = new int[states];
        int end = 0;
        for (int child : transitions.get(0)) if (child != 0) queue[end++] = child;
        for (int start = 0; start < end; start++) {
            int state = queue[start];
            int[] row = transitions.get(state), fallback = transitions.get(failure[state]);
            for (int c = 0; c < alphabet; c++) {
                int child = row[c];
                if (child == 0) {
                    row[c] = fallback[c];
                } else {
                    failure[child] = fallback[c];
                    queue[end++] = child;
                }
            }
        }
        List<long[]> counts = new ArrayList<>();
        for (Object value : texts) {
            String text = (String) value;
            long[] visits = new long[states];
            int state = 0;
            for (int i = 0; i < text.length(); i++) {
                state = transitions.get(state)[text.charAt(i) - firstCharacter];
                visits[state]++;
            }

            for (int i = end - 1; i >= 0; i--) {
                int v = queue[i];
                visits[failure[v]] += visits[v];
            }
            long[] row = new long[patterns.size()];
            for (int i = 0; i < row.length; i++) row[i] = visits[terminal[i]];
            counts.add(row);
        }
        return Map.of("counts", counts);
    }

    private static long number(Object value) { return ((Number) value).longValue(); }

    private static List<Integer> boundaries(int length) {
        List<Integer> result = new ArrayList<>(length + 1);
        for (int i = 0; i <= length; i++) result.add(i);
        return result;
    }
}
