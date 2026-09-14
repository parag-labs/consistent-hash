// Package consistenthash places keys on nodes so that adding or removing a node
// moves as few keys as possible. It implements five strategies from the consistent
// hashing family - a ring with virtual nodes, rendezvous (HRW), jump, Maglev, and
// bounded-load - all sharing the same portable FNV hashes so a given key lands on
// the same node here as in the Python, Rust, C#, Java, and TypeScript ports.
package consistenthash

// Fnv1a32 is FNV-1a over the UTF-8 bytes of s, 32-bit. It is deliberately not the
// language's built-in string hash: FNV is tiny, dependency-free, and identical in
// every language, which is what makes cross-language placement agree.
func Fnv1a32(s string) uint32 {
	var h uint32 = 0x811C9DC5
	for _, b := range []byte(s) {
		h ^= uint32(b)
		h *= 0x01000193
	}
	return h
}

// Fnv1a64 is the 64-bit twin of Fnv1a32, used by the strategies that need a wider
// hash space (jump's LCG seed, Maglev's table offsets, rendezvous scores).
func Fnv1a64(s string) uint64 {
	var h uint64 = 0xCBF29CE484222325
	for _, b := range []byte(s) {
		h ^= uint64(b)
		h *= 0x100000001B3
	}
	return h
}
