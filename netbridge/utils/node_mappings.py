"""
Node mapping utilities for NetBridge.
"""
import logging

logger = logging.getLogger(__name__)


def map_nodes(topology, node_mappings):
    """
    Map topology nodes to GNS3 templates based on node mappings.
    
    Args:
        topology: The parsed topology (CMLTopology or VIRLTopology)
        node_mappings (dict): Mapping from node types to GNS3 templates
        
    Returns:
        The same topology object with GNS3 template information added to nodes
        
    Raises:
        ValueError: If a required node type mapping is missing
    """
    for node_id, node in topology.nodes.items():
        # Get the node type (or use a default if missing)
        node_type = node.node_type or "unknown"
        
        # Check if we have a mapping for this node type
        if node_type in node_mappings:
            mapping = node_mappings[node_type]
            node.gns3_template = mapping.get("gns3_template", "qemu")
            node.console_type = mapping.get("console_type", "telnet")
            logger.debug(f"Mapped node {node_id} ({node_type}) to {node.gns3_template}")
        else:
            # Use a default mapping for unknown node types
            node.gns3_template = "qemu"
            node.console_type = "telnet"
            logger.warning(f"No mapping found for node type '{node_type}' (node ID: {node_id})")
    
    return topology


def create_default_mapping():
    """
    Create a default node mapping configuration.
    
    Returns:
        dict: Default node mapping configuration
    """
    return {
        "iosv": {
            "gns3_template": "Cisco IOSv",
            "console_type": "telnet"
        },
        "iosvl2": {
            "gns3_template": "Cisco IOSvL2",
            "console_type": "telnet"
        },
        "csr1000v": {
            "gns3_template": "Cisco CSR1000v",
            "console_type": "telnet"
        },
        "nxosv": {
            "gns3_template": "Cisco NX-OSv",
            "console_type": "telnet"
        },
        "asav": {
            "gns3_template": "Cisco ASAv",
            "console_type": "telnet"
        },
        "linux": {
            "gns3_template": "Linux",
            "console_type": "telnet"
        }
    }