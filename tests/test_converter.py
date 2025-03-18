"""
Tests for the converter module.
"""
import os
import pytest
import tempfile
import shutil
from pathlib import Path
from netbridge.converter import Converter
from netbridge.utils.config import DEFAULT_NODE_MAPPINGS


class TestConverter:
    """Test cases for the Converter class."""
    
    @pytest.fixture
    def sample_cml_file(self):
        """Sample CML file for testing."""
        return Path(__file__).parent / "fixtures" / "cml_samples" / "sample_topology.yaml"
    
    @pytest.fixture
    def temp_output_dir(self):
        """Temporary output directory for testing."""
        output_dir = tempfile.mkdtemp()
        yield Path(output_dir)
        shutil.rmtree(output_dir)
    
    def test_detect_file_type_cml(self, sample_cml_file):
        """Test detecting CML file type."""
        if not sample_cml_file.exists():
            pytest.skip("Sample CML file not found")
            
        converter = Converter()
        file_type = converter._detect_file_type(sample_cml_file)
        assert file_type == "cml"
    
    def test_convert_cml_to_gns3(self, sample_cml_file, temp_output_dir):
        """Test converting CML to GNS3."""
        if not sample_cml_file.exists():
            pytest.skip("Sample CML file not found")
        
        converter = Converter(node_mappings=DEFAULT_NODE_MAPPINGS)
        result = converter.convert(sample_cml_file, temp_output_dir)
        
        # Check if conversion was successful
        assert "node_count" in result
        assert "link_count" in result
        assert result["node_count"] > 0
        
        # Check if GNS3 project file was created
        assert any(temp_output_dir.glob("*.gns3"))