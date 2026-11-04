from netsim.engine import Simulator
from netsim.link import Packet
from netsim.network import build_leaf_spine


def make():
    sim = Simulator()
    net = build_leaf_spine(sim, n_leaves=4, n_spines=2, hosts_per_leaf=2)
    return sim, net


def test_topology_counts():
    _, net = make()
    assert len(net.hosts) == 8
    assert len(net.switches) == 6
    assert len(net.links) == 32


def test_same_leaf_arrival_time():
    sim, net = make()
    net.send(Packet(0, "H0", "H1", 4096, 0))
    sim.run()
    h1 = net.hosts["H1"]
    assert len(h1.received) == 1
    assert h1.received[0][1] == 2656


def test_cross_leaf_arrival_time():
    sim, net = make()
    net.send(Packet(0, "H0", "H7", 4096, 0))
    sim.run()
    h7 = net.hosts["H7"]
    assert len(h7.received) == 1
    assert h7.received[0][1] == 4 * 1328  # H0 -> L0 -> spine -> L3 -> H7


def test_all_pairs_delivered_to_the_right_host():
    sim, net = make()
    pid = 0
    for src in net.hosts:
        for dst in net.hosts:
            if src != dst:
                net.send(Packet(pid, src, dst, 4096, 0))
                pid += 1
    sim.run()
    for name, host in net.hosts.items():
        assert len(host.received) == 7
        for packet, _ in host.received:
            assert packet.dst == name


def test_uplinks_are_balanced():
    sim, net = make()
    pid = 0
    for src in net.hosts:
        for dst in net.hosts:
            if src != dst:
                net.send(Packet(pid, src, dst, 4096, 0))
                pid += 1
    sim.run()
    to_s0 = net.links[("L0", "S0")].packets_sent
    to_s1 = net.links[("L0", "S1")].packets_sent
    assert to_s0 == to_s1
