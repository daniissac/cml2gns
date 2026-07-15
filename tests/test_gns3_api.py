"""Integration tests for the server-backed GNS3 deployment workflow."""

import json
from urllib.parse import urlsplit

import pytest
from click.testing import CliRunner

from cml2gns.cli import cli
from cml2gns.converter import Converter
from cml2gns.utils.gns3_api import GNS3APIClient


PROJECT_ID = "11111111-1111-4111-8111-111111111111"
TEMPLATE_ID = "22222222-2222-4222-8222-222222222222"


class FakeResponse:
    def __init__(self, payload=None):
        self.payload = b"" if payload is None else json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


class FakeGNS3Transport:
    """A deterministic urllib transport that behaves like the needed API."""

    def __init__(self):
        self.requests = []
        self.node_counter = 0

    def __call__(self, request, timeout):
        method = request.get_method()
        path = urlsplit(request.full_url).path
        body = json.loads(request.data) if request.data else None
        self.requests.append((method, path, body, dict(request.headers), timeout))

        if method == "GET" and path == "/v2/version":
            return FakeResponse({"version": "2.2.59"})
        if method == "GET" and path == "/v2/templates":
            return FakeResponse(
                [
                    {
                        "name": "Cisco IOSv",
                        "template_id": TEMPLATE_ID,
                        "template_type": "qemu",
                    }
                ]
            )
        if method == "POST" and path == "/v2/projects":
            return FakeResponse({"project_id": PROJECT_ID, "name": body["name"]})
        if method == "POST" and "/templates/" in path:
            self.node_counter += 1
            node_id = f"00000000-0000-4000-8000-{self.node_counter:012d}"
            return FakeResponse(
                {
                    "node_id": node_id,
                    "name": body["name"],
                    "ports": [
                        {
                            "name": "GigabitEthernet0/0",
                            "short_name": "Gi0/0",
                            "adapter_number": 0,
                            "port_number": 0,
                        }
                    ],
                }
            )
        if method == "POST" and path.endswith("/links"):
            return FakeResponse(
                {
                    "link_id": "33333333-3333-4333-8333-333333333333",
                }
            )
        if method == "POST" and path.endswith("/drawings"):
            return FakeResponse(body)
        if method == "DELETE" and path == f"/v2/projects/{PROJECT_ID}":
            return FakeResponse()
        raise AssertionError(f"Unexpected request: {method} {path}")


@pytest.fixture
def fake_transport(monkeypatch):
    transport = FakeGNS3Transport()
    monkeypatch.setattr("cml2gns.utils.gns3_api.urlopen", transport)
    return transport


def _write_topology(path, interface="GigabitEthernet0/0"):
    path.write_text(
        "lab:\n"
        "  title: API Lab\n"
        "  nodes:\n"
        "    - {id: n1, label: R1, node_definition: iosv, x: 10, y: 20}\n"
        "    - {id: n2, label: R2, node_definition: iosv, x: 30, y: 40}\n"
        "  links:\n"
        f"    - {{id: l1, n1: n1, i1: {interface}, n2: n2, i2: {interface}}}\n"
    )


def _client(**kwargs):
    return GNS3APIClient(host="127.0.0.1", port=3080, **kwargs)


def test_client_and_converter_deploy_full_request_workflow(fake_transport, tmp_path):
    source = tmp_path / "lab.yaml"
    _write_topology(source)
    mappings = {"iosv": {"gns3_template": "Cisco IOSv"}}

    client = _client(token="secret-token")
    assert client.get_version()["version"] == "2.2.59"
    result = Converter(node_mappings=mappings).deploy(source, client)

    assert result["project_id"] == PROJECT_ID
    assert result["node_count"] == 2
    assert result["link_count"] == 1
    methods_and_paths = [(method, path) for method, path, *_ in fake_transport.requests]
    assert ("POST", "/v2/projects") in methods_and_paths
    assert any(
        method == "POST" and path.endswith("/links")
        for method, path in methods_and_paths
    )
    assert not any(method == "DELETE" for method, _ in methods_and_paths)
    assert all(
        headers.get("Authorization") == "Bearer secret-token"
        for _, _, _, headers, _ in fake_transport.requests
    )


def test_deploy_rolls_back_partial_project_on_interface_error(fake_transport, tmp_path):
    source = tmp_path / "bad-interface.yaml"
    _write_topology(source, interface="GigabitEthernet9/9")
    mappings = {"iosv": {"gns3_template": "Cisco IOSv"}}

    with pytest.raises(ValueError, match="is not available"):
        Converter(node_mappings=mappings).deploy(source, _client())

    assert any(
        method == "DELETE" and path == f"/v2/projects/{PROJECT_ID}"
        for method, path, *_ in fake_transport.requests
    )


def test_missing_template_fails_before_project_creation(fake_transport, tmp_path):
    source = tmp_path / "missing.yaml"
    _write_topology(source)
    mappings = {"iosv": {"gns3_template": "Not Installed"}}

    with pytest.raises(ValueError, match="not installed"):
        Converter(node_mappings=mappings).deploy(source, _client())

    assert not any(
        method == "POST" and path == "/v2/projects"
        for method, path, *_ in fake_transport.requests
    )


def test_deploy_cli_smoke(fake_transport, tmp_path):
    source = tmp_path / "cli.yaml"
    mapping = tmp_path / "mapping.json"
    _write_topology(source)
    mapping.write_text(
        json.dumps(
            {
                "iosv": {"gns3_template": "Cisco IOSv"},
            }
        )
    )

    result = CliRunner().invoke(
        cli,
        [
            "deploy",
            "-i",
            str(source),
            "-m",
            str(mapping),
            "--host",
            "127.0.0.1",
            "--port",
            "3080",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Deployed 'API Lab'" in result.output


def test_server_url_rejects_embedded_credentials():
    with pytest.raises(ValueError, match="must not contain credentials"):
        GNS3APIClient(host="https://user:password@gns3.example")
