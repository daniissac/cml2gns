#!/usr/bin/env python3
"""
Command line interface for cml2gns.
"""
import sys
import click
import logging
from pathlib import Path

from cml2gns import __version__
from cml2gns.converter import Converter
from cml2gns.utils.config import load_config, DEFAULT_NODE_MAPPINGS, GNS3_VERSION_REVISIONS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("cml2gns")


def _build_node_mappings(mapping_path):
    """Merge default and optional custom node mappings."""
    node_mappings = dict(DEFAULT_NODE_MAPPINGS)
    if mapping_path:
        try:
            custom_mappings = load_config(mapping_path)
            node_mappings.update(custom_mappings)
            click.echo(f"Loaded custom node mappings from {mapping_path}")
        except Exception as e:
            click.echo(f"Error loading custom mappings: {e}")
            sys.exit(1)
    return node_mappings


@click.group()
@click.version_option(version=__version__, prog_name="cml2gns")
@click.option("--debug/--no-debug", default=False, help="Enable debug logging")
def cli(debug):
    """cml2gns: Convert CML/VIRL topology files to GNS3 projects."""
    if debug:
        logger.setLevel(logging.DEBUG)
        click.echo("Debug mode enabled")


@cli.command()
@click.option(
    "--input", "-i", required=True, type=click.Path(exists=True),
    help="Input CML/VIRL file path"
)
@click.option(
    "--output", "-o", required=True, type=click.Path(),
    help="Output directory for GNS3 project"
)
@click.option(
    "--mapping", "-m", type=click.Path(exists=True),
    help="Custom node mapping JSON file"
)
@click.option(
    "--force/--no-force", default=False,
    help="Overwrite existing output directory"
)
@click.option(
    "--dry-run", is_flag=True, default=False,
    help="Parse and validate without writing files"
)
@click.option(
    "--strict", is_flag=True, default=False,
    help="Fail on unmapped node types instead of using a generic fallback"
)
@click.option(
    "--gns3-version", type=click.Choice(sorted(GNS3_VERSION_REVISIONS.keys())),
    default=None,
    help="Target GNS3 version family (e.g. 2.0, 2.1, 2.2)"
)
@click.option(
    "--portable", is_flag=True, default=False,
    help="Also produce a .gns3p portable project archive"
)
@click.option(
    "--interactive", is_flag=True, default=False,
    help="Prompt for GNS3 template names for unmapped node types"
)
def convert(input, output, mapping, force, dry_run, strict, gns3_version,
            portable, interactive):
    """Convert a CML/VIRL topology file to a GNS3 project."""
    input_path = Path(input)
    output_path = Path(output)

    if not dry_run:
        if output_path.exists() and not force:
            click.echo(f"Error: Output directory '{output}' already exists. Use --force to overwrite.")
            sys.exit(1)
        if not output_path.exists():
            output_path.mkdir(parents=True)

    node_mappings = _build_node_mappings(mapping)

    if interactive:
        node_mappings = _interactive_mapping_phase(input_path, node_mappings)

    try:
        converter = Converter(
            node_mappings=node_mappings,
            strict=strict,
            gns3_version=gns3_version,
        )
        result = converter.convert(input_path, output_path,
                                   dry_run=dry_run, portable=portable)

        if dry_run:
            click.echo("Dry run (no files written):")
            click.echo(f"  Nodes: {result['node_count']}")
            click.echo(f"  Links: {result['link_count']}")
        else:
            click.echo(f"Successfully converted {input} to GNS3 project at {output}")
            click.echo(f"Created {result['node_count']} nodes and {result['link_count']} links")

        if result.get("portable_file"):
            click.echo(f"Portable project: {result['portable_file']}")

        if result.get("unmapped_types"):
            click.echo(
                f"Warning: unmapped node types (fell back to generic QEMU): "
                f"{', '.join(result['unmapped_types'])}"
            )
            click.echo("  Tip: create a JSON mapping file and pass it with --mapping")
    except Exception as e:
        click.echo(f"Error during conversion: {e}")
        logger.exception("Conversion error")
        sys.exit(1)


@cli.command()
@click.option(
    "--input", "-i", required=True, type=click.Path(exists=True),
    help="Input CML/VIRL file path to validate"
)
@click.option(
    "--mapping", "-m", type=click.Path(exists=True),
    help="Custom node mapping JSON file"
)
def validate(input, mapping):
    """Validate a CML/VIRL topology file without converting it."""
    node_mappings = _build_node_mappings(mapping)

    try:
        converter = Converter(node_mappings=node_mappings)
        info = converter.validate_file(Path(input))

        click.echo(f"File type:      {info['file_type'].upper()}")
        click.echo(f"Topology name:  {info['topology_name']}")
        click.echo(f"Nodes:          {info['node_count']}")
        click.echo(f"Links:          {info['link_count']}")

        if info["unmapped_types"]:
            click.echo(f"Unmapped types: {', '.join(info['unmapped_types'])}")
            click.echo("  Tip: create a JSON mapping file and pass it with --mapping")
        else:
            click.echo("All node types have mappings.")

        click.echo("Validation passed.")
    except Exception as e:
        click.echo(f"Validation failed: {e}")
        logger.exception("Validation error")
        sys.exit(1)


@cli.command()
def list_mappings():
    """List the default node type mappings."""
    click.echo("Default CML/VIRL to GNS3 node mappings:")
    click.echo(f"  {'Node Type':<22} {'GNS3 Template':<28} {'Compute':<16} Console")
    click.echo(f"  {'-' * 22} {'-' * 28} {'-' * 16} {'-' * 7}")
    for node_type, m in DEFAULT_NODE_MAPPINGS.items():
        click.echo(
            f"  {node_type:<22} {m['gns3_template']:<28} "
            f"{m.get('compute_type', 'qemu'):<16} {m.get('console_type', 'telnet')}"
        )


@cli.command()
@click.option(
    "--input", "-i", required=True, type=click.Path(exists=True),
    help="Input GNS3 .gns3 project file"
)
@click.option(
    "--output", "-o", required=True, type=click.Path(),
    help="Output CML YAML file path"
)
def reverse(input, output):
    """Convert a GNS3 project file back to CML YAML."""
    try:
        converter = Converter()
        result = converter.reverse_convert(Path(input), Path(output))
        click.echo(f"Successfully converted GNS3 project to CML YAML: {output}")
        click.echo(f"  Nodes: {result['node_count']}")
        click.echo(f"  Links: {result['link_count']}")
    except Exception as e:
        click.echo(f"Error during reverse conversion: {e}")
        logger.exception("Reverse conversion error")
        sys.exit(1)


@cli.command()
@click.option(
    "--input-dir", "-i", required=True,
    type=click.Path(exists=True, file_okay=False),
    help="Directory containing CML/VIRL files to convert"
)
@click.option(
    "--output-dir", "-o", required=True, type=click.Path(),
    help="Base output directory for GNS3 projects"
)
@click.option(
    "--mapping", "-m", type=click.Path(exists=True),
    help="Custom node mapping JSON file"
)
@click.option(
    "--gns3-version", type=click.Choice(sorted(GNS3_VERSION_REVISIONS.keys())),
    default=None,
    help="Target GNS3 version family"
)
@click.option(
    "--portable", is_flag=True, default=False,
    help="Also produce .gns3p portable project archives"
)
def batch(input_dir, output_dir, mapping, gns3_version, portable):
    """Batch-convert all CML/VIRL files in a directory."""
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)

    node_mappings = _build_node_mappings(mapping)

    extensions = ('.yaml', '.yml', '.virl', '.xml', '.gns3')
    files = sorted(
        f for f in input_dir.iterdir()
        if f.is_file() and f.suffix.lower() in extensions
    )

    if not files:
        click.echo(f"No CML/VIRL files found in {input_dir}")
        sys.exit(0)

    click.echo(f"Found {len(files)} file(s) to convert.")

    converter = Converter(
        node_mappings=node_mappings,
        gns3_version=gns3_version,
    )

    success = 0
    failed = 0

    for file_path in files:
        project_output = output_dir / file_path.stem
        try:
            result = converter.convert(file_path, project_output,
                                       portable=portable)
            click.echo(
                f"  OK  {file_path.name} -> {result['node_count']} nodes, "
                f"{result['link_count']} links"
            )
            success += 1
        except Exception as e:
            click.echo(f"  FAIL {file_path.name}: {e}")
            failed += 1

    click.echo(f"\nBatch complete: {success} succeeded, {failed} failed.")


@cli.command()
@click.option(
    "--file-a", "-a", required=True, type=click.Path(exists=True),
    help="First topology file"
)
@click.option(
    "--file-b", "-b", required=True, type=click.Path(exists=True),
    help="Second topology file"
)
def diff(file_a, file_b):
    """Compare two topology files and show differences."""
    try:
        converter = Converter()
        result = converter.diff(Path(file_a), Path(file_b))
        click.echo(result["summary"])
    except Exception as e:
        click.echo(f"Error during diff: {e}")
        logger.exception("Diff error")
        sys.exit(1)


@cli.command(name="show")
@click.option(
    "--input", "-i", required=True, type=click.Path(exists=True),
    help="Topology file to visualize"
)
def show_topology(input):
    """Display an ASCII visualization of a topology."""
    try:
        converter = Converter()
        output = converter.visualize(Path(input))
        click.echo(output)
    except Exception as e:
        click.echo(f"Error during visualization: {e}")
        logger.exception("Visualization error")
        sys.exit(1)


@cli.command(name="export-clab")
@click.option(
    "--input", "-i", required=True, type=click.Path(exists=True),
    help="Input CML/VIRL/GNS3 topology file"
)
@click.option(
    "--output", "-o", required=True, type=click.Path(),
    help="Output .clab.yml file path"
)
@click.option(
    "--mapping", "-m", type=click.Path(exists=True),
    help="Custom node mapping JSON file"
)
def export_clab(input, output, mapping):
    """Export a topology to containerlab .clab.yml format."""
    node_mappings = _build_node_mappings(mapping)
    try:
        converter = Converter(node_mappings=node_mappings)
        result = converter.export_containerlab(Path(input), Path(output))
        click.echo(f"Exported containerlab topology: {output}")
        click.echo(f"  Nodes: {result['node_count']}  Links: {result['link_count']}")
    except Exception as e:
        click.echo(f"Error during export: {e}")
        logger.exception("Containerlab export error")
        sys.exit(1)


@cli.command(name="server-check")
@click.option("--host", default="localhost", help="GNS3 server hostname")
@click.option("--port", default=3080, type=int, help="GNS3 server port")
@click.option("--user", default=None, help="GNS3 server username")
@click.option("--password", default=None, help="GNS3 server password")
@click.option(
    "--mapping", "-m", type=click.Path(exists=True),
    help="Custom node mapping JSON file"
)
def server_check(host, port, user, password, mapping):
    """Check template availability on a GNS3 server."""
    from cml2gns.utils.gns3_api import GNS3APIClient
    node_mappings = _build_node_mappings(mapping)
    try:
        client = GNS3APIClient(host=host, port=port, user=user, password=password)
        version = client.get_version()
        click.echo(f"GNS3 server version: {version.get('version', 'unknown')}")

        enriched, missing = client.resolve_node_mappings(node_mappings)
        resolved = len(node_mappings) - len(missing)
        click.echo(f"Templates resolved: {resolved}/{len(node_mappings)}")
        if missing:
            click.echo(f"Missing templates: {', '.join(missing)}")
    except ConnectionError as e:
        click.echo(f"Cannot connect to GNS3 server: {e}")
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}")
        logger.exception("Server check error")
        sys.exit(1)


def _interactive_mapping_phase(input_path, node_mappings):
    """Scan the input file for unmapped types and prompt the user."""
    try:
        converter = Converter(node_mappings=node_mappings)
        info = converter.validate_file(input_path)
    except Exception:
        return node_mappings

    unmapped = info.get("unmapped_types", [])
    if not unmapped:
        return node_mappings

    click.echo(f"\nUnmapped node types found: {', '.join(unmapped)}")
    click.echo("Enter GNS3 template names (leave blank to skip):\n")

    for ntype in unmapped:
        template = click.prompt(
            f"  GNS3 template for '{ntype}'",
            default="", show_default=False
        )
        if template.strip():
            console = click.prompt(
                f"  Console type for '{ntype}'",
                default="telnet"
            )
            compute = click.prompt(
                f"  Compute type for '{ntype}'",
                default="qemu"
            )
            node_mappings[ntype] = {
                "gns3_template": template.strip(),
                "console_type": console.strip(),
                "compute_type": compute.strip(),
                "symbol": ":/symbols/classic/computer.svg",
                "properties": {},
            }
            click.echo(f"  -> Mapped '{ntype}' to '{template.strip()}'")
        click.echo()

    return node_mappings


def main():
    """Main entry point for the CLI."""
    try:
        cli()
    except Exception as e:
        logger.exception("Unhandled exception")
        click.echo(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
