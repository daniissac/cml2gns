"""
Tests for the CLI interface.
"""
import json
import pytest
from pathlib import Path
from click.testing import CliRunner

from cml2gns.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def sample_cml_file():
    return str(Path(__file__).parent / "fixtures" / "cml_samples" / "sample_topology.yaml")


@pytest.fixture
def sample_virl_file():
    return str(Path(__file__).parent / "fixtures" / "virl_samples" / "sample_topology.xml")


class TestConvertCommand:

    def test_convert_cml(self, runner, sample_cml_file, tmp_path):
        out_dir = str(tmp_path / "out")
        result = runner.invoke(cli, ["convert", "-i", sample_cml_file, "-o", out_dir])
        assert result.exit_code == 0
        assert "Successfully converted" in result.output
        assert any(Path(out_dir).glob("*.gns3"))

    def test_convert_virl(self, runner, sample_virl_file, tmp_path):
        out_dir = str(tmp_path / "out")
        result = runner.invoke(cli, ["convert", "-i", sample_virl_file, "-o", out_dir])
        assert result.exit_code == 0
        assert "Successfully converted" in result.output

    def test_convert_refuses_existing_dir(self, runner, sample_cml_file, tmp_path):
        out_dir = str(tmp_path)  # already exists
        result = runner.invoke(cli, ["convert", "-i", sample_cml_file, "-o", out_dir])
        assert result.exit_code != 0
        assert "already exists" in result.output

    def test_convert_force_overwrites(self, runner, sample_cml_file, tmp_path):
        out_dir = str(tmp_path)
        result = runner.invoke(cli, [
            "convert", "-i", sample_cml_file, "-o", out_dir, "--force"
        ])
        assert result.exit_code == 0
        assert "Successfully converted" in result.output

    def test_convert_dry_run(self, runner, sample_cml_file, tmp_path):
        out_dir = str(tmp_path / "dry")
        result = runner.invoke(cli, [
            "convert", "-i", sample_cml_file, "-o", out_dir, "--dry-run"
        ])
        assert result.exit_code == 0
        assert "Dry run" in result.output
        assert "Nodes:" in result.output
        assert not Path(out_dir).exists()

    def test_convert_strict_fails_on_unmapped(self, runner, tmp_path):
        cml = tmp_path / "input.yaml"
        cml.write_text(
            "---\ntopology:\n  name: t\n  nodes:\n    n1:\n"
            "      node_definition: weird_device\n  links:\n"
        )
        out_dir = str(tmp_path / "out")
        result = runner.invoke(cli, [
            "convert", "-i", str(cml), "-o", out_dir, "--strict"
        ])
        assert result.exit_code != 0
        assert "unmapped node types" in result.output.lower() or "Strict mode" in result.output

    def test_convert_with_custom_mapping(self, runner, sample_cml_file, tmp_path):
        mapping_file = tmp_path / "mappings.json"
        mapping_file.write_text(json.dumps({
            "iosv": {
                "gns3_template": "My Custom IOSv",
                "console_type": "telnet",
                "compute_type": "qemu",
                "symbol": ":/symbols/classic/router.svg",
            }
        }))
        out_dir = str(tmp_path / "out")
        result = runner.invoke(cli, [
            "convert", "-i", sample_cml_file, "-o", out_dir,
            "-m", str(mapping_file),
        ])
        assert result.exit_code == 0
        assert "custom node mappings" in result.output.lower()


class TestValidateCommand:

    def test_validate_cml(self, runner, sample_cml_file):
        result = runner.invoke(cli, ["validate", "-i", sample_cml_file])
        assert result.exit_code == 0
        assert "Validation passed" in result.output
        assert "CML" in result.output

    def test_validate_virl(self, runner, sample_virl_file):
        result = runner.invoke(cli, ["validate", "-i", sample_virl_file])
        assert result.exit_code == 0
        assert "Validation passed" in result.output
        assert "VIRL" in result.output

    def test_validate_reports_unmapped(self, runner, tmp_path):
        cml = tmp_path / "input.yaml"
        cml.write_text(
            "---\ntopology:\n  name: t\n  nodes:\n    n1:\n"
            "      node_definition: alien_box\n  links:\n"
        )
        result = runner.invoke(cli, ["validate", "-i", str(cml)])
        assert result.exit_code == 0
        assert "alien_box" in result.output


class TestListMappingsCommand:

    def test_list_mappings(self, runner):
        result = runner.invoke(cli, ["list-mappings"])
        assert result.exit_code == 0
        assert "iosv" in result.output
        assert "Cisco IOSv" in result.output
        assert "qemu" in result.output


class TestVersionFlag:

    def test_version_output(self, runner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "cml2gns" in result.output
