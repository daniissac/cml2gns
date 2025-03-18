"""
Generator for GNS3 project files.
"""
import os
import json
import shutil
import logging
import uuid
from pathlib import Path
from netbridge.models.gns3_model import GNS3Project, GNS3Node, GNS3Link

logger = logging.getLogger(__name__)


class GNS3Generator:
    """
    Generator for GNS3 project files from parsed CML/VIRL topologies.
    """
    
    def __init__(self):
        """Initialize the GNS3 generator."""
        pass
    
    def generate(self, topology, output_dir, project_id=None):
        """
        Generate a GNS3 project from a parsed topology.
        
        Args:
            topology: The parsed topology (CMLTopology or VIRLTopology)
            output_dir (Path): Directory to save the GNS3 project
            project_id (str): Optional project UUID
            
        Returns:
            dict: Statistics about the generated project
            
        Raises:
            ValueError: If generation fails
        """
        logger.info(f"Generating GNS3 project in {output_dir}")
        output_dir = Path(output_dir)
        
        # Create output directory if needed
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create GNS3 project structure
        project = GNS3Project(
            name=topology.name,
            project_id=project_id or str(uuid.uuid4())
        )
        
        # Map nodes from source topology to GNS3 nodes
        node_map = {}  # Maps original node IDs to GNS3 node UUIDs
        
        for node in topology.nodes.values():
            # Create a GNS3 node from the topology node
            gns3_node = GNS3Node(
                name=node.label,
                node_type=node.gns3_template if hasattr(node, 'gns3_template') else "qemu",
                node_id=str(uuid.uuid4()),
                console_type=node.console_type if hasattr(node, 'console_type') else "telnet",
                x=int(node.x),
                y=int(node.y)
            )
            
            project.add_node(gns3_node)
            node_map[node.id] = gns3_node.node_id
            
            # If node has configuration, save it to project directory
            if node.configuration:
                config_dir = output_dir / "configs"
                config_dir.mkdir(exist_ok=True)
                
                config_file = config_dir / f"{gns3_node.name}_{gns3_node.node_id}.cfg"
                with open(config_file, 'w') as f:
                    f.write(node.configuration)
                
                logger.debug(f"Saved configuration for node {node.id} to {config_file}")
        
        # Create links between GNS3 nodes
        for link in topology.links.values():
            # Check if both endpoints exist in our node map
            if link.node1_id in node_map and link.node2_id in node_map:
                gns3_link = GNS3Link(
                    link_id=str(uuid.uuid4()),
                    node1_id=node_map[link.node1_id],
                    node2_id=node_map[link.node2_id],
                    interface1=link.interface1,
                    interface2=link.interface2
                )
                project.add_link(gns3_link)
            else:
                logger.warning(f"Skipping link {link.id}: endpoint not found in node map")
        
        # Write project file
        project_file = output_dir / f"{project.name}.gns3"
        with open(project_file, 'w') as f:
            json.dump(project.to_dict(), f, indent=2)
        
        logger.info(f"Created GNS3 project file: {project_file}")
        
        # Return statistics
        return {
            "project_file": str(project_file),
            "node_count": len(project.nodes),
            "link_count": len(project.links)
        }