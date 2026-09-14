using Xunit;

namespace ConsistentHash.Tests;

public class StrategyTests
{
    [Fact]
    public void Fnv64_MatchesKnownVectors()
    {
        Assert.Equal(0xCBF29CE484222325, HashRing.Fnv1a64(""));
        Assert.Equal(0x85944171F73967E8, HashRing.Fnv1a64("foobar"));
    }

    [Fact]
    public void Jump_IsStableAndInRange()
    {
        for (ulong k = 0; k < 1000; k++)
        {
            var b = Jump.JumpConsistentHash(k, 17);
            Assert.InRange(b, 0, 16);
            Assert.Equal(b, Jump.JumpConsistentHash(k, 17));
        }
    }

    [Fact]
    public void Rendezvous_RemovalMovesOnlyThatNodesKeys()
    {
        var keys = Enumerable.Range(0, 5000).Select(i => $"key-{i}").ToList();
        var hrw = new Rendezvous(new[] { "a", "b", "c", "d" });
        var before = keys.ToDictionary(k => k, k => hrw.Get(k));
        hrw.Remove("d");
        foreach (var k in keys)
        {
            if (before[k] != "d")
            {
                Assert.Equal(before[k], hrw.Get(k));
            }
        }
    }

    [Fact]
    public void Rendezvous_WeightBiasesLoad()
    {
        var hrw = new Rendezvous();
        hrw.Add("small", 1);
        hrw.Add("big", 4);
        var big = Enumerable.Range(0, 8000).Count(i => hrw.Get($"key-{i}") == "big");
        Assert.True(big > 4000, $"weight had no effect: big={big}");
    }

    [Fact]
    public void Maglev_CoversAndBalances()
    {
        var mag = new Maglev(new[] { "a", "b", "c", "d" }, 1019);
        var counts = new Dictionary<string, int>();
        for (var i = 0; i < 8000; i++)
        {
            var node = mag.Get($"key-{i}")!;
            counts[node] = counts.GetValueOrDefault(node, 0) + 1;
        }

        Assert.Equal(4, counts.Count);
        Assert.True(counts.Values.Max() - counts.Values.Min() < 400);
    }

    [Fact]
    public void BoundedLoad_CapsHotNodes()
    {
        var nodes = Enumerable.Range(0, 5).Select(i => $"node-{i}").ToArray();
        var bl = new BoundedLoad(nodes, replicas: 200, epsilon: 0.25);
        for (var i = 0; i < 5000; i++)
        {
            bl.Get($"key-{i}");
        }

        var loads = bl.Loads;
        var mean = (double)loads.Values.Sum() / nodes.Length;
        Assert.True(loads.Values.Max() <= (1.25 * mean) + 1);
    }
}
