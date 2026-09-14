package consistenthash

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strconv"
	"testing"
)

// vectors mirrors the parts of conformance/vectors.json this port checks.
type vectors struct {
	Hash struct {
		Fnv1a32 map[string]string `json:"fnv1a_32"`
		Fnv1a64 map[string]string `json:"fnv1a_64"`
	} `json:"hash"`
	Ring struct {
		Replicas   int               `json:"replicas"`
		Nodes      []string          `json:"nodes"`
		Assignment map[string]string `json:"assignment"`
	} `json:"ring"`
	Rendezvous struct {
		Nodes      []string          `json:"nodes"`
		Assignment map[string]string `json:"assignment"`
	} `json:"rendezvous"`
	Jump struct {
		Nodes      []string          `json:"nodes"`
		Assignment map[string]string `json:"assignment"`
	} `json:"jump"`
	Maglev struct {
		TableSize  int               `json:"table_size"`
		Nodes      []string          `json:"nodes"`
		Assignment map[string]string `json:"assignment"`
	} `json:"maglev"`
	BoundedLoad struct {
		Replicas    int               `json:"replicas"`
		EpsilonNum  int               `json:"epsilon_num"`
		EpsilonDen  int               `json:"epsilon_den"`
		Nodes       []string          `json:"nodes"`
		KeysInOrder []string          `json:"keys_in_order"`
		Assignment  map[string]string `json:"assignment"`
	} `json:"bounded_load"`
}

func loadVectors(t *testing.T) vectors {
	t.Helper()
	path := filepath.Join("..", "conformance", "vectors.json")
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read vectors: %v", err)
	}
	var v vectors
	if err := json.Unmarshal(raw, &v); err != nil {
		t.Fatalf("parse vectors: %v", err)
	}
	return v
}

func mustHex(t *testing.T, s string) uint64 {
	t.Helper()
	n, err := strconv.ParseUint(s[2:], 16, 64)
	if err != nil {
		t.Fatalf("bad hex %q: %v", s, err)
	}
	return n
}

func TestConformanceHash(t *testing.T) {
	v := loadVectors(t)
	for probe, hex := range v.Hash.Fnv1a32 {
		if got := uint64(Fnv1a32(probe)); got != mustHex(t, hex) {
			t.Errorf("fnv32(%q)=%#x want %s", probe, got, hex)
		}
	}
	for probe, hex := range v.Hash.Fnv1a64 {
		if got := Fnv1a64(probe); got != mustHex(t, hex) {
			t.Errorf("fnv64(%q)=%#x want %s", probe, got, hex)
		}
	}
}

func TestConformanceRing(t *testing.T) {
	v := loadVectors(t)
	r := NewRing(v.Ring.Nodes, v.Ring.Replicas)
	for key, node := range v.Ring.Assignment {
		if got := r.Get(key); got != node {
			t.Errorf("ring[%s]=%s want %s", key, got, node)
		}
	}
}

func TestConformanceRendezvous(t *testing.T) {
	v := loadVectors(t)
	h := NewRendezvous(v.Rendezvous.Nodes)
	for key, node := range v.Rendezvous.Assignment {
		if got := h.Get(key); got != node {
			t.Errorf("hrw[%s]=%s want %s", key, got, node)
		}
	}
}

func TestConformanceJump(t *testing.T) {
	v := loadVectors(t)
	j := NewJump(v.Jump.Nodes)
	for key, node := range v.Jump.Assignment {
		if got := j.Get(key); got != node {
			t.Errorf("jump[%s]=%s want %s", key, got, node)
		}
	}
}

func TestConformanceMaglev(t *testing.T) {
	v := loadVectors(t)
	m := NewMaglev(v.Maglev.Nodes, v.Maglev.TableSize)
	for key, node := range v.Maglev.Assignment {
		if got := m.Get(key); got != node {
			t.Errorf("maglev[%s]=%s want %s", key, got, node)
		}
	}
}

func TestConformanceBoundedLoad(t *testing.T) {
	v := loadVectors(t)
	eps := float64(v.BoundedLoad.EpsilonNum) / float64(v.BoundedLoad.EpsilonDen)
	b := NewBoundedLoad(v.BoundedLoad.Nodes, v.BoundedLoad.Replicas, eps)
	// Order-sensitive: replay keys in the pinned order.
	for _, key := range v.BoundedLoad.KeysInOrder {
		if got := b.Get(key); got != v.BoundedLoad.Assignment[key] {
			t.Errorf("bounded[%s]=%s want %s", key, got, v.BoundedLoad.Assignment[key])
		}
	}
}
