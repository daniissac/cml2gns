"""
Models for CML topologies.
"""


class CMLTopology:
    """
    Model for a CML topology.
    """
    
    def __init__(self, name=None, description=None, notes=None):
        """
        Initialize a CML topology.
        
        Args:
            name (str): Topology name
            description (str): Topology description
            notes (str): Additional notes
        """
        self.name = name or "Unnamed Topology"
        self.description = description or ""
        self.notes = notes or ""
        self.nodes = {}  # id -> CMLNode
        self.links = {}  # id -> CMLLink
    
    def add_node(self, node):
        """Add a node to the topology."""
        self.nodes[node.id] = node
    
    def add_link(self, link):
        """Add a link to the topology."""
        self.links[link.id] = link
    
    def __repr__(self):
        return f"CMLTopology(name={self.name}, nodes={len(self.nodes)}, links={len(self.links)})"


class CMLNode:
    """
    Model for a CML node.
    """
    
    def __init__(self, id, label=None, node_type=None, x=0, y=0, configuration=None, image_definition=None):
        """
        Initialize a CML node.
        
        Args:
            id (str): Node ID
            label (str): Display label
            node_type (str): Node type/definition
            x (float): X position
            y (float): Y position
            configuration (str): Node configuration
            image_definition (str): Image definition
        """
        self.id = id
        self.label = label or id
        self.node_type = node_type
        self.x = x
        self.y = y
        self.configuration = configuration or ""
        self.image_definition = image_definition
        self.interfaces = []
        
        # Will be filled in during node mapping
        self.gns3_template = None
        self.console_type = None
    
    def add_interface(self, interface_id):
        """Add an interface to the node."""
        self.interfaces.append(interface_id)
    
    def __repr__(self):
        return f"CMLNode(id={self.id}, type={self.node_type})"


class CMLLink:
    """
    Model for a CML link.
    """
    
    def __init__(self, id, node1_id, interface1, node2_id, interface2):
        """
        Initialize a CML link.
        
        Args:
            id (str): Link ID
            node1_id (str): ID of first node
            interface1 (str): Interface on first node
            node2_id (str): ID of second node
            interface2 (str): Interface on second node
        """
        self.id = id
        self.node1_id = node1_id
        self.interface1 = interface1
        self.node2_id = node2_id
        self.interface2 = interface2
    
    def __repr__(self):
        return f"CMLLink(id={self.id}, {self.node1_id}:{self.interface1} <-> {self.node2_id}:{self.interface2})"