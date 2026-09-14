//! Consistent hashing as a family of strategies - a ring with virtual nodes,
//! rendezvous (HRW), jump, Maglev, and bounded-load - sharing one set of portable
//! FNV hashes so a key lands on the same node here as in the Python, Go, C#, Java,
//! and TypeScript ports.

mod bounded;
mod jump;
mod maglev;
mod rendezvous;
mod ring;

pub use bounded::BoundedLoad;
pub use jump::{jump_consistent_hash, Jump};
pub use maglev::Maglev;
pub use rendezvous::Rendezvous;
pub use ring::Ring;

/// FNV-1a over the UTF-8 bytes of `s`, 32-bit. Not the language's built-in hash:
/// FNV is tiny and identical in every language, which is what makes placement agree.
pub fn fnv1a_32(s: &str) -> u32 {
    let mut h: u32 = 0x811C9DC5;
    for b in s.as_bytes() {
        h ^= *b as u32;
        h = h.wrapping_mul(0x0100_0193);
    }
    h
}

/// FNV-1a over the UTF-8 bytes of `s`, 64-bit. Used by the strategies that need a
/// wider hash space (jump's LCG seed, Maglev's table offsets, rendezvous scores).
pub fn fnv1a_64(s: &str) -> u64 {
    let mut h: u64 = 0xCBF2_9CE4_8422_2325;
    for b in s.as_bytes() {
        h ^= *b as u64;
        h = h.wrapping_mul(0x0000_0100_0000_01B3);
    }
    h
}

pub(crate) fn is_prime(n: usize) -> bool {
    if n < 2 {
        return false;
    }
    if n.is_multiple_of(2) {
        return n == 2;
    }
    let mut i = 3;
    while i * i <= n {
        if n.is_multiple_of(i) {
            return false;
        }
        i += 2;
    }
    true
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn fnv_known_vectors() {
        assert_eq!(fnv1a_32(""), 0x811C9DC5);
        assert_eq!(fnv1a_32("foobar"), 0xBF9C_F968);
        assert_eq!(fnv1a_64(""), 0xCBF2_9CE4_8422_2325);
        assert_eq!(fnv1a_64("foobar"), 0x8594_4171_F739_67E8);
    }
}
