package consistenthash

import (
	"fmt"
	"testing"
)

func TestFnvKnownVectors(t *testing.T) {
	if Fnv1a32("") != 0x811C9DC5 {
		t.Fatalf("fnv32 empty: got %#x", Fnv1a32(""))
	}
	if Fnv1a32("foobar") != 0xBF9CF968 {
		t.Fatalf("fnv32 foobar: got %#x", Fnv1a32("foobar"))
	}
	if Fnv1a64("") != 0xCBF29CE484222325 {
		t.Fatalf("fnv64 empty: got %#x", Fnv1a64(""))
	}
	if Fnv1a64("foobar") != 0x85944171F73967E8 {
		t.Fatalf("fnv64 foobar: got %#x", Fnv1a64("foobar"))
	}
}

func nodes(n int) []string {
	out := make([]string, n)
	for i := range out {
		out[i] = fmt.Sprintf("node-%d", i)
	}
	return out
}

func TestRingRemapIsSmall(t *testing.T) {
	keys := make([]string, 5000)
	for i := range keys {
		keys[i] = fmt.Sprintf("key-%d", i)
	}
	r := NewRing([]string{"a", "b", "c"}, 200)
	before := map[string]string{}
	for _, k := range keys {
		before[k] = r.Get(k)
	}
	r.Add("d")
	moved := 0
	for _, k := range keys {
		after := r.Get(k)
		if after != before[k] {
			moved++
			if after != "d" {
				t.Fatalf("moved key %s went to %s, not the new node", k, after)
			}
		}
	}
	if frac := float64(moved) / float64(len(keys)); frac >= 0.40 {
		t.Fatalf("remap fraction too high: %.3f", frac)
	}
}

func TestRingReplicasDistinct(t *testing.T) {
	r := NewRing([]string{"a", "b", "c", "d", "e"}, 100)
	reps := r.GetReplicas("some-key", 3)
	if len(reps) != 3 {
		t.Fatalf("want 3 replicas, got %d", len(reps))
	}
	seen := map[string]bool{}
	for _, n := range reps {
		if seen[n] {
			t.Fatalf("duplicate replica %s", n)
		}
		seen[n] = true
	}
}

func TestJumpInRangeAndStable(t *testing.T) {
	for k := uint64(0); k < 1000; k++ {
		b := JumpConsistentHash(k, 17)
		if b < 0 || b >= 17 {
			t.Fatalf("bucket out of range: %d", b)
		}
		if b != JumpConsistentHash(k, 17) {
			t.Fatalf("jump not stable for %d", k)
		}
	}
}

func TestRendezvousRemovalMovesOnlyItsKeys(t *testing.T) {
	keys := make([]string, 5000)
	for i := range keys {
		keys[i] = fmt.Sprintf("key-%d", i)
	}
	h := NewRendezvous([]string{"a", "b", "c", "d"})
	before := map[string]string{}
	for _, k := range keys {
		before[k] = h.Get(k)
	}
	h.Remove("d")
	for _, k := range keys {
		after := h.Get(k)
		if before[k] != "d" && after != before[k] {
			t.Fatalf("key %s moved despite its node staying", k)
		}
	}
}

func TestRendezvousWeightBiasesLoad(t *testing.T) {
	h := NewRendezvous(nil)
	h.Add("small", 1)
	h.Add("big", 4)
	small, big := 0, 0
	for i := 0; i < 8000; i++ {
		if h.Get(fmt.Sprintf("key-%d", i)) == "big" {
			big++
		} else {
			small++
		}
	}
	if big <= small {
		t.Fatalf("weight had no effect: big=%d small=%d", big, small)
	}
}

func TestMaglevCoversAndBalances(t *testing.T) {
	m := NewMaglev([]string{"a", "b", "c", "d"}, 1019)
	counts := map[string]int{}
	for i := 0; i < 8000; i++ {
		counts[m.Get(fmt.Sprintf("key-%d", i))]++
	}
	if len(counts) != 4 {
		t.Fatalf("not all nodes used: %v", counts)
	}
	min, max := 1<<30, 0
	for _, c := range counts {
		if c < min {
			min = c
		}
		if c > max {
			max = c
		}
	}
	if max-min >= 400 {
		t.Fatalf("maglev spread too wide: min=%d max=%d", min, max)
	}
}

func TestBoundedLoadCapsHotNodes(t *testing.T) {
	ns := nodes(5)
	b := NewBoundedLoad(ns, 200, 0.25)
	for i := 0; i < 5000; i++ {
		b.Get(fmt.Sprintf("key-%d", i))
	}
	loads := b.Loads()
	total := 0
	peak := 0
	for _, c := range loads {
		total += c
		if c > peak {
			peak = c
		}
	}
	mean := float64(total) / float64(len(ns))
	if float64(peak) > 1.25*mean+1 {
		t.Fatalf("a node exceeded the cap: peak=%d mean=%.1f", peak, mean)
	}
}
