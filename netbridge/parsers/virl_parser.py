"""
Parser for VIRL (XML) topology files.
"""
import re
import xml.etree.ElementTree as ET
import logging
from pathlib import Path
from netbridge.models.virl_model import VIRLTopology, VIRLNode, VIRLLink

logger = logging.getLogger(__name__)


class VIRLParser:
    """
    Parser for Virtual Internet Routing Lab (VIRL) XML topology files.
    """
    
    def parse(self, file_path):
        """
        Parse a VIRL XML file into a topology model.
        
        Args:
            file_path (Path): Path to the VIRL XML file
            
        Returns:
            VIRLTopology: Parsed topology object
            
        Raises:
            ValueError: If the file cannot be parsed as valid VIRL XML
        """
        logger.info(f"Parsing VIRL file: {file_path}")
        
        try:
            # Parse XML
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Determine XML namespace if present
            ns = {}
            match = re.match(r'\{(.*)\}', root.tag)
            if match:
                ns['virl'] = match.group(1)
                nsmap = {'virl': ns['virl']}
            else:
                nsmap = None
            
            # Extract topology metadata
            topology = VIRLTopology(
                name=Path(file_path).stem,
                description=self._get_text(root, './virl:annotation', nsmap) or '',
                notes=''
            )
            
            # Parse nodes (in VIRL they might be called 'node' or 'device')
            for node_elem in root.findall('./virl:node', nsmap) + root.findall('./virl:device', nsmap):
                node_id = node_elem.get('id') or node_elem.get('name')
                if not node_id:
                    continue
                
                node_type = node_elem.get('type') or node_elem.get('subtype')
                label = node_elem.get('name') or node_elem.get('label') or node_id
                
                # Get position if available
                x, y = 0, 0
                pos_elem = node_elem.find('./virl:position', nsmap)
                if pos_elem is not None:
                    x = float(pos_elem.get('x', 0))
                    y = float(pos_elem.get('y', 0))
                
                # Get configuration if available
                config = ''
                config_elem = node_elem.find('./virl:configuration', nsmap) or node_elem.find('./virl:config', nsmap)
                if config_elem is not None:
                    config = config_elem.text or ''
                
                # Create node object
                node = VIRLNode(
                    id=node_id,
                    label=label,
                    node_type=node_type,
                    x=x,
                    y=y,
                    configuration=config,
                    image=node_elem.get('image', '')
                )
                
                # Add interfaces to node
                for intf_elem in node_elem.findall('./virl:interface', nsmap):
                    intf_id = intf_elem.get('id') or intf_elem.get('name')
                    if intf_id:
                        node.add_interface(intf_id)
                
                topology.add_node(node)
            
            # Parse links
            for link_elem in root.findall('./virl:link', nsmap) + root.findall('./virl:connection', nsmap):
                link_id = link_elem.get('id')
                
                # Links connect two interfaces
                endpoints = []
                for endpoint_elem in link_elem.findall('./virl:endpoint', nsmap) + link_elem.findall('./virl:interface', nsmap):
                    node_id = endpoint_elem.get('node') or endpoint_elem.get('device')
                    intf_id = endpoint_elem.get('interface') or endpoint_elem.get('port')
                    if node_id:
                        endpoints.append((node_id, intf_id))
                
                # Create link if we have two endpoints
                if len(endpoints) >= 2:
                    link = VIRLLink(
                        id=link_id or f"link_{len(topology.links) + 1}",
                        node1_id=endpoints[0][0],
                        interface1=endpoints[0][1],
                        node2_id=endpoints[1][0],
                        interface2=endpoints[1][1]
                    )
                    topology.add_link(link)
            
            logger.info(f"Successfully parsed {len(topology.nodes)} nodes and {len(topology.links)} links")
            return topology
            
        except ET.ParseError as e:
            logger.error(f"Error parsing XML in {file_path}: {str(e)}")
            raise ValueError(f"Invalid XML in VIRL file: {str(e)}")
        except Exception as e:
            logger.error(f"Error parsing VIRL file {file_path}: {str(e)}")
            raise ValueError(f"Error parsing VIRL file: {str(e)}")
    
    def _get_text(self, elem, xpath, nsmap):
        """Helper to get text from an XML element."""
        try:
            sub_elem = elem.find(xpath, nsmap)
            return sub_elem.text if sub_elem is not None else None
        except:
            return None