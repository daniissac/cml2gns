#!/usr/bin/env python3
"""
Command line interface for NetBridge.
"""
import os
import sys
import click
import logging
from pathlib import Path

from netbridge.converter import Converter
from netbridge.utils.config import load_config, DEFAULT_NODE_MAPPINGS

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("netbridge")


@click.group()
@click.option("--debug/--no-debug", default=False, help="Enable debug logging")
def cli(debug):
    """NetBridge: Convert CML/VIRL YAML files to GNS3 projects."""
    if debug:
        logger.setLevel(logging.DEBUG)
        click.echo("Debug mode enabled")


@cli.command()
@click.option(
    "--input", "-i", required=True, type=click.Path(exists=True),
    help="Input CML/VIRL YAML file path"
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
def convert(input, output, mapping, force):
    """Convert CML/VIRL YAML to GNS3 project."""
    input_path = Path(input)
    output_path = Path(output)
    
    # Check if output directory exists
    if output_path.exists() and not force:
        click.echo(f"Error: Output directory '{output}' already exists. Use --force to overwrite.")
        sys.exit(1)
    
    # Create output directory if it doesn't exist
    if not output_path.exists():
        output_path.mkdir(parents=True)
    
    # Load node mappings
    node_mappings = DEFAULT_NODE_MAPPINGS
    if mapping:
        try:
            custom_mappings = load_config(mapping)
            node_mappings.update(custom_mappings)
            click.echo(f"Loaded custom node mappings from {mapping}")
        except Exception as e:
            click.echo(f"Error loading custom mappings: {e}")
            sys.exit(1)
    
    # Create converter and run conversion
    try:
        converter = Converter(node_mappings=node_mappings)
        result = converter.convert(input_path, output_path)
        click.echo(f"Successfully converted {input} to GNS3 project at {output}")
        click.echo(f"Created {result['node_count']} nodes and {result['link_count']} links")
    except Exception as e:
        click.echo(f"Error during conversion: {e}")
        logger.exception("Conversion error")
        sys.exit(1)


@cli.command()
def list_mappings():
    """List the default node type mappings."""
    click.echo("Default CML/VIRL to GNS3 node mappings:")
    for node_type, mapping in DEFAULT_NODE_MAPPINGS.items():
        click.echo(f"  {node_type}: {mapping['gns3_template']}")


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