"""Latency and throughput measurements, computed from what the hosts actually received."""

from netsim.network import Network


def latencies(net: Network) -> list[int]:
    """One-way latency (ns) of every delivered packet: arrival time - creation time."""
    return [
        arrival - packet.created_at
        for host in net.hosts.values()
        for packet, arrival in host.received
    ]


def percentile(values: list[int], p: float) -> int:
    """Nearest-rank percentile (p in 0..100) -- no numpy needed."""
    ordered = sorted(values)
    rank = max(1, round(p / 100 * len(ordered)))
    return ordered[rank - 1]


def summary(net: Network) -> dict[str, float]:
    lat = latencies(net)
    delivered_bytes = sum(p.size for h in net.hosts.values() for p, _ in h.received)
    end = net.sim.now
    return {
        "delivered": len(lat),
        "dropped": net.total_dropped(),
        "latency_avg_ns": sum(lat) / len(lat),
        "latency_p99_ns": percentile(lat, 99),
        "latency_max_ns": max(lat),
        "throughput_gbps": delivered_bytes * 8 / end if end else 0.0,  # bits/ns = Gb/s
    }
