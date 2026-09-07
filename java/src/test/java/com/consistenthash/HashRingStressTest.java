package com.consistenthash;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;

import org.junit.jupiter.api.Test;

/**
 * Stress suite: a rebalance storm. Hundreds of random add/remove operations, with
 * two invariants that must never break - ownership never dangles after a removal,
 * and a single membership change moves only a small, bounded fraction of keys.
 */
class HashRingStressTest {

    @Test
    void ownershipNeverDanglesUnderChurn() {
        Random rng = new Random(2024);
        List<String> keys = new ArrayList<>();
        for (int i = 0; i < 3000; i++) {
            keys.add("key-" + i);
        }
        List<String> initial = new ArrayList<>();
        for (int i = 0; i < 8; i++) {
            initial.add("node-" + i);
        }
        HashRing ring = new HashRing(initial, 150);

        for (int round = 0; round < 300; round++) {
            Set<String> live = new HashSet<>(ring.nodes());
            if (rng.nextDouble() < 0.5 || live.size() <= 1) {
                ring.add("node-" + rng.nextInt(41));
            } else {
                List<String> liveList = new ArrayList<>(live);
                ring.remove(liveList.get(rng.nextInt(liveList.size())));
            }

            Set<String> now = new HashSet<>(ring.nodes());
            for (int s = 0; s < 200; s++) {
                String key = keys.get(rng.nextInt(keys.size()));
                assertTrue(now.contains(ring.get(key)));
            }
        }
    }

    @Test
    void singleChangeMovesBoundedFractionAcrossManyRounds() {
        Random rng = new Random(99);
        List<String> keys = new ArrayList<>();
        for (int i = 0; i < 5000; i++) {
            keys.add("key-" + i);
        }
        List<String> initial = new ArrayList<>();
        for (int i = 0; i < 10; i++) {
            initial.add("node-" + i);
        }
        HashRing ring = new HashRing(initial, 200);

        double worst = 0.0;
        for (int round = 0; round < 60; round++) {
            Map<String, String> before = new HashMap<>();
            for (String k : keys) {
                before.put(k, ring.get(k));
            }
            if (rng.nextDouble() < 0.5 || ring.size() <= 1) {
                ring.add("node-" + rng.nextInt(61));
            } else {
                ring.remove(ring.nodes().get(rng.nextInt(ring.size())));
            }

            int moved = 0;
            for (String k : keys) {
                if (!before.get(k).equals(ring.get(k))) {
                    moved++;
                }
            }
            double frac = moved / (double) keys.size();
            worst = Math.max(worst, frac);
            assertTrue(frac < 0.35, "a single change moved " + (int) (frac * 100) + "% of keys");
        }
        assertTrue(worst < 0.35);
    }

    @Test
    void ringRecoversToEmptyAndBack() {
        HashRing ring = new HashRing(List.of(), 50);
        assertNull(ring.get("k"));
        for (int i = 0; i < 20; i++) {
            ring.add("n" + i);
        }
        assertTrue(new HashSet<>(ring.nodes()).contains(ring.get("k")));
        for (String n : new ArrayList<>(ring.nodes())) {
            ring.remove(n);
        }
        assertNull(ring.get("k"));
        assertEquals(0, ring.size());
    }
}
