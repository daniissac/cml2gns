"""
Tests for topology and project validators.
"""
import pytest

from cml2gns.models.cml_model import CMLTopology, CMLNode, CMLLink
from cml2gns.models.gns3_model import GNS3Project, GNS3Node, GNS3Link
from cml2gns.utils.validators import validate_topology, validate_gns3_project


class TestValidateTopology:

    def _make_topology(self, nodes=None, links=None, name="test"):
        topo = CMLTopology(name=name)
        for n in (nodes or []):
            topo.add_node(n)
        for l in (links or []):
            topo.add_link(l)
        return topo

    def test_valid_topology(self):
        n1 = CMLNode(id="n1", node_type="iosv")
        n2 = CMLNode(id="n2", node_type="iosv")
        link = CMLLink(id="l1", node1_id="n1", interface1="g0/0",
                        node2_id="n2", interface2="g0/0")
        topo = self._make_topology(nodes=[n1, n2], links=[link])
        assert validate_topology(topo) is True

    def test_no_nodes(self):
        topo = self._make_topology()
        with pytest.raises(ValueError, match="No nodes found"):
            validate_topology(topo)

    def test_link_references_missing_node(self):
        n1 = CMLNode(id="n1", node_type="iosv")
        link = CMLLink(id="l1", node1_id="n1", interface1="g0/0",
                        node2_id="missing", interface2="g0/0")
        topo = self._make_topology(nodes=[n1], links=[link])
        with pytest.raises(ValueError, match="Node missing not found"):
            validate_topology(topo)

    def test_unnamed_topology_gets_default(self):
        n1 = CMLNode(id="n1", node_type="iosv")
        topo = self._make_topology(nodes=[n1], name=None)
        topo.name = ""
        validate_topology(topo)
        assert topo.name == "Unnamed Topology"


class TestValidateGNS3Project:

    def test_valid_project(self):
        proj = GNS3Project(name="p", project_id="pid")
        proj.add_node(GNS3Node(name="R1", node_type="qemu", node_id="nid"))
        assert validate_gns3_project(proj) is True

    def test_no_project_id(self):
        proj = GNS3Project(name="p")
        proj.add_node(GNS3Node(name="R1", node_type="qemu", node_id="nid"))
        with pytest.raises(ValueError, match="No project ID"):
            validate_gns3_project(proj)

    def test_no_nodes(self):
        proj = GNS3Project(name="p", project_id="pid")
        with pytest.raises(ValueError, match="No nodes found"):
            validate_gns3_project(proj)

    def test_link_references_missing_node(self):
        proj = GNS3Project(name="p", project_id="pid")
        proj.add_node(GNS3Node(name="R1", node_type="qemu", node_id="nid"))
        proj.add_link(GNS3Link(
            link_id="lid", node1_id="nid", node2_id="missing",
            interface1="g0/0", interface2="g0/0",
        ))
        with pytest.raises(ValueError, match="Node missing not found"):
            validate_gns3_project(proj)
