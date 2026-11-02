import pytest

from netsim.engine import Simulator


def test_events_run_in_time_order():
    sim = Simulator()
    log = []
    sim.schedule(30, log.append, "c")
    sim.schedule(10, log.append, "a")
    sim.schedule(20, log.append, "b")
    sim.run()
    assert log == ["a", "b", "c"]
    assert sim.now == 30


def test_same_time_events_keep_insertion_order():
    sim = Simulator()
    log = []
    sim.schedule(30, log.append, "c")
    sim.schedule(30, log.append, "a")
    sim.run()
    assert log == ["c", "a"]
    assert sim.now == 30


def test_run_until_stops_and_keeps_remaining_events():
    sim = Simulator()
    log = []
    sim.schedule(10, log.append, "c")
    sim.schedule(50, log.append, "a")
    sim.run(until=20)
    assert sim.now == 20
    assert log == ["c"]
    sim.run()
    assert sim.now == 50
    assert log == ["c", "a"]


def test_negative_delay_is_rejected():
    sim = Simulator()
    log = []
    with pytest.raises(ValueError):
        sim.schedule(-10, log.append, "c")
