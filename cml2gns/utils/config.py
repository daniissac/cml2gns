"""
Configuration utilities for cml2gns.
"""
import json
import logging

logger = logging.getLogger(__name__)

# GNS3 version-to-revision mapping
GNS3_VERSION_REVISIONS = {
    "2.0": {"revision": 7, "default_version": "2.0.0"},
    "2.1": {"revision": 8, "default_version": "2.1.0"},
    "2.2": {"revision": 9, "default_version": "2.2.47"},
}

# Default node mappings from CML/VIRL node types to GNS3 templates
DEFAULT_NODE_MAPPINGS = {
    # --- Cisco Routers ---
    "iosv": {
        "gns3_template": "Cisco IOSv",
        "console_type": "telnet",
        "compute_type": "qemu",
        "symbol": ":/symbols/classic/router.svg",
        "properties": {
            "ram": 512,
            "adapters": 4,
            "adapter_type": "e1000",
        },
    },
    "csr1000v": {
        "gns3_template": "Cisco CSR1000v",
        "console_type": "telnet",
        "compute_type": "qemu",
        "symbol": ":/symbols/classic/router.svg",
        "properties": {
            "ram": 3072,
            "adapters": 4,
            "adapter_type": "virtio-net-pci",
        },
    },
    "cat8000v": {
        "gns3_template": "Cisco Catalyst 8000V",
        "console_type": "telnet",
        "compute_type": "qemu",
        "symbol": ":/symbols/classic/router.svg",
        "properties": {
            "ram": 4096,
            "adapters": 4,
            "adapter_type": "virtio-net-pci",
        },
    },
    "iosxrv": {
        "gns3_template": "Cisco IOS XRv",
        "console_type": "telnet",
        "compute_type": "qemu",
        "symbol": ":/symbols/classic/router.svg",
        "properties": {
            "ram": 3072,
            "adapters": 4,
            "adapter_type": "e1000",
        },
    },
    "iosxrv9000": {
        "gns3_template": "Cisco IOS XRv 9000",
        "console_type": "telnet",
        "compute_type": "qemu",
        "symbol": ":/symbols/classic/router.svg",
        "properties": {
            "ram": 8192,
            "adapters": 7,
            "adapter_type": "virtio-net-pci",
        },
    },
    "isrv": {
        "gns3_template": "Cisco ISRv",
        "console_type": "telnet",
        "compute_type": "qemu",
        "symbol": ":/symbols/classic/router.svg",
        "properties": {
            "ram": 4096,
            "adapters": 4,
            "adapter_type": "virtio-net-pci",
        },
    },
    # --- Cisco Switches ---
    "iosvl2": {
        "gns3_template": "Cisco IOSvL2",
        "console_type": "telnet",
        "compute_type": "qemu",
        "symbol": ":/symbols/classic/ethernet_switch.svg",
        "properties": {
            "ram": 512,
            "adapters": 4,
            "adapter_type": "e1000",
        },
    },
    "cat9000v": {
        "gns3_template": "Cisco Catalyst 9000V",
        "console_type": "telnet",
        "compute_type": "qemu",
        "symbol": ":/symbols/classic/ethernet_switch.svg",
        "properties": {
            "ram": 4096,
            "adapters": 4,
            "adapter_type": "virtio-net-pci",
        },
    },
    "cat9kv": {
        "gns3_template": "Cisco Catalyst 9000V",
        "console_type": "telnet",
        "compute_type": "qemu",
        "symbol": ":/symbols/classic/ethernet_switch.svg",
        "properties": {
            "ram": 4096,
            "adapters": 4,
            "adapter_type": "virtio-net-pci",
        },
    },
    # --- Cisco DC / NX-OS ---
    "nxosv": {
        "gns3_template": "Cisco NX-OSv",
        "console_type": "telnet",
        "compute_type": "qemu",
        "symbol": ":/symbols/classic/multilayer_switch.svg",
        "properties": {
            "ram": 4096,
            "adapters": 8,
            "adapter_type": "e1000",
        },
    },
    "nxosv9000": {
        "gns3_template": "Cisco NX-OSv 9000",
        "console_type": "telnet",
        "compute_type": "qemu",
        "symbol": ":/symbols/classic/multilayer_switch.svg",
        "properties": {
            "ram": 8192,
            "adapters": 10,
            "adapter_type": "virtio-net-pci",
        },
    },
    # --- Cisco Security ---
    "asav": {
        "gns3_template": "Cisco ASAv",
        "console_type": "telnet",
        "compute_type": "qemu",
        "symbol": ":/symbols/classic/firewall.svg",
        "properties": {
            "ram": 2048,
            "adapters": 4,
            "adapter_type": "virtio-net-pci",
        },
    },
    "ftdv": {
        "gns3_template": "Cisco FTDv",
        "console_type": "telnet",
        "compute_type": "qemu",
        "symbol": ":/symbols/classic/firewall.svg",
        "properties": {
            "ram": 8192,
            "adapters": 4,
            "adapter_type": "virtio-net-pci",
        },
    },
    # --- IOS on Linux ---
    "iol": {
        "gns3_template": "Cisco IOL",
        "console_type": "telnet",
        "compute_type": "iou",
        "symbol": ":/symbols/classic/router.svg",
        "properties": {
            "ram": 256,
        },
    },
    "ioll2": {
        "gns3_template": "Cisco IOL L2",
        "console_type": "telnet",
        "compute_type": "iou",
        "symbol": ":/symbols/classic/ethernet_switch.svg",
        "properties": {
            "ram": 256,
        },
    },
    # --- SD-WAN ---
    "vmanage": {
        "gns3_template": "Cisco vManage",
        "console_type": "telnet",
        "compute_type": "qemu",
        "symbol": ":/symbols/classic/server.svg",
        "properties": {
            "ram": 16384,
            "adapters": 2,
            "adapter_type": "virtio-net-pci",
        },
    },
    "vbond": {
        "gns3_template": "Cisco vBond",
        "console_type": "telnet",
        "compute_type": "qemu",
        "symbol": ":/symbols/classic/router.svg",
        "properties": {
            "ram": 2048,
            "adapters": 4,
            "adapter_type": "virtio-net-pci",
        },
    },
    "vsmart": {
        "gns3_template": "Cisco vSmart",
        "console_type": "telnet",
        "compute_type": "qemu",
        "symbol": ":/symbols/classic/router.svg",
        "properties": {
            "ram": 4096,
            "adapters": 2,
            "adapter_type": "virtio-net-pci",
        },
    },
    "vedge": {
        "gns3_template": "Cisco vEdge",
        "console_type": "telnet",
        "compute_type": "qemu",
        "symbol": ":/symbols/classic/router.svg",
        "properties": {
            "ram": 2048,
            "adapters": 4,
            "adapter_type": "virtio-net-pci",
        },
    },
    # --- Linux / General ---
    "linux": {
        "gns3_template": "Linux",
        "console_type": "telnet",
        "compute_type": "qemu",
        "symbol": ":/symbols/classic/computer.svg",
        "properties": {
            "ram": 512,
            "adapters": 1,
            "adapter_type": "virtio-net-pci",
        },
    },
    "alpine": {
        "gns3_template": "Alpine Linux",
        "console_type": "telnet",
        "compute_type": "docker",
        "symbol": ":/symbols/classic/computer.svg",
        "properties": {},
    },
    "ubuntu": {
        "gns3_template": "Ubuntu",
        "console_type": "telnet",
        "compute_type": "qemu",
        "symbol": ":/symbols/classic/computer.svg",
        "properties": {
            "ram": 1024,
            "adapters": 1,
            "adapter_type": "virtio-net-pci",
        },
    },
    "coreos": {
        "gns3_template": "CoreOS",
        "console_type": "telnet",
        "compute_type": "qemu",
        "symbol": ":/symbols/classic/computer.svg",
        "properties": {
            "ram": 2048,
            "adapters": 1,
            "adapter_type": "virtio-net-pci",
        },
    },
    "server": {
        "gns3_template": "Linux",
        "console_type": "telnet",
        "compute_type": "qemu",
        "symbol": ":/symbols/classic/server.svg",
        "properties": {
            "ram": 1024,
            "adapters": 1,
            "adapter_type": "virtio-net-pci",
        },
    },
    "desktop": {
        "gns3_template": "Linux",
        "console_type": "vnc",
        "compute_type": "qemu",
        "symbol": ":/symbols/classic/computer.svg",
        "properties": {
            "ram": 1024,
            "adapters": 1,
            "adapter_type": "virtio-net-pci",
        },
    },
    "routem": {
        "gns3_template": "Linux",
        "console_type": "telnet",
        "compute_type": "qemu",
        "symbol": ":/symbols/classic/router.svg",
        "properties": {
            "ram": 256,
            "adapters": 2,
            "adapter_type": "virtio-net-pci",
        },
    },
    # --- Infrastructure ---
    "wan_emulator": {
        "gns3_template": "WAN Emulator",
        "console_type": "none",
        "compute_type": "qemu",
        "symbol": ":/symbols/classic/cloud.svg",
        "properties": {},
    },
    "unmanaged_switch": {
        "gns3_template": "Ethernet switch",
        "console_type": "none",
        "compute_type": "ethernet_switch",
        "symbol": ":/symbols/classic/ethernet_switch.svg",
        "properties": {},
    },
    "trex": {
        "gns3_template": "TRex",
        "console_type": "telnet",
        "compute_type": "docker",
        "symbol": ":/symbols/classic/computer.svg",
        "properties": {},
    },
    "external_connector": {
        "gns3_template": "Cloud",
        "console_type": "none",
        "compute_type": "cloud",
        "symbol": ":/symbols/classic/cloud.svg",
        "properties": {},
    },
    # --- VIRL 1.x LXC containers ---
    "lxc-iperf": {
        "gns3_template": "Linux",
        "console_type": "telnet",
        "compute_type": "docker",
        "symbol": ":/symbols/classic/computer.svg",
        "properties": {},
    },
    "lxc-ostinato-drone": {
        "gns3_template": "TRex",
        "console_type": "telnet",
        "compute_type": "docker",
        "symbol": ":/symbols/classic/computer.svg",
        "properties": {},
    },
    "lxc-routem": {
        "gns3_template": "Linux",
        "console_type": "telnet",
        "compute_type": "docker",
        "symbol": ":/symbols/classic/router.svg",
        "properties": {},
    },
    "management-lxc": {
        "gns3_template": "Linux",
        "console_type": "telnet",
        "compute_type": "docker",
        "symbol": ":/symbols/classic/computer.svg",
        "properties": {},
    },
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
        with open(file_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON in {file_path}: {str(e)}")
        raise ValueError(f"Invalid JSON in configuration file: {str(e)}")
    except Exception as e:
        logger.error(f"Error loading configuration from {file_path}: {str(e)}")
        raise ValueError(f"Error loading configuration: {str(e)}")