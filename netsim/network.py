"""Switches, network graph, routing (our mini Subnet Manager) and a leaf-spine topology."""

from collections import deque

from netsim.engine import Simulator
from netsim.link import Host, Link, Packet


class Switch:
    """Store-and-forward switch: looks up the destination in its table and forwards."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.ports: dict[
            str, Link
        ] = {}  # neighbor name -> outgoing link to that neighbor
        self.table: dict[
            str, str
        ] = {}  # destination host -> neighbor to send it to (next hop)

    def receive(self, packet: Packet) -> None:
        next_hop = self.table[packet.dst]
        self.ports[next_hop].send(packet)


class Network:
    def __init__(
        self, sim: Simulator, bandwidth_gbps: int = 100, latency_ns: int = 1000
    ) -> None:
        self.sim = sim
        self.bandwidth_gbps = bandwidth_gbps
        self.latency_ns = latency_ns
        self.hosts: dict[str, Host] = {}
        self.switches: dict[str, Switch] = {}
        self.links: dict[tuple[str, str], Link] = {}  # (from, to) -> one-way link
        self.graph: dict[str, list[str]] = {}  # node -> neighbors (adjacency list)

    def add_host(self, name: str) -> None:
        self.hosts[name] = Host(self.sim, name)
        self.graph[name] = []

    def add_switch(self, name: str) -> None:
        self.switches[name] = Switch(name)
        self.graph[name] = []

    def node(self, name: str) -> Host | Switch:
        return self.hosts.get(name) or self.switches[name]

    def connect(self, a: str, b: str) -> None:
        """One cable = two one-way links (a->b and b->a)."""
        for src, dst in ((a, b), (b, a)):
            link = Link(self.sim, self.bandwidth_gbps, self.latency_ns, self.node(dst))
            self.links[(src, dst)] = link
            self.graph[src].append(dst)
            if src in self.switches:
                self.switches[src].ports[dst] = link

    def send(self, packet: Packet) -> None:
        """A host sends on its only cable (to its leaf switch)."""
        leaf = self.graph[packet.src][0]
        self.links[(packet.src, leaf)].send(packet)

    def compute_routes(self) -> None:
        """Mini Subnet Manager: fill every switch's table with a shortest-path next hop.

        Trick: run ONE BFS starting FROM each destination host. When the BFS reaches a
        switch s coming from neighbor p, then p is one step closer to the destination,
        so p is the next hop from s toward that destination.
        """
        for dst in self.hosts:
            queue = deque([dst])
            visited = {dst}
            while queue:
                cur = queue.popleft()
                for elem in self.graph[cur]:
                    if elem in visited:
                        continue
                    visited.add(elem)
                    if elem in self.switches:
                        self.switches[elem].table[dst] = cur
                        queue.append(elem)


def build_leaf_spine(
    sim: Simulator,
    n_leaves: int,
    n_spines: int,
    hosts_per_leaf: int,
    bandwidth_gbps: int = 100,
    latency_ns: int = 1000,
) -> Network:
    """Names: spines S0.., leaves L0.., hosts H0.. (H0..H{k-1} under L0, and so on)."""
    net = Network(sim, bandwidth_gbps, latency_ns)
    for s in range(n_spines):
        net.add_switch(f"S{s}")
    h = 0
    for l in range(n_leaves):
        net.add_switch(f"L{l}")
        for s in range(n_spines):
            net.connect(f"L{l}", f"S{s}")
        for _ in range(hosts_per_leaf):
            net.add_host(f"H{h}")
            net.connect(f"H{h}", f"L{l}")
            h += 1
    net.compute_routes()
    return net
