package com.consistenthash;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.TreeSet;

/**
 * Consistent hashing with bounded loads (Google, 2017): keys are placed clockwise on
 * the ring, but no node may exceed ceil((1+epsilon)*keys/nodes). A full node overflows
 * to the next under cap, so no node exceeds its fair share by more than epsilon.
 * Placement depends on load, so it is stateful and order-sensitive.
 */
public final class BoundedLoad {

    private final double epsilon;
    private final List<String> nodes;
    private final TreeMap<Long, String> ring = new TreeMap<>();
    private final Map<String, Integer> load = new HashMap<>();
    private final Map<String, String> assigned = new HashMap<>();

    public BoundedLoad() {
        this(new ArrayList<>(), 100, 0.25);
    }

    public BoundedLoad(List<String> nodes, int replicas, double epsilon) {
        if (epsilon < 0) {
            throw new IllegalArgumentException("epsilon must be non-negative");
        }
        this.epsilon = epsilon;
        this.nodes = new ArrayList<>(new TreeSet<>(nodes));
        buildRing(replicas);
    }

    public String get(String key) {
        if (ring.isEmpty()) {
            return null;
        }
        String existing = assigned.get(key);
        if (existing != null) {
            return existing;
        }
        int cap = capacity();
        long h = HashRing.fnv1a32(key);
        // Walk clockwise from the key, wrapping once, taking the first node under cap.
        List<String> order = new ArrayList<>(ring.tailMap(h, false).values());
        order.addAll(ring.values());
        for (String node : order) {
            if (load.getOrDefault(node, 0) < cap) {
                assign(key, node);
                return node;
            }
        }
        String fallback = order.get(0);
        assign(key, fallback);
        return fallback;
    }

    public Map<String, Integer> loads() {
        return new HashMap<>(load);
    }

    public List<String> nodes() {
        return new ArrayList<>(nodes);
    }

    public int size() {
        return nodes.size();
    }

    private void assign(String key, String node) {
        assigned.put(key, node);
        load.merge(node, 1, Integer::sum);
    }

    private int capacity() {
        int total = assigned.size() + 1;
        return (int) Math.ceil((1 + epsilon) * total / nodes.size());
    }

    private void buildRing(int replicas) {
        for (String node : nodes) {
            for (int r = 0; r < replicas; r++) {
                long slot = HashRing.fnv1a32(node + "#" + r);
                while (ring.containsKey(slot)) {
                    slot = (slot + 1) & 0xFFFFFFFFL;
                }
                ring.put(slot, node);
            }
        }
    }
}
