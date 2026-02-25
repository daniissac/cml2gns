"""
Node mapping utilities for cml2gns.
"""
import logging

logger = logging.getLogger(__name__)


def _lookup(node_type, node_mappings):
    """Look up a node type with case-insensitive fallback."""
    if node_type in node_mappings:
        return node_mappings[node_type]

    lower = node_type.lower()
    for key, value in node_mappings.items():
        if key.lower() == lower:
            return value

    return None


def map_nodes(topology, node_mappings):
    """
    Map topology nodes to GNS3 templates based on node mappings.
    
    Performs an exact-match lookup first, then a case-insensitive fallback.
    Passes through ``properties`` from the mapping for GNS3 node generation.
    """
    unmapped_types = set()

    for node_id, node in topology.nodes.items():
        node_type = node.node_type or "unknown"

        mapping = _lookup(node_type, node_mappings)
        if mapping is not None:
            node.gns3_template = mapping.get("gns3_template", "qemu")
            node.console_type = mapping.get("console_type", "telnet")
            node.gns3_compute_type = mapping.get("compute_type", "qemu")
            node.gns3_symbol = mapping.get("symbol")
            node.gns3_properties = dict(mapping.get("properties", {}))

            if hasattr(node, 'ram') and node.ram and "ram" not in node.gns3_properties:
                node.gns3_properties["ram"] = node.ram

            logger.debug(f"Mapped node {node_id} ({node_type}) to {node.gns3_template}")
        else:
            node.gns3_template = "qemu"
            node.console_type = "telnet"
            node.gns3_compute_type = "qemu"
            node.gns3_symbol = None
            node.gns3_properties = {}
            unmapped_types.add(node_type)
            logger.warning(
                f"No mapping found for node type '{node_type}' (node ID: {node_id}). "
                f"Falling back to generic QEMU. Add it to a custom mapping file with --mapping."
            )

    if unmapped_types:
        sorted_types = ", ".join(sorted(unmapped_types))
        logger.warning(
            f"Unmapped node types: {sorted_types}. "
            f"Create a JSON mapping file and pass it with --mapping to fix this."
        )

    return topology
