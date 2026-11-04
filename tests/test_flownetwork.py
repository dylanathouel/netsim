from netsim.engine import Simulator
from netsim.link import Packet
from netsim.network import build_leaf_spine

BUFFER = 4


def incast(lossless: bool, n: int = 10):
    """H1..H7 each send n packets to H0 at t=0. Returns (net, number of packets sent)."""
    sim = Simulator()
    net = build_leaf_spine(sim, 4, 2, 2, buffer_size=BUFFER, lossless=lossless)
    pid = 0
    for src in net.hosts:
        if src == "H0":
            continue
        for _ in range(n):
            net.send(Packet(pid, src, "H0", 4096, 0))
            pid += 1
    sim.run()
    return net, pid


def stream_intervals(buffer_size: int, n: int = 20) -> list[int]:
    """H0 sends n packets to H7; returns the time gaps between consecutive arrivals."""
    sim = Simulator()
    net = build_leaf_spine(sim, 4, 2, 2, buffer_size=buffer_size)
    for i in range(n):
        net.send(Packet(i, "H0", "H7", 4096, 0))
    sim.run()
    times = [t for _, t in net.hosts["H7"].received]
    return [b - a for a, b in zip(times, times[1:])]


def test_lossless_incast_delivers_everything():
    net, sent = incast(lossless=True)
    assert len(net.hosts["H0"].received) == sent
    assert net.total_dropped() == 0
    assert all(s.max_occupancy <= BUFFER for s in net.switches.values())
    assert all(not link.queue for link in net.links.values())


def test_lossy_incast_drops_but_conserves_packets():
    net, sent = incast(lossless=False)
    received = len(net.hosts["H0"].received)
    dropped = net.total_dropped()
    assert dropped > 0
    assert received + dropped == sent


def test_buffer_of_1_limits_throughput():
    # credit round trip: 328 (tx) + 1000 (packet travels) + 1000 (credit travels back)
    assert stream_intervals(1) == [2328] * 19


def test_buffer_at_bandwidth_delay_product_keeps_full_rate():
    # 8 slots >= 2328 / 328 = 7.1 -> the link never waits for a credit
    assert stream_intervals(8) == [328] * 19
