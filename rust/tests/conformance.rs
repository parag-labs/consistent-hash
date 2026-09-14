//! The Rust port must reproduce the committed golden vectors exactly.

use consistent_hash::{fnv1a_32, fnv1a_64, BoundedLoad, Jump, Maglev, Rendezvous, Ring};
use serde_json::Value;
use std::fs;
use std::path::Path;

fn load() -> Value {
    let path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("conformance")
        .join("vectors.json");
    let raw = fs::read_to_string(path).expect("read vectors.json");
    serde_json::from_str(&raw).expect("parse vectors.json")
}

fn hex(s: &str) -> u64 {
    u64::from_str_radix(s.trim_start_matches("0x"), 16).unwrap()
}

fn strs(v: &Value) -> Vec<&str> {
    v.as_array()
        .unwrap()
        .iter()
        .map(|x| x.as_str().unwrap())
        .collect()
}

#[test]
fn conformance_hash() {
    let v = load();
    for (probe, expected) in v["hash"]["fnv1a_32"].as_object().unwrap() {
        assert_eq!(
            fnv1a_32(probe) as u64,
            hex(expected.as_str().unwrap()),
            "fnv32 {probe}"
        );
    }
    for (probe, expected) in v["hash"]["fnv1a_64"].as_object().unwrap() {
        assert_eq!(
            fnv1a_64(probe),
            hex(expected.as_str().unwrap()),
            "fnv64 {probe}"
        );
    }
}

#[test]
fn conformance_ring() {
    let v = load();
    let spec = &v["ring"];
    let ring = Ring::new(
        &strs(&spec["nodes"]),
        spec["replicas"].as_u64().unwrap() as usize,
    );
    for (key, node) in spec["assignment"].as_object().unwrap() {
        assert_eq!(ring.get(key).unwrap(), node.as_str().unwrap(), "ring {key}");
    }
}

#[test]
fn conformance_rendezvous() {
    let v = load();
    let spec = &v["rendezvous"];
    let hrw = Rendezvous::new(&strs(&spec["nodes"]));
    for (key, node) in spec["assignment"].as_object().unwrap() {
        assert_eq!(hrw.get(key).unwrap(), node.as_str().unwrap(), "hrw {key}");
    }
}

#[test]
fn conformance_jump() {
    let v = load();
    let spec = &v["jump"];
    let jump = Jump::new(&strs(&spec["nodes"]));
    for (key, node) in spec["assignment"].as_object().unwrap() {
        assert_eq!(jump.get(key).unwrap(), node.as_str().unwrap(), "jump {key}");
    }
}

#[test]
fn conformance_maglev() {
    let v = load();
    let spec = &v["maglev"];
    let maglev = Maglev::new(
        &strs(&spec["nodes"]),
        spec["table_size"].as_u64().unwrap() as usize,
    );
    for (key, node) in spec["assignment"].as_object().unwrap() {
        assert_eq!(
            maglev.get(key).unwrap(),
            node.as_str().unwrap(),
            "maglev {key}"
        );
    }
}

#[test]
fn conformance_bounded_load() {
    let v = load();
    let spec = &v["bounded_load"];
    let eps = spec["epsilon_num"].as_f64().unwrap() / spec["epsilon_den"].as_f64().unwrap();
    let mut b = BoundedLoad::new(
        &strs(&spec["nodes"]),
        spec["replicas"].as_u64().unwrap() as usize,
        eps,
    );
    for key in strs(&spec["keys_in_order"]) {
        let want = spec["assignment"][key].as_str().unwrap();
        assert_eq!(b.get(key).unwrap(), want, "bounded {key}");
    }
}
