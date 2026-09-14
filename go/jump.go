package consistenthash

// Jump is Lamping & Veach's jump consistent hash over an ordered bucket list. It
// keeps no per-node state and computes a bucket in O(ln N) with a short LCG loop.
// The buckets are an ordered range, so it stays consistent when nodes are appended
// or removed at the tail; pulling one from the middle reshuffles the tail.
type Jump struct {
	nodes []string
}

// NewJump builds a jump placer over an ordered node list.
func NewJump(nodes []string) *Jump {
	cp := make([]string, len(nodes))
	copy(cp, nodes)
	return &Jump{nodes: cp}
}

// Add appends a node as a new tail bucket.
func (j *Jump) Add(node string) {
	for _, n := range j.nodes {
		if n == node {
			return
		}
	}
	j.nodes = append(j.nodes, node)
}

// Remove deletes a node, preserving the order of the rest.
func (j *Jump) Remove(node string) {
	for i, n := range j.nodes {
		if n == node {
			j.nodes = append(j.nodes[:i], j.nodes[i+1:]...)
			return
		}
	}
}

// Get returns the node owning key, or "" if empty.
func (j *Jump) Get(key string) string {
	if len(j.nodes) == 0 {
		return ""
	}
	return j.nodes[JumpConsistentHash(Fnv1a64(key), len(j.nodes))]
}

// Nodes returns the buckets in order.
func (j *Jump) Nodes() []string {
	out := make([]string, len(j.nodes))
	copy(out, j.nodes)
	return out
}

// Len is the number of buckets.
func (j *Jump) Len() int { return len(j.nodes) }

// JumpConsistentHash maps key to a bucket in [0, numBuckets) with O(1) memory.
func JumpConsistentHash(key uint64, numBuckets int) int {
	if numBuckets < 1 {
		panic("numBuckets must be at least 1")
	}
	var b int64 = -1
	var j int64
	for j < int64(numBuckets) {
		b = j
		key = key*2862933555777941757 + 1
		j = int64(float64(b+1) * (float64(int64(1)<<31) / float64((key>>33)+1)))
	}
	return int(b)
}
