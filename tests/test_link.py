from netsim.engine import Simulator
from netsim.link import Host, Link, Packet


def make(bw=100, lat=1000):
    sim = Simulator()
    host = Host(sim, "B")
    link = Link(sim, bw, lat, host)
    return sim, host, link


def test_single_packet_arrival_time():
    sim, host, link = make()
    link.send(Packet(0, "A", "B", 4096, 0))
    sim.run()
    assert len(host.received) == 1
    assert host.received[0][1] == 1328


def test_back_to_back_packets_queue_behind_each_other():
    sim, host, link = make()
    link.send(Packet(0, "A", "B", 4096, 0))
    link.send(Packet(1, "A", "B", 4096, 0))
    sim.run()
    interval = host.received[1][1] - host.received[0][1]
    assert interval == 328
    assert host.received[0][1] == 1328
    assert host.received[1][1] == 1656


def test_conservation_and_fifo_order():
    sim, host, link = make()
    for i in range(100):
        link.send(Packet(i, "A", "B", 4096, 0))
    sim.run()
    assert len(host.received) == 100
    pids = [packet.pid for packet, _ in host.received]
    assert pids == list(range(100))
