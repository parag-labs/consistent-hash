using System.Globalization;
using System.Text.Json;
using Xunit;

namespace ConsistentHash.Tests;

/// <summary>The C# port must reproduce the committed golden vectors exactly.</summary>
public class ConformanceTests
{
    private static readonly JsonElement Vectors = LoadVectors();

    private static JsonElement LoadVectors()
    {
        // Walk up from the test bin directory to the repo root, then into conformance/.
        var dir = AppContext.BaseDirectory;
        while (dir is not null && !File.Exists(Path.Combine(dir, "conformance", "vectors.json")))
        {
            dir = Directory.GetParent(dir)?.FullName;
        }

        if (dir is null)
        {
            throw new FileNotFoundException("could not locate conformance/vectors.json");
        }

        var raw = File.ReadAllText(Path.Combine(dir, "conformance", "vectors.json"));
        return JsonDocument.Parse(raw).RootElement.Clone();
    }

    private static ulong Hex(string s) =>
        ulong.Parse(s.AsSpan(2), NumberStyles.HexNumber, CultureInfo.InvariantCulture);

    private static string[] Nodes(JsonElement spec) =>
        spec.GetProperty("nodes").EnumerateArray().Select(e => e.GetString()!).ToArray();

    [Fact]
    public void Hash_Matches()
    {
        foreach (var p in Vectors.GetProperty("hash").GetProperty("fnv1a_32").EnumerateObject())
        {
            Assert.Equal(Hex(p.Value.GetString()!), HashRing.Fnv1a32(p.Name));
        }

        foreach (var p in Vectors.GetProperty("hash").GetProperty("fnv1a_64").EnumerateObject())
        {
            Assert.Equal(Hex(p.Value.GetString()!), HashRing.Fnv1a64(p.Name));
        }
    }

    [Fact]
    public void Ring_Matches()
    {
        var spec = Vectors.GetProperty("ring");
        var ring = new HashRing(Nodes(spec), spec.GetProperty("replicas").GetInt32());
        foreach (var kv in spec.GetProperty("assignment").EnumerateObject())
        {
            Assert.Equal(kv.Value.GetString(), ring.Get(kv.Name));
        }
    }

    [Fact]
    public void Rendezvous_Matches()
    {
        var spec = Vectors.GetProperty("rendezvous");
        var hrw = new Rendezvous(Nodes(spec));
        foreach (var kv in spec.GetProperty("assignment").EnumerateObject())
        {
            Assert.Equal(kv.Value.GetString(), hrw.Get(kv.Name));
        }
    }

    [Fact]
    public void Jump_Matches()
    {
        var spec = Vectors.GetProperty("jump");
        var jump = new Jump(Nodes(spec));
        foreach (var kv in spec.GetProperty("assignment").EnumerateObject())
        {
            Assert.Equal(kv.Value.GetString(), jump.Get(kv.Name));
        }
    }

    [Fact]
    public void Maglev_Matches()
    {
        var spec = Vectors.GetProperty("maglev");
        var maglev = new Maglev(Nodes(spec), spec.GetProperty("table_size").GetInt32());
        foreach (var kv in spec.GetProperty("assignment").EnumerateObject())
        {
            Assert.Equal(kv.Value.GetString(), maglev.Get(kv.Name));
        }
    }

    [Fact]
    public void BoundedLoad_Matches()
    {
        var spec = Vectors.GetProperty("bounded_load");
        var epsilon = (double)spec.GetProperty("epsilon_num").GetInt32()
            / spec.GetProperty("epsilon_den").GetInt32();
        var bounded = new BoundedLoad(Nodes(spec), spec.GetProperty("replicas").GetInt32(), epsilon);
        var assignment = spec.GetProperty("assignment");
        foreach (var keyElem in spec.GetProperty("keys_in_order").EnumerateArray())
        {
            var key = keyElem.GetString()!;
            Assert.Equal(assignment.GetProperty(key).GetString(), bounded.Get(key));
        }
    }
}
