package com.consistenthash;

import java.util.ArrayList;
import java.util.List;

/**
 * Jump consistent hash (Lamping &amp; Veach, 2014) over an ordered bucket list. No
 * per-node state, O(ln N) lookups. Buckets are an ordered range, so it stays consistent
 * when nodes are appended or removed at the tail.
 */
public final class Jump {

    private final List<String> nodes;

    public Jump() {
        this.nodes = new ArrayList<>();
    }

    public Jump(List<String> nodes) {
        this.nodes = new ArrayList<>(nodes);
    }

    public void add(String node) {
        if (!nodes.contains(node)) {
            nodes.add(node);
        }
    }

    public void remove(String node) {
        nodes.remove(node);
    }

    public String get(String key) {
        if (nodes.isEmpty()) {
            return null;
        }
        return nodes.get(jumpConsistentHash(HashRing.fnv1a64(key), nodes.size()));
    }

    public List<String> nodes() {
        return new ArrayList<>(nodes);
    }

    public int size() {
        return nodes.size();
    }

    /** Maps key to a bucket in [0, numBuckets) with O(1) memory. */
    public static int jumpConsistentHash(long key, int numBuckets) {
        if (numBuckets < 1) {
            throw new IllegalArgumentException("numBuckets must be at least 1");
        }
        long b = -1;
        long j = 0;
        while (j < numBuckets) {
            b = j;
            key = key * 2862933555777941757L + 1L; // wraps mod 2^64
            j = (long) ((b + 1) * ((double) (1L << 31) / (double) ((key >>> 33) + 1)));
        }
        return (int) b;
    }
}
