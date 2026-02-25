"""
Parser for VIRL (XML) topology files.

Uses defusedxml for safe XML parsing (DTD/XXE protection).
"""
import re
import logging
from pathlib import Path

from defusedxml import ElementTree as ET

from cml2gns.models.virl_model import VIRLTopology, VIRLNode, VIRLLink

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
            tree = ET.parse(str(file_path))
            root = tree.getroot()
            
            ns_match = re.match(r'\{(.*)\}', root.tag)
            if ns_match:
                ns_uri = ns_match.group(1)
                nsmap = {'virl': ns_uri}
            else:
                nsmap = None

            def _find(parent, *local_names):
                """Find all child elements matching any of the given local names."""
                results = []
                for name in local_names:
                    if nsmap:
                        results.extend(parent.findall(f'./virl:{name}', nsmap))
                    else:
                        results.extend(parent.findall(f'./{name}'))
                return results

            def _find_one(parent, *local_names):
                """Find the first child element matching any of the given local names."""
                for name in local_names:
                    if nsmap:
                        elem = parent.find(f'./virl:{name}', nsmap)
                    else:
                        elem = parent.find(f'./{name}')
                    if elem is not None:
                        return elem
                return None

            topology = VIRLTopology(
                name=Path(file_path).stem,
                description='',
                notes='',
            )
            annotation = _find_one(root, 'annotation')
            if annotation is not None and annotation.text:
                topology.description = annotation.text

            for node_elem in _find(root, 'node', 'device'):
                node_id = node_elem.get('id') or node_elem.get('name')
                if not node_id:
                    continue
                
                node_type = node_elem.get('subtype') or node_elem.get('type')
                label = node_elem.get('name') or node_elem.get('label') or node_id
                
                x, y = 0, 0
                pos_elem = _find_one(node_elem, 'position')
                if pos_elem is not None:
                    x = float(pos_elem.get('x', 0))
                    y = float(pos_elem.get('y', 0))
                
                config = ''
                config_elem = _find_one(node_elem, 'configuration', 'config')
                if config_elem is not None:
                    config = config_elem.text or ''
                
                if not config:
                    for entry in _find(node_elem, 'extensions'):
                        for child in _find(entry, 'entry'):
                            if child.get('key') == 'config':
                                config = child.text or ''
                                break

                node = VIRLNode(
                    id=node_id,
                    label=label,
                    node_type=node_type,
                    x=x,
                    y=y,
                    configuration=config,
                    image=node_elem.get('image', '')
                )
                
                for intf_elem in _find(node_elem, 'interface'):
                    intf_id = intf_elem.get('id') or intf_elem.get('name')
                    if intf_id:
                        node.add_interface(intf_id)
                
                topology.add_node(node)
            
            for link_elem in _find(root, 'link', 'connection'):
                link_id = link_elem.get('id')
                
                endpoints = []
                for endpoint_elem in _find(link_elem, 'endpoint', 'interface'):
                    node_id = endpoint_elem.get('node') or endpoint_elem.get('device')
                    intf_id = endpoint_elem.get('interface') or endpoint_elem.get('port')
                    if node_id:
                        endpoints.append((node_id, intf_id))
                
                if not endpoints:
                    src = link_elem.get('src')
                    dst = link_elem.get('dst')
                    if src and dst:
                        endpoints = [
                            (src, link_elem.get('srcPort')),
                            (dst, link_elem.get('dstPort')),
                        ]
                
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
