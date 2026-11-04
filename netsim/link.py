"""Packets, hosts and unidirectional links, with optional credit-based flow control.

Units: time in ns (int), size in bytes, bandwidth in Gb/s.
Handy fact: 1 Gb/s = 1 bit per ns, so 100 Gb/s = 100 bits/ns.
"""

from collections import deque
from collections.abc import Callable
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
    def receive(self, packet: Packet, link: "Link") -> None: ...


class Host:
    """An endpoint that records every packet it receives, with the arrival time."""

    def __init__(self, sim: Simulator, name: str) -> None:
        self.sim = sim
        self.name = name
        self.received: list[tuple[Packet, int]] = []

    def receive(self, packet: Packet, link: "Link | None" = None) -> None:
        self.received.append((packet, self.sim.now))


class Link:
    """One-way link, FIFO. If `credits` is not None, it only sends when the receiver has room."""

    def __init__(
        self,
        sim: Simulator,
        bandwidth_gbps: int,
        latency_ns: int,
        dst: Receiver,
        credits: int | None = None,
    ) -> None:
        self.sim = sim
        self.bandwidth_gbps = bandwidth_gbps
        self.latency_ns = latency_ns
        self.dst = dst
        self.credits = (
            credits  # free slots in the receiver's buffer (None = no flow control)
        )
        # each entry: (packet, on_depart) -- on_depart() is called when the packet starts
        # transmitting, i.e. when it leaves the previous buffer
        self.queue: deque[tuple[Packet, Callable[[], None] | None]] = deque()
        self.busy = False
        self.packets_sent = 0

    def tx_time(self, size: int) -> int:
        return (size * 8 + self.bandwidth_gbps - 1) // self.bandwidth_gbps

    def send(self, packet: Packet, on_depart: Callable[[], None] | None = None) -> None:
        self.queue.append((packet, on_depart))
        self._try_start()

    def _try_start(self) -> None:
        if self.busy or not self.queue:
            return
        if self.credits is not None:
            if self.credits == 0:
                return
            self.credits -= 1

        packet, on_depart = self.queue.popleft()
        self.busy = True
        if on_depart is not None:
            on_depart()
        self.sim.schedule(self.tx_time(packet.size), self._tx_done, packet)

    def _tx_done(self, packet: Packet) -> None:
        self.sim.schedule(self.latency_ns, self.dst.receive, packet, self)
        self.packets_sent += 1
        self.busy = False
        self._try_start()

    def return_credit(self) -> None:
        """Called (after the cable latency) when the receiver frees one buffer slot."""
        if self.credits is None:
            raise RuntimeError("credit returned to a link without flow control")
        self.credits += 1
        self._try_start()
