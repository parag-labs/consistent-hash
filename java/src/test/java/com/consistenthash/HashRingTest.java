package com.consistenthash;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.Test;

class HashRingTest {

    @Test
    void emptyRingReturnsNull() {
        assertNull(new HashRing().get("anything"));
    }

    @Test
    void lookupIsStable() {
        HashRing ring = new HashRing(List.of("a", "b", "c"), 100);
        assertEquals(ring.get("user-42"), ring.get("user-42"));
    }

    @Test
    void everyKeyMapsToARealNode() {
        HashRing ring = new HashRing(List.of("a", "b", "c"), 100);
        var valid = new HashSet<>(List.of("a", "b", "c"));
        for (int i = 0; i < 500; i++) {
            assertTrue(valid.contains(ring.get("k" + i)));
        }
    }

    @Test
    void fnv1aMatchesKnownVectors() {
        assertEquals(0x811C9DC5L, HashRing.fnv1a32(""));
        assertEquals(0xE40C292CL, HashRing.fnv1a32("a"));
        assertEquals(0xBF9CF968L, HashRing.fnv1a32("foobar"));
    }

    @Test
    void distributionIsReasonablyEven() {
        HashRing ring = new HashRing(List.of("a", "b", "c", "d"), 400);
        Map<String, Integer> counts = new HashMap<>();
        for (int i = 0; i < 8000; i++) {
            counts.merge(ring.get("key-" + i), 1, Integer::sum);
        }
        for (String node : List.of("a", "b", "c", "d")) {
            int c = counts.getOrDefault(node, 0);
            assertTrue(c > 1300 && c < 2700, node + " got " + c);
        }
    }

    @Test
    void addingANodeRemapsOnlyASmallFraction() {
        List<String> keys = new ArrayList<>();
        for (int i = 0; i < 5000; i++) {
            keys.add("key-" + i);
        }
        HashRing ring = new HashRing(List.of("a", "b", "c"), 200);
        Map<String, String> before = new HashMap<>();
        for (String k : keys) {
            before.put(k, ring.get(k));
        }

        ring.add("d");
        int moved = 0;
        for (String k : keys) {
            String now = ring.get(k);
            if (!before.get(k).equals(now)) {
                moved++;
                assertEquals("d", now);
            }
        }
        assertTrue(moved / (double) keys.size() < 0.40);
    }

    @Test
    void removingANodeOnlyMovesItsKeys() {
        List<String> keys = new ArrayList<>();
        for (int i = 0; i < 5000; i++) {
            keys.add("key-" + i);
        }
        HashRing ring = new HashRing(List.of("a", "b", "c", "d"), 200);
        Map<String, String> before = new HashMap<>();
        for (String k : keys) {
            before.put(k, ring.get(k));
        }

        ring.remove("d");
        var remaining = new HashSet<>(List.of("a", "b", "c"));
        for (String k : keys) {
            if (!before.get(k).equals("d")) {
                assertEquals(before.get(k), ring.get(k));
            } else {
                assertTrue(remaining.contains(ring.get(k)));
            }
        }
    }

    @Test
    void getReplicasReturnsDistinctNodes() {
        HashRing ring = new HashRing(List.of("a", "b", "c", "d", "e"), 100);
        List<String> reps = ring.getReplicas("some-key", 3);
        assertEquals(3, reps.size());
        assertEquals(3, new HashSet<>(reps).size());
    }

    @Test
    void getReplicasCapsAtNodeCount() {
        HashRing ring = new HashRing(List.of("a", "b"), 50);
        assertEquals(2, ring.getReplicas("k", 5).size());
    }

    @Test
    void idempotentAddAndRemove() {
        HashRing ring = new HashRing(List.of(), 10);
        ring.add("a");
        ring.add("a");
        assertEquals(List.of("a"), ring.nodes());
        ring.remove("ghost");
        assertEquals(List.of("a"), ring.nodes());
    }
}
