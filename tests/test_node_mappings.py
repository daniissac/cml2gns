"""
Tests for node mapping utilities.
"""
import pytest

from cml2gns.models.cml_model import CMLTopology, CMLNode
from cml2gns.utils.node_mappings import map_nodes
from cml2gns.utils.config import DEFAULT_NODE_MAPPINGS


class TestMapNodes:

    def _topology_with_types(self, *types):
        topo = CMLTopology(name="test")
        for i, t in enumerate(types):
            topo.add_node(CMLNode(id=f"n{i}", node_type=t))
        return topo

    def test_known_type_mapped(self):
        topo = self._topology_with_types("iosv")
        map_nodes(topo, DEFAULT_NODE_MAPPINGS)
        node = topo.nodes["n0"]
        assert node.gns3_template == "Cisco IOSv"
        assert node.console_type == "telnet"
        assert node.gns3_compute_type == "qemu"
        assert node.gns3_symbol == ":/symbols/classic/router.svg"

    def test_unknown_type_falls_back(self):
        topo = self._topology_with_types("totally_unknown")
        map_nodes(topo, DEFAULT_NODE_MAPPINGS)
        node = topo.nodes["n0"]
        assert node.gns3_template == "qemu"
        assert node.console_type == "telnet"
        assert node.gns3_compute_type == "qemu"
        assert node.gns3_symbol is None

    def test_custom_mapping_overrides(self):
        custom = {
            "mydevice": {
                "gns3_template": "My Custom Device",
                "console_type": "vnc",
                "compute_type": "docker",
                "symbol": ":/symbols/classic/server.svg",
            }
        }
        topo = self._topology_with_types("mydevice")
        map_nodes(topo, custom)
        node = topo.nodes["n0"]
        assert node.gns3_template == "My Custom Device"
        assert node.console_type == "vnc"
        assert node.gns3_compute_type == "docker"
        assert node.gns3_symbol == ":/symbols/classic/server.svg"

    def test_mixed_mapped_and_unmapped(self):
        topo = self._topology_with_types("iosv", "weird_thing")
        map_nodes(topo, DEFAULT_NODE_MAPPINGS)
        assert topo.nodes["n0"].gns3_template == "Cisco IOSv"
        assert topo.nodes["n1"].gns3_template == "qemu"

    def test_all_default_mappings_have_required_fields(self):
        for node_type, mapping in DEFAULT_NODE_MAPPINGS.items():
            assert "gns3_template" in mapping, f"{node_type} missing gns3_template"
            assert "console_type" in mapping, f"{node_type} missing console_type"
            assert "compute_type" in mapping, f"{node_type} missing compute_type"
            assert "symbol" in mapping, f"{node_type} missing symbol"
