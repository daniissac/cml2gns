"""
Models for GNS3 projects.
"""
import json


class GNS3Project:
    """
    Model for a GNS3 project.
    """
    
    def __init__(self, name=None, project_id=None):
        """
        Initialize a GNS3 project.
        
        Args:
            name (str): Project name
            project_id (str): Project UUID
        """
        self.name = name or "Unnamed Project"
        self.project_id = project_id
        self.nodes = {}  # node_id -> GNS3Node
        self.links = {}  # link_id -> GNS3Link
    
    def add_node(self, node):
        """Add a node to the project."""
        self.nodes[node.node_id] = node
    
    def add_link(self, link):
        """Add a link to the project."""
        self.links[link.link_id] = link
    
    def to_dict(self):
        """
        Convert project to GNS3 project format.
        
        Returns:
            dict: GNS3 project dictionary
        """
        return {
            "project_id": self.project_id,
            "name": self.name,
            "auto_start": False,
            "auto_close": True,
            "scene_width": 2000,
            "scene_height": 1000,
            "version": "2.2.27",
            "type": "topology",
            "topology": {
                "nodes": [node.to_dict() for node in self.nodes.values()],
                "links": [link.to_dict() for link in self.links.values()]
            }
        }
    
    def __repr__(self):
        return f"GNS3Project(name={self.name}, nodes={len(self.nodes)}, links={len(self.links)})"


class GNS3Node:
    """
    Model for a GNS3 node.
    """
    
    def __init__(self, name=None, node_type=None, node_id=None, console_type="telnet", x=0, y=0):
        """
        Initialize a GNS3 node.
        
        Args:
            name (str): Node name
            node_type (str): Node type (template)
            node_id (str): Node UUID
            console_type (str): Console type (telnet, vnc, etc.)
            x (int): X position
            y (int): Y position
        """
        self.name = name
        self.node_type = node_type
        self.node_id = node_id
        self.console_type = console_type
        self.x = x
        self.y = y
    
    def to_dict(self):
        """
        Convert node to GNS3 node format.
        
        Returns:
            dict: GNS3 node dictionary
        """
        return {
            "id": self.node_id,
            "name": self.name,
            "type": self.node_type,
            "template_id": f"template-{self.node_type.lower()}",
            "compute_id": "local",
            "console_type": self.console_type,
            "console_auto_start": False,
            "symbol": f":/symbols/{self.node_type.lower()}.svg",
            "x": self.x,
            "y": self.y,
            "z": 1,
            "properties": {}
        }
    
    def __repr__(self):
        return f"GNS3Node(name={self.name}, type={self.node_type})"


class GNS3Link:
    """
    Model for a GNS3 link.
    """
    
    def __init__(self, link_id=None, node1_id=None, node2_id=None, interface1=None, interface2=None):
        """
        Initialize a GNS3 link.
        
        Args:
            link_id (str): Link UUID
            node1_id (str): ID of first node
            interface1 (str): Interface on first node
            node2_id (str): ID of second node
            interface2 (str): Interface on second node
        """
        self.link_id = link_id
        self.node1_id = node1_id
        self.interface1 = interface1
        self.node2_id = node2_id
        self.interface2 = interface2
    
    def to_dict(self):
        """
        Convert link to GNS3 link format.
        
        Returns:
            dict: GNS3 link dictionary
        """
        return {
            "id": self.link_id,
            "link_type": "ethernet",
            "nodes": [
                {
                    "node_id": self.node1_id,
                    "adapter_number": 0,
                    "port_number": self._interface_to_port(self.interface1)
                },
                {
                    "node_id": self.node2_id,
                    "adapter_number": 0,
                    "port_number": self._interface_to_port(self.interface2)
                }
            ],
            "suspend": False
        }
    
    def _interface_to_port(self, interface):
        """
        Convert interface name to port number.
        
        Args:
            interface (str): Interface name
            
        Returns:
            int: Port number
        """
        if interface is None:
            return 0
            
        # Try to extract a number from the interface
        if isinstance(interface, (int, float)):
            return int(interface)
            
        # Try to extract number from interface name (e.g., GigabitEthernet0/1 -> 1)
        import re
        match = re.search(r'(\d+)/?(\d+)?$', str(interface))
        if match:
            if match.group(2):
                return int(match.group(2))
            return int(match.group(1))
        
        # Default to 0 if no number found
        return 0
    
    def __repr__(self):
        return f"GNS3Link(id={self.link_id}, {self.node1_id}:{self.interface1} <-> {self.node2_id}:{self.interface2})"