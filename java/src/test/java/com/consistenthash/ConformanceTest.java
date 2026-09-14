package com.consistenthash;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import org.json.JSONObject;
import org.junit.jupiter.api.Test;

/** The Java port must reproduce the committed golden vectors exactly. */
class ConformanceTest {

    private static JSONObject vectors() throws IOException {
        // Walk up from the working directory to the repo root, then into conformance/.
        Path dir = Paths.get("").toAbsolutePath();
        while (dir != null && !Files.exists(dir.resolve("conformance/vectors.json"))) {
            dir = dir.getParent();
        }
        if (dir == null) {
            throw new IOException("could not locate conformance/vectors.json");
        }
        return new JSONObject(Files.readString(dir.resolve("conformance/vectors.json")));
    }

    private static long hex(String s) {
        return Long.parseUnsignedLong(s.substring(2), 16);
    }

    private static List<String> nodes(JSONObject spec) {
        List<String> out = new ArrayList<>();
        spec.getJSONArray("nodes").forEach(o -> out.add((String) o));
        return out;
    }

    @Test
    void hashMatches() throws IOException {
        JSONObject h = vectors().getJSONObject("hash");
        JSONObject h32 = h.getJSONObject("fnv1a_32");
        for (String probe : h32.keySet()) {
            assertEquals(hex(h32.getString(probe)), HashRing.fnv1a32(probe), "fnv32 " + probe);
        }
        JSONObject h64 = h.getJSONObject("fnv1a_64");
        for (String probe : h64.keySet()) {
            assertEquals(hex(h64.getString(probe)), HashRing.fnv1a64(probe), "fnv64 " + probe);
        }
    }

    @Test
    void ringMatches() throws IOException {
        JSONObject spec = vectors().getJSONObject("ring");
        HashRing ring = new HashRing(nodes(spec), spec.getInt("replicas"));
        JSONObject a = spec.getJSONObject("assignment");
        for (String key : a.keySet()) {
            assertEquals(a.getString(key), ring.get(key), "ring " + key);
        }
    }

    @Test
    void rendezvousMatches() throws IOException {
        JSONObject spec = vectors().getJSONObject("rendezvous");
        Rendezvous hrw = new Rendezvous(nodes(spec));
        JSONObject a = spec.getJSONObject("assignment");
        for (String key : a.keySet()) {
            assertEquals(a.getString(key), hrw.get(key), "hrw " + key);
        }
    }

    @Test
    void jumpMatches() throws IOException {
        JSONObject spec = vectors().getJSONObject("jump");
        Jump jump = new Jump(nodes(spec));
        JSONObject a = spec.getJSONObject("assignment");
        for (String key : a.keySet()) {
            assertEquals(a.getString(key), jump.get(key), "jump " + key);
        }
    }

    @Test
    void maglevMatches() throws IOException {
        JSONObject spec = vectors().getJSONObject("maglev");
        Maglev maglev = new Maglev(nodes(spec), spec.getInt("table_size"));
        JSONObject a = spec.getJSONObject("assignment");
        for (String key : a.keySet()) {
            assertEquals(a.getString(key), maglev.get(key), "maglev " + key);
        }
    }

    @Test
    void boundedLoadMatches() throws IOException {
        JSONObject spec = vectors().getJSONObject("bounded_load");
        double eps = (double) spec.getInt("epsilon_num") / spec.getInt("epsilon_den");
        BoundedLoad bounded = new BoundedLoad(nodes(spec), spec.getInt("replicas"), eps);
        JSONObject a = spec.getJSONObject("assignment");
        spec.getJSONArray("keys_in_order").forEach(o -> {
            String key = (String) o;
            assertEquals(a.getString(key), bounded.get(key), "bounded " + key);
        });
    }
}
