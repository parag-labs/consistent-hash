using Xunit;

namespace ConsistentHash.Tests;

// Stress suite: a rebalance storm. Hammer the ring with hundreds of random
// add/remove operations and assert the two properties that must never break -
// ownership never dangles after a removal, and a single membership change moves
// only a small, bounded fraction of keys (the whole point of consistent hashing).
public class HashRingStressTests
{
    [Fact]
    public void OwnershipNeverDanglesUnderChurn()
    {
        var rng = new Random(2024);
        var keys = Enumerable.Range(0, 3000).Select(i => $"key-{i}").ToList();
        var ring = new HashRing(Enumerable.Range(0, 8).Select(i => $"node-{i}"), replicas: 150);

        for (var round = 0; round < 300; round++)
        {
            var live = ring.Nodes.ToHashSet();
            if (rng.NextDouble() < 0.5 || live.Count <= 1)
            {
                ring.Add($"node-{rng.Next(0, 41)}");
            }
            else
            {
                ring.Remove(live.ElementAt(rng.Next(live.Count)));
            }

            var now = ring.Nodes.ToHashSet();
            // Spot-check a sample each round; every key must land on a live node.
            for (var s = 0; s < 200; s++)
            {
                var key = keys[rng.Next(keys.Count)];
                Assert.Contains(ring.Get(key)!, now);
            }
        }
    }

    [Fact]
    public void SingleChangeMovesBoundedFractionAcrossManyRounds()
    {
        var rng = new Random(99);
        var keys = Enumerable.Range(0, 5000).Select(i => $"key-{i}").ToList();
        var ring = new HashRing(Enumerable.Range(0, 10).Select(i => $"node-{i}"), replicas: 200);

        var worst = 0.0;
        for (var round = 0; round < 60; round++)
        {
            var before = keys.ToDictionary(k => k, k => ring.Get(k));
            if (rng.NextDouble() < 0.5 || ring.Count <= 1)
            {
                ring.Add($"node-{rng.Next(0, 61)}");
            }
            else
            {
                ring.Remove(ring.Nodes[rng.Next(ring.Count)]);
            }

            var moved = keys.Count(k => before[k] != ring.Get(k));
            var frac = moved / (double)keys.Count;
            worst = Math.Max(worst, frac);
            // A single change on a cluster this size never moves near half the keys;
            // modulo hashing would move almost all of them.
            Assert.True(frac < 0.35, $"a single change moved {frac:P0} of keys");
        }

        Assert.True(worst < 0.35);
    }

    [Fact]
    public void RingRecoversToEmptyAndBack()
    {
        var ring = new HashRing(replicas: 50);
        Assert.Null(ring.Get("k"));
        for (var i = 0; i < 20; i++)
        {
            ring.Add($"n{i}");
        }

        Assert.Contains(ring.Get("k")!, ring.Nodes.ToHashSet());
        foreach (var n in ring.Nodes.ToList())
        {
            ring.Remove(n);
        }

        Assert.Null(ring.Get("k"));
        Assert.Equal(0, ring.Count);
    }
}
