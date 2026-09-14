use crate::fnv1a_64;
use std::collections::HashMap;

/// Highest-random-weight (rendezvous) placement: score every node for the key and
/// take the max. No ring to rebuild, weights are first-class, lookups are O(N).
pub struct Rendezvous {
    weights: HashMap<String, u32>,
}

impl Rendezvous {
    pub fn new(nodes: &[&str]) -> Self {
        let mut h = Rendezvous {
            weights: HashMap::new(),
        };
        for n in nodes {
            h.add(n, 1);
        }
        h
    }

    pub fn add(&mut self, node: &str, weight: u32) {
        assert!(weight >= 1, "weight must be at least 1");
        self.weights.insert(node.to_string(), weight);
    }

    pub fn remove(&mut self, node: &str) {
        self.weights.remove(node);
    }

    pub fn get(&self, key: &str) -> Option<&str> {
        if self.weights.is_empty() {
            return None;
        }
        let weighted = self.is_weighted();
        let mut best: Option<&str> = None;
        let mut best_score = f64::NEG_INFINITY;
        for (node, &w) in &self.weights {
            let s = self.score(node, key, w, weighted);
            if s > best_score || (s == best_score && Some(node.as_str()) > best) {
                best_score = s;
                best = Some(node.as_str());
            }
        }
        best
    }

    pub fn get_replicas(&self, key: &str, count: usize) -> Vec<String> {
        if self.weights.is_empty() || count == 0 {
            return Vec::new();
        }
        let weighted = self.is_weighted();
        let mut ranked: Vec<(&String, f64)> = self
            .weights
            .iter()
            .map(|(n, &w)| (n, self.score(n, key, w, weighted)))
            .collect();
        ranked.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap().then_with(|| b.0.cmp(a.0)));
        ranked
            .into_iter()
            .take(count.min(self.weights.len()))
            .map(|(n, _)| n.clone())
            .collect()
    }

    pub fn nodes(&self) -> Vec<String> {
        let mut out: Vec<String> = self.weights.keys().cloned().collect();
        out.sort();
        out
    }

    pub fn len(&self) -> usize {
        self.weights.len()
    }

    pub fn is_empty(&self) -> bool {
        self.weights.is_empty()
    }

    fn is_weighted(&self) -> bool {
        self.weights.values().any(|&w| w != 1)
    }

    fn score(&self, node: &str, key: &str, weight: u32, weighted: bool) -> f64 {
        let h = fnv1a_64(&format!("{node}#{key}"));
        if !weighted {
            return h as f64; // pure integer score - portable, what conformance pins
        }
        let normalized = (h as f64 + 1.0) / (u64::MAX as f64 + 1.0);
        -(weight as f64) / normalized.ln()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn removal_only_moves_that_nodes_keys() {
        let keys: Vec<String> = (0..5000).map(|i| format!("key-{i}")).collect();
        let mut h = Rendezvous::new(&["a", "b", "c", "d"]);
        let before: Vec<String> = keys.iter().map(|k| h.get(k).unwrap().to_string()).collect();
        h.remove("d");
        for (i, k) in keys.iter().enumerate() {
            let after = h.get(k).unwrap();
            if before[i] != "d" {
                assert_eq!(after, before[i]);
            }
        }
    }

    #[test]
    fn weight_biases_load() {
        let mut h = Rendezvous::new(&[]);
        h.add("small", 1);
        h.add("big", 4);
        let mut big = 0;
        for i in 0..8000 {
            if h.get(&format!("key-{i}")) == Some("big") {
                big += 1;
            }
        }
        assert!(big > 4000, "weight had no effect: big={big}");
    }
}
