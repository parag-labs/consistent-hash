package com.consistenthash;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * Highest-random-weight (rendezvous) placement: score every node for the key and take
 * the max. No ring to rebuild, weights are first-class, lookups are O(N).
 */
public final class Rendezvous {

    private final Map<String, Integer> weights = new LinkedHashMap<>();

    public Rendezvous() {
    }

    public Rendezvous(List<String> nodes) {
        for (String n : nodes) {
            add(n, 1);
        }
    }

    public void add(String node, int weight) {
        if (weight < 1) {
            throw new IllegalArgumentException("weight must be at least 1");
        }
        weights.put(node, weight);
    }

    public void add(String node) {
        add(node, 1);
    }

    public void remove(String node) {
        weights.remove(node);
    }

    public String get(String key) {
        if (weights.isEmpty()) {
            return null;
        }
        boolean weighted = isWeighted();
        String best = null;
        double bestScore = Double.NEGATIVE_INFINITY;
        for (Map.Entry<String, Integer> e : weights.entrySet()) {
            double s = score(e.getKey(), key, e.getValue(), weighted);
            if (s > bestScore || (s == bestScore && (best == null || e.getKey().compareTo(best) > 0))) {
                bestScore = s;
                best = e.getKey();
            }
        }
        return best;
    }

    public List<String> getReplicas(String key, int count) {
        if (weights.isEmpty() || count <= 0) {
            return new ArrayList<>();
        }
        boolean weighted = isWeighted();
        TreeMap<Double, TreeMap<String, String>> ranked = new TreeMap<>();
        List<String[]> scored = new ArrayList<>();
        for (Map.Entry<String, Integer> e : weights.entrySet()) {
            scored.add(new String[] {e.getKey(), Double.toString(score(e.getKey(), key, e.getValue(), weighted))});
        }
        scored.sort((a, b) -> {
            int c = Double.compare(Double.parseDouble(b[1]), Double.parseDouble(a[1]));
            return c != 0 ? c : b[0].compareTo(a[0]);
        });
        List<String> out = new ArrayList<>();
        for (int i = 0; i < Math.min(count, scored.size()); i++) {
            out.add(scored.get(i)[0]);
        }
        return out;
    }

    public List<String> nodes() {
        List<String> out = new ArrayList<>(weights.keySet());
        out.sort(null);
        return out;
    }

    public int size() {
        return weights.size();
    }

    private boolean isWeighted() {
        for (int w : weights.values()) {
            if (w != 1) {
                return true;
            }
        }
        return false;
    }

    private static double score(String node, String key, int weight, boolean weighted) {
        long h = HashRing.fnv1a64(node + "#" + key);
        if (!weighted) {
            return unsignedToDouble(h); // pure integer score - portable, what conformance pins
        }
        double normalized = (unsignedToDouble(h) + 1) / (unsignedToDouble(-1L) + 1);
        return -weight / Math.log(normalized);
    }

    /** Convert an unsigned 64-bit value (held in a long) to double, matching the way
     * every other port converts u64 -> double for the score. */
    static double unsignedToDouble(long x) {
        if (x >= 0) {
            return (double) x;
        }
        return ((double) (x >>> 1)) * 2.0 + (double) (x & 1L);
    }
}
