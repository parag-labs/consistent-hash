package com.consistenthash;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.TreeMap;

/**
 * A consistent-hash ring with virtual nodes. Keys and nodes share one circular
 * hash space, so adding or removing a node only remaps the keys next to it rather
 * than the whole keyspace. Each physical node occupies many ring points so load
 * spreads evenly. The hash is FNV-1a (32-bit) to match the Python and C# ports.
 */
public final class HashRing {

    private final int replicas;
    private final TreeMap<Long, String> ring = new TreeMap<>();
    private final java.util.TreeSet<String> nodes = new java.util.TreeSet<>();

    public HashRing() {
        this(List.of(), 100);
    }

    public HashRing(List<String> initial, int replicas) {
        if (replicas < 1) {
            throw new IllegalArgumentException("replicas must be at least 1");
        }
        this.replicas = replicas;
        for (String node : initial) {
            add(node);
        }
    }

    /** FNV-1a 32-bit as an unsigned value held in a long. */
    public static long fnv1a32(String data) {
        long h = 0x811C9DC5L;
        for (byte b : data.getBytes(StandardCharsets.UTF_8)) {
            h ^= (b & 0xFF);
            h = (h * 0x01000193L) & 0xFFFFFFFFL;
        }
        return h;
    }

    public List<String> nodes() {
        return new ArrayList<>(nodes);
    }

    public int size() {
        return nodes.size();
    }

    public void add(String node) {
        if (!nodes.add(node)) {
            return;
        }
        for (int r = 0; r < replicas; r++) {
            long slot = fnv1a32(node + "#" + r);
            while (ring.containsKey(slot)) {
                slot = (slot + 1) & 0xFFFFFFFFL; // deterministic nudge on collision
            }
            ring.put(slot, node);
        }
    }

    public void remove(String node) {
        if (!nodes.remove(node)) {
            return;
        }
        ring.values().removeIf(n -> n.equals(node));
    }

    public String get(String key) {
        if (ring.isEmpty()) {
            return null;
        }
        long h = fnv1a32(key);
        var entry = ring.higherEntry(h);
        if (entry == null) {
            entry = ring.firstEntry(); // wrap around
        }
        return entry.getValue();
    }

    public List<String> getReplicas(String key, int count) {
        List<String> result = new ArrayList<>();
        if (ring.isEmpty() || count <= 0) {
            return result;
        }
        int cap = Math.min(count, nodes.size());
        long h = fnv1a32(key);
        // Walk clockwise from the key, wrapping once, collecting distinct nodes.
        List<String> order = new ArrayList<>(ring.tailMap(h, false).values());
        order.addAll(ring.values()); // wrap-around continuation
        for (String node : order) {
            if (!result.contains(node)) {
                result.add(node);
                if (result.size() == cap) {
                    break;
                }
            }
        }
        return result;
    }
}
