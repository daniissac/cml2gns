"""
Main converter module for NetBridge.
"""
import os
import logging
import uuid
from pathlib import Path

from netbridge.parsers.cml_parser import CMLParser
from netbridge.parsers.virl_parser import VIRLParser
from netbridge.generators.gns3_generator import GNS3Generator
from netbridge.utils.validators import validate_topology
from netbridge.utils.node_mappings import map_nodes

logger = logging.getLogger(__name__)


class Converter:
    """
    Core converter class that orchestrates the conversion process.
    """
    
    def __init__(self, node_mappings=None):
        """
        Initialize the converter with optional node mappings.
        
        Args:
            node_mappings (dict): Custom node mappings configuration
        """
        self.node_mappings = node_mappings or {}
        self.cml_parser = CMLParser()
        self.virl_parser = VIRLParser()
        self.gns3_generator = GNS3Generator()
    
    def _detect_file_type(self, input_file):
        """
        Detect if the input file is CML or VIRL format.
        
        Args:
            input_file (Path): Path to the input file
            
        Returns:
            str: "cml" or "virl"
            
        Raises:
            ValueError: If the file type cannot be determined
        """
        with open(input_file, 'r') as f:
            content = f.read(1000)  # Read first 1000 characters
            
        if "topology:" in content or "nodes:" in content:
            # Basic CML structure check
            logger.info(f"Detected CML format for {input_file}")
            return "cml"
        elif "<topology" in content or "<lab" in content:
            # Basic VIRL structure check
            logger.info(f"Detected VIRL format for {input_file}")
            return "virl"
        else:
            logger.error(f"Could not determine file type for {input_file}")
            raise ValueError(f"Unknown file format for {input_file}. Must be CML or VIRL.")
    
    def convert(self, input_file, output_dir):
        """
        Convert a CML/VIRL file to GNS3 project.
        
        Args:
            input_file (Path): Path to the input CML/VIRL file
            output_dir (Path): Directory to save the GNS3 project
            
        Returns:
            dict: Statistics about the conversion (nodes, links, etc.)
            
        Raises:
            ValueError: For invalid input or conversion errors
        """
        input_file = Path(input_file)
        output_dir = Path(output_dir)
        
        logger.info(f"Starting conversion of {input_file} to {output_dir}")
        
        # Detect file type and parse accordingly
        file_type = self._detect_file_type(input_file)
        
        # Parse input file
        if file_type == "cml":
            topology = self.cml_parser.parse(input_file)
        else:  # virl
            topology = self.virl_parser.parse(input_file)
        
        # Validate the parsed topology
        validate_topology(topology)
        
        # Map nodes to GNS3 templates
        mapped_topology = map_nodes(topology, self.node_mappings)
        
        # Generate GNS3 project
        project_uuid = str(uuid.uuid4())
        result = self.gns3_generator.generate(mapped_topology, output_dir, project_uuid)
        
        logger.info(f"Conversion complete. Created {result['node_count']} nodes and {result['link_count']} links")
        return result
