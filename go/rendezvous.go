package consistenthash

import (
	"math"
	"sort"
)

// Rendezvous is highest-random-weight (HRW) placement: score every node for the key
// and take the max. No ring to rebuild, and weights are first-class. Lookups are
// O(N), which suits small clusters where that is cheap.
type Rendezvous struct {
	weights map[string]int
}

// NewRendezvous builds an unweighted HRW placer over nodes.
func NewRendezvous(nodes []string) *Rendezvous {
	h := &Rendezvous{weights: make(map[string]int)}
	for _, n := range nodes {
		h.Add(n, 1)
	}
	return h
}

// Add registers a node with an integer weight (>= 1). A heavier node wins more keys.
func (h *Rendezvous) Add(node string, weight int) {
	if weight < 1 {
		panic("weight must be at least 1")
	}
	h.weights[node] = weight
}

// Remove drops a node.
func (h *Rendezvous) Remove(node string) { delete(h.weights, node) }

// Get returns the node with the highest score for key, or "" if empty.
func (h *Rendezvous) Get(key string) string {
	if len(h.weights) == 0 {
		return ""
	}
	weighted := h.isWeighted()
	best := ""
	bestScore := math.Inf(-1)
	for node, w := range h.weights {
		s := h.score(node, key, w, weighted)
		if s > bestScore || (s == bestScore && node > best) {
			bestScore = s
			best = node
		}
	}
	return best
}

// GetReplicas returns the top count nodes by score.
func (h *Rendezvous) GetReplicas(key string, count int) []string {
	if len(h.weights) == 0 || count <= 0 {
		return []string{}
	}
	weighted := h.isWeighted()
	type scored struct {
		node  string
		score float64
	}
	ranked := make([]scored, 0, len(h.weights))
	for node, w := range h.weights {
		ranked = append(ranked, scored{node, h.score(node, key, w, weighted)})
	}
	sort.Slice(ranked, func(i, j int) bool {
		if ranked[i].score != ranked[j].score {
			return ranked[i].score > ranked[j].score
		}
		return ranked[i].node > ranked[j].node
	})
	cap := count
	if cap > len(ranked) {
		cap = len(ranked)
	}
	out := make([]string, cap)
	for i := 0; i < cap; i++ {
		out[i] = ranked[i].node
	}
	return out
}

// Nodes returns the nodes in sorted order.
func (h *Rendezvous) Nodes() []string {
	out := make([]string, 0, len(h.weights))
	for n := range h.weights {
		out = append(out, n)
	}
	sort.Strings(out)
	return out
}

// Len is the number of nodes.
func (h *Rendezvous) Len() int { return len(h.weights) }

func (h *Rendezvous) isWeighted() bool {
	for _, w := range h.weights {
		if w != 1 {
			return true
		}
	}
	return false
}

func (h *Rendezvous) score(node, key string, weight int, weighted bool) float64 {
	hv := Fnv1a64(node + "#" + key)
	if !weighted {
		return float64(hv) // pure integer score - portable, what conformance pins
	}
	normalized := (float64(hv) + 1) / (math.MaxUint64 + 1.0)
	return -float64(weight) / math.Log(normalized)
}
