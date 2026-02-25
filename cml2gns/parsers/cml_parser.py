"""
Parser for CML YAML files.

Supports both CML 2.0-style (dict-based nodes/links with node_a/interface_a)
and CML 2.5+-style (list-based nodes/links with n1/i1 shorthand, interface
definitions, and ``lab`` root key).
"""
import yaml
import logging
from pathlib import Path
from cml2gns.models.cml_model import CMLTopology, CMLNode, CMLLink, CMLInterface

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
            with open(file_path, 'r', encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f)

            topology_data = self._extract_topology_section(yaml_data, file_path)

            topology = CMLTopology(
                name=(topology_data.get('name')
                      or topology_data.get('title')
                      or Path(file_path).stem),
                description=topology_data.get('description', ''),
                notes=topology_data.get('notes', '')
            )
            
            self._parse_nodes(topology, topology_data)
            self._parse_links(topology, topology_data)
            self._parse_annotations(topology, topology_data)
            
            logger.info(
                f"Successfully parsed {len(topology.nodes)} nodes "
                f"and {len(topology.links)} links"
            )
            return topology
            
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML in {file_path}: {str(e)}")
            raise ValueError(f"Invalid YAML in CML file: {str(e)}")
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error parsing CML file {file_path}: {str(e)}")
            raise ValueError(f"Error parsing CML file: {str(e)}")

    @staticmethod
    def _extract_topology_section(yaml_data, file_path):
        """Extract the topology/lab section from the parsed YAML data."""
        if not isinstance(yaml_data, dict):
            raise ValueError("CML file root must be a YAML mapping")

        for key in ('topology', 'lab'):
            section = yaml_data.get(key)
            if section and isinstance(section, dict):
                return section

        if 'nodes' in yaml_data:
            return yaml_data

        raise ValueError(
            f"Missing 'topology' or 'lab' section in CML file: {file_path}"
        )

    def _parse_nodes(self, topology, topology_data):
        """Parse nodes from dict-keyed or list-based format."""
        nodes_data = topology_data.get('nodes')
        if not nodes_data:
            return

        if isinstance(nodes_data, dict):
            self._parse_nodes_dict(topology, nodes_data)
        elif isinstance(nodes_data, list):
            self._parse_nodes_list(topology, nodes_data)
        else:
            raise ValueError("'nodes' section must be a mapping or a list")

    def _parse_nodes_dict(self, topology, nodes_data):
        """Parse nodes stored as {node_id: {fields...}}."""
        for node_id, node_data in nodes_data.items():
            if not isinstance(node_data, dict):
                node_data = {}
            node = self._build_node(str(node_id), node_data)
            topology.add_node(node)

    def _parse_nodes_list(self, topology, nodes_data):
        """Parse nodes stored as [{id: ..., ...}, ...]."""
        for idx, node_data in enumerate(nodes_data):
            if not isinstance(node_data, dict):
                continue
            node_id = str(node_data.get('id', f'node_{idx}'))
            node = self._build_node(node_id, node_data)
            topology.add_node(node)

    @staticmethod
    def _build_node(node_id, node_data):
        node = CMLNode(
            id=node_id,
            label=node_data.get('label', node_id),
            node_type=node_data.get('node_definition'),
            x=node_data.get('x', 0),
            y=node_data.get('y', 0),
            configuration=node_data.get('configuration', ''),
            image_definition=node_data.get('image_definition', ''),
            ram=node_data.get('ram'),
            cpus=node_data.get('cpus'),
            boot_disk_size=node_data.get('boot_disk_size'),
            data_volume=node_data.get('data_volume'),
            cpu_limit=node_data.get('cpu_limit'),
            tags=node_data.get('tags', []),
        )

        interfaces_data = node_data.get('interfaces')
        if isinstance(interfaces_data, list):
            for iface in interfaces_data:
                if isinstance(iface, dict):
                    node.add_interface(CMLInterface(
                        id=iface.get('id'),
                        label=iface.get('label'),
                        slot=iface.get('slot'),
                        iface_type=iface.get('type'),
                    ))
                else:
                    node.add_interface(str(iface))

        return node

    def _parse_links(self, topology, topology_data):
        """Parse links from dict-keyed or list-based format."""
        links_data = topology_data.get('links')
        if not links_data:
            return

        if isinstance(links_data, dict):
            self._parse_links_dict(topology, links_data)
        elif isinstance(links_data, list):
            self._parse_links_list(topology, links_data)
        else:
            raise ValueError("'links' section must be a mapping or a list")

    def _parse_links_dict(self, topology, links_data):
        for link_id, link_data in links_data.items():
            if not isinstance(link_data, dict):
                continue
            link = self._build_link(str(link_id), link_data, topology)
            if link:
                topology.add_link(link)

    def _parse_links_list(self, topology, links_data):
        for idx, link_data in enumerate(links_data):
            if not isinstance(link_data, dict):
                continue
            link_id = str(link_data.get('id', f'link_{idx}'))
            link = self._build_link(link_id, link_data, topology)
            if link:
                topology.add_link(link)

    @staticmethod
    def _build_link(link_id, link_data, topology):
        """Build a CMLLink supporting both old and new key conventions."""
        node1 = (link_data.get('node_a')
                 or link_data.get('n1')
                 or link_data.get('src'))
        node2 = (link_data.get('node_b')
                 or link_data.get('n2')
                 or link_data.get('dst'))

        iface1_raw = (link_data.get('interface_a')
                      or link_data.get('i1')
                      or link_data.get('srcPort'))
        iface2_raw = (link_data.get('interface_b')
                      or link_data.get('i2')
                      or link_data.get('dstPort'))

        if node1 is None or node2 is None:
            logger.warning(f"Link {link_id}: missing endpoint node IDs, skipping")
            return None

        node1 = str(node1)
        node2 = str(node2)

        iface1 = CMLParser._resolve_interface(node1, iface1_raw, topology)
        iface2 = CMLParser._resolve_interface(node2, iface2_raw, topology)

        return CMLLink(
            id=link_id,
            node1_id=node1,
            interface1=iface1,
            node2_id=node2,
            interface2=iface2,
        )

    @staticmethod
    def _resolve_interface(node_id, iface_ref, topology):
        """Resolve an interface reference to a label.

        If the reference is a numeric interface ID and the node has interface
        definitions, map it to the interface label.  Otherwise pass it through.
        """
        if iface_ref is None:
            return None

        node = topology.nodes.get(str(node_id))
        if node is None:
            return str(iface_ref)

        return node.get_interface_label(iface_ref)

    @staticmethod
    def _parse_annotations(topology, topology_data):
        """Extract annotations/notes from the topology data."""
        annotations = topology_data.get('annotations')
        if isinstance(annotations, list):
            topology.annotations = annotations
