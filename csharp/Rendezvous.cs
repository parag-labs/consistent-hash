namespace ConsistentHash;

/// <summary>
/// Highest-random-weight (rendezvous) placement: score every node for the key and
/// take the max. No ring to rebuild, weights are first-class, lookups are O(N).
/// </summary>
public sealed class Rendezvous
{
    private readonly Dictionary<string, int> _weights = new();

    public Rendezvous(IEnumerable<string>? nodes = null)
    {
        if (nodes is not null)
        {
            foreach (var n in nodes)
            {
                Add(n);
            }
        }
    }

    public void Add(string node, int weight = 1)
    {
        if (weight < 1)
        {
            throw new ArgumentOutOfRangeException(nameof(weight), "weight must be at least 1");
        }

        _weights[node] = weight;
    }

    public void Remove(string node) => _weights.Remove(node);

    public string? Get(string key)
    {
        if (_weights.Count == 0)
        {
            return null;
        }

        var weighted = IsWeighted();
        string? best = null;
        var bestScore = double.NegativeInfinity;
        foreach (var (node, weight) in _weights)
        {
            var s = Score(node, key, weight, weighted);
            if (s > bestScore || (s == bestScore && string.CompareOrdinal(node, best) > 0))
            {
                bestScore = s;
                best = node;
            }
        }

        return best;
    }

    public IReadOnlyList<string> GetReplicas(string key, int count)
    {
        if (_weights.Count == 0 || count <= 0)
        {
            return Array.Empty<string>();
        }

        var weighted = IsWeighted();
        return _weights
            .Select(kv => (node: kv.Key, score: Score(kv.Key, key, kv.Value, weighted)))
            .OrderByDescending(x => x.score)
            .ThenByDescending(x => x.node, StringComparer.Ordinal)
            .Take(Math.Min(count, _weights.Count))
            .Select(x => x.node)
            .ToList();
    }

    public IReadOnlyList<string> Nodes =>
        _weights.Keys.OrderBy(n => n, StringComparer.Ordinal).ToList();

    public int Count => _weights.Count;

    private bool IsWeighted() => _weights.Values.Any(w => w != 1);

    private static double Score(string node, string key, int weight, bool weighted)
    {
        var h = HashRing.Fnv1a64($"{node}#{key}");
        if (!weighted)
        {
            return h; // pure integer score - portable, what conformance pins
        }

        var normalized = ((double)h + 1) / ((double)ulong.MaxValue + 1);
        return -weight / Math.Log(normalized);
    }
}
