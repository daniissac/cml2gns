"""Regression tests for real output contracts and round-trip behavior."""

import json
import zipfile
from pathlib import Path

import yaml

from cml2gns.converter import Converter
from cml2gns.parsers.cml_parser import CMLParser
from cml2gns.parsers.gns3_parser import GNS3Parser
from cml2gns.utils.config import DEFAULT_NODE_MAPPINGS


FIXTURES = Path(__file__).parent / "fixtures"
CML_LIST_SAMPLE = FIXTURES / "cml_samples" / "sample_topology_list.yaml"


def test_generated_project_uses_gns3_node_schema_and_round_trips(tmp_path):
    converter = Converter(node_mappings=DEFAULT_NODE_MAPPINGS)
    result = converter.convert(CML_LIST_SAMPLE, tmp_path / "gns3")

    project_path = Path(result["project_file"])
    project = json.loads(project_path.read_text())
    assert all("node_type" in node for node in project["topology"]["nodes"])
    assert all("type" not in node for node in project["topology"]["nodes"])
    assert all("template_id" not in node for node in project["topology"]["nodes"])

    recovered_path = tmp_path / "recovered.yaml"
    converter.reverse_convert(project_path, recovered_path)
    recovered = yaml.safe_load(recovered_path.read_text())["lab"]

    assert recovered["version"] == "0.3.0"
    interface_ids = {
        node["id"]: {interface["id"] for interface in node.get("interfaces", [])}
        for node in recovered["nodes"]
    }
    for link in recovered["links"]:
        assert link["i1"] in interface_ids[link["n1"]]
        assert link["i2"] in interface_ids[link["n2"]]


def test_startup_configs_are_preserved_exactly_by_default(tmp_path):
    topology = CMLParser().parse(CML_LIST_SAMPLE)
    converter = Converter(node_mappings=DEFAULT_NODE_MAPPINGS)
    converter.convert(CML_LIST_SAMPLE, tmp_path)

    config_file = next((tmp_path / "configs").glob("Router1_*.cfg"))
    assert config_file.read_text() == topology.nodes["r1"].configuration


def test_config_normalization_is_explicit_and_non_destructive(tmp_path):
    source = tmp_path / "quoted.yaml"
    source.write_text(
        "lab:\n"
        "  title: quoted\n"
        "  nodes:\n"
        "    - id: n1\n"
        "      label: R1\n"
        "      node_definition: iosv\n"
        "      configuration: |\n"
        '        hostname "R1"\n'
        "        enable secret 5 encrypted-value\n"
    )
    converter = Converter(
        node_mappings=DEFAULT_NODE_MAPPINGS,
        normalize_configs=True,
    )
    converter.convert(source, tmp_path / "out")
    config = next((tmp_path / "out" / "configs").glob("R1_*.cfg")).read_text()
    assert "hostname R1" in config
    assert "enable secret 5 encrypted-value" in config


def test_portable_archive_contains_project_and_sidecars(tmp_path):
    converter = Converter(node_mappings=DEFAULT_NODE_MAPPINGS)
    result = converter.convert(CML_LIST_SAMPLE, tmp_path / "project", portable=True)
    archive = Path(result["portable_file"])

    assert archive.suffix == ".gns3project"
    with zipfile.ZipFile(archive) as package:
        names = package.namelist()
    assert any(name.endswith(".gns3") for name in names)
    assert any(name.startswith("configs/") for name in names)


def test_parser_repairs_legacy_cml2gns_type_field(tmp_path):
    project = tmp_path / "legacy.gns3"
    project.write_text(
        json.dumps(
            {
                "name": "legacy",
                "type": "topology",
                "topology": {
                    "nodes": [
                        {
                            "node_id": "11111111-1111-4111-8111-111111111111",
                            "name": "switch",
                            "type": "ethernet_switch",
                        }
                    ],
                    "links": [],
                },
            }
        )
    )
    topology = GNS3Parser().parse(project)
    assert (
        topology.nodes["11111111-1111-4111-8111-111111111111"].node_type
        == "unmanaged_switch"
    )
