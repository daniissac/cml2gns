"""
Main converter module for cml2gns.
"""

import json
import logging
import uuid
from pathlib import Path

import yaml

from cml2gns.parsers.cml_parser import CMLParser
from cml2gns.parsers.virl_parser import VIRLParser
from cml2gns.generators.gns3_generator import GNS3Generator
from cml2gns.models.gns3_model import GNS3Link
from cml2gns.utils.validators import validate_topology
from cml2gns.utils.node_mappings import map_nodes, lookup_node_mapping
from cml2gns.utils.config import GNS3_VERSION_REVISIONS, validate_node_mappings
from cml2gns.utils.topology_diff import diff_topologies
from cml2gns.utils.visualizer import visualize_topology

logger = logging.getLogger(__name__)


class Converter:
    """
    Core converter class that orchestrates the conversion process.
    """

    def __init__(
        self,
        node_mappings=None,
        strict=False,
        gns3_version=None,
        normalize_configs=False,
    ):
        """
        Args:
            node_mappings (dict): Custom node mappings configuration
            strict (bool): If True, fail on unmapped node types instead of
                using a generic fallback.
            gns3_version (str): Target GNS3 version family (e.g. "2.0", "2.2").
            normalize_configs (bool): Apply the opt-in, non-destructive config
                normalization rules before writing sidecar config files.
        """
        self.node_mappings = node_mappings if node_mappings is not None else {}
        validate_node_mappings(self.node_mappings, require_template=True)
        self.strict = strict
        self.cml_parser = CMLParser()
        self.virl_parser = VIRLParser()

        gen_version = None
        gen_revision = None
        if gns3_version and gns3_version in GNS3_VERSION_REVISIONS:
            info = GNS3_VERSION_REVISIONS[gns3_version]
            gen_version = info["default_version"]
            gen_revision = info["revision"]

        config_transformer = None
        if normalize_configs:
            from cml2gns.utils.config_transform import ConfigTransformer

            config_transformer = ConfigTransformer()

        self.gns3_generator = GNS3Generator(
            gns3_version=gen_version,
            gns3_revision=gen_revision,
            config_transformer=config_transformer,
        )

    def _detect_file_type(self, input_file):
        """
        Detect if the input file is CML, VIRL, or GNS3 format.

        Returns:
            str: "cml", "virl", or "gns3"
        """
        input_file = Path(input_file)
        lower_name = input_file.name.lower()

        if lower_name.endswith((".clab.yml", ".clab.yaml")):
            logger.info(f"Detected containerlab format for {input_file}")
            return "containerlab"

        if input_file.suffix.lower() == ".gns3":
            logger.info(f"Detected GNS3 format for {input_file}")
            return "gns3"

        if input_file.suffix.lower() in {".xml", ".virl"}:
            logger.info(f"Detected VIRL format for {input_file}")
            return "virl"

        with open(input_file, "r", encoding="utf-8") as f:
            content = f.read()

        if content.lstrip().startswith("{"):
            try:
                data = json.loads(content)
                if isinstance(data, dict) and (
                    data.get("type") == "topology" or "topology" in data
                ):
                    logger.info(f"Detected GNS3 format for {input_file}")
                    return "gns3"
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

        if content.lstrip().startswith("<"):
            logger.info(f"Detected VIRL format for {input_file}")
            return "virl"

        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError:
            data = None

        if isinstance(data, dict) and any(
            key in data for key in ("lab", "topology", "nodes")
        ):
            logger.info(f"Detected CML format for {input_file}")
            return "cml"

        logger.error(f"Could not determine file type for {input_file}")
        raise ValueError(
            f"Unknown file format for {input_file}. "
            f"Must be CML, VIRL, GNS3, or containerlab."
        )

    def _parse(self, input_file):
        """Parse an input file and return the topology and detected file type."""
        input_file = Path(input_file)
        file_type = self._detect_file_type(input_file)

        if file_type == "cml":
            topology = self.cml_parser.parse(input_file)
        elif file_type == "virl":
            topology = self.virl_parser.parse(input_file)
        elif file_type == "gns3":
            from cml2gns.parsers.gns3_parser import GNS3Parser

            topology = GNS3Parser().parse(input_file)
        elif file_type == "containerlab":
            from cml2gns.parsers.containerlab_parser import ContainerlabParser

            topology = ContainerlabParser().parse(input_file)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

        return topology, file_type

    def validate_file(self, input_file):
        """
        Parse and validate a CML/VIRL file without converting it.
        """
        topology, file_type = self._parse(input_file)
        validate_topology(topology)

        unmapped = set()
        for node in topology.nodes.values():
            node_type = node.node_type or "unknown"
            if lookup_node_mapping(node_type, self.node_mappings) is None:
                unmapped.add(node_type)

        return {
            "file_type": file_type,
            "topology_name": topology.name,
            "node_count": len(topology.nodes),
            "link_count": len(topology.links),
            "unmapped_types": sorted(unmapped),
        }

    def convert(self, input_file, output_dir, dry_run=False, portable=False):
        """
        Convert a CML/VIRL file to GNS3 project.
        """
        input_file = Path(input_file)
        output_dir = Path(output_dir)

        logger.info(f"Starting conversion of {input_file} to {output_dir}")

        topology, _ = self._parse(input_file)
        validate_topology(topology)
        mapped_topology = map_nodes(topology, self.node_mappings)

        unmapped = {
            n.node_type or "unknown"
            for n in mapped_topology.nodes.values()
            if lookup_node_mapping(n.node_type or "unknown", self.node_mappings) is None
        }

        if unmapped and self.strict:
            raise ValueError(
                f"Strict mode: unmapped node types found: {', '.join(sorted(unmapped))}. "
                f"Add them to a custom mapping file and pass it with --mapping."
            )

        if dry_run:
            return {
                "project_file": None,
                "node_count": len(mapped_topology.nodes),
                "link_count": len(mapped_topology.links),
                "unmapped_types": sorted(unmapped),
                "dry_run": True,
            }

        project_uuid = str(uuid.uuid4())
        result = self.gns3_generator.generate(
            mapped_topology,
            output_dir,
            project_uuid,
            portable=portable,
        )
        result["unmapped_types"] = sorted(unmapped)

        logger.info(
            f"Conversion complete. Created {result['node_count']} nodes and {result['link_count']} links"
        )
        return result

    def diff(self, file_a, file_b):
        """
        Compare two topology files and return a diff report.

        Both files can be in any supported format (CML, VIRL, GNS3,
        containerlab).
        """
        topo_a, _ = self._parse(file_a)
        topo_b, _ = self._parse(file_b)
        return diff_topologies(
            topo_a,
            topo_b,
            label_a=str(file_a),
            label_b=str(file_b),
        )

    def visualize(self, input_file):
        """Return an ASCII visualization of a topology file."""
        topology, _ = self._parse(input_file)
        return visualize_topology(topology)

    def export_containerlab(self, input_file, output_file):
        """Convert any supported topology file to containerlab .clab.yml."""
        topology, _ = self._parse(input_file)
        validate_topology(topology)
        mapped_topology = map_nodes(topology, self.node_mappings)

        from cml2gns.generators.containerlab_generator import ContainerlabGenerator

        generator = ContainerlabGenerator()
        return generator.generate(mapped_topology, output_file)

    def reverse_convert(self, input_file, output_file):
        """
        Convert a GNS3 project file back to CML YAML.
        """
        input_file = Path(input_file)
        output_file = Path(output_file)

        from cml2gns.parsers.gns3_parser import GNS3Parser
        from cml2gns.generators.cml_generator import CMLGenerator

        topology = GNS3Parser().parse(input_file)
        validate_topology(topology)

        generator = CMLGenerator()
        result = generator.generate(topology, output_file)

        logger.info(
            f"Reverse conversion complete. Wrote {result['node_count']} nodes "
            f"and {result['link_count']} links to {output_file}"
        )
        return result

    def deploy(self, input_file, client, project_name=None, rollback_on_error=True):
        """Create a runnable project on a GNS3 server from installed templates.

        Offline ``.gns3`` generation cannot infer proprietary image filenames
        or local template settings. Server deployment resolves the mappings
        against templates that are actually installed and asks GNS3 to create
        each node from those templates.
        """
        topology, file_type = self._parse(input_file)
        validate_topology(topology)

        used_mappings = {}
        unmapped = set()
        for node in topology.nodes.values():
            node_type = node.node_type or "unknown"
            mapping = lookup_node_mapping(node_type, self.node_mappings)
            if mapping is None:
                unmapped.add(node_type)
            else:
                used_mappings[node_type] = mapping

        if unmapped:
            raise ValueError(
                "Cannot deploy unmapped node types: " + ", ".join(sorted(unmapped))
            )

        resolved, missing_templates = client.resolve_node_mappings(used_mappings)
        if missing_templates:
            raise ValueError(
                "Required GNS3 templates are not installed: "
                + ", ".join(sorted(set(missing_templates)))
            )

        project = client.create_project(project_name or topology.name)
        if not isinstance(project, dict) or not project.get("project_id"):
            raise ValueError("GNS3 server did not return a project_id")

        project_id = project["project_id"]
        created_nodes = {}
        created_links = 0
        created_drawings = 0

        try:
            for node in topology.nodes.values():
                mapping = lookup_node_mapping(node.node_type or "unknown", resolved)
                server_node = client.create_node_from_template(
                    project_id=project_id,
                    template_id=mapping["template_id"],
                    name=node.label,
                    x=node.x or 0,
                    y=node.y or 0,
                )
                if not isinstance(server_node, dict) or not server_node.get("node_id"):
                    raise ValueError(
                        f"GNS3 server did not return a node_id for {node.label}"
                    )
                created_nodes[node.id] = server_node

            for link in topology.links.values():
                node1 = created_nodes[link.node1_id]
                node2 = created_nodes[link.node2_id]
                endpoints = [
                    self._server_endpoint(node1, link.interface1),
                    self._server_endpoint(node2, link.interface2),
                ]
                link_model = GNS3Link(
                    interface1=link.interface1,
                    interface2=link.interface2,
                )
                client.create_link(
                    project_id,
                    endpoints,
                    link_type=link_model._detect_link_type(),
                )
                created_links += 1

            from cml2gns.utils.annotations import extract_drawings

            for drawing in extract_drawings(topology):
                client.create_drawing(project_id, drawing.to_dict())
                created_drawings += 1
        except Exception:
            if rollback_on_error:
                try:
                    client.delete_project(project_id)
                except Exception:
                    logger.exception(
                        "Failed to roll back partial GNS3 project %s", project_id
                    )
            raise

        config_count = sum(
            len(node.iter_configurations())
            if hasattr(node, "iter_configurations")
            else int(bool(node.configuration))
            for node in topology.nodes.values()
        )
        return {
            "project_id": project_id,
            "project_name": project.get("name") or project_name or topology.name,
            "project_url": f"{client.base_url}/v2/projects/{project_id}",
            "file_type": file_type,
            "node_count": len(created_nodes),
            "link_count": created_links,
            "drawing_count": created_drawings,
            "config_count": config_count,
        }

    @staticmethod
    def _server_endpoint(server_node, interface):
        """Resolve a CML interface label to a server node adapter/port pair."""
        ports = server_node.get("ports") or []
        normalized = str(interface or "").casefold().replace(" ", "")

        for port in ports:
            names = (port.get("name"), port.get("short_name"))
            if any(
                name is not None and str(name).casefold().replace(" ", "") == normalized
                for name in names
            ):
                return {
                    "node_id": server_node["node_id"],
                    "adapter_number": int(port.get("adapter_number", 0)),
                    "port_number": int(port.get("port_number", 0)),
                }

        adapter, port_number = GNS3Link._parse_interface(interface)
        if ports:
            for port in ports:
                if (
                    int(port.get("adapter_number", -1)) == adapter
                    and int(port.get("port_number", -1)) == port_number
                ):
                    return {
                        "node_id": server_node["node_id"],
                        "adapter_number": adapter,
                        "port_number": port_number,
                    }
            raise ValueError(
                f"Interface '{interface}' is not available on GNS3 node "
                f"'{server_node.get('name', server_node['node_id'])}'"
            )

        return {
            "node_id": server_node["node_id"],
            "adapter_number": adapter,
            "port_number": port_number,
        }
