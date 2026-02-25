"""
Annotations / drawings preservation.

Converts CML notes and VIRL annotations into GNS3 drawing objects
so that topology labels and documentation survive the conversion.
"""
import logging

from cml2gns.models.gns3_model import GNS3Drawing

logger = logging.getLogger(__name__)


def extract_drawings(topology):
    """
    Extract annotation/drawing objects from a parsed topology.

    Sources:
        - CML topology.notes / topology.description
        - CML node labels with annotation markers
        - VIRL topology notes

    Returns:
        list[GNS3Drawing]
    """
    drawings = []
    y_offset = -150

    notes = getattr(topology, 'notes', '') or ''
    description = getattr(topology, 'description', '') or ''

    if description.strip():
        drawings.append(
            GNS3Drawing.from_text(
                f"Description: {description.strip()}",
                x=-200, y=y_offset, font_size=12,
            )
        )
        y_offset -= 30

    if notes.strip():
        for line in notes.strip().splitlines():
            if line.strip():
                drawings.append(
                    GNS3Drawing.from_text(line.strip(), x=-200, y=y_offset, font_size=11)
                )
                y_offset -= 25

    annotations = getattr(topology, 'annotations', None)
    if isinstance(annotations, list):
        for ann in annotations:
            text = ann if isinstance(ann, str) else str(ann.get("text", ""))
            x = int(ann.get("x", -200)) if isinstance(ann, dict) else -200
            y = int(ann.get("y", y_offset)) if isinstance(ann, dict) else y_offset
            if text.strip():
                drawings.append(GNS3Drawing.from_text(text.strip(), x=x, y=y))
                y_offset -= 25

    return drawings
