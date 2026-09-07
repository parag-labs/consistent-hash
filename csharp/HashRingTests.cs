using Xunit;

namespace ConsistentHash.Tests;

public class HashRingTests
{
    [Fact]
    public void EmptyRingReturnsNull()
    {
        Assert.Null(new HashRing().Get("anything"));
    }

    [Fact]
    public void LookupIsStable()
    {
        var ring = new HashRing(new[] { "a", "b", "c" });
        Assert.Equal(ring.Get("user-42"), ring.Get("user-42"));
    }

    [Fact]
    public void EveryKeyMapsToARealNode()
    {
        var ring = new HashRing(new[] { "a", "b", "c" });
        for (var i = 0; i < 500; i++)
        {
            Assert.Contains(ring.Get($"k{i}"), new[] { "a", "b", "c" });
        }
    }

    [Fact]
    public void Fnv1aMatchesKnownVectors()
    {
        Assert.Equal(0x811C9DC5u, HashRing.Fnv1a32(""));
        Assert.Equal(0xE40C292Cu, HashRing.Fnv1a32("a"));
        Assert.Equal(0xBF9CF968u, HashRing.Fnv1a32("foobar"));
    }

    [Fact]
    public void DistributionIsReasonablyEven()
    {
        var ring = new HashRing(new[] { "a", "b", "c", "d" }, replicas: 400);
        var counts = new Dictionary<string, int>();
        for (var i = 0; i < 8000; i++)
        {
            var node = ring.Get($"key-{i}")!;
            counts[node] = counts.GetValueOrDefault(node) + 1;
        }

        foreach (var node in new[] { "a", "b", "c", "d" })
        {
            Assert.InRange(counts[node], 1300, 2700);
        }
    }

    [Fact]
    public void AddingANodeRemapsOnlyASmallFraction()
    {
        var keys = Enumerable.Range(0, 5000).Select(i => $"key-{i}").ToList();
        var ring = new HashRing(new[] { "a", "b", "c" }, replicas: 200);
        var before = keys.ToDictionary(k => k, k => ring.Get(k));

        ring.Add("d");
        var moved = keys.Count(k => before[k] != ring.Get(k));
        Assert.True(moved / (double)keys.Count < 0.40);
        foreach (var k in keys)
        {
            if (before[k] != ring.Get(k))
            {
                Assert.Equal("d", ring.Get(k));
            }
        }
    }

    [Fact]
    public void RemovingANodeOnlyMovesItsKeys()
    {
        var keys = Enumerable.Range(0, 5000).Select(i => $"key-{i}").ToList();
        var ring = new HashRing(new[] { "a", "b", "c", "d" }, replicas: 200);
        var before = keys.ToDictionary(k => k, k => ring.Get(k));

        ring.Remove("d");
        foreach (var k in keys)
        {
            if (before[k] != "d")
            {
                Assert.Equal(before[k], ring.Get(k));
            }
            else
            {
                Assert.Contains(ring.Get(k), new[] { "a", "b", "c" });
            }
        }
    }

    [Fact]
    public void GetReplicasReturnsDistinctNodes()
    {
        var ring = new HashRing(new[] { "a", "b", "c", "d", "e" });
        var reps = ring.GetReplicas("some-key", 3);
        Assert.Equal(3, reps.Count);
        Assert.Equal(3, reps.Distinct().Count());
    }

    [Fact]
    public void GetReplicasCapsAtNodeCount()
    {
        var ring = new HashRing(new[] { "a", "b" }, replicas: 50);
        Assert.Equal(2, ring.GetReplicas("k", 5).Count);
    }

    [Fact]
    public void IdempotentAddAndRemove()
    {
        var ring = new HashRing(replicas: 10);
        ring.Add("a");
        ring.Add("a");
        Assert.Equal(new[] { "a" }, ring.Nodes);
        ring.Remove("ghost");
        Assert.Equal(new[] { "a" }, ring.Nodes);
    }
}
