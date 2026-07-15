# cml2gns

**Network lab topology translation and GNS3 deployment.**

[![CI](https://github.com/daniissac/cml2gns/actions/workflows/ci.yml/badge.svg)](https://github.com/daniissac/cml2gns/actions/workflows/ci.yml)
[![Python 3.9–3.14](https://img.shields.io/badge/Python-3.9%E2%80%933.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

`cml2gns` converts Cisco Modeling Labs (CML) and VIRL topologies into GNS3 project files, deploys them against templates installed on a GNS3 server, and provides supporting tools for validation, comparison, visualization, reverse conversion, and containerlab export.

The package name stays focused on its primary workflow—CML to GNS3—while the project now presents itself honestly as a broader topology toolkit. Renaming the Python package would break existing commands and imports without improving interoperability.

## What works

- CML YAML in list-based and dictionary-based layouts
- VIRL XML parsed with `defusedxml`
- GNS3 2.x project generation using the official `node_type` project field
- Server-backed deployment using real, installed GNS3 template IDs
- Link, node-position, annotation, and sidecar startup-config preservation
- GNS3-to-CML best-effort reverse conversion
- containerlab import and export
- Topology validation, diffing, batch conversion, and ASCII visualization
- GNS3 portable archives with the `.gns3project` extension

The test suite covers Python 3.9 through 3.14 in GitHub Actions.

## Installation

The project is not yet published on PyPI. Install it from source:

```bash
git clone https://github.com/daniissac/cml2gns.git
cd cml2gns
python -m pip install .
```

For development:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

## Choose a conversion mode

### Create an offline GNS3 project

```bash
cml2gns convert \
  --input branch-lab.yaml \
  --output build/branch-lab \
  --portable
```

This writes a schema-valid `.gns3` file and, when requested, a `.gns3project` archive. CML startup configurations are written unchanged into the output's `configs/` directory.

Offline conversion cannot discover proprietary images or machine-specific GNS3 template settings. QEMU, IOU, and Docker nodes still need compatible images and properties on the system that opens the project.

### Deploy through a running GNS3 server

```bash
cml2gns deploy \
  --input branch-lab.yaml \
  --host localhost \
  --port 3080
```

Deployment resolves only the templates needed by the topology, creates nodes from their real server-side templates, connects their interfaces, and rolls back the new project if a later step fails. Template names come from the built-in mappings or a custom mapping file.

For token authentication, set `GNS3_API_TOKEN`. For basic authentication, pass `--user` and set `GNS3_PASSWORD`.

Startup configs are not injected during server deployment because the destination filename and mechanism depend on the emulator and appliance. Use offline conversion to preserve them as sidecars, then apply them through the appropriate GNS3/device workflow.

## Common commands

```bash
# Validate without writing files
cml2gns validate --input branch-lab.yaml

# Preview an offline conversion
cml2gns convert -i branch-lab.yaml -o build/branch-lab --dry-run

# Fail instead of creating generic fallback nodes
cml2gns convert -i branch-lab.yaml -o build/branch-lab --strict

# Check installed templates on a GNS3 server
cml2gns server-check --host localhost --port 3080

# Convert a GNS3 project back to CML YAML (best effort)
cml2gns reverse -i project.gns3 -o recovered.yaml

# Export any supported topology to containerlab
cml2gns export-clab -i branch-lab.yaml -o branch-lab.clab.yml

# Compare or visualize topologies
cml2gns diff -a before.yaml -b after.yaml
cml2gns show -i branch-lab.yaml

# Inspect built-in node mappings
cml2gns list-mappings
```

Run `cml2gns --help` or `cml2gns COMMAND --help` for every option.

## Custom node mappings

Custom mappings override built-in mappings by CML `node_definition`:

```json
{
  "iosv": {
    "gns3_template": "My IOSv Template",
    "console_type": "telnet",
    "compute_type": "qemu",
    "symbol": ":/symbols/classic/router.svg",
    "properties": {
      "ram": 768,
      "adapters": 4,
      "adapter_type": "e1000"
    }
  }
}
```

Use it with `--mapping mappings.json`. For server deployment, `gns3_template` must match an installed template name. A real `template_id` may also be supplied; the server verifies that it exists.

## Conversion boundaries

Topology formats do not share a perfect one-to-one model. Keep these boundaries in mind:

- Device images are never bundled. Cisco and other vendor images must be supplied under their own licenses.
- GNS3-to-CML node definitions are inferred from GNS3 emulator types when the original CML metadata is unavailable.
- Interface labels are matched first; adapter/port numbers are used as a fallback.
- The optional `--normalize-config` transform only removes quotes around a quoted hostname. Secrets and other configuration lines are preserved.
- Portable archives contain the generated project and sidecar files, not missing appliance images.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Please include a regression test for parser, generator, or API behavior changes.

## License

[MIT](LICENSE)
