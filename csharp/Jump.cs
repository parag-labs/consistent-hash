namespace ConsistentHash;

/// <summary>
/// Jump consistent hash (Lamping &amp; Veach, 2014) over an ordered bucket list. No
/// per-node state, O(ln N) lookups. Buckets are an ordered range, so it stays
/// consistent when nodes are appended or removed at the tail.
/// </summary>
public sealed class Jump
{
    private readonly List<string> _nodes;

    public Jump(IEnumerable<string>? nodes = null)
    {
        _nodes = nodes is null ? new List<string>() : new List<string>(nodes);
    }

    public void Add(string node)
    {
        if (!_nodes.Contains(node))
        {
            _nodes.Add(node);
        }
    }

    public void Remove(string node) => _nodes.Remove(node);

    public string? Get(string key)
    {
        if (_nodes.Count == 0)
        {
            return null;
        }

        return _nodes[JumpConsistentHash(HashRing.Fnv1a64(key), _nodes.Count)];
    }

    public IReadOnlyList<string> Nodes => _nodes.ToList();

    public int Count => _nodes.Count;

    /// <summary>Maps <paramref name="key"/> to a bucket in [0, numBuckets) with O(1) memory.</summary>
    public static int JumpConsistentHash(ulong key, int numBuckets)
    {
        if (numBuckets < 1)
        {
            throw new ArgumentOutOfRangeException(nameof(numBuckets), "numBuckets must be at least 1");
        }

        long b = -1, j = 0;
        while (j < numBuckets)
        {
            b = j;
            key = (key * 2862933555777941757UL) + 1UL;
            j = (long)((b + 1) * ((double)(1L << 31) / ((key >> 33) + 1)));
        }

        return (int)b;
    }
}
