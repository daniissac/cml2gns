#!/usr/bin/env python3
"""
Command line interface for cml2gns.
"""

import sys
import click
import logging
import shutil
import tempfile
from pathlib import Path

from cml2gns import __version__
from cml2gns.converter import Converter
from cml2gns.utils.config import (
    load_config,
    DEFAULT_NODE_MAPPINGS,
    GNS3_VERSION_REVISIONS,
    validate_node_mappings,
)

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("cml2gns")


def _build_node_mappings(mapping_path):
    """Merge default and optional custom node mappings."""
    node_mappings = {
        node_type: {
            **mapping,
            "properties": dict(mapping.get("properties", {})),
        }
        for node_type, mapping in DEFAULT_NODE_MAPPINGS.items()
    }
    if mapping_path:
        try:
            custom_mappings = load_config(mapping_path)
            validate_node_mappings(custom_mappings)
            for node_type, custom in custom_mappings.items():
                merged = dict(node_mappings.get(node_type, {}))
                merged.update(custom)
                if "properties" in custom:
                    properties = dict(
                        node_mappings.get(node_type, {}).get("properties", {})
                    )
                    properties.update(custom["properties"])
                    merged["properties"] = properties
                node_mappings[node_type] = merged
            validate_node_mappings(node_mappings, require_template=True)
            click.echo(f"Loaded custom node mappings from {mapping_path}")
        except Exception as e:
            raise click.ClickException(f"Error loading custom mappings: {e}") from e
    return node_mappings


@click.group()
@click.version_option(version=__version__, prog_name="cml2gns")
@click.option("--debug/--no-debug", default=False, help="Enable debug logging")
def cli(debug):
    """Translate, validate, and deploy network lab topologies."""
    if debug:
        logger.setLevel(logging.DEBUG)
        click.echo("Debug mode enabled")


@cli.command()
@click.option(
    "--input",
    "-i",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Input topology file path",
)
@click.option(
    "--output",
    "-o",
    required=True,
    type=click.Path(file_okay=False),
    help="Output directory for GNS3 project",
)
@click.option(
    "--mapping",
    "-m",
    type=click.Path(exists=True, dir_okay=False),
    help="Custom node mapping JSON file",
)
@click.option(
    "--force/--no-force", default=False, help="Overwrite existing output directory"
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Parse and validate without writing files",
)
@click.option(
    "--strict",
    is_flag=True,
    default=False,
    help="Fail on unmapped node types instead of using a generic fallback",
)
@click.option(
    "--gns3-version",
    type=click.Choice(sorted(GNS3_VERSION_REVISIONS.keys())),
    default=None,
    help="Target GNS3 version family (e.g. 2.0, 2.1, 2.2)",
)
@click.option(
    "--portable",
    is_flag=True,
    default=False,
    help="Also produce a .gns3project portable project archive",
)
@click.option(
    "--normalize-config",
    is_flag=True,
    default=False,
    help="Normalize quoted hostnames in sidecar startup configs",
)
@click.option(
    "--interactive",
    is_flag=True,
    default=False,
    help="Prompt for GNS3 template names for unmapped node types",
)
def convert(
    input,
    output,
    mapping,
    force,
    dry_run,
    strict,
    gns3_version,
    portable,
    normalize_config,
    interactive,
):
    """Convert a supported topology file to an offline GNS3 project."""
    input_path = Path(input)
    output_path = Path(output)
    replace_existing = False

    if not dry_run:
        if output_path.exists() or output_path.is_symlink():
            if not force:
                raise click.ClickException(
                    f"Output directory '{output}' already exists. "
                    "Use --force to overwrite."
                )
            if output_path.is_symlink() or not output_path.is_dir():
                raise click.ClickException(
                    f"Refusing to replace non-directory output path '{output}'"
                )

            resolved_output = output_path.resolve()
            protected = {
                Path(resolved_output.anchor),
                Path.cwd().resolve(),
                Path.home().resolve(),
            }
            if resolved_output in protected or input_path.resolve().is_relative_to(
                resolved_output
            ):
                raise click.ClickException(
                    f"Refusing to remove protected output directory '{output}'"
                )
            replace_existing = True
    node_mappings = _build_node_mappings(mapping)

    if interactive:
        node_mappings = _interactive_mapping_phase(input_path, node_mappings)

    staging_root = None
    try:
        converter = Converter(
            node_mappings=node_mappings,
            strict=strict,
            gns3_version=gns3_version,
            normalize_configs=normalize_config,
        )
        conversion_output = output_path
        if replace_existing:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            staging_root = Path(
                tempfile.mkdtemp(
                    prefix=f".{output_path.name}.cml2gns-",
                    dir=output_path.parent,
                )
            )
            conversion_output = staging_root / "output"

        result = converter.convert(
            input_path, conversion_output, dry_run=dry_run, portable=portable
        )

        if replace_existing:
            project_name = Path(result["project_file"]).name
            staged_portable = (
                Path(result["portable_file"]) if result.get("portable_file") else None
            )
            portable_target = None
            if staged_portable is not None:
                portable_target = output_path.parent / staged_portable.name
                if portable_target.is_symlink() or portable_target.is_dir():
                    raise click.ClickException(
                        f"Refusing to replace portable archive path '{portable_target}'"
                    )
            shutil.rmtree(output_path)
            conversion_output.replace(output_path)
            result["project_file"] = str(output_path / project_name)
            if staged_portable is not None:
                staged_portable.replace(portable_target)
                result["portable_file"] = str(portable_target)

        if dry_run:
            click.echo("Dry run (no files written):")
            click.echo(f"  Nodes: {result['node_count']}")
            click.echo(f"  Links: {result['link_count']}")
        else:
            click.echo(f"Successfully converted {input} to GNS3 project at {output}")
            click.echo(
                f"Created {result['node_count']} nodes and {result['link_count']} links"
            )

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
    finally:
        if staging_root is not None and staging_root.exists():
            shutil.rmtree(staging_root, ignore_errors=True)


@cli.command()
@click.option(
    "--input",
    "-i",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Input topology file path to validate",
)
@click.option(
    "--mapping",
    "-m",
    type=click.Path(exists=True, dir_okay=False),
    help="Custom node mapping JSON file",
)
def validate(input, mapping):
    """Validate a supported topology file without converting it."""
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
    "--input",
    "-i",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Input GNS3 .gns3 project file",
)
@click.option(
    "--output",
    "-o",
    required=True,
    type=click.Path(dir_okay=False),
    help="Output CML YAML file path",
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
    "--input-dir",
    "-i",
    required=True,
    type=click.Path(exists=True, file_okay=False),
    help="Directory containing supported topology files",
)
@click.option(
    "--output-dir",
    "-o",
    required=True,
    type=click.Path(file_okay=False),
    help="Base output directory for GNS3 projects",
)
@click.option(
    "--mapping",
    "-m",
    type=click.Path(exists=True, dir_okay=False),
    help="Custom node mapping JSON file",
)
@click.option(
    "--gns3-version",
    type=click.Choice(sorted(GNS3_VERSION_REVISIONS.keys())),
    default=None,
    help="Target GNS3 version family",
)
@click.option(
    "--portable",
    is_flag=True,
    default=False,
    help="Also produce .gns3project portable project archives",
)
@click.option(
    "--normalize-config",
    is_flag=True,
    default=False,
    help="Normalize quoted hostnames in sidecar startup configs",
)
def batch(input_dir, output_dir, mapping, gns3_version, portable, normalize_config):
    """Batch-convert supported topology files in a directory."""
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)

    node_mappings = _build_node_mappings(mapping)

    extensions = (".yaml", ".yml", ".virl", ".xml", ".gns3")
    files = sorted(
        f for f in input_dir.iterdir() if f.is_file() and f.suffix.lower() in extensions
    )

    if not files:
        click.echo(f"No supported topology files found in {input_dir}")
        sys.exit(0)

    click.echo(f"Found {len(files)} file(s) to convert.")

    converter = Converter(
        node_mappings=node_mappings,
        gns3_version=gns3_version,
        normalize_configs=normalize_config,
    )

    success = 0
    failed = 0

    for file_path in files:
        project_output = output_dir / file_path.stem
        try:
            result = converter.convert(file_path, project_output, portable=portable)
            click.echo(
                f"  OK  {file_path.name} -> {result['node_count']} nodes, "
                f"{result['link_count']} links"
            )
            success += 1
        except Exception as e:
            click.echo(f"  FAIL {file_path.name}: {e}")
            failed += 1

    click.echo(f"\nBatch complete: {success} succeeded, {failed} failed.")
    if failed:
        raise click.ClickException(f"{failed} conversion(s) failed")


@cli.command()
@click.option(
    "--file-a",
    "-a",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="First topology file",
)
@click.option(
    "--file-b",
    "-b",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Second topology file",
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
    "--input",
    "-i",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Topology file to visualize",
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
    "--input",
    "-i",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Input CML/VIRL/GNS3 topology file",
)
@click.option(
    "--output",
    "-o",
    required=True,
    type=click.Path(dir_okay=False),
    help="Output .clab.yml file path",
)
@click.option(
    "--mapping",
    "-m",
    type=click.Path(exists=True, dir_okay=False),
    help="Custom node mapping JSON file",
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
@click.option("--host", default="localhost", help="GNS3 server hostname or URL")
@click.option("--port", default=3080, type=int, help="GNS3 server port")
@click.option(
    "--protocol",
    type=click.Choice(["http", "https"]),
    default="http",
    show_default=True,
    help="Protocol when --host is a hostname",
)
@click.option("--user", default=None, help="GNS3 server username")
@click.option(
    "--password",
    default=None,
    envvar="GNS3_PASSWORD",
    help="GNS3 password (or set GNS3_PASSWORD)",
)
@click.option(
    "--token",
    default=None,
    envvar="GNS3_API_TOKEN",
    help="GNS3 API token (or set GNS3_API_TOKEN)",
)
@click.option(
    "--mapping",
    "-m",
    type=click.Path(exists=True, dir_okay=False),
    help="Custom node mapping JSON file",
)
def server_check(host, port, protocol, user, password, token, mapping):
    """Check template availability on a GNS3 server."""
    from cml2gns.utils.gns3_api import GNS3APIClient

    node_mappings = _build_node_mappings(mapping)
    try:
        client = GNS3APIClient(
            host=host,
            port=port,
            protocol=protocol,
            user=user,
            password=password,
            token=token,
        )
        version = client.get_version()
        click.echo(f"GNS3 server version: {version.get('version', 'unknown')}")

        _, missing = client.resolve_node_mappings(node_mappings)
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


@cli.command()
@click.option(
    "--input",
    "-i",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Input topology file",
)
@click.option(
    "--mapping",
    "-m",
    type=click.Path(exists=True, dir_okay=False),
    help="Custom node mapping JSON file",
)
@click.option("--project-name", default=None, help="Override the GNS3 project name")
@click.option("--host", default="localhost", help="GNS3 server hostname or URL")
@click.option("--port", default=3080, type=int, help="GNS3 server port")
@click.option(
    "--protocol",
    type=click.Choice(["http", "https"]),
    default="http",
    show_default=True,
    help="Protocol when --host is a hostname",
)
@click.option("--user", default=None, help="GNS3 server username")
@click.option(
    "--password",
    default=None,
    envvar="GNS3_PASSWORD",
    help="GNS3 password (or set GNS3_PASSWORD)",
)
@click.option(
    "--token",
    default=None,
    envvar="GNS3_API_TOKEN",
    help="GNS3 API token (or set GNS3_API_TOKEN)",
)
@click.option(
    "--keep-partial",
    is_flag=True,
    default=False,
    help="Keep a partially created project if deployment fails",
)
def deploy(
    input,
    mapping,
    project_name,
    host,
    port,
    protocol,
    user,
    password,
    token,
    keep_partial,
):
    """Deploy a topology using templates installed on a GNS3 server."""
    from cml2gns.utils.gns3_api import GNS3APIClient

    node_mappings = _build_node_mappings(mapping)
    client = GNS3APIClient(
        host=host,
        port=port,
        protocol=protocol,
        user=user,
        password=password,
        token=token,
    )

    try:
        result = Converter(node_mappings=node_mappings).deploy(
            Path(input),
            client,
            project_name=project_name,
            rollback_on_error=not keep_partial,
        )
        click.echo(f"Deployed '{result['project_name']}' to {client.base_url}")
        click.echo(
            f"  Nodes: {result['node_count']}  Links: {result['link_count']}  "
            f"Drawings: {result['drawing_count']}"
        )
        click.echo(f"  Project ID: {result['project_id']}")
        if result["config_count"]:
            click.echo(
                "  Note: startup configs are preserved by offline conversion but "
                "are not injected during server deployment."
            )
    except ConnectionError as e:
        raise click.ClickException(str(e)) from e
    except Exception as e:
        logger.exception("Deployment error")
        raise click.ClickException(str(e)) from e


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
            f"  GNS3 template for '{ntype}'", default="", show_default=False
        )
        if template.strip():
            console = click.prompt(f"  Console type for '{ntype}'", default="telnet")
            compute = click.prompt(f"  Compute type for '{ntype}'", default="qemu")
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
