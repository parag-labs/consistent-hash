use crate::fnv1a_64;

/// Jump consistent hash (Lamping & Veach, 2014) over an ordered bucket list. No
/// per-node state, O(ln N) lookups. Buckets are an ordered range, so it stays
/// consistent when nodes are appended or removed at the tail.
pub struct Jump {
    nodes: Vec<String>,
}

impl Jump {
    pub fn new(nodes: &[&str]) -> Self {
        Jump {
            nodes: nodes.iter().map(|n| n.to_string()).collect(),
        }
    }

    pub fn add(&mut self, node: &str) {
        if !self.nodes.iter().any(|n| n == node) {
            self.nodes.push(node.to_string());
        }
    }

    pub fn remove(&mut self, node: &str) {
        if let Some(i) = self.nodes.iter().position(|n| n == node) {
            self.nodes.remove(i);
        }
    }

    pub fn get(&self, key: &str) -> Option<&str> {
        if self.nodes.is_empty() {
            return None;
        }
        let b = jump_consistent_hash(fnv1a_64(key), self.nodes.len() as u32);
        Some(self.nodes[b as usize].as_str())
    }

    pub fn nodes(&self) -> Vec<String> {
        self.nodes.clone()
    }

    pub fn len(&self) -> usize {
        self.nodes.len()
    }

    pub fn is_empty(&self) -> bool {
        self.nodes.is_empty()
    }
}

/// Map `key` to a bucket in `[0, num_buckets)` with O(1) memory.
pub fn jump_consistent_hash(mut key: u64, num_buckets: u32) -> u32 {
    assert!(num_buckets >= 1, "num_buckets must be at least 1");
    let mut b: i64 = -1;
    let mut j: i64 = 0;
    while j < num_buckets as i64 {
        b = j;
        key = key.wrapping_mul(2862933555777941757).wrapping_add(1);
        j = ((b + 1) as f64 * ((1i64 << 31) as f64 / ((key >> 33) + 1) as f64)) as i64;
    }
    b as u32
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn in_range_and_stable() {
        for k in 0..1000u64 {
            let b = jump_consistent_hash(k, 17);
            assert!(b < 17);
            assert_eq!(b, jump_consistent_hash(k, 17));
        }
    }

    #[test]
    fn growth_moves_bounded_fraction() {
        let keys: Vec<String> = (0..20000).map(|i| format!("key-{i}")).collect();
        let init: Vec<&str> = (0..8).map(|_| "").collect();
        let mut j = Jump::new(&init[..0]);
        for i in 0..8 {
            j.add(&format!("node-{i}"));
        }
        let before: Vec<String> = keys.iter().map(|k| j.get(k).unwrap().to_string()).collect();
        j.add("node-8");
        let moved = keys
            .iter()
            .enumerate()
            .filter(|(i, k)| j.get(k).unwrap() != before[*i])
            .count();
        assert!((moved as f64) / (keys.len() as f64) < 0.20);
    }
}
