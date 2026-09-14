use crate::{fnv1a_64, is_prime};

/// Maglev lookup-table hashing (Google, 2016). A fixed prime-sized permutation table
/// is built once; each node claims slots in a deterministic interleaving. Lookups are
/// a single array index, and losing a node only rewrites its own slots.
pub struct Maglev {
    m: usize,
    nodes: Vec<String>,
    table: Vec<i64>,
}

impl Maglev {
    pub fn new(nodes: &[&str], table_size: usize) -> Self {
        assert!(is_prime(table_size), "table_size must be prime");
        let mut sorted: Vec<String> = nodes.iter().map(|n| n.to_string()).collect();
        sorted.sort();
        sorted.dedup();
        let mut m = Maglev {
            m: table_size,
            nodes: sorted,
            table: Vec::new(),
        };
        m.build();
        m
    }

    pub fn add(&mut self, node: &str) {
        if !self.nodes.iter().any(|n| n == node) {
            self.nodes.push(node.to_string());
            self.nodes.sort();
            self.build();
        }
    }

    pub fn remove(&mut self, node: &str) {
        if let Some(i) = self.nodes.iter().position(|n| n == node) {
            self.nodes.remove(i);
            self.build();
        }
    }

    pub fn get(&self, key: &str) -> Option<&str> {
        if self.nodes.is_empty() {
            return None;
        }
        let slot = (fnv1a_64(key) % self.m as u64) as usize;
        Some(self.nodes[self.table[slot] as usize].as_str())
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

    fn build(&mut self) {
        let n = self.nodes.len();
        if n == 0 {
            self.table = Vec::new();
            return;
        }
        let mut offset = vec![0u64; n];
        let mut skip = vec![0u64; n];
        for (i, name) in self.nodes.iter().enumerate() {
            offset[i] = fnv1a_64(&format!("{name}#offset")) % self.m as u64;
            skip[i] = fnv1a_64(&format!("{name}#skip")) % (self.m as u64 - 1) + 1;
        }
        let mut table = vec![-1i64; self.m];
        let mut next = vec![0u64; n];
        let mut filled = 0;
        while filled < self.m {
            for i in 0..n {
                let mut c = ((offset[i] + next[i] * skip[i]) % self.m as u64) as usize;
                while table[c] >= 0 {
                    next[i] += 1;
                    c = ((offset[i] + next[i] * skip[i]) % self.m as u64) as usize;
                }
                table[c] = i as i64;
                next[i] += 1;
                filled += 1;
                if filled == self.m {
                    break;
                }
            }
        }
        self.table = table;
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;

    #[test]
    fn covers_and_balances() {
        let m = Maglev::new(&["a", "b", "c", "d"], 1019);
        let mut counts: HashMap<String, i32> = HashMap::new();
        for i in 0..8000 {
            *counts
                .entry(m.get(&format!("key-{i}")).unwrap().to_string())
                .or_default() += 1;
        }
        assert_eq!(counts.len(), 4);
        let max = counts.values().max().unwrap();
        let min = counts.values().min().unwrap();
        assert!(max - min < 400, "spread too wide: {min}..{max}");
    }

    #[test]
    fn removal_is_minimal() {
        let keys: Vec<String> = (0..8000).map(|i| format!("key-{i}")).collect();
        let mut m = Maglev::new(&["a", "b", "c", "d"], 1019);
        let before: Vec<String> = keys.iter().map(|k| m.get(k).unwrap().to_string()).collect();
        m.remove("d");
        let moved = keys
            .iter()
            .enumerate()
            .filter(|(i, k)| m.get(k).unwrap() != before[*i])
            .count();
        assert!((moved as f64) / (keys.len() as f64) < 0.35);
    }
}
