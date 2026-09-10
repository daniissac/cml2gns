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
    name = getattr(topology, "name", "Unknown")
    desc = getattr(topology, "description", "")
    parts = [f"Topology: {name}"]
    if desc:
        parts.append(f"  Description: {desc}")
    parts.append(f"  Nodes: {len(topology.nodes)}  Links: {len(topology.links)}")
    border = "=" * max(len(p) for p in parts)
    return "\n".join([border] + parts + [border])


def _node_table(topology):
    rows = [("Label", "Type", "X", "Y", "Interfaces")]
    rows.append(("-" * 20, "-" * 18, "-" * 5, "-" * 5, "-" * 12))
    for node in topology.nodes.values():
        interfaces = {
            str(getattr(iface, "label", None) or getattr(iface, "id", iface))
            for iface in getattr(node, "interfaces", [])
        }
        for link in topology.links.values():
            if link.node1_id == node.id and link.interface1:
                interfaces.add(str(link.interface1))
            if link.node2_id == node.id and link.interface2:
                interfaces.add(str(link.interface2))
        ntype = getattr(node, "node_type", "") or ""
        rows.append(
            (
                str(node.label),
                ntype,
                str(int(getattr(node, "x", 0))),
                str(int(getattr(node, "y", 0))),
                str(len(interfaces)),
            )
        )
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
        rows.append((n1, i1, n2, i2))

    col_widths = [max(len(r[i]) for r in rows) for i in range(4)]
    lines = []
    for row in rows:
        line = "  ".join(row[i].ljust(col_widths[i]) for i in range(4))
        lines.append(line)
    return "\n".join(lines)


def _ascii_graph(topology):
    """Render each physical link once as a minimal ASCII diagram."""
    if not topology.nodes:
        return "(empty topology)"

    node_label = {}
    for node in topology.nodes.values():
        node_label[node.id] = node.label

    connected = set()
    lines = ["Connection diagram:"]
    for link in topology.links.values():
        n1 = node_label.get(link.node1_id, link.node1_id)
        n2 = node_label.get(link.node2_id, link.node2_id)
        i1 = str(link.interface1 or "")
        i2 = str(link.interface2 or "")
        lines.append(f"  [ {n1} ] ---({i1})---({i2})--- [ {n2} ]")
        connected.update((link.node1_id, link.node2_id))

    for node in topology.nodes.values():
        if node.id not in connected:
            lines.append(f"  [ {node.label} ]")
    return "\n".join(lines)
