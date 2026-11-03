"""Packets, hosts and unidirectional links.

Units: time in ns (int), size in bytes, bandwidth in Gb/s.
Handy fact: 1 Gb/s = 1 bit per ns, so 100 Gb/s = 100 bits/ns.
"""

from collections import deque
from dataclasses import dataclass
from typing import Protocol

from netsim.engine import Simulator


@dataclass
class Packet:
    pid: int
    src: str
    dst: str
    size: int  # bytes
    created_at: int  # ns


class Receiver(Protocol):
    def receive(self, packet: Packet) -> None: ...


class Host:
    """An endpoint that records every packet it receives, with the arrival time."""

    def __init__(self, sim: Simulator, name: str) -> None:
        self.sim = sim
        self.name = name
        self.received: list[tuple[Packet, int]] = []

    def receive(self, packet: Packet) -> None:
        self.received.append((packet, self.sim.now))


class Link:
    """One-way link: transmits one packet at a time, FIFO, then the packet travels `latency` ns."""

    def __init__(
        self, sim: Simulator, bandwidth_gbps: int, latency_ns: int, dst: Receiver
    ) -> None:
        self.sim = sim
        self.bandwidth_gbps = bandwidth_gbps
        self.latency_ns = latency_ns
        self.dst = dst  # anything with a .receive(packet) method
        self.queue: deque[Packet] = deque()  # packets waiting to be transmitted
        self.busy = False  # True while a packet is being pushed onto the wire
        self.packets_sent = 0

    def tx_time(self, size: int) -> int:
        """Serialization delay in ns, rounded UP to a whole ns."""
        return ((size * 8) + self.bandwidth_gbps - 1) // self.bandwidth_gbps

    def send(self, packet: Packet) -> None:
        """Called by whoever wants to send: queue the packet and start if the link is idle."""
        self.queue.append(packet)
        if not self.busy:
            self._start_next()

    def _start_next(self) -> None:
        packet = self.queue.popleft()
        time = self.tx_time(packet.size)
        self.busy = True
        self.sim.schedule(time, self._tx_done, packet)

    def _tx_done(self, packet: Packet) -> None:
        self.sim.schedule(self.latency_ns, self.dst.receive, packet)
        self.packets_sent += 1
        self.busy = False
        if self.queue:
            self._start_next()
