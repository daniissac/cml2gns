"""
Tests for topology and project validators.
"""

import pytest

from cml2gns.models.cml_model import CMLTopology, CMLNode, CMLLink
from cml2gns.models.gns3_model import GNS3Project, GNS3Node, GNS3Link
from cml2gns.utils.validators import validate_topology, validate_gns3_project


PROJECT_ID = "11111111-1111-4111-8111-111111111111"
NODE_ID = "22222222-2222-4222-8222-222222222222"
MISSING_NODE_ID = "33333333-3333-4333-8333-333333333333"
LINK_ID = "44444444-4444-4444-8444-444444444444"


class TestValidateTopology:
    def _make_topology(self, nodes=None, links=None, name="test"):
        topo = CMLTopology(name=name)
        for n in nodes or []:
            topo.add_node(n)
        for link in links or []:
            topo.add_link(link)
        return topo

    def test_valid_topology(self):
        n1 = CMLNode(id="n1", node_type="iosv")
        n2 = CMLNode(id="n2", node_type="iosv")
        link = CMLLink(
            id="l1", node1_id="n1", interface1="g0/0", node2_id="n2", interface2="g0/0"
        )
        topo = self._make_topology(nodes=[n1, n2], links=[link])
        assert validate_topology(topo) is True

    def test_no_nodes(self):
        topo = self._make_topology()
        with pytest.raises(ValueError, match="No nodes found"):
            validate_topology(topo)

    def test_link_references_missing_node(self):
        n1 = CMLNode(id="n1", node_type="iosv")
        link = CMLLink(
            id="l1",
            node1_id="n1",
            interface1="g0/0",
            node2_id="missing",
            interface2="g0/0",
        )
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
        proj = GNS3Project(name="p", project_id=PROJECT_ID)
        proj.add_node(GNS3Node(name="R1", node_type="qemu", node_id=NODE_ID))
        assert validate_gns3_project(proj) is True

    def test_no_project_id(self):
        proj = GNS3Project(name="p")
        proj.add_node(GNS3Node(name="R1", node_type="qemu", node_id=NODE_ID))
        with pytest.raises(ValueError, match="No project ID"):
            validate_gns3_project(proj)

    def test_no_nodes(self):
        proj = GNS3Project(name="p", project_id=PROJECT_ID)
        with pytest.raises(ValueError, match="No nodes found"):
            validate_gns3_project(proj)

    def test_link_references_missing_node(self):
        proj = GNS3Project(name="p", project_id=PROJECT_ID)
        proj.add_node(GNS3Node(name="R1", node_type="qemu", node_id=NODE_ID))
        proj.add_link(
            GNS3Link(
                link_id=LINK_ID,
                node1_id=NODE_ID,
                node2_id=MISSING_NODE_ID,
                interface1="g0/0",
                interface2="g0/0",
            )
        )
        with pytest.raises(ValueError, match=f"Node {MISSING_NODE_ID} not found"):
            validate_gns3_project(proj)
