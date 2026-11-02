"""Discrete-event simulation engine.

Time is an integer number of nanoseconds: no float rounding,
so a run with the same inputs always gives exactly the same result.
"""

import heapq
import itertools
from collections.abc import Callable
from typing import Any


class Simulator:
    def __init__(self) -> None:
        self.now: int = 0  # current simulated time (ns)
        self._queue: list[tuple] = []  # heap of (time, seq, callback, args)
        self._seq = itertools.count()  # tie-breaker for events at the same time
        self.events_processed: int = 0

    def schedule(self, delay: int, callback: Callable[..., Any], *args: Any) -> None:
        """Run callback(*args) `delay` ns after the current time."""
        if delay < 0:
            raise ValueError
        heapq.heappush(self._queue, (self.now + delay, next(self._seq), callback, args))

    def run(self, until: int | None = None) -> None:
        """Process events in time order until the queue is empty or time passes `until`."""
        while self._queue:
            if until is not None and self._queue[0][0] > until:
                self.now = until
                break
            time, _, callback, args = heapq.heappop(self._queue)
            self.now = time
            callback(*args)
            self.events_processed += 1


if __name__ == "__main__":
    # Tiny demo: two nodes play ping-pong over a 1000 ns link, 3 round trips.
    sim = Simulator()

    def receive(node: str, other: str, remaining: int) -> None:
        print(f"t={sim.now:>5} ns  {node} received")
        if remaining > 0:
            sim.schedule(1000, receive, other, node, remaining - 1)

    sim.schedule(0, receive, "A", "B", 5)
    sim.run()
    print("events:", sim.events_processed)
