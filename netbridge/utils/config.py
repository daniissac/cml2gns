"""
Configuration utilities for NetBridge.
"""
import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Default node mappings from CML/VIRL node types to GNS3 templates
DEFAULT_NODE_MAPPINGS = {
    "iosv": {
        "gns3_template": "Cisco IOSv",
        "console_type": "telnet"
    },
    "iosvl2": {
        "gns3_template": "Cisco IOSvL2",
        "console_type": "telnet"
    },
    "csr1000v": {
        "gns3_template": "Cisco CSR1000v",
        "console_type": "telnet"
    },
    "iosxrv": {
        "gns3_template": "Cisco IOS XRv",
        "console_type": "telnet"
    },
    "nxosv": {
        "gns3_template": "Cisco NX-OSv",
        "console_type": "telnet"
    },
    "asav": {
        "gns3_template": "Cisco ASAv",
        "console_type": "telnet"
    },
    "linux": {
        "gns3_template": "Linux",
        "console_type": "telnet"
    },
    "ubuntu": {
        "gns3_template": "Ubuntu",
        "console_type": "telnet"
    },
    "external_connector": {
        "gns3_template": "Cloud",
        "console_type": "none"
    }
}


def load_config(file_path):
    """
    Load configuration from a JSON file.
    
    Args:
        file_path (str): Path to the configuration file
        
    Returns:
        dict: Configuration data
        
    Raises:
        ValueError: If the file cannot be parsed as valid JSON
    """
    try:
        with open(file_path, 'r') as f:
            config = json.load(f)
        return config
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON in {file_path}: {str(e)}")
        raise ValueError(f"Invalid JSON in configuration file: {str(e)}")
    except Exception as e:
        logger.error(f"Error loading configuration from {file_path}: {str(e)}")
        raise ValueError(f"Error loading configuration: {str(e)}")


def save_config(config, file_path):
    """
    Save configuration to a JSON file.
    
    Args:
        config (dict): Configuration data
        file_path (str): Path to save the configuration
        
    Raises:
        IOError: If the file cannot be written
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving configuration to {file_path}: {str(e)}")
        raise IOError(f"Error saving configuration: {str(e)}")