namespace ConsistentHash;

/// <summary>
/// Maglev lookup-table hashing (Google, 2016). A fixed prime-sized permutation table
/// is built once; each node claims slots in a deterministic interleaving. Lookups are
/// a single array index, and losing a node only rewrites its own slots.
/// </summary>
public sealed class Maglev
{
    private readonly int _m;
    private List<string> _nodes;
    private int[] _table = Array.Empty<int>();

    public Maglev(IEnumerable<string>? nodes = null, int tableSize = 65537)
    {
        if (!IsPrime(tableSize))
        {
            throw new ArgumentException("tableSize must be prime", nameof(tableSize));
        }

        _m = tableSize;
        _nodes = (nodes ?? Enumerable.Empty<string>())
            .Distinct()
            .OrderBy(n => n, StringComparer.Ordinal)
            .ToList();
        Build();
    }

    public void Add(string node)
    {
        if (!_nodes.Contains(node))
        {
            _nodes.Add(node);
            _nodes = _nodes.OrderBy(n => n, StringComparer.Ordinal).ToList();
            Build();
        }
    }

    public void Remove(string node)
    {
        if (_nodes.Remove(node))
        {
            Build();
        }
    }

    public string? Get(string key)
    {
        if (_nodes.Count == 0)
        {
            return null;
        }

        return _nodes[_table[HashRing.Fnv1a64(key) % (ulong)_m]];
    }

    public IReadOnlyList<string> Nodes => _nodes.ToList();

    public int Count => _nodes.Count;

    private void Build()
    {
        var n = _nodes.Count;
        if (n == 0)
        {
            _table = Array.Empty<int>();
            return;
        }

        var offset = new ulong[n];
        var skip = new ulong[n];
        for (var i = 0; i < n; i++)
        {
            offset[i] = HashRing.Fnv1a64($"{_nodes[i]}#offset") % (ulong)_m;
            skip[i] = (HashRing.Fnv1a64($"{_nodes[i]}#skip") % (ulong)(_m - 1)) + 1;
        }

        var table = new int[_m];
        Array.Fill(table, -1);
        var next = new ulong[n];
        var filled = 0;
        while (filled < _m)
        {
            for (var i = 0; i < n; i++)
            {
                var c = (offset[i] + (next[i] * skip[i])) % (ulong)_m;
                while (table[c] >= 0)
                {
                    next[i]++;
                    c = (offset[i] + (next[i] * skip[i])) % (ulong)_m;
                }

                table[c] = i;
                next[i]++;
                filled++;
                if (filled == _m)
                {
                    break;
                }
            }
        }

        _table = table;
    }

    private static bool IsPrime(int n)
    {
        if (n < 2)
        {
            return false;
        }

        if (n % 2 == 0)
        {
            return n == 2;
        }

        for (var i = 3; i * i <= n; i += 2)
        {
            if (n % i == 0)
            {
                return false;
            }
        }

        return true;
    }
}
