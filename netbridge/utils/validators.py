"""
Validation utilities for NetBridge.
"""
import logging

logger = logging.getLogger(__name__)


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
    
    logger.info(f"Topology validation passed: {len(topology.nodes)} nodes, {len(topology.links)} links")
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
    
    # Check if project has a name
    if not project.name:
        logger.warning("GNS3 project has no name, using default")
        project.name = "Unnamed Project"
    
    # Check if project has nodes
    if not project.nodes:
        logger.error("GNS3 project has no nodes")
        raise ValueError("Invalid GNS3 project: No nodes found")
    
    # Check if each link references valid nodes
    for link_id, link in project.links.items():
        if link.node1_id not in project.nodes:
            logger.error(f"Link {link_id} references non-existent node {link.node1_id}")
            raise ValueError(f"Invalid link {link_id}: Node {link.node1_id} not found")
        
        if link.node2_id not in project.nodes:
            logger.error(f"Link {link_id} references non-existent node {link.node2_id}")
            raise ValueError(f"Invalid link {link_id}: Node {link.node2_id} not found")
    
    logger.info(f"GNS3 project validation passed: {len(project.nodes)} nodes, {len(project.links)} links")
    return True