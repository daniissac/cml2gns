"""
Main converter module for cml2gns.
"""
import json
import logging
import uuid
from pathlib import Path

import yaml

from cml2gns.parsers.cml_parser import CMLParser
from cml2gns.parsers.virl_parser import VIRLParser
from cml2gns.generators.gns3_generator import GNS3Generator
from cml2gns.utils.validators import validate_topology
from cml2gns.utils.node_mappings import map_nodes
from cml2gns.utils.config import GNS3_VERSION_REVISIONS
from cml2gns.utils.topology_diff import diff_topologies
from cml2gns.utils.visualizer import visualize_topology

logger = logging.getLogger(__name__)


class Converter:
    """
    Core converter class that orchestrates the conversion process.
    """
    
    def __init__(self, node_mappings=None, strict=False,
                 gns3_version=None):
        """
        Args:
            node_mappings (dict): Custom node mappings configuration
            strict (bool): If True, fail on unmapped node types instead of
                using a generic fallback.
            gns3_version (str): Target GNS3 version family (e.g. "2.0", "2.2").
        """
        self.node_mappings = node_mappings or {}
        self.strict = strict
        self.cml_parser = CMLParser()
        self.virl_parser = VIRLParser()

        gen_version = None
        gen_revision = None
        if gns3_version and gns3_version in GNS3_VERSION_REVISIONS:
            info = GNS3_VERSION_REVISIONS[gns3_version]
            gen_version = info["default_version"]
            gen_revision = info["revision"]

        self.gns3_generator = GNS3Generator(
            gns3_version=gen_version,
            gns3_revision=gen_revision,
        )
    
    def _detect_file_type(self, input_file):
        """
        Detect if the input file is CML, VIRL, or GNS3 format.
        
        Returns:
            str: "cml", "virl", or "gns3"
        """
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read(1000)
            
        if content.lstrip().startswith('{'):
            try:
                with open(input_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if data.get("type") == "topology" or "topology" in data:
                    logger.info(f"Detected GNS3 format for {input_file}")
                    return "gns3"
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

        if "topology:" in content or "nodes:" in content or "lab:" in content:
            suffix = str(input_file).lower()
            if suffix.endswith('.clab.yml') or suffix.endswith('.clab.yaml'):
                logger.info(f"Detected containerlab format for {input_file}")
                return "containerlab"
            logger.info(f"Detected CML format for {input_file}")
            return "cml"
        elif "<topology" in content or "<lab" in content:
            logger.info(f"Detected VIRL format for {input_file}")
            return "virl"
        else:
            logger.error(f"Could not determine file type for {input_file}")
            raise ValueError(
                f"Unknown file format for {input_file}. "
                f"Must be CML, VIRL, GNS3, or containerlab."
            )
    
    def _parse(self, input_file):
        """Parse an input file and return the topology and detected file type."""
        input_file = Path(input_file)
        file_type = self._detect_file_type(input_file)

        if file_type == "cml":
            topology = self.cml_parser.parse(input_file)
        elif file_type == "virl":
            topology = self.virl_parser.parse(input_file)
        elif file_type == "gns3":
            from cml2gns.parsers.gns3_parser import GNS3Parser
            topology = GNS3Parser().parse(input_file)
        elif file_type == "containerlab":
            from cml2gns.parsers.containerlab_parser import ContainerlabParser
            topology = ContainerlabParser().parse(input_file)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

        return topology, file_type

    def validate_file(self, input_file):
        """
        Parse and validate a CML/VIRL file without converting it.
        """
        topology, file_type = self._parse(input_file)
        validate_topology(topology)

        unmapped = set()
        for node in topology.nodes.values():
            node_type = node.node_type or "unknown"
            if node_type not in self.node_mappings:
                unmapped.add(node_type)

        return {
            "file_type": file_type,
            "topology_name": topology.name,
            "node_count": len(topology.nodes),
            "link_count": len(topology.links),
            "unmapped_types": sorted(unmapped),
        }

    def convert(self, input_file, output_dir, dry_run=False, portable=False):
        """
        Convert a CML/VIRL file to GNS3 project.
        """
        input_file = Path(input_file)
        output_dir = Path(output_dir)
        
        logger.info(f"Starting conversion of {input_file} to {output_dir}")
        
        topology, _ = self._parse(input_file)
        validate_topology(topology)
        mapped_topology = map_nodes(topology, self.node_mappings)

        unmapped = {
            n.node_type or "unknown"
            for n in mapped_topology.nodes.values()
            if getattr(n, 'gns3_template', None) == "qemu"
            and (n.node_type or "unknown") not in self.node_mappings
        }

        if unmapped and self.strict:
            raise ValueError(
                f"Strict mode: unmapped node types found: {', '.join(sorted(unmapped))}. "
                f"Add them to a custom mapping file and pass it with --mapping."
            )

        if dry_run:
            return {
                "project_file": None,
                "node_count": len(mapped_topology.nodes),
                "link_count": len(mapped_topology.links),
                "unmapped_types": sorted(unmapped),
                "dry_run": True,
            }

        project_uuid = str(uuid.uuid4())
        result = self.gns3_generator.generate(
            mapped_topology, output_dir, project_uuid,
            portable=portable,
        )
        result["unmapped_types"] = sorted(unmapped)
        
        logger.info(f"Conversion complete. Created {result['node_count']} nodes and {result['link_count']} links")
        return result

    def diff(self, file_a, file_b):
        """
        Compare two topology files and return a diff report.

        Both files can be in any supported format (CML, VIRL, GNS3,
        containerlab).
        """
        topo_a, _ = self._parse(file_a)
        topo_b, _ = self._parse(file_b)
        return diff_topologies(
            topo_a, topo_b,
            label_a=str(file_a), label_b=str(file_b),
        )

    def visualize(self, input_file):
        """Return an ASCII visualization of a topology file."""
        topology, _ = self._parse(input_file)
        return visualize_topology(topology)

    def export_containerlab(self, input_file, output_file):
        """Convert any supported topology file to containerlab .clab.yml."""
        topology, _ = self._parse(input_file)
        validate_topology(topology)
        mapped_topology = map_nodes(topology, self.node_mappings)

        from cml2gns.generators.containerlab_generator import ContainerlabGenerator
        generator = ContainerlabGenerator()
        return generator.generate(mapped_topology, output_file)

    def reverse_convert(self, input_file, output_file):
        """
        Convert a GNS3 project file back to CML YAML.
        """
        input_file = Path(input_file)
        output_file = Path(output_file)

        from cml2gns.parsers.gns3_parser import GNS3Parser
        from cml2gns.generators.cml_generator import CMLGenerator

        topology = GNS3Parser().parse(input_file)
        validate_topology(topology)

        generator = CMLGenerator()
        result = generator.generate(topology, output_file)

        logger.info(
            f"Reverse conversion complete. Wrote {result['node_count']} nodes "
            f"and {result['link_count']} links to {output_file}"
        )
        return result
