"""Randomized verification: many reproducible scenarios, each checked against invariants."""

import pytest

from netsim.engine import Simulator
from netsim.metrics import latencies, summary
from netsim.network import build_leaf_spine
from netsim.traffic import random_traffic

SEEDS = range(50)
BUFFER = 4


def run(seed: int, lossless: bool = True, n_packets: int = 300):
    sim = Simulator()
    net = build_leaf_spine(sim, 4, 2, 2, buffer_size=BUFFER, lossless=lossless)
    sent = random_traffic(net, n_packets, seed)
    sim.run()
    return net, sent


def min_latency(net, packet) -> int:
    """Physical lower bound: path length x (serialization + propagation), with zero queuing."""
    same_leaf = net.graph[packet.src][0] == net.graph[packet.dst][0]
    hops = 2 if same_leaf else 4
    link = next(iter(net.links.values()))
    return hops * (link.tx_time(packet.size) + link.latency_ns)


@pytest.mark.parametrize("seed", SEEDS)
def test_lossless_invariants(seed):
    net, sent = run(seed)
    delivered = sum(len(h.received) for h in net.hosts.values())
    assert delivered == sent  # nothing lost
    assert net.total_dropped() == 0
    assert all(
        s.max_occupancy <= BUFFER for s in net.switches.values()
    )  # buffers respected
    assert all(not link.queue for link in net.links.values())  # nothing stuck
    for name, host in net.hosts.items():
        for packet, arrival in host.received:
            assert packet.dst == name  # right host
            assert arrival - packet.created_at >= min_latency(
                net, packet
            )  # physics respected


@pytest.mark.parametrize("seed", SEEDS)
def test_lossy_conservation(seed):
    net, sent = run(seed, lossless=False)
    delivered = sum(len(h.received) for h in net.hosts.values())
    assert net.total_dropped() > 0  # the scenario really is congested
    assert delivered + net.total_dropped() == sent  # every packet accounted for


def test_same_seed_same_result():
    a, _ = run(seed=7)
    b, _ = run(seed=7)
    assert latencies(a) == latencies(b)


def test_different_seeds_give_different_scenarios():
    a, _ = run(seed=1)
    b, _ = run(seed=2)
    assert latencies(a) != latencies(b)


def test_summary_is_consistent():
    net, sent = run(seed=0)
    s = summary(net)
    assert s["delivered"] == sent
    assert s["latency_avg_ns"] <= s["latency_p99_ns"] <= s["latency_max_ns"]
