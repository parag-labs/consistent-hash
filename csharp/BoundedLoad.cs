namespace ConsistentHash;

/// <summary>
/// Consistent hashing with bounded loads (Google, 2017): keys are placed clockwise on
/// the ring, but no node may exceed ceil((1+epsilon)*keys/nodes). A full node overflows
/// to the next under cap, so no node exceeds its fair share by more than epsilon.
/// Placement depends on load, so it is stateful and order-sensitive.
/// </summary>
public sealed class BoundedLoad
{
    private readonly double _epsilon;
    private readonly List<string> _nodes;
    private readonly SortedDictionary<uint, string> _ring = new();
    private uint[] _sorted = Array.Empty<uint>();
    private readonly Dictionary<string, int> _load = new();
    private readonly Dictionary<string, string> _assigned = new();

    public BoundedLoad(IEnumerable<string>? nodes = null, int replicas = 100, double epsilon = 0.25)
    {
        if (epsilon < 0)
        {
            throw new ArgumentOutOfRangeException(nameof(epsilon), "epsilon must be non-negative");
        }

        _epsilon = epsilon;
        _nodes = (nodes ?? Enumerable.Empty<string>())
            .Distinct()
            .OrderBy(n => n, StringComparer.Ordinal)
            .ToList();
        BuildRing(replicas);
    }

    public string? Get(string key)
    {
        if (_sorted.Length == 0)
        {
            return null;
        }

        if (_assigned.TryGetValue(key, out var existing))
        {
            return existing;
        }

        var cap = Capacity();
        var start = FirstClockwise(HashRing.Fnv1a32(key));
        for (var i = 0; i < _sorted.Length; i++)
        {
            var node = _ring[_sorted[(start + i) % _sorted.Length]];
            if (_load.GetValueOrDefault(node, 0) < cap)
            {
                Assign(key, node);
                return node;
            }
        }

        var fallback = _ring[_sorted[start % _sorted.Length]];
        Assign(key, fallback);
        return fallback;
    }

    public IReadOnlyDictionary<string, int> Loads => new Dictionary<string, int>(_load);

    public IReadOnlyList<string> Nodes => _nodes.ToList();

    public int Count => _nodes.Count;

    private void Assign(string key, string node)
    {
        _assigned[key] = node;
        _load[node] = _load.GetValueOrDefault(node, 0) + 1;
    }

    private int Capacity()
    {
        var total = _assigned.Count + 1;
        return (int)Math.Ceiling((1 + _epsilon) * total / _nodes.Count);
    }

    private void BuildRing(int replicas)
    {
        foreach (var node in _nodes)
        {
            for (var r = 0; r < replicas; r++)
            {
                var slot = HashRing.Fnv1a32($"{node}#{r}");
                while (_ring.ContainsKey(slot))
                {
                    slot += 1;
                }

                _ring[slot] = node;
            }
        }

        _sorted = _ring.Keys.ToArray();
    }

    private int FirstClockwise(uint h)
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

        return lo == _sorted.Length ? 0 : lo;
    }
}
