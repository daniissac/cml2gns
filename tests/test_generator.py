"""
Tests for the GNS3 generator.
"""

import json
import pytest
from pathlib import Path

from cml2gns.models.cml_model import CMLTopology, CMLNode, CMLLink
from cml2gns.generators.gns3_generator import GNS3Generator
from cml2gns.utils.node_mappings import map_nodes
from cml2gns.utils.config import DEFAULT_NODE_MAPPINGS


PROJECT_ID = "11111111-1111-4111-8111-111111111111"


class TestGNS3Generator:
    def _build_topology(self):
        topo = CMLTopology(name="gen_test")
        n1 = CMLNode(
            id="r1",
            label="Router1",
            node_type="iosv",
            x=10,
            y=20,
            configuration="hostname R1",
        )
        n2 = CMLNode(id="s1", label="Switch1", node_type="iosvl2", x=30, y=40)
        topo.add_node(n1)
        topo.add_node(n2)
        link = CMLLink(
            id="l1",
            node1_id="r1",
            interface1="GigabitEthernet0/0",
            node2_id="s1",
            interface2="GigabitEthernet0/1",
        )
        topo.add_link(link)
        map_nodes(topo, DEFAULT_NODE_MAPPINGS)
        return topo

    @pytest.fixture
    def generator(self):
        return GNS3Generator()

    def test_generate_creates_project_file(self, generator, tmp_path):
        topo = self._build_topology()
        result = generator.generate(topo, tmp_path, project_id=PROJECT_ID)
        project_file = Path(result["project_file"])
        assert project_file.exists()
        assert project_file.suffix == ".gns3"

    def test_generate_node_count(self, generator, tmp_path):
        topo = self._build_topology()
        result = generator.generate(topo, tmp_path)
        assert result["node_count"] == 2

    def test_generate_link_count(self, generator, tmp_path):
        topo = self._build_topology()
        result = generator.generate(topo, tmp_path)
        assert result["link_count"] == 1

    def test_generated_json_structure(self, generator, tmp_path):
        topo = self._build_topology()
        result = generator.generate(topo, tmp_path, project_id=PROJECT_ID)
        with open(result["project_file"]) as f:
            data = json.load(f)

        assert data["project_id"] == PROJECT_ID
        assert data["name"] == "gen_test"
        assert data["type"] == "topology"
        assert len(data["topology"]["nodes"]) == 2
        assert len(data["topology"]["links"]) == 1
        assert all("node_type" in node for node in data["topology"]["nodes"])
        assert all("type" not in node for node in data["topology"]["nodes"])

        node_names = {n["name"] for n in data["topology"]["nodes"]}
        assert node_names == {"Router1", "Switch1"}

    def test_generate_saves_config_files(self, generator, tmp_path):
        topo = self._build_topology()
        generator.generate(topo, tmp_path)
        config_dir = tmp_path / "configs"
        assert config_dir.exists()
        cfg_files = list(config_dir.glob("Router1_*.cfg"))
        assert len(cfg_files) == 1
        assert "hostname R1" in cfg_files[0].read_text()

    def test_generate_preserves_named_config_records(self, generator, tmp_path):
        topo = CMLTopology(name="named_configs")
        node = CMLNode(
            id="r1",
            label="Router1",
            node_type="iosv",
            configuration=[
                {"name": "ios_config.txt", "content": "hostname R1\n"},
                {"name": "day0.txt", "content": "interface Loopback0\n"},
            ],
        )
        topo.add_node(node)
        map_nodes(topo, DEFAULT_NODE_MAPPINGS)

        result = generator.generate(topo, tmp_path)

        config_root = tmp_path / "configs"
        assert result["config_count"] == 2
        assert next(config_root.glob("Router1_*/ios_config.txt")).read_text() == (
            "hostname R1\n"
        )
        assert next(config_root.glob("Router1_*/day0.txt")).read_text() == (
            "interface Loopback0\n"
        )

    def test_generate_uses_correct_symbol(self, generator, tmp_path):
        topo = self._build_topology()
        result = generator.generate(topo, tmp_path)
        with open(result["project_file"]) as f:
            data = json.load(f)
        symbols = {n["name"]: n["symbol"] for n in data["topology"]["nodes"]}
        assert symbols["Router1"] == ":/symbols/classic/router.svg"
        assert symbols["Switch1"] == ":/symbols/classic/ethernet_switch.svg"

    def test_generate_skips_link_with_missing_endpoint(self, generator, tmp_path):
        topo = CMLTopology(name="broken_link")
        n1 = CMLNode(id="r1", label="R1", node_type="iosv")
        topo.add_node(n1)
        link = CMLLink(
            id="l1",
            node1_id="r1",
            interface1="g0/0",
            node2_id="missing",
            interface2="g0/0",
        )
        topo.add_link(link)
        map_nodes(topo, DEFAULT_NODE_MAPPINGS)
        # The generator should skip the invalid link but not crash
        result = generator.generate(topo, tmp_path)
        assert result["link_count"] == 0

    def test_portable_uses_official_extension(self, generator, tmp_path):
        topo = self._build_topology()
        result = generator.generate(topo, tmp_path / "project", portable=True)
        portable = Path(result["portable_file"])
        assert portable.suffix == ".gns3project"
        assert portable.exists()

    def test_project_and_config_names_are_path_safe(self, generator, tmp_path):
        topo = self._build_topology()
        topo.name = "branch/lab"
        topo.nodes["r1"].label = "edge/router"
        result = generator.generate(topo, tmp_path)
        assert Path(result["project_file"]).name == "branch_lab.gns3"
        assert list((tmp_path / "configs").glob("edge_router_*.cfg"))

    def test_invalid_project_does_not_leave_partial_output(self, generator, tmp_path):
        topo = CMLTopology(name="invalid")
        topo.add_node(CMLNode(id="n1", label="same", node_type="iosv"))
        topo.add_node(CMLNode(id="n2", label="same", node_type="iosv"))
        map_nodes(topo, DEFAULT_NODE_MAPPINGS)
        output = tmp_path / "not-created"

        with pytest.raises(ValueError, match="Duplicate node name"):
            generator.generate(topo, output)

        assert not output.exists()
