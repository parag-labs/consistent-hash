package consistenthash

import (
	"fmt"
	"sort"
)

// Maglev is Google's lookup-table hashing: build a fixed prime-sized permutation
// table once, where each node claims slots in a deterministic interleaving. Lookups
// are a single array index, balance is tighter than the ring, and losing a node only
// rewrites its own slots.
type Maglev struct {
	m     int
	nodes []string
	table []int
}

// NewMaglev builds a Maglev table of the given prime size over nodes.
func NewMaglev(nodes []string, tableSize int) *Maglev {
	if !isPrime(tableSize) {
		panic("tableSize must be prime")
	}
	m := &Maglev{m: tableSize, nodes: dedupeSorted(nodes)}
	m.build()
	return m
}

// Add inserts a node and rebuilds the table.
func (m *Maglev) Add(node string) {
	for _, n := range m.nodes {
		if n == node {
			return
		}
	}
	m.nodes = append(m.nodes, node)
	sort.Strings(m.nodes)
	m.build()
}

// Remove deletes a node and rebuilds the table.
func (m *Maglev) Remove(node string) {
	for i, n := range m.nodes {
		if n == node {
			m.nodes = append(m.nodes[:i], m.nodes[i+1:]...)
			m.build()
			return
		}
	}
}

// Get returns the node owning key, or "" if empty.
func (m *Maglev) Get(key string) string {
	if len(m.nodes) == 0 {
		return ""
	}
	return m.nodes[m.table[Fnv1a64(key)%uint64(m.m)]]
}

// Nodes returns the nodes in sorted order.
func (m *Maglev) Nodes() []string {
	out := make([]string, len(m.nodes))
	copy(out, m.nodes)
	return out
}

// Len is the number of nodes.
func (m *Maglev) Len() int { return len(m.nodes) }

func (m *Maglev) build() {
	n := len(m.nodes)
	if n == 0 {
		m.table = nil
		return
	}
	offset := make([]uint64, n)
	skip := make([]uint64, n)
	for i, name := range m.nodes {
		offset[i] = Fnv1a64(fmt.Sprintf("%s#offset", name)) % uint64(m.m)
		skip[i] = Fnv1a64(fmt.Sprintf("%s#skip", name))%uint64(m.m-1) + 1
	}
	table := make([]int, m.m)
	for i := range table {
		table[i] = -1
	}
	next := make([]uint64, n)
	filled := 0
	for filled < m.m {
		for i := 0; i < n; i++ {
			c := (offset[i] + next[i]*skip[i]) % uint64(m.m)
			for table[c] >= 0 {
				next[i]++
				c = (offset[i] + next[i]*skip[i]) % uint64(m.m)
			}
			table[c] = i
			next[i]++
			filled++
			if filled == m.m {
				break
			}
		}
	}
	m.table = table
}

func isPrime(n int) bool {
	if n < 2 {
		return false
	}
	if n%2 == 0 {
		return n == 2
	}
	for i := 3; i*i <= n; i += 2 {
		if n%i == 0 {
			return false
		}
	}
	return true
}

func dedupeSorted(nodes []string) []string {
	seen := make(map[string]struct{}, len(nodes))
	out := make([]string, 0, len(nodes))
	for _, n := range nodes {
		if _, ok := seen[n]; !ok {
			seen[n] = struct{}{}
			out = append(out, n)
		}
	}
	sort.Strings(out)
	return out
}
