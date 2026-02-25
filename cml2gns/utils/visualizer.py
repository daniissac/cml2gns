"""
ASCII topology visualizer.

Produces a human-readable text diagram of nodes, links, and basic
layout information for quick terminal-based topology preview.
"""
import logging

logger = logging.getLogger(__name__)


def visualize_topology(topology):
    """
    Render a topology as an ASCII string.

    Returns:
        str: multi-line ASCII visualization.
    """
    lines = []
    lines.append(_header(topology))
    lines.append("")
    lines.append(_node_table(topology))
    lines.append("")
    lines.append(_link_table(topology))
    lines.append("")
    lines.append(_ascii_graph(topology))
    return "\n".join(lines)


def _header(topology):
    name = getattr(topology, 'name', 'Unknown')
    desc = getattr(topology, 'description', '')
    parts = [f"Topology: {name}"]
    if desc:
        parts.append(f"  Description: {desc}")
    parts.append(
        f"  Nodes: {len(topology.nodes)}  Links: {len(topology.links)}"
    )
    border = "=" * max(len(p) for p in parts)
    return "\n".join([border] + parts + [border])


def _node_table(topology):
    rows = [("Label", "Type", "X", "Y", "Interfaces")]
    rows.append(("-" * 20, "-" * 18, "-" * 5, "-" * 5, "-" * 12))
    for node in topology.nodes.values():
        iface_count = len(getattr(node, 'interfaces', []))
        ntype = getattr(node, 'node_type', '') or ''
        rows.append((
            str(node.label)[:20],
            ntype[:18],
            str(int(getattr(node, 'x', 0))),
            str(int(getattr(node, 'y', 0))),
            str(iface_count),
        ))
    col_widths = [max(len(r[i]) for r in rows) for i in range(5)]
    lines = []
    for row in rows:
        line = "  ".join(row[i].ljust(col_widths[i]) for i in range(5))
        lines.append(line)
    return "\n".join(lines)


def _link_table(topology):
    node_label = {}
    for node in topology.nodes.values():
        node_label[node.id] = node.label

    rows = [("Endpoint A", "Interface A", "Endpoint B", "Interface B")]
    rows.append(("-" * 20, "-" * 16, "-" * 20, "-" * 16))
    for link in topology.links.values():
        n1 = node_label.get(link.node1_id, link.node1_id)
        n2 = node_label.get(link.node2_id, link.node2_id)
        i1 = str(link.interface1 or "")
        i2 = str(link.interface2 or "")
        rows.append((n1[:20], i1[:16], n2[:20], i2[:16]))

    col_widths = [max(len(r[i]) for r in rows) for i in range(4)]
    lines = []
    for row in rows:
        line = "  ".join(row[i].ljust(col_widths[i]) for i in range(4))
        lines.append(line)
    return "\n".join(lines)


def _ascii_graph(topology):
    """Render a minimal ASCII adjacency diagram."""
    if not topology.nodes:
        return "(empty topology)"

    node_label = {}
    for node in topology.nodes.values():
        node_label[node.id] = node.label

    adjacency = {}
    for node in topology.nodes.values():
        adjacency[node.label] = []

    for link in topology.links.values():
        n1 = node_label.get(link.node1_id, link.node1_id)
        n2 = node_label.get(link.node2_id, link.node2_id)
        i1 = str(link.interface1 or "")
        i2 = str(link.interface2 or "")
        if n1 in adjacency:
            adjacency[n1].append((n2, i1, i2))
        if n2 in adjacency:
            adjacency[n2].append((n1, i2, i1))

    lines = ["Connection diagram:"]
    for label in sorted(adjacency):
        box = f"[ {label} ]"
        neighbors = adjacency[label]
        if not neighbors:
            lines.append(f"  {box}")
        else:
            for idx, (peer, local_if, remote_if) in enumerate(neighbors):
                prefix = f"  {box}" if idx == 0 else " " * (len(box) + 2)
                link_desc = f"{local_if}" if local_if else ""
                peer_desc = f"{remote_if}" if remote_if else ""
                arrow = f" ---({link_desc})---({peer_desc})--- [ {peer} ]"
                lines.append(f"{prefix}{arrow}")
    return "\n".join(lines)
