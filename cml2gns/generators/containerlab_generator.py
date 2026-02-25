"""
Generator for containerlab .clab.yml topology files.
"""
import yaml
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_CML_TO_KIND = {
    "iosv": "cisco_iosv",
    "iosvl2": "cisco_iosvl2",
    "csr1000v": "cisco_csr1000v",
    "cat8000v": "cisco_cat8000v",
    "iosxrv": "cisco_xrv",
    "iosxrv9000": "cisco_xrv9000",
    "nxosv": "cisco_nxos",
    "nxosv9000": "cisco_n9kv",
    "asav": "cisco_asav",
    "ftdv": "cisco_ftdv",
    "linux": "linux",
    "alpine": "linux",
    "unmanaged_switch": "bridge",
    "external_connector": "bridge",
}


class ContainerlabGenerator:
    """
    Generate containerlab .clab.yml files from a parsed topology.
    """

    def generate(self, topology, output_file):
        output_file = Path(output_file)
        logger.info(f"Generating containerlab file: {output_file}")

        node_label = {}
        for node in topology.nodes.values():
            node_label[node.id] = node.label

        nodes_section = {}
        for node in topology.nodes.values():
            kind = _CML_TO_KIND.get(
                getattr(node, 'node_type', '') or '', "linux"
            )
            nodes_section[node.label] = {"kind": kind}

        links_section = []
        for link in topology.links.values():
            n1 = node_label.get(link.node1_id, link.node1_id)
            n2 = node_label.get(link.node2_id, link.node2_id)
            i1 = link.interface1 or "eth0"
            i2 = link.interface2 or "eth0"
            links_section.append({
                "endpoints": [f"{n1}:{i1}", f"{n2}:{i2}"]
            })

        clab = {
            "name": topology.name,
            "topology": {
                "nodes": nodes_section,
                "links": links_section,
            },
        }

        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(clab, f, default_flow_style=False, sort_keys=False)

        return {
            "output_file": str(output_file),
            "node_count": len(nodes_section),
            "link_count": len(links_section),
        }
