package com.consistenthash;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.TreeSet;

/**
 * Maglev lookup-table hashing (Google, 2016). A fixed prime-sized permutation table is
 * built once; each node claims slots in a deterministic interleaving. Lookups are a
 * single array index, and losing a node only rewrites its own slots.
 */
public final class Maglev {

    private final int m;
    private List<String> nodes;
    private int[] table = new int[0];

    public Maglev() {
        this(new ArrayList<>(), 65537);
    }

    public Maglev(List<String> nodes, int tableSize) {
        if (!isPrime(tableSize)) {
            throw new IllegalArgumentException("tableSize must be prime");
        }
        this.m = tableSize;
        this.nodes = new ArrayList<>(new TreeSet<>(nodes));
        build();
    }

    public void add(String node) {
        if (!nodes.contains(node)) {
            nodes.add(node);
            nodes.sort(null);
            build();
        }
    }

    public void remove(String node) {
        if (nodes.remove(node)) {
            build();
        }
    }

    public String get(String key) {
        if (nodes.isEmpty()) {
            return null;
        }
        int slot = (int) Long.remainderUnsigned(HashRing.fnv1a64(key), m);
        return nodes.get(table[slot]);
    }

    public List<String> nodes() {
        return new ArrayList<>(nodes);
    }

    public int size() {
        return nodes.size();
    }

    private void build() {
        int n = nodes.size();
        if (n == 0) {
            table = new int[0];
            return;
        }
        long[] offset = new long[n];
        long[] skip = new long[n];
        for (int i = 0; i < n; i++) {
            offset[i] = Long.remainderUnsigned(HashRing.fnv1a64(nodes.get(i) + "#offset"), m);
            skip[i] = Long.remainderUnsigned(HashRing.fnv1a64(nodes.get(i) + "#skip"), m - 1) + 1;
        }
        int[] t = new int[m];
        Arrays.fill(t, -1);
        long[] next = new long[n];
        int filled = 0;
        while (filled < m) {
            for (int i = 0; i < n; i++) {
                int c = (int) ((offset[i] + next[i] * skip[i]) % m);
                while (t[c] >= 0) {
                    next[i]++;
                    c = (int) ((offset[i] + next[i] * skip[i]) % m);
                }
                t[c] = i;
                next[i]++;
                filled++;
                if (filled == m) {
                    break;
                }
            }
        }
        table = t;
    }

    private static boolean isPrime(int n) {
        if (n < 2) {
            return false;
        }
        if (n % 2 == 0) {
            return n == 2;
        }
        for (int i = 3; (long) i * i <= n; i += 2) {
            if (n % i == 0) {
                return false;
            }
        }
        return true;
    }
}
