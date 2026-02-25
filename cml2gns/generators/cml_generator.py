"""
Generator for CML YAML topology files from parsed GNS3 projects.
"""
import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


class CMLGenerator:
    """
    Generates a CML YAML topology file from a parsed topology model.
    """

    def generate(self, topology, output_file):
        """
        Write a CML YAML file from a topology.

        Args:
            topology: A CMLTopology (or compatible) object.
            output_file (Path): Destination YAML file path.

        Returns:
            dict: Statistics about the generated file.
        """
        output_file = Path(output_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        data = topology.to_dict()

        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False,
                      allow_unicode=True)

        logger.info(f"Wrote CML topology to {output_file}")
        return {
            "output_file": str(output_file),
            "node_count": len(topology.nodes),
            "link_count": len(topology.links),
        }
