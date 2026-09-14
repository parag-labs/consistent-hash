use crate::fnv1a_32;
use std::collections::{BTreeSet, HashMap};

/// A consistent-hash ring with virtual nodes. Keys and nodes share one circular FNV
/// space; a key is owned by the first node clockwise from it. Each node occupies
/// `replicas` ring points so load spreads evenly.
pub struct Ring {
    replicas: usize,
    ring: HashMap<u32, String>,
    sorted: Vec<u32>,
    nodes: BTreeSet<String>,
}

impl Ring {
    pub fn new(nodes: &[&str], replicas: usize) -> Self {
        assert!(replicas >= 1, "replicas must be at least 1");
        let mut r = Ring {
            replicas,
            ring: HashMap::new(),
            sorted: Vec::new(),
            nodes: BTreeSet::new(),
        };
        for n in nodes {
            r.add(n);
        }
        r
    }

    pub fn add(&mut self, node: &str) {
        if !self.nodes.insert(node.to_string()) {
            return;
        }
        for i in 0..self.replicas {
            let mut slot = fnv1a_32(&format!("{node}#{i}"));
            while self.ring.contains_key(&slot) {
                slot = slot.wrapping_add(1); // deterministic nudge on collision
            }
            self.ring.insert(slot, node.to_string());
        }
        self.reindex();
    }

    pub fn remove(&mut self, node: &str) {
        if !self.nodes.remove(node) {
            return;
        }
        self.ring.retain(|_, n| n != node);
        self.reindex();
    }

    pub fn get(&self, key: &str) -> Option<&str> {
        if self.sorted.is_empty() {
            return None;
        }
        let idx = self.first_clockwise(fnv1a_32(key));
        Some(self.ring[&self.sorted[idx]].as_str())
    }

    pub fn get_replicas(&self, key: &str, count: usize) -> Vec<String> {
        let mut result = Vec::new();
        if self.sorted.is_empty() || count == 0 {
            return result;
        }
        let start = self.first_clockwise(fnv1a_32(key));
        let cap = count.min(self.nodes.len());
        for i in 0..self.sorted.len() {
            let node = &self.ring[&self.sorted[(start + i) % self.sorted.len()]];
            if !result.iter().any(|n| n == node) {
                result.push(node.clone());
                if result.len() == cap {
                    break;
                }
            }
        }
        result
    }

    pub fn nodes(&self) -> Vec<String> {
        self.nodes.iter().cloned().collect()
    }

    pub fn len(&self) -> usize {
        self.nodes.len()
    }

    pub fn is_empty(&self) -> bool {
        self.nodes.is_empty()
    }

    fn first_clockwise(&self, h: u32) -> usize {
        match self.sorted.partition_point(|&s| s <= h) {
            i if i == self.sorted.len() => 0, // wrap around
            i => i,
        }
    }

    fn reindex(&mut self) {
        self.sorted = self.ring.keys().copied().collect();
        self.sorted.sort_unstable();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn adding_a_node_remaps_a_small_fraction() {
        let keys: Vec<String> = (0..5000).map(|i| format!("key-{i}")).collect();
        let mut r = Ring::new(&["a", "b", "c"], 200);
        let before: Vec<String> = keys.iter().map(|k| r.get(k).unwrap().to_string()).collect();
        r.add("d");
        let mut moved = 0;
        for (i, k) in keys.iter().enumerate() {
            let after = r.get(k).unwrap();
            if after != before[i] {
                moved += 1;
                assert_eq!(after, "d", "moved key must land on the new node");
            }
        }
        assert!((moved as f64) / (keys.len() as f64) < 0.40);
    }

    #[test]
    fn replicas_are_distinct() {
        let r = Ring::new(&["a", "b", "c", "d", "e"], 100);
        let reps = r.get_replicas("some-key", 3);
        assert_eq!(reps.len(), 3);
        let unique: BTreeSet<_> = reps.iter().collect();
        assert_eq!(unique.len(), 3);
    }
}
