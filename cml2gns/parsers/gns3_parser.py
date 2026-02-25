"""
Parser for GNS3 project (.gns3) JSON files.

Produces a CMLTopology so the same topology model can be used for
reverse conversion back to CML YAML.
"""
import json
import logging
from pathlib import Path

from cml2gns.models.cml_model import CMLTopology, CMLNode, CMLLink

logger = logging.getLogger(__name__)

# Reverse map: GNS3 compute type -> approximate CML node_definition
_COMPUTE_TO_CML = {
    "qemu": "linux",
    "docker": "alpine",
    "iou": "iol",
    "ethernet_switch": "unmanaged_switch",
    "cloud": "external_connector",
    "vpcs": "linux",
}


class GNS3Parser:
    """
    Parser for GNS3 .gns3 project JSON files.
    """

    def parse(self, file_path):
        """
        Parse a .gns3 file into a CMLTopology.

        Args:
            file_path (Path): Path to the .gns3 file

        Returns:
            CMLTopology: Parsed topology
        """
        file_path = Path(file_path)
        logger.info(f"Parsing GNS3 file: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            name = data.get("name", file_path.stem)
            topology = CMLTopology(name=name)

            topo_section = data.get("topology", {})

            node_id_map = {}

            for node_data in topo_section.get("nodes", []):
                node_id = node_data.get("node_id", "")
                label = node_data.get("name", node_id)
                compute_type = node_data.get("type", "qemu")
                node_type = _COMPUTE_TO_CML.get(compute_type, "linux")

                node = CMLNode(
                    id=node_id,
                    label=label,
                    node_type=node_type,
                    x=node_data.get("x", 0),
                    y=node_data.get("y", 0),
                )
                topology.add_node(node)
                node_id_map[node_id] = node

            for idx, link_data in enumerate(topo_section.get("links", [])):
                link_id = link_data.get("link_id", f"link_{idx}")
                link_nodes = link_data.get("nodes", [])
                if len(link_nodes) < 2:
                    continue

                ep1 = link_nodes[0]
                ep2 = link_nodes[1]

                iface1 = self._format_interface(ep1)
                iface2 = self._format_interface(ep2)

                link = CMLLink(
                    id=link_id,
                    node1_id=ep1.get("node_id", ""),
                    interface1=iface1,
                    node2_id=ep2.get("node_id", ""),
                    interface2=iface2,
                )
                topology.add_link(link)

            logger.info(
                f"Parsed GNS3 project: {len(topology.nodes)} nodes, "
                f"{len(topology.links)} links"
            )
            return topology

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in GNS3 file: {e}")
        except Exception as e:
            raise ValueError(f"Error parsing GNS3 file: {e}")

    @staticmethod
    def _format_interface(endpoint):
        adapter = endpoint.get("adapter_number", 0)
        port = endpoint.get("port_number", 0)
        return f"GigabitEthernet{adapter}/{port}"
