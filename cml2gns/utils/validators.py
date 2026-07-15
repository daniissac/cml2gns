"""
Validation utilities for cml2gns.
"""

import logging
import uuid

logger = logging.getLogger(__name__)

GNS3_NODE_TYPES = {
    "cloud",
    "nat",
    "ethernet_hub",
    "ethernet_switch",
    "frame_relay_switch",
    "atm_switch",
    "docker",
    "dynamips",
    "vpcs",
    "traceng",
    "virtualbox",
    "vmware",
    "iou",
    "qemu",
}


def _validate_uuid(value, label):
    """Raise a readable error when a GNS3 identifier is not a UUID."""
    try:
        parsed = uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError(f"Invalid GNS3 project: {label} must be a UUID") from exc
    if str(parsed) != str(value).lower():
        raise ValueError(f"Invalid GNS3 project: {label} must be a canonical UUID")


def validate_topology(topology):
    """
    Validate a parsed topology for completeness and correctness.

    Args:
        topology: The parsed topology (CMLTopology or VIRLTopology)

    Raises:
        ValueError: If the topology is invalid
    """
    # Check if topology has a name
    if not topology.name:
        logger.warning("Topology has no name, using default")
        topology.name = "Unnamed Topology"

    # Check if topology has nodes
    if not topology.nodes:
        logger.error("Topology has no nodes")
        raise ValueError("Invalid topology: No nodes found")

    # Check if each link references valid nodes
    for link_id, link in topology.links.items():
        if link.node1_id not in topology.nodes:
            logger.error(f"Link {link_id} references non-existent node {link.node1_id}")
            raise ValueError(f"Invalid link {link_id}: Node {link.node1_id} not found")

        if link.node2_id not in topology.nodes:
            logger.error(f"Link {link_id} references non-existent node {link.node2_id}")
            raise ValueError(f"Invalid link {link_id}: Node {link.node2_id} not found")

    logger.info(
        f"Topology validation passed: {len(topology.nodes)} nodes, {len(topology.links)} links"
    )
    return True


def validate_gns3_project(project):
    """
    Validate a GNS3 project for completeness and correctness.

    Args:
        project: The GNS3 project

    Raises:
        ValueError: If the project is invalid
    """
    # Check if project has an ID
    if not project.project_id:
        logger.error("GNS3 project has no ID")
        raise ValueError("Invalid GNS3 project: No project ID")
    _validate_uuid(project.project_id, "project_id")

    # Check if project has a name
    if not project.name:
        logger.warning("GNS3 project has no name, using default")
        project.name = "Unnamed Project"

    # Check if project has nodes
    if not project.nodes:
        logger.error("GNS3 project has no nodes")
        raise ValueError("Invalid GNS3 project: No nodes found")

    names = set()
    for node_id, node in project.nodes.items():
        _validate_uuid(node_id, f"node_id {node_id}")
        if node.node_id != node_id:
            raise ValueError(
                f"Invalid GNS3 project: Node key {node_id} does not match node_id"
            )
        if not node.name:
            raise ValueError(f"Invalid GNS3 project: Node {node_id} has no name")
        normalized_name = node.name.casefold()
        if normalized_name in names:
            raise ValueError(f"Invalid GNS3 project: Duplicate node name '{node.name}'")
        names.add(normalized_name)
        if node.template_id:
            _validate_uuid(node.template_id, f"template_id for node {node.name}")
        if node.compute_type not in GNS3_NODE_TYPES:
            raise ValueError(
                f"Invalid GNS3 project: Unsupported node_type "
                f"'{node.compute_type}' for node {node.name}"
            )

    # Check if each link references valid nodes
    for link_id, link in project.links.items():
        _validate_uuid(link_id, f"link_id {link_id}")
        if link.node1_id not in project.nodes:
            logger.error(f"Link {link_id} references non-existent node {link.node1_id}")
            raise ValueError(f"Invalid link {link_id}: Node {link.node1_id} not found")

        if link.node2_id not in project.nodes:
            logger.error(f"Link {link_id} references non-existent node {link.node2_id}")
            raise ValueError(f"Invalid link {link_id}: Node {link.node2_id} not found")

    # Validate the serialized contract as well as the in-memory relationships.
    # This catches field-name regressions such as using ``type`` instead of the
    # GNS3 schema's required ``node_type`` key.
    document = project.to_dict()
    for key in ("project_id", "type", "revision", "version", "name", "topology"):
        if key not in document:
            raise ValueError(f"Invalid GNS3 project: Missing '{key}'")
    if document["type"] != "topology":
        raise ValueError("Invalid GNS3 project: type must be 'topology'")
    topology = document["topology"]
    for key in ("nodes", "links", "drawings", "computes"):
        if key not in topology or not isinstance(topology[key], list):
            raise ValueError(f"Invalid GNS3 project: topology.{key} must be a list")
    for node in topology["nodes"]:
        for key in ("name", "node_type", "compute_id"):
            if key not in node:
                raise ValueError(f"Invalid GNS3 project: Node is missing '{key}'")
        if "type" in node:
            raise ValueError(
                "Invalid GNS3 project: Node field must be 'node_type', not 'type'"
            )

    logger.info(
        f"GNS3 project validation passed: {len(project.nodes)} nodes, {len(project.links)} links"
    )
    return True
