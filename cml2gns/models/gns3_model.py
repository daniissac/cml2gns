"""
Models for GNS3 projects.
"""
import re
import uuid

# Serial interface patterns for link_type detection
_SERIAL_PATTERN = re.compile(r'^[Ss]erial', re.IGNORECASE)


class GNS3Project:
    """
    Model for a GNS3 project.
    """
    
    DEFAULT_VERSION = "2.2.47"
    DEFAULT_REVISION = 9

    def __init__(self, name=None, project_id=None, version=None, revision=None):
        self.name = name or "Unnamed Project"
        self.project_id = project_id
        self.version = version or self.DEFAULT_VERSION
        self.revision = revision if revision is not None else self.DEFAULT_REVISION
        self.nodes = {}  # node_id -> GNS3Node
        self.links = {}  # link_id -> GNS3Link
        self.drawings = []  # list of GNS3Drawing
    
    def add_node(self, node):
        """Add a node to the project."""
        self.nodes[node.node_id] = node
    
    def add_link(self, link):
        """Add a link to the project."""
        self.links[link.link_id] = link

    def add_drawing(self, drawing):
        """Add a drawing/annotation to the project."""
        self.drawings.append(drawing)

    def to_dict(self):
        return {
            "project_id": self.project_id,
            "name": self.name,
            "auto_start": False,
            "auto_close": True,
            "scene_width": 2000,
            "scene_height": 1000,
            "revision": self.revision,
            "version": self.version,
            "type": "topology",
            "topology": {
                "nodes": [node.to_dict() for node in self.nodes.values()],
                "links": [link.to_dict() for link in self.links.values()],
                "drawings": [d.to_dict() for d in self.drawings],
                "computes": []
            }
        }
    
    def __repr__(self):
        return f"GNS3Project(name={self.name}, nodes={len(self.nodes)}, links={len(self.links)})"


class GNS3Node:
    """
    Model for a GNS3 node.
    """
    
    _TEMPLATE_NS = uuid.UUID('d3b10265-1c60-4a44-9ab3-90e8e4b0d2a0')

    def __init__(self, name=None, node_type=None, node_id=None,
                 console_type="telnet", compute_type="qemu", x=0, y=0,
                 symbol=None, properties=None):
        self.name = name
        self.node_type = node_type
        self.node_id = node_id
        self.console_type = console_type
        self.compute_type = compute_type
        self.x = x
        self.y = y
        self.symbol = symbol or ":/symbols/classic/computer.svg"
        self.properties = properties or {}
    
    def to_dict(self):
        template_id = str(uuid.uuid5(self._TEMPLATE_NS, self.node_type or "qemu"))
        return {
            "node_id": self.node_id,
            "name": self.name,
            "type": self.compute_type,
            "template_id": template_id,
            "compute_id": "local",
            "console_type": self.console_type,
            "console_auto_start": False,
            "symbol": self.symbol,
            "x": self.x,
            "y": self.y,
            "z": 1,
            "properties": dict(self.properties),
        }
    
    def __repr__(self):
        return f"GNS3Node(name={self.name}, type={self.node_type})"


class GNS3Link:
    """
    Model for a GNS3 link.
    """
    
    def __init__(self, link_id=None, node1_id=None, node2_id=None,
                 interface1=None, interface2=None):
        self.link_id = link_id
        self.node1_id = node1_id
        self.interface1 = interface1
        self.node2_id = node2_id
        self.interface2 = interface2
    
    def to_dict(self):
        adapter1, port1 = self._parse_interface(self.interface1)
        adapter2, port2 = self._parse_interface(self.interface2)
        return {
            "link_id": self.link_id,
            "link_type": self._detect_link_type(),
            "nodes": [
                {
                    "node_id": self.node1_id,
                    "adapter_number": adapter1,
                    "port_number": port1,
                },
                {
                    "node_id": self.node2_id,
                    "adapter_number": adapter2,
                    "port_number": port2,
                },
            ],
            "suspend": False,
        }

    def _detect_link_type(self):
        """Return 'serial' if either interface looks like a serial port."""
        for iface in (self.interface1, self.interface2):
            if iface and _SERIAL_PATTERN.match(str(iface)):
                return "serial"
        return "ethernet"

    @staticmethod
    def _parse_interface(interface):
        """
        Parse an interface name into adapter and port numbers.
        
        For interfaces like GigabitEthernet0/1, the first number (0) is the
        adapter and the second (1) is the port. For single-number interfaces
        like eth0, the number is the adapter and port defaults to 0.
        """
        if interface is None:
            return 0, 0

        if isinstance(interface, (int, float)):
            return int(interface), 0

        match = re.search(r'(\d+)/(\d+)(?:/(\d+))?$', str(interface))
        if match:
            if match.group(3) is not None:
                return int(match.group(1)), int(match.group(3))
            return int(match.group(1)), int(match.group(2))

        match = re.search(r'(\d+)$', str(interface))
        if match:
            return int(match.group(1)), 0

        return 0, 0
    
    def __repr__(self):
        return f"GNS3Link(id={self.link_id}, {self.node1_id}:{self.interface1} <-> {self.node2_id}:{self.interface2})"


class GNS3Drawing:
    """
    Model for a GNS3 drawing (annotation/label/shape on the canvas).
    """

    def __init__(self, drawing_id=None, svg=None, x=0, y=0, z=0,
                 rotation=0, locked=False):
        self.drawing_id = drawing_id or str(uuid.uuid4())
        self.svg = svg or ""
        self.x = x
        self.y = y
        self.z = z
        self.rotation = rotation
        self.locked = locked

    def to_dict(self):
        return {
            "drawing_id": self.drawing_id,
            "svg": self.svg,
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "rotation": self.rotation,
            "locked": self.locked,
        }

    @staticmethod
    def from_text(text, x=0, y=0, font_size=14, color="#000000"):
        """Create a drawing from plain text (renders as an SVG text element)."""
        escaped = (text.replace("&", "&amp;")
                       .replace("<", "&lt;")
                       .replace(">", "&gt;"))
        height = font_size + 10
        width = max(len(text) * (font_size // 2), 50)
        svg = (
            f'<svg width="{width}" height="{height}">'
            f'<text font-family="monospace" font-size="{font_size}" '
            f'fill="{color}" x="0" y="{font_size}">{escaped}</text></svg>'
        )
        return GNS3Drawing(svg=svg, x=x, y=y)

    def __repr__(self):
        return f"GNS3Drawing(id={self.drawing_id}, x={self.x}, y={self.y})"
