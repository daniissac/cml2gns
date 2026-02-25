"""
Tests for the new features: diff, containerlab, visualization,
GNS3 API client, drawings, and config transformation.
"""
import json
import os
import pytest
import tempfile
from pathlib import Path

from cml2gns.converter import Converter
from cml2gns.models.cml_model import CMLTopology, CMLNode, CMLLink
from cml2gns.models.gns3_model import GNS3Drawing, GNS3Project
from cml2gns.parsers.containerlab_parser import ContainerlabParser
from cml2gns.generators.containerlab_generator import ContainerlabGenerator
from cml2gns.utils.topology_diff import diff_topologies
from cml2gns.utils.visualizer import visualize_topology
from cml2gns.utils.annotations import extract_drawings
from cml2gns.utils.config_transform import ConfigTransformer


FIXTURES = Path(__file__).parent / "fixtures"
CML_SAMPLE = FIXTURES / "cml_samples" / "sample_topology.yaml"
CLAB_SAMPLE = FIXTURES / "containerlab_samples" / "sample.clab.yml"


def _make_topology(name, nodes_spec, links_spec):
    t = CMLTopology(name=name)
    for nid, label, ntype in nodes_spec:
        t.add_node(CMLNode(id=nid, label=label, node_type=ntype))
    for lid, n1, i1, n2, i2 in links_spec:
        t.add_link(CMLLink(id=lid, node1_id=n1, interface1=i1,
                           node2_id=n2, interface2=i2))
    return t


class TestTopologyDiff:

    def test_identical_topologies(self):
        t = _make_topology("T", [("n1", "R1", "iosv")], [])
        result = diff_topologies(t, t)
        assert "identical" in result["summary"].lower()
        assert result["nodes_added"] == []
        assert result["nodes_removed"] == []

    def test_node_added(self):
        ta = _make_topology("T", [("n1", "R1", "iosv")], [])
        tb = _make_topology("T", [("n1", "R1", "iosv"), ("n2", "R2", "iosv")], [])
        result = diff_topologies(ta, tb)
        assert "R2" in result["nodes_added"]

    def test_node_removed(self):
        ta = _make_topology("T", [("n1", "R1", "iosv"), ("n2", "R2", "iosv")], [])
        tb = _make_topology("T", [("n1", "R1", "iosv")], [])
        result = diff_topologies(ta, tb)
        assert "R2" in result["nodes_removed"]

    def test_node_type_changed(self):
        ta = _make_topology("T", [("n1", "R1", "iosv")], [])
        tb = _make_topology("T", [("n1", "R1", "csr1000v")], [])
        result = diff_topologies(ta, tb)
        assert len(result["nodes_changed"]) == 1
        assert result["nodes_changed"][0]["label"] == "R1"

    def test_link_added(self):
        ta = _make_topology("T",
            [("n1", "R1", "iosv"), ("n2", "R2", "iosv")], [])
        tb = _make_topology("T",
            [("n1", "R1", "iosv"), ("n2", "R2", "iosv")],
            [("l1", "n1", "eth0", "n2", "eth0")])
        result = diff_topologies(ta, tb)
        assert len(result["links_added"]) == 1

    def test_name_changed(self):
        ta = _make_topology("Alpha", [("n1", "R1", "iosv")], [])
        tb = _make_topology("Beta", [("n1", "R1", "iosv")], [])
        result = diff_topologies(ta, tb)
        assert result["name_changed"] is True

    def test_diff_via_converter(self):
        converter = Converter()
        result = converter.diff(CML_SAMPLE, CML_SAMPLE)
        assert "identical" in result["summary"].lower()


class TestContainerlabParser:

    def test_parse_sample(self):
        parser = ContainerlabParser()
        topo = parser.parse(CLAB_SAMPLE)
        assert topo.name == "lab-test"
        assert len(topo.nodes) == 3
        assert len(topo.links) == 2

    def test_node_types(self):
        parser = ContainerlabParser()
        topo = parser.parse(CLAB_SAMPLE)
        labels = {n.label for n in topo.nodes.values()}
        assert "r1" in labels
        assert "sw1" in labels

    def test_parse_link_endpoints(self):
        parser = ContainerlabParser()
        topo = parser.parse(CLAB_SAMPLE)
        link = list(topo.links.values())[0]
        assert link.interface1 == "eth1"


class TestContainerlabGenerator:

    def test_roundtrip(self):
        parser = ContainerlabParser()
        topo = parser.parse(CLAB_SAMPLE)

        with tempfile.NamedTemporaryFile(suffix=".clab.yml", delete=False) as tf:
            out_path = Path(tf.name)
        try:
            gen = ContainerlabGenerator()
            result = gen.generate(topo, out_path)
            assert result["node_count"] == 3
            assert result["link_count"] == 2
            assert out_path.exists()
        finally:
            out_path.unlink(missing_ok=True)

    def test_export_via_converter(self):
        with tempfile.NamedTemporaryFile(suffix=".clab.yml", delete=False) as tf:
            out_path = Path(tf.name)
        try:
            converter = Converter()
            result = converter.export_containerlab(CML_SAMPLE, out_path)
            assert result["node_count"] == 3
            assert out_path.exists()
        finally:
            out_path.unlink(missing_ok=True)


class TestVisualizer:

    def test_basic_visualization(self):
        topo = _make_topology("TestNet",
            [("n1", "R1", "iosv"), ("n2", "R2", "iosv")],
            [("l1", "n1", "Gi0/0", "n2", "Gi0/0")])
        output = visualize_topology(topo)
        assert "TestNet" in output
        assert "R1" in output
        assert "R2" in output

    def test_empty_topology(self):
        topo = CMLTopology(name="Empty")
        output = visualize_topology(topo)
        assert "Empty" in output
        assert "empty topology" in output

    def test_visualize_via_converter(self):
        converter = Converter()
        output = converter.visualize(CML_SAMPLE)
        assert "Router 1" in output
        assert "Router 2" in output


class TestAnnotations:

    def test_notes_become_drawings(self):
        topo = CMLTopology(name="T", notes="This is a note")
        drawings = extract_drawings(topo)
        assert len(drawings) >= 1
        svg_combined = " ".join(d.svg for d in drawings)
        assert "note" in svg_combined.lower()

    def test_description_becomes_drawing(self):
        topo = CMLTopology(name="T", description="My description")
        drawings = extract_drawings(topo)
        assert len(drawings) >= 1
        assert any("Description" in d.svg for d in drawings)

    def test_empty_notes_no_drawings(self):
        topo = CMLTopology(name="T")
        drawings = extract_drawings(topo)
        assert drawings == []


class TestGNS3Drawing:

    def test_from_text(self):
        d = GNS3Drawing.from_text("Hello World", x=10, y=20)
        assert "Hello World" in d.svg
        assert d.x == 10
        assert d.y == 20

    def test_to_dict(self):
        d = GNS3Drawing(svg="<svg/>", x=5, y=10, z=2)
        result = d.to_dict()
        assert result["svg"] == "<svg/>"
        assert result["x"] == 5

    def test_project_drawings_serialized(self):
        p = GNS3Project(name="test", project_id="abc")
        p.add_drawing(GNS3Drawing.from_text("Label"))
        d = p.to_dict()
        assert len(d["topology"]["drawings"]) == 1


class TestConfigTransformer:

    def test_hostname_normalize(self):
        t = ConfigTransformer()
        result = t.transform('hostname "myrouter"\n', direction="cml_to_gns3")
        assert result.strip() == "hostname myrouter"

    def test_empty_config(self):
        t = ConfigTransformer()
        assert t.transform("") == ""
        assert t.transform(None) is None

    def test_rules_respect_node_type(self):
        t = ConfigTransformer()
        config = "feature telnet\nhostname nx"
        result = t.transform(config, node_type="nxosv", direction="cml_to_gns3")
        assert "disabled for GNS3" in result

    def test_rules_skip_wrong_node_type(self):
        t = ConfigTransformer()
        config = "feature telnet\nhostname nx"
        result = t.transform(config, node_type="iosv", direction="cml_to_gns3")
        assert "disabled for GNS3" not in result

    def test_enable_secret_replaced(self):
        t = ConfigTransformer()
        config = "enable secret 5 $1$abc$xyz\n"
        result = t.transform(config, direction="cml_to_gns3")
        assert "enable secret 0 cisco" in result
