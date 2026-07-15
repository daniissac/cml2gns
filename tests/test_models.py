"""
Tests for GNS3 models (GNS3Project, GNS3Node, GNS3Link).
"""

import pytest

from cml2gns.models.gns3_model import GNS3Project, GNS3Node, GNS3Link


class TestGNS3Node:
    def test_to_dict_basic(self):
        node = GNS3Node(
            name="R1",
            node_type="Cisco IOSv",
            node_id="abc-123",
            console_type="telnet",
            compute_type="qemu",
            x=100,
            y=200,
            symbol=":/symbols/classic/router.svg",
        )
        d = node.to_dict()
        assert d["node_id"] == "abc-123"
        assert d["name"] == "R1"
        assert d["node_type"] == "qemu"
        assert "type" not in d
        assert "template_id" not in d
        assert d["console_type"] == "telnet"
        assert d["symbol"] == ":/symbols/classic/router.svg"
        assert d["x"] == 100
        assert d["y"] == 200

    def test_default_symbol(self):
        node = GNS3Node(name="N1", node_type="qemu", node_id="id1")
        assert node.symbol == ":/symbols/classic/computer.svg"

    def test_custom_symbol(self):
        node = GNS3Node(
            name="FW",
            node_type="ASAv",
            node_id="id2",
            symbol=":/symbols/classic/firewall.svg",
        )
        d = node.to_dict()
        assert d["symbol"] == ":/symbols/classic/firewall.svg"

    def test_real_template_id_is_preserved(self):
        template_id = "22222222-2222-4222-8222-222222222222"
        node = GNS3Node(
            name="R1",
            node_type="Cisco IOSv",
            node_id="id2",
            template_id=template_id,
        )
        assert node.to_dict()["template_id"] == template_id


class TestGNS3LinkInterfaceParsing:
    @pytest.mark.parametrize(
        "interface,expected",
        [
            ("GigabitEthernet0/0", (0, 0)),
            ("GigabitEthernet0/1", (0, 1)),
            ("GigabitEthernet1/0", (1, 0)),
            ("GigabitEthernet0/0/0", (0, 0)),
            ("GigabitEthernet0/0/1", (0, 1)),
            ("GigabitEthernet1/0/2", (1, 2)),
            ("eth0", (0, 0)),
            ("eth3", (3, 0)),
            ("Ethernet0/1", (0, 1)),
            (None, (0, 0)),
            (2, (2, 0)),
            ("loopback0", (0, 0)),
        ],
    )
    def test_parse_interface(self, interface, expected):
        assert GNS3Link._parse_interface(interface) == expected

    def test_to_dict_adapter_port(self):
        link = GNS3Link(
            link_id="link-1",
            node1_id="n1",
            node2_id="n2",
            interface1="GigabitEthernet1/3",
            interface2="GigabitEthernet0/0",
        )
        d = link.to_dict()
        assert d["nodes"][0]["adapter_number"] == 1
        assert d["nodes"][0]["port_number"] == 3
        assert d["nodes"][1]["adapter_number"] == 0
        assert d["nodes"][1]["port_number"] == 0


class TestGNS3Project:
    def test_to_dict_structure(self):
        proj = GNS3Project(
            name="test", project_id="11111111-1111-4111-8111-111111111111"
        )
        node = GNS3Node(
            name="R1",
            node_type="qemu",
            node_id="22222222-2222-4222-8222-222222222222",
        )
        proj.add_node(node)
        d = proj.to_dict()
        assert d["name"] == "test"
        assert d["project_id"] == "11111111-1111-4111-8111-111111111111"
        assert d["type"] == "topology"
        assert len(d["topology"]["nodes"]) == 1
        assert d["topology"]["drawings"] == []
        assert d["topology"]["computes"] == []

    def test_default_version(self):
        proj = GNS3Project(name="t")
        d = proj.to_dict()
        assert d["version"] == GNS3Project.DEFAULT_VERSION

    def test_custom_version(self):
        proj = GNS3Project(name="t", version="2.3.0")
        d = proj.to_dict()
        assert d["version"] == "2.3.0"
