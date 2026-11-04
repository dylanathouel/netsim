"""Random but reproducible traffic: the same seed always gives the same scenario."""

import random

from netsim.link import Packet
from netsim.network import Network

SIZES = [256, 1024, 2048, 4096]  # bytes


def random_traffic(
    net: Network, n_packets: int, seed: int, duration_ns: int = 5_000
) -> int:
    """Schedule n_packets random sends (random src, dst, size and start time). Returns n_packets."""
    rng = random.Random(seed)  # our own generator: never the global `random`
    hosts = sorted(net.hosts)  # sorted -> same order on every machine
    for pid in range(n_packets):
        src, dst = rng.sample(hosts, 2)  # two DIFFERENT hosts
        size = rng.choice(SIZES)
        start = rng.randrange(duration_ns)
        packet = Packet(pid, src, dst, size, created_at=start)
        net.sim.schedule(start, net.send, packet)
    return n_packets
