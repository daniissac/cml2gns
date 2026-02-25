"""
Parser for containerlab .clab.yml topology files.
"""
import yaml
import logging
from pathlib import Path

from cml2gns.models.cml_model import CMLTopology, CMLNode, CMLLink

logger = logging.getLogger(__name__)

_KIND_TO_CML = {
    "cisco_iosv": "iosv",
    "cisco_iosvl2": "iosvl2",
    "cisco_csr1000v": "csr1000v",
    "cisco_cat8000v": "cat8000v",
    "cisco_xrd": "iosxrv9000",
    "cisco_xrv": "iosxrv",
    "cisco_xrv9000": "iosxrv9000",
    "cisco_nxos": "nxosv9000",
    "cisco_n9kv": "nxosv9000",
    "cisco_ftdv": "ftdv",
    "cisco_asav": "asav",
    "linux": "linux",
    "bridge": "unmanaged_switch",
    "ovs-bridge": "unmanaged_switch",
    "srl": "linux",
    "ceos": "linux",
    "vr-ros": "linux",
}


class ContainerlabParser:
    """
    Parser for containerlab .clab.yml topology files.
    """

    def parse(self, file_path):
        file_path = Path(file_path)
        logger.info(f"Parsing containerlab file: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                raise ValueError("Containerlab file root must be a YAML mapping")

            name = data.get("name", file_path.stem)
            topology = CMLTopology(name=name)

            topo_section = data.get("topology", {})
            kinds = topo_section.get("kinds", {})
            defaults = topo_section.get("defaults", {})

            nodes_data = topo_section.get("nodes", {})
            if not isinstance(nodes_data, dict):
                raise ValueError("'topology.nodes' must be a mapping")

            x_pos = 0
            for node_name, node_data in nodes_data.items():
                if not isinstance(node_data, dict):
                    node_data = {}

                kind = node_data.get("kind", "")
                kind_defaults = kinds.get(kind, {}) if kind else {}

                node_type = _KIND_TO_CML.get(kind, kind or "linux")

                config = ""
                startup_config = (
                    node_data.get("startup-config")
                    or kind_defaults.get("startup-config")
                    or ""
                )
                if startup_config and Path(startup_config).exists():
                    try:
                        with open(startup_config, 'r', encoding='utf-8') as cf:
                            config = cf.read()
                    except OSError:
                        pass

                node = CMLNode(
                    id=node_name,
                    label=node_data.get("labels", {}).get("label", node_name)
                    if isinstance(node_data.get("labels"), dict) else node_name,
                    node_type=node_type,
                    x=x_pos,
                    y=0,
                    configuration=config,
                )
                x_pos += 200
                topology.add_node(node)

            links_data = topo_section.get("links", [])
            for idx, link_entry in enumerate(links_data):
                endpoints = self._parse_link_entry(link_entry)
                if endpoints and len(endpoints) >= 2:
                    link = CMLLink(
                        id=f"link_{idx}",
                        node1_id=endpoints[0][0],
                        interface1=endpoints[0][1],
                        node2_id=endpoints[1][0],
                        interface2=endpoints[1][1],
                    )
                    topology.add_link(link)

            logger.info(
                f"Parsed containerlab topology: {len(topology.nodes)} nodes, "
                f"{len(topology.links)} links"
            )
            return topology

        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in containerlab file: {e}")
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Error parsing containerlab file: {e}")

    @staticmethod
    def _parse_link_entry(entry):
        """Parse a containerlab link entry into [(node, iface), ...]."""
        if isinstance(entry, dict):
            eps = entry.get("endpoints", [])
            if isinstance(eps, list) and len(eps) >= 2:
                return [ContainerlabParser._split_endpoint(e) for e in eps[:2]]
            return None

        if isinstance(entry, str) and ":" in entry:
            parts = entry.split("---") if "---" in entry else entry.split(",")
            if len(parts) >= 2:
                return [ContainerlabParser._split_endpoint(p.strip()) for p in parts[:2]]
        return None

    @staticmethod
    def _split_endpoint(ep_str):
        """Split 'node:interface' string."""
        ep_str = str(ep_str).strip()
        if ":" in ep_str:
            node, iface = ep_str.split(":", 1)
            return node.strip(), iface.strip()
        return ep_str, ""
