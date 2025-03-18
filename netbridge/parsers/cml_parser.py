"""
Parser for CML YAML files.
"""
import yaml
import logging
from pathlib import Path
from netbridge.models.cml_model import CMLTopology, CMLNode, CMLLink

logger = logging.getLogger(__name__)


class CMLParser:
    """
    Parser for Cisco Modeling Labs (CML) YAML topology files.
    """
    
    def parse(self, file_path):
        """
        Parse a CML YAML file into a topology model.
        
        Args:
            file_path (Path): Path to the CML YAML file
            
        Returns:
            CMLTopology: Parsed topology object
            
        Raises:
            ValueError: If the file cannot be parsed as valid CML YAML
        """
        logger.info(f"Parsing CML file: {file_path}")
        
        try:
            with open(file_path, 'r') as f:
                yaml_data = yaml.safe_load(f)
            
            # Validate basic structure
            if not yaml_data.get('topology'):
                raise ValueError("Missing 'topology' section in CML file")

            # Extract topology metadata
            topology_data = yaml_data['topology']
            topology = CMLTopology(
                name=topology_data.get('name', Path(file_path).stem),
                description=topology_data.get('description', ''),
                notes=topology_data.get('notes', '')
            )
            
            # Parse nodes
            nodes_data = topology_data.get('nodes', {})
            for node_id, node_data in nodes_data.items():
                node = CMLNode(
                    id=node_id,
                    label=node_data.get('label', node_id),
                    node_type=node_data.get('node_definition'),
                    x=node_data.get('x', 0),
                    y=node_data.get('y', 0),
                    configuration=node_data.get('configuration', ''),
                    image_definition=node_data.get('image_definition', '')
                )
                topology.add_node(node)
                
            # Parse links
            links_data = topology_data.get('links', {})
            for link_id, link_data in links_data.items():
                # In CML, links connect interfaces on nodes
                link = CMLLink(
                    id=link_id,
                    node1_id=link_data.get('node_a'),
                    interface1=link_data.get('interface_a'),
                    node2_id=link_data.get('node_b'),
                    interface2=link_data.get('interface_b')
                )
                topology.add_link(link)
            
            logger.info(f"Successfully parsed {len(topology.nodes)} nodes and {len(topology.links)} links")
            return topology
            
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML in {file_path}: {str(e)}")
            raise ValueError(f"Invalid YAML in CML file: {str(e)}")
        except Exception as e:
            logger.error(f"Error parsing CML file {file_path}: {str(e)}")
            raise ValueError(f"Error parsing CML file: {str(e)}")