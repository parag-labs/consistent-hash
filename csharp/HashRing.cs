namespace ConsistentHash;

/// <summary>
/// A consistent-hash ring with virtual nodes. Keys and nodes share one circular
/// hash space, so adding or removing a node only remaps the keys next to it rather
/// than the whole keyspace. Each physical node occupies many ring points so load
/// spreads evenly. The hash is FNV-1a (32-bit) to match the Python and Java ports.
/// </summary>
public sealed class HashRing
{
    private readonly int _replicas;
    private readonly SortedDictionary<uint, string> _ring = new();
    private readonly HashSet<string> _nodes = new();
    private uint[] _sorted = Array.Empty<uint>();

    public HashRing(IEnumerable<string>? nodes = null, int replicas = 100)
    {
        if (replicas < 1)
        {
            throw new ArgumentOutOfRangeException(nameof(replicas), "replicas must be at least 1");
        }

        _replicas = replicas;
        if (nodes is not null)
        {
            foreach (var node in nodes)
            {
                Add(node);
            }
        }
    }

    public static uint Fnv1a32(string data)
    {
        uint h = 0x811C9DC5;
        foreach (var b in System.Text.Encoding.UTF8.GetBytes(data))
        {
            h ^= b;
            h *= 0x01000193;
        }

        return h;
    }

    public IReadOnlyList<string> Nodes => _nodes.OrderBy(n => n, StringComparer.Ordinal).ToList();

    public int Count => _nodes.Count;

    public void Add(string node)
    {
        if (!_nodes.Add(node))
        {
            return;
        }

        for (var r = 0; r < _replicas; r++)
        {
            var slot = Fnv1a32($"{node}#{r}");
            while (_ring.ContainsKey(slot))
            {
                slot += 1; // deterministic nudge on collision
            }

            _ring[slot] = node;
        }

        Reindex();
    }

    public void Remove(string node)
    {
        if (!_nodes.Remove(node))
        {
            return;
        }

        foreach (var slot in _ring.Where(kv => kv.Value == node).Select(kv => kv.Key).ToList())
        {
            _ring.Remove(slot);
        }

        Reindex();
    }

    public string? Get(string key)
    {
        if (_sorted.Length == 0)
        {
            return null;
        }

        var idx = FirstClockwise(Fnv1a32(key));
        return _ring[_sorted[idx]];
    }

    public IReadOnlyList<string> GetReplicas(string key, int count)
    {
        var result = new List<string>();
        if (_sorted.Length == 0 || count <= 0)
        {
            return result;
        }

        var start = FirstClockwise(Fnv1a32(key));
        var cap = Math.Min(count, _nodes.Count);
        for (var i = 0; i < _sorted.Length; i++)
        {
            var node = _ring[_sorted[(start + i) % _sorted.Length]];
            if (!result.Contains(node))
            {
                result.Add(node);
                if (result.Count == cap)
                {
                    break;
                }
            }
        }

        return result;
    }

    private int FirstClockwise(uint h)
    {
        var idx = LowerBound(h);
        return idx == _sorted.Length ? 0 : idx; // wrap around
    }

    /// <summary>Index of the first ring slot strictly greater than <paramref name="h"/>.</summary>
    private int LowerBound(uint h)
    {
        int lo = 0, hi = _sorted.Length;
        while (lo < hi)
        {
            var mid = (lo + hi) / 2;
            if (_sorted[mid] <= h)
            {
                lo = mid + 1;
            }
            else
            {
                hi = mid;
            }
        }

        return lo;
    }

    private void Reindex()
    {
        _sorted = _ring.Keys.ToArray();
    }
}
