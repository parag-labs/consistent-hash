use crate::fnv1a_32;
use std::collections::HashMap;

/// Consistent hashing with bounded loads (Google, 2017): keys are placed clockwise on
/// the ring, but no node may exceed `ceil((1+epsilon)*keys/nodes)`. A full node
/// overflows to the next under cap, so no node exceeds its fair share by more than
/// `epsilon`. Placement depends on load, so it is stateful and order-sensitive.
pub struct BoundedLoad {
    epsilon: f64,
    nodes: Vec<String>,
    ring: HashMap<u32, String>,
    sorted: Vec<u32>,
    load: HashMap<String, usize>,
    assigned: HashMap<String, String>,
}

impl BoundedLoad {
    pub fn new(nodes: &[&str], replicas: usize, epsilon: f64) -> Self {
        assert!(epsilon >= 0.0, "epsilon must be non-negative");
        let mut sorted: Vec<String> = nodes.iter().map(|n| n.to_string()).collect();
        sorted.sort();
        sorted.dedup();
        let mut b = BoundedLoad {
            epsilon,
            nodes: sorted,
            ring: HashMap::new(),
            sorted: Vec::new(),
            load: HashMap::new(),
            assigned: HashMap::new(),
        };
        b.build_ring(replicas);
        b
    }

    pub fn get(&mut self, key: &str) -> Option<String> {
        if self.sorted.is_empty() {
            return None;
        }
        if let Some(node) = self.assigned.get(key) {
            return Some(node.clone());
        }
        let cap = self.capacity();
        let start = self.first_clockwise(fnv1a_32(key));
        let n = self.sorted.len();
        for i in 0..n {
            let node = self.ring[&self.sorted[(start + i) % n]].clone();
            if *self.load.get(&node).unwrap_or(&0) < cap {
                self.assign(key, &node);
                return Some(node);
            }
        }
        let node = self.ring[&self.sorted[start % n]].clone();
        self.assign(key, &node);
        Some(node)
    }

    pub fn loads(&self) -> HashMap<String, usize> {
        self.load.clone()
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

    fn assign(&mut self, key: &str, node: &str) {
        self.assigned.insert(key.to_string(), node.to_string());
        *self.load.entry(node.to_string()).or_insert(0) += 1;
    }

    fn capacity(&self) -> usize {
        let total = self.assigned.len() + 1;
        ((1.0 + self.epsilon) * total as f64 / self.nodes.len() as f64).ceil() as usize
    }

    fn build_ring(&mut self, replicas: usize) {
        for node in &self.nodes {
            for i in 0..replicas {
                let mut slot = fnv1a_32(&format!("{node}#{i}"));
                while self.ring.contains_key(&slot) {
                    slot = slot.wrapping_add(1);
                }
                self.ring.insert(slot, node.clone());
            }
        }
        self.sorted = self.ring.keys().copied().collect();
        self.sorted.sort_unstable();
    }

    fn first_clockwise(&self, h: u32) -> usize {
        match self.sorted.partition_point(|&s| s <= h) {
            i if i == self.sorted.len() => 0,
            i => i,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn caps_hot_nodes() {
        let ns: Vec<String> = (0..5).map(|i| format!("node-{i}")).collect();
        let refs: Vec<&str> = ns.iter().map(|s| s.as_str()).collect();
        let mut b = BoundedLoad::new(&refs, 200, 0.25);
        for i in 0..5000 {
            b.get(&format!("key-{i}"));
        }
        let loads = b.loads();
        let total: usize = loads.values().sum();
        let peak = *loads.values().max().unwrap();
        let mean = total as f64 / ns.len() as f64;
        assert!(peak as f64 <= 1.25 * mean + 1.0, "peak {peak} exceeded cap");
    }

    #[test]
    fn idempotent_per_key() {
        let mut b = BoundedLoad::new(&["a", "b", "c"], 100, 0.5);
        let first = b.get("user-42");
        assert_eq!(first, b.get("user-42"));
    }
}
