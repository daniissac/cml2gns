"""
Models for CML topologies.
"""


class CMLTopology:
    """
    Model for a CML topology.
    """
    
    def __init__(self, name=None, description=None, notes=None):
        self.name = name or "Unnamed Topology"
        self.description = description or ""
        self.notes = notes or ""
        self.nodes = {}  # id -> CMLNode
        self.links = {}  # id -> CMLLink
        self.annotations = []  # list of annotation dicts or strings
    
    def add_node(self, node):
        """Add a node to the topology."""
        self.nodes[node.id] = node
    
    def add_link(self, link):
        """Add a link to the topology."""
        self.links[link.id] = link

    def to_dict(self):
        """Serialize the topology back to CML YAML-compatible dict."""
        return {
            "lab": {
                "title": self.name,
                "description": self.description,
                "notes": self.notes,
                "nodes": [node.to_dict() for node in self.nodes.values()],
                "links": [link.to_dict() for link in self.links.values()],
            }
        }

    def __repr__(self):
        return f"CMLTopology(name={self.name}, nodes={len(self.nodes)}, links={len(self.links)})"


class CMLInterface:
    """
    Model for a CML node interface.
    """

    def __init__(self, id, label=None, slot=None, iface_type=None):
        self.id = id
        self.label = label
        self.slot = slot
        self.type = iface_type

    def to_dict(self):
        d = {"id": self.id}
        if self.label:
            d["label"] = self.label
        if self.slot is not None:
            d["slot"] = self.slot
        if self.type:
            d["type"] = self.type
        return d

    def __repr__(self):
        return f"CMLInterface(id={self.id}, label={self.label})"


class CMLNode:
    """
    Model for a CML node.
    """
    
    def __init__(self, id, label=None, node_type=None, x=0, y=0,
                 configuration=None, image_definition=None,
                 ram=None, cpus=None, boot_disk_size=None,
                 data_volume=None, cpu_limit=None, tags=None):
        self.id = id
        self.label = label or id
        self.node_type = node_type
        self.x = x
        self.y = y
        self.configuration = configuration or ""
        self.image_definition = image_definition
        self.ram = ram
        self.cpus = cpus
        self.boot_disk_size = boot_disk_size
        self.data_volume = data_volume
        self.cpu_limit = cpu_limit
        self.tags = tags or []
        self.interfaces = []  # list of CMLInterface or str
        
        # Will be filled in during node mapping
        self.gns3_template = None
        self.console_type = None
    
    def add_interface(self, interface):
        """Add an interface to the node (CMLInterface or str)."""
        self.interfaces.append(interface)

    def get_interface_label(self, interface_id):
        """Resolve an interface ID to its label, falling back to the ID itself."""
        for iface in self.interfaces:
            if isinstance(iface, CMLInterface):
                if str(iface.id) == str(interface_id):
                    return iface.label or str(interface_id)
            elif str(iface) == str(interface_id):
                return str(iface)
        return str(interface_id) if interface_id is not None else None

    def to_dict(self):
        d = {
            "id": self.id,
            "label": self.label,
            "node_definition": self.node_type,
            "x": self.x,
            "y": self.y,
            "configuration": self.configuration,
        }
        if self.image_definition:
            d["image_definition"] = self.image_definition
        if self.ram is not None:
            d["ram"] = self.ram
        if self.cpus is not None:
            d["cpus"] = self.cpus
        if self.interfaces:
            d["interfaces"] = [
                iface.to_dict() if isinstance(iface, CMLInterface) else {"id": iface}
                for iface in self.interfaces
            ]
        if self.tags:
            d["tags"] = self.tags
        return d

    def __repr__(self):
        return f"CMLNode(id={self.id}, type={self.node_type})"


class CMLLink:
    """
    Model for a CML link.
    """
    
    def __init__(self, id, node1_id, interface1, node2_id, interface2):
        self.id = id
        self.node1_id = node1_id
        self.interface1 = interface1
        self.node2_id = node2_id
        self.interface2 = interface2

    def to_dict(self):
        return {
            "id": self.id,
            "n1": self.node1_id,
            "i1": self.interface1,
            "n2": self.node2_id,
            "i2": self.interface2,
        }

    def __repr__(self):
        return f"CMLLink(id={self.id}, {self.node1_id}:{self.interface1} <-> {self.node2_id}:{self.interface2})"