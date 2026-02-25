"""
Tests for CML and VIRL parsers.
"""
import pytest
import tempfile
from pathlib import Path

from cml2gns.parsers.cml_parser import CMLParser
from cml2gns.parsers.virl_parser import VIRLParser


class TestCMLParser:
    """Test cases for the CML YAML parser."""

    @pytest.fixture
    def parser(self):
        return CMLParser()

    @pytest.fixture
    def sample_cml_file(self):
        return Path(__file__).parent / "fixtures" / "cml_samples" / "sample_topology.yaml"

    def test_parse_sample(self, parser, sample_cml_file):
        if not sample_cml_file.exists():
            pytest.skip("Sample CML file not found")
        topo = parser.parse(sample_cml_file)
        assert topo.name == "Sample CML Topology"
        assert len(topo.nodes) == 3
        assert len(topo.links) == 2

    def test_parse_node_fields(self, parser, sample_cml_file):
        if not sample_cml_file.exists():
            pytest.skip("Sample CML file not found")
        topo = parser.parse(sample_cml_file)
        r1 = topo.nodes["router1"]
        assert r1.label == "Router 1"
        assert r1.node_type == "iosv"
        assert r1.x == 100
        assert r1.y == 100
        assert "hostname Router1" in r1.configuration

    def test_parse_link_fields(self, parser, sample_cml_file):
        if not sample_cml_file.exists():
            pytest.skip("Sample CML file not found")
        topo = parser.parse(sample_cml_file)
        link = topo.links["link1"]
        assert link.node1_id == "router1"
        assert link.interface1 == "GigabitEthernet0/0"
        assert link.node2_id == "switch1"
        assert link.interface2 == "GigabitEthernet0/1"

    def test_parse_missing_topology_section(self, parser, tmp_path):
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("random_key: true\n")
        with pytest.raises(ValueError, match="Missing 'topology' or 'lab' section"):
            parser.parse(bad_file)

    def test_parse_root_nodes_accepted(self, parser, tmp_path):
        """Files with 'nodes:' at root level are accepted (CML shorthand)."""
        f = tmp_path / "root_nodes.yaml"
        f.write_text("nodes:\n  r1:\n    label: R1\n    node_definition: linux\n")
        topo = parser.parse(f)
        assert len(topo.nodes) == 1

    def test_parse_invalid_yaml(self, parser, tmp_path):
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("{{invalid yaml!!")
        with pytest.raises(ValueError, match="Invalid YAML"):
            parser.parse(bad_file)

    def test_parse_empty_nodes(self, parser, tmp_path):
        f = tmp_path / "empty_nodes.yaml"
        f.write_text("---\ntopology:\n  name: test\n  nodes:\n  links:\n")
        topo = parser.parse(f)
        assert len(topo.nodes) == 0

    def test_parse_minimal_node(self, parser, tmp_path):
        f = tmp_path / "minimal.yaml"
        f.write_text(
            "---\ntopology:\n  name: minimal\n  nodes:\n    n1:\n"
            "      node_definition: linux\n  links:\n"
        )
        topo = parser.parse(f)
        assert len(topo.nodes) == 1
        assert topo.nodes["n1"].node_type == "linux"
        assert topo.nodes["n1"].label == "n1"


    def test_parse_list_format(self, parser):
        sample = Path(__file__).parent / "fixtures" / "cml_samples" / "sample_topology_list.yaml"
        if not sample.exists():
            pytest.skip("List-format sample not found")
        topo = parser.parse(sample)
        assert topo.name == "Sample CML List Topology"
        assert len(topo.nodes) == 3
        assert len(topo.links) == 2

    def test_parse_list_format_node_fields(self, parser):
        sample = Path(__file__).parent / "fixtures" / "cml_samples" / "sample_topology_list.yaml"
        if not sample.exists():
            pytest.skip("List-format sample not found")
        topo = parser.parse(sample)
        r1 = topo.nodes["r1"]
        assert r1.label == "Router1"
        assert r1.node_type == "iosv"
        assert r1.ram == 512

    def test_parse_list_format_interface_resolution(self, parser):
        sample = Path(__file__).parent / "fixtures" / "cml_samples" / "sample_topology_list.yaml"
        if not sample.exists():
            pytest.skip("List-format sample not found")
        topo = parser.parse(sample)
        link = topo.links["l1"]
        assert link.node1_id == "r1"
        assert link.interface1 == "GigabitEthernet0/0"
        assert link.node2_id == "s1"
        assert link.interface2 == "GigabitEthernet0/1"

    def test_parse_lab_root_key(self, parser, tmp_path):
        f = tmp_path / "lab_root.yaml"
        f.write_text(
            "---\nlab:\n  title: Lab Test\n  nodes:\n    n1:\n"
            "      node_definition: linux\n  links:\n"
        )
        topo = parser.parse(f)
        assert topo.name == "Lab Test"
        assert len(topo.nodes) == 1

    def test_parse_n1_i1_link_keys(self, parser, tmp_path):
        f = tmp_path / "shorthand.yaml"
        f.write_text(
            "---\ntopology:\n  name: short\n"
            "  nodes:\n    r1:\n      node_definition: iosv\n"
            "    r2:\n      node_definition: iosv\n"
            "  links:\n    l1:\n      n1: r1\n      i1: eth0\n"
            "      n2: r2\n      i2: eth0\n"
        )
        topo = parser.parse(f)
        link = topo.links["l1"]
        assert link.node1_id == "r1"
        assert link.interface1 == "eth0"


class TestVIRLParser:
    """Test cases for the VIRL XML parser."""

    @pytest.fixture
    def parser(self):
        return VIRLParser()

    @pytest.fixture
    def sample_virl_file(self):
        return Path(__file__).parent / "fixtures" / "virl_samples" / "sample_topology.xml"

    def test_parse_sample(self, parser, sample_virl_file):
        if not sample_virl_file.exists():
            pytest.skip("Sample VIRL file not found")
        topo = parser.parse(sample_virl_file)
        assert len(topo.nodes) == 3
        assert len(topo.links) == 2

    def test_parse_node_fields(self, parser, sample_virl_file):
        if not sample_virl_file.exists():
            pytest.skip("Sample VIRL file not found")
        topo = parser.parse(sample_virl_file)
        r1 = topo.nodes["router1"]
        assert r1.label == "router1"
        assert r1.node_type == "iosv"
        assert r1.x == 100.0
        assert r1.y == 100.0
        assert "hostname Router1" in r1.configuration

    def test_parse_connection_fields(self, parser, sample_virl_file):
        if not sample_virl_file.exists():
            pytest.skip("Sample VIRL file not found")
        topo = parser.parse(sample_virl_file)
        assert len(topo.links) == 2
        link_endpoints = set()
        for link in topo.links.values():
            link_endpoints.add((link.node1_id, link.node2_id))
        assert ("router1", "switch1") in link_endpoints
        assert ("router2", "switch1") in link_endpoints

    def test_parse_node_interfaces(self, parser, sample_virl_file):
        if not sample_virl_file.exists():
            pytest.skip("Sample VIRL file not found")
        topo = parser.parse(sample_virl_file)
        sw = topo.nodes["switch1"]
        assert len(sw.interfaces) == 2

    def test_parse_invalid_xml(self, parser, tmp_path):
        bad_file = tmp_path / "bad.xml"
        bad_file.write_text("<broken xml>")
        with pytest.raises(ValueError, match="Invalid XML"):
            parser.parse(bad_file)

    def test_parse_no_namespace(self, parser, tmp_path):
        f = tmp_path / "no_ns.xml"
        f.write_text(
            '<?xml version="1.0"?>\n'
            '<topology>\n'
            '  <node name="r1" subtype="iosv">\n'
            '    <position x="10" y="20"/>\n'
            '  </node>\n'
            '</topology>'
        )
        topo = parser.parse(f)
        assert len(topo.nodes) == 1
        assert topo.nodes["r1"].node_type == "iosv"
        assert topo.nodes["r1"].x == 10.0
