"""
Topology diff/comparison utility.

Compares two parsed topologies (regardless of source format) and produces
a structured report of differences in nodes, links, and configurations.
"""
import logging

logger = logging.getLogger(__name__)


def diff_topologies(topo_a, topo_b, label_a="A", label_b="B"):
    """
    Compare two topologies and return a diff report.

    Args:
        topo_a: First topology (CMLTopology, VIRLTopology, or any
                object with ``.nodes`` and ``.links`` dicts).
        topo_b: Second topology.
        label_a: Human-readable label for topo_a.
        label_b: Human-readable label for topo_b.

    Returns:
        dict with keys:
            name_changed (bool): Whether the topology name differs.
            nodes_added   (list[str]): Node labels only in topo_b.
            nodes_removed (list[str]): Node labels only in topo_a.
            nodes_changed (list[dict]): Nodes present in both but differing.
            links_added   (list[str]): Link IDs only in topo_b.
            links_removed (list[str]): Link IDs only in topo_a.
            links_changed (list[dict]): Links present in both but differing.
            summary (str):  Human-readable summary.
    """
    nodes_a = _index_nodes_by_label(topo_a)
    nodes_b = _index_nodes_by_label(topo_b)

    labels_a = set(nodes_a)
    labels_b = set(nodes_b)

    added_labels = sorted(labels_b - labels_a)
    removed_labels = sorted(labels_a - labels_b)
    common_labels = sorted(labels_a & labels_b)

    nodes_changed = []
    for label in common_labels:
        na = nodes_a[label]
        nb = nodes_b[label]
        changes = _compare_nodes(na, nb)
        if changes:
            nodes_changed.append({"label": label, "changes": changes})

    links_a = _index_links(topo_a)
    links_b = _index_links(topo_b)

    keys_a = set(links_a)
    keys_b = set(links_b)

    links_added = sorted(keys_b - keys_a)
    links_removed = sorted(keys_a - keys_b)
    common_link_keys = sorted(keys_a & keys_b)

    links_changed = []
    for key in common_link_keys:
        la = links_a[key]
        lb = links_b[key]
        changes = _compare_links(la, lb)
        if changes:
            links_changed.append({"key": key, "changes": changes})

    name_changed = getattr(topo_a, 'name', '') != getattr(topo_b, 'name', '')

    total_changes = (
        int(name_changed)
        + len(added_labels) + len(removed_labels) + len(nodes_changed)
        + len(links_added) + len(links_removed) + len(links_changed)
    )

    lines = []
    if total_changes == 0:
        lines.append("Topologies are identical.")
    else:
        lines.append(f"{total_changes} difference(s) found.")
        if name_changed:
            lines.append(
                f"  Name: '{getattr(topo_a, 'name', '')}' -> "
                f"'{getattr(topo_b, 'name', '')}'"
            )
        if added_labels:
            lines.append(f"  Nodes added in {label_b}: {', '.join(added_labels)}")
        if removed_labels:
            lines.append(f"  Nodes removed from {label_a}: {', '.join(removed_labels)}")
        for nc in nodes_changed:
            desc = "; ".join(
                f"{c['field']}: '{c['a']}' -> '{c['b']}'" for c in nc["changes"]
            )
            lines.append(f"  Node '{nc['label']}' changed: {desc}")
        if links_added:
            lines.append(f"  Links added in {label_b}: {', '.join(links_added)}")
        if links_removed:
            lines.append(f"  Links removed from {label_a}: {', '.join(links_removed)}")
        for lc in links_changed:
            desc = "; ".join(
                f"{c['field']}: '{c['a']}' -> '{c['b']}'" for c in lc["changes"]
            )
            lines.append(f"  Link '{lc['key']}' changed: {desc}")

    return {
        "name_changed": name_changed,
        "nodes_added": added_labels,
        "nodes_removed": removed_labels,
        "nodes_changed": nodes_changed,
        "links_added": links_added,
        "links_removed": links_removed,
        "links_changed": links_changed,
        "summary": "\n".join(lines),
    }


def _index_nodes_by_label(topo):
    """Index nodes by their label for comparison purposes."""
    out = {}
    for node in topo.nodes.values():
        out[node.label] = node
    return out


def _index_links(topo):
    """Create a stable key for each link based on endpoint labels."""
    node_label = {}
    for node in topo.nodes.values():
        node_label[node.id] = node.label

    out = {}
    for link in topo.links.values():
        n1 = node_label.get(link.node1_id, link.node1_id)
        n2 = node_label.get(link.node2_id, link.node2_id)
        i1 = str(link.interface1 or "")
        i2 = str(link.interface2 or "")
        ep_a = f"{n1}:{i1}"
        ep_b = f"{n2}:{i2}"
        key = " <-> ".join(sorted([ep_a, ep_b]))
        out[key] = link
    return out


def _compare_nodes(na, nb):
    changes = []
    for field in ("node_type", "x", "y"):
        va = getattr(na, field, None)
        vb = getattr(nb, field, None)
        if va != vb:
            changes.append({"field": field, "a": va, "b": vb})

    config_a = getattr(na, "configuration", "") or ""
    config_b = getattr(nb, "configuration", "") or ""
    if config_a.strip() != config_b.strip():
        changes.append({"field": "configuration", "a": "(differs)", "b": "(differs)"})

    return changes


def _compare_links(la, lb):
    changes = []
    for field in ("interface1", "interface2"):
        va = str(getattr(la, field, "") or "")
        vb = str(getattr(lb, field, "") or "")
        if va != vb:
            changes.append({"field": field, "a": va, "b": vb})
    return changes
