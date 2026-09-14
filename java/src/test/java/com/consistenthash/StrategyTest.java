package com.consistenthash;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class StrategyTest {

    private static List<String> keys(int n) {
        List<String> out = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            out.add("key-" + i);
        }
        return out;
    }

    @Test
    void fnv64MatchesKnownVectors() {
        assertEquals(0xCBF29CE484222325L, HashRing.fnv1a64(""));
        assertEquals(0x85944171F73967E8L, HashRing.fnv1a64("foobar"));
    }

    @Test
    void jumpIsStableAndInRange() {
        for (long k = 0; k < 1000; k++) {
            int b = Jump.jumpConsistentHash(k, 17);
            assertTrue(b >= 0 && b < 17);
            assertEquals(b, Jump.jumpConsistentHash(k, 17));
        }
    }

    @Test
    void rendezvousRemovalMovesOnlyItsKeys() {
        List<String> keys = keys(5000);
        Rendezvous hrw = new Rendezvous(List.of("a", "b", "c", "d"));
        Map<String, String> before = new HashMap<>();
        for (String k : keys) {
            before.put(k, hrw.get(k));
        }
        hrw.remove("d");
        for (String k : keys) {
            if (!before.get(k).equals("d")) {
                assertEquals(before.get(k), hrw.get(k));
            }
        }
    }

    @Test
    void rendezvousWeightBiasesLoad() {
        Rendezvous hrw = new Rendezvous();
        hrw.add("small", 1);
        hrw.add("big", 4);
        int big = 0;
        for (int i = 0; i < 8000; i++) {
            if ("big".equals(hrw.get("key-" + i))) {
                big++;
            }
        }
        assertTrue(big > 4000, "weight had no effect: big=" + big);
    }

    @Test
    void maglevCoversAndBalances() {
        Maglev mag = new Maglev(List.of("a", "b", "c", "d"), 1019);
        Map<String, Integer> counts = new HashMap<>();
        for (int i = 0; i < 8000; i++) {
            counts.merge(mag.get("key-" + i), 1, Integer::sum);
        }
        assertEquals(4, counts.size());
        int max = counts.values().stream().max(Integer::compare).get();
        int min = counts.values().stream().min(Integer::compare).get();
        assertTrue(max - min < 400);
    }

    @Test
    void boundedLoadCapsHotNodes() {
        List<String> nodes = List.of("node-0", "node-1", "node-2", "node-3", "node-4");
        BoundedLoad bl = new BoundedLoad(nodes, 200, 0.25);
        for (int i = 0; i < 5000; i++) {
            bl.get("key-" + i);
        }
        Map<String, Integer> loads = bl.loads();
        double mean = loads.values().stream().mapToInt(Integer::intValue).sum() / (double) nodes.size();
        int peak = loads.values().stream().max(Integer::compare).get();
        assertTrue(peak <= 1.25 * mean + 1, "a node exceeded the cap: peak=" + peak);
    }
}
