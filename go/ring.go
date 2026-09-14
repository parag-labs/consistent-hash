package consistenthash

import (
	"fmt"
	"sort"
)

// Ring is consistent hashing with virtual nodes: keys and nodes share one circular
// FNV space, and a key is owned by the first node clockwise from it. Each physical
// node occupies Replicas points on the ring so load spreads evenly and a departing
// node's keys scatter across many neighbors.
type Ring struct {
	replicas int
	ring     map[uint32]string
	sorted   []uint32
	nodes    map[string]struct{}
}

// NewRing builds a ring with the given nodes and virtual-node count (replicas).
func NewRing(nodes []string, replicas int) *Ring {
	if replicas < 1 {
		panic("replicas must be at least 1")
	}
	r := &Ring{
		replicas: replicas,
		ring:     make(map[uint32]string),
		nodes:    make(map[string]struct{}),
	}
	for _, n := range nodes {
		r.Add(n)
	}
	return r
}

// Add inserts a node and its virtual replicas. A repeated node is a no-op.
func (r *Ring) Add(node string) {
	if _, ok := r.nodes[node]; ok {
		return
	}
	r.nodes[node] = struct{}{}
	for i := 0; i < r.replicas; i++ {
		slot := Fnv1a32(fmt.Sprintf("%s#%d", node, i))
		for {
			if _, taken := r.ring[slot]; !taken {
				break
			}
			slot++ // deterministic nudge on collision
		}
		r.ring[slot] = node
	}
	r.reindex()
}

// Remove deletes a node and all its slots. Removing an absent node is a no-op.
func (r *Ring) Remove(node string) {
	if _, ok := r.nodes[node]; !ok {
		return
	}
	delete(r.nodes, node)
	for slot, n := range r.ring {
		if n == node {
			delete(r.ring, slot)
		}
	}
	r.reindex()
}

// Get returns the node that owns key, or "" if the ring is empty.
func (r *Ring) Get(key string) string {
	if len(r.sorted) == 0 {
		return ""
	}
	return r.ring[r.sorted[r.firstClockwise(Fnv1a32(key))]]
}

// GetReplicas returns the first count distinct nodes clockwise from key.
func (r *Ring) GetReplicas(key string, count int) []string {
	result := []string{}
	if len(r.sorted) == 0 || count <= 0 {
		return result
	}
	start := r.firstClockwise(Fnv1a32(key))
	cap := count
	if cap > len(r.nodes) {
		cap = len(r.nodes)
	}
	seen := make(map[string]struct{})
	for i := 0; i < len(r.sorted); i++ {
		node := r.ring[r.sorted[(start+i)%len(r.sorted)]]
		if _, dup := seen[node]; dup {
			continue
		}
		seen[node] = struct{}{}
		result = append(result, node)
		if len(result) == cap {
			break
		}
	}
	return result
}

// Nodes returns the physical nodes in sorted order.
func (r *Ring) Nodes() []string {
	return sortedKeys(r.nodes)
}

// Len is the number of physical nodes.
func (r *Ring) Len() int { return len(r.nodes) }

func (r *Ring) firstClockwise(h uint32) int {
	idx := sort.Search(len(r.sorted), func(i int) bool { return r.sorted[i] > h })
	if idx == len(r.sorted) {
		return 0 // wrap around
	}
	return idx
}

func (r *Ring) reindex() {
	r.sorted = r.sorted[:0]
	for slot := range r.ring {
		r.sorted = append(r.sorted, slot)
	}
	sort.Slice(r.sorted, func(i, j int) bool { return r.sorted[i] < r.sorted[j] })
}

func sortedKeys(m map[string]struct{}) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}
