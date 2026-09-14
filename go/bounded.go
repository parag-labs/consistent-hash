package consistenthash

import (
	"fmt"
	"math"
	"sort"
)

// BoundedLoad is consistent hashing with bounded loads (Google, 2017): keys are
// placed clockwise on the ring, but no node may exceed ceil((1+Epsilon)*keys/nodes).
// When the clockwise owner is full, the key overflows to the next node under cap, so
// no node exceeds its fair share by more than Epsilon. Placement depends on load, so
// it is stateful and order-sensitive.
type BoundedLoad struct {
	replicas int
	epsilon  float64
	nodes    []string
	ring     map[uint32]string
	sorted   []uint32
	load     map[string]int
	assigned map[string]string
}

// NewBoundedLoad builds a bounded-load placer over nodes with the given replica count
// and epsilon (the allowed overshoot above the mean, e.g. 0.25 for +25%).
func NewBoundedLoad(nodes []string, replicas int, epsilon float64) *BoundedLoad {
	if epsilon < 0 {
		panic("epsilon must be non-negative")
	}
	b := &BoundedLoad{
		replicas: replicas,
		epsilon:  epsilon,
		nodes:    dedupeSorted(nodes),
		ring:     make(map[uint32]string),
		load:     make(map[string]int),
		assigned: make(map[string]string),
	}
	b.buildRing()
	return b
}

// Get returns the node owning key, respecting the per-node cap. It is idempotent for
// a key already assigned.
func (b *BoundedLoad) Get(key string) string {
	if len(b.sorted) == 0 {
		return ""
	}
	if node, ok := b.assigned[key]; ok {
		return node
	}
	capacity := b.capacity()
	start := b.firstClockwise(Fnv1a32(key))
	n := len(b.sorted)
	for i := 0; i < n; i++ {
		node := b.ring[b.sorted[(start+i)%n]]
		if b.load[node] < capacity {
			b.assigned[key] = node
			b.load[node]++
			return node
		}
	}
	// Every node at cap (only with a tiny epsilon): fall back to first clockwise.
	node := b.ring[b.sorted[start%n]]
	b.assigned[key] = node
	b.load[node]++
	return node
}

// Loads returns a copy of the current per-node key counts.
func (b *BoundedLoad) Loads() map[string]int {
	out := make(map[string]int, len(b.load))
	for k, v := range b.load {
		out[k] = v
	}
	return out
}

// Nodes returns the nodes in sorted order.
func (b *BoundedLoad) Nodes() []string {
	out := make([]string, len(b.nodes))
	copy(out, b.nodes)
	return out
}

// Len is the number of nodes.
func (b *BoundedLoad) Len() int { return len(b.nodes) }

func (b *BoundedLoad) capacity() int {
	total := len(b.assigned) + 1
	return int(math.Ceil((1 + b.epsilon) * float64(total) / float64(len(b.nodes))))
}

func (b *BoundedLoad) buildRing() {
	for _, node := range b.nodes {
		for i := 0; i < b.replicas; i++ {
			slot := Fnv1a32(fmt.Sprintf("%s#%d", node, i))
			for {
				if _, taken := b.ring[slot]; !taken {
					break
				}
				slot++
			}
			b.ring[slot] = node
		}
	}
	b.sorted = b.sorted[:0]
	for slot := range b.ring {
		b.sorted = append(b.sorted, slot)
	}
	sort.Slice(b.sorted, func(i, j int) bool { return b.sorted[i] < b.sorted[j] })
}

func (b *BoundedLoad) firstClockwise(h uint32) int {
	idx := sort.Search(len(b.sorted), func(i int) bool { return b.sorted[i] > h })
	if idx == len(b.sorted) {
		return 0
	}
	return idx
}
