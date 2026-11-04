"""Switches, network graph, routing (our mini Subnet Manager) and a leaf-spine topology."""

from collections import defaultdict, deque

from netsim.engine import Simulator
from netsim.link import Host, Link, Packet


class Switch:
    """Store-and-forward switch with one input buffer per incoming link."""

    def __init__(
        self,
        sim: Simulator,
        name: str,
        buffer_size: int | None = None,
        lossless: bool = True,
    ) -> None:
        self.sim = sim
        self.name = name
        self.ports: dict[str, Link] = {}
        self.table: dict[str, str] = {}
        self.buffer_size = buffer_size
        self.lossless = lossless
        self.occupancy: dict[Link, int] = defaultdict(int)
        self.max_occupancy = 0
        self.dropped = 0

    def receive(self, packet: Packet, link: Link) -> None:
        """`link` is the incoming link: each one has its own input buffer."""
        if self.buffer_size is not None and self.occupancy[link] >= self.buffer_size:
            if self.lossless:
                raise RuntimeError("error")
            self.dropped += 1
            return
        self.occupancy[link] += 1
        self.max_occupancy = max(self.max_occupancy, self.occupancy[link])
        next_hop = self.table[packet.dst]
        self.ports[next_hop].send(packet, on_depart=lambda: self._free_slot(link))

    def _free_slot(self, link: Link) -> None:
        """The packet left our buffer: free its slot and give the credit back upstream."""
        self.occupancy[link] -= 1
        if link.credits is not None:
            self.sim.schedule(link.latency_ns, link.return_credit)


class Network:
    def __init__(
        self,
        sim: Simulator,
        bandwidth_gbps: int = 100,
        latency_ns: int = 1000,
        buffer_size: int | None = None,
        lossless: bool = True,
    ) -> None:
        self.sim = sim
        self.buffer_size = buffer_size
        self.lossless = lossless
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
        self.switches[name] = Switch(self.sim, name, self.buffer_size, self.lossless)
        self.graph[name] = []

    def node(self, name: str) -> Host | Switch:
        return self.hosts.get(name) or self.switches[name]

    def connect(self, a: str, b: str) -> None:
        """One cable = two one-way links (a->b and b->a)."""
        for src, dst in ((a, b), (b, a)):
            credits = None
            if dst in self.switches and self.lossless and self.buffer_size is not None:
                credits = self.buffer_size
            link = Link(
                self.sim, self.bandwidth_gbps, self.latency_ns, self.node(dst), credits
            )
            self.links[(src, dst)] = link
            self.graph[src].append(dst)
            if src in self.switches:
                self.switches[src].ports[dst] = link

    def total_dropped(self) -> int:
        return sum(s.dropped for s in self.switches.values())

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
        for i, dst in enumerate(self.hosts):
            # Pass 1: BFS from dst -> distance of every node to dst
            dist = {dst: 0}
            queue = deque([dst])
            while queue:
                cur = queue.popleft()
                for n in self.graph[cur]:
                    if n in dist:
                        continue
                    dist[n] = dist[cur] + 1
                    if n in self.switches:
                        queue.append(n)

            # Pass 2: each switch picks among ALL neighbors one step closer to dst
            for name, switch in self.switches.items():
                if name not in dist:
                    continue
                candidates = [
                    n
                    for n in self.graph[name]
                    if n in dist and dist[n] == dist[name] - 1
                ]
                switch.table[dst] = candidates[i % len(candidates)]


def build_leaf_spine(
    sim: Simulator,
    n_leaves: int,
    n_spines: int,
    hosts_per_leaf: int,
    bandwidth_gbps: int = 100,
    latency_ns: int = 1000,
    buffer_size: int | None = None,
    lossless: bool = True,
) -> Network:
    """Names: spines S0.., leaves L0.., hosts H0.. (H0..H{k-1} under L0, and so on)."""
    net = Network(sim, bandwidth_gbps, latency_ns, buffer_size, lossless)
    for i in range(n_spines):
        net.add_switch(f"S{i}")
    h = 0
    for l in range(n_leaves):
        net.add_switch(f"L{l}")
        for i in range(n_spines):
            net.connect(f"L{l}", f"S{i}")
        for _ in range(hosts_per_leaf):
            net.add_host(f"H{h}")
            net.connect(f"H{h}", f"L{l}")
            h += 1
    net.compute_routes()
    return net
