# NetBridge: CML to GNS3 Converter

NetBridge is a powerful tool for converting Cisco Modeling Labs (CML) and Virtual Internet Routing Lab (VIRL) YAML topology files into GNS3 projects. This tool enables network engineers to seamlessly transition between different network simulation platforms.

## Features

- Convert CML/VIRL YAML topology files to GNS3 project files
- Preserve node configurations and connections
- Map CML/VIRL device types to appropriate GNS3 appliances
- Support for custom node mapping configurations
- Command-line interface for easy integration into workflows
- Detailed logging and validation

## Installation

```bash
git clone https://github.com/daniissac/netbridge.git
cd netbridge
pip install -e .
```

## Quick Start

```bash
# Convert a CML file to GNS3
netbridge convert --input my_topology.yaml --output my_gns3_project

# Convert with custom node mappings
netbridge convert --input my_topology.yaml --output my_gns3_project --mapping my_mappings.json

# Get help
netbridge --help
```

## Configuration

NetBridge uses a configuration file to map CML/VIRL node types to GNS3 appliances. The default mappings include common Cisco devices, but you can create custom mappings:

```json
{
  "iosv": {
    "gns3_template": "Cisco IOSv",
    "console_type": "telnet"
  },
  "csr1000v": {
    "gns3_template": "Cisco CSR1000v",
    "console_type": "telnet"
  }
}
```

## Requirements

- Python 3.8 or higher
- PyYAML
- Click
- Jinja2

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- The GNS3 team for their excellent network simulation platform
- Cisco for CML/VIRL topology formats
