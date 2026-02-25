"""
GNS3 server HTTP API client.

Connects to a running GNS3 server to fetch template IDs, validate
appliance availability, and optionally import projects.
"""
import json
import logging
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
import base64

logger = logging.getLogger(__name__)

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 3080


class GNS3APIClient:
    """
    Lightweight GNS3 server API client using only stdlib urllib.
    """

    def __init__(self, host=None, port=None, user=None, password=None):
        self.base_url = f"http://{host or DEFAULT_HOST}:{port or DEFAULT_PORT}"
        self._auth_header = None
        if user:
            creds = base64.b64encode(
                f"{user}:{password or ''}".encode()
            ).decode()
            self._auth_header = f"Basic {creds}"

    def _request(self, path, method="GET", body=None):
        url = urljoin(self.base_url + "/", path.lstrip("/"))
        headers = {"Accept": "application/json"}
        if self._auth_header:
            headers["Authorization"] = self._auth_header
        if body is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(body).encode()

        req = Request(url, data=body, headers=headers, method=method)
        try:
            with urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except HTTPError as e:
            logger.error(f"GNS3 API error {e.code}: {e.reason} ({url})")
            raise
        except URLError as e:
            logger.error(f"Cannot reach GNS3 server at {url}: {e.reason}")
            raise ConnectionError(
                f"Cannot reach GNS3 server at {self.base_url}: {e.reason}"
            ) from e

    def get_version(self):
        return self._request("/v2/version")

    def list_templates(self):
        return self._request("/v2/templates")

    def get_template_by_name(self, name):
        """Find a template by name (case-insensitive)."""
        lower = name.lower()
        for t in self.list_templates():
            if t.get("name", "").lower() == lower:
                return t
        return None

    def list_projects(self):
        return self._request("/v2/projects")

    def import_project(self, project_id, gns3p_path):
        """Import a .gns3p portable archive into the server."""
        with open(gns3p_path, 'rb') as f:
            data = f.read()

        url = urljoin(
            self.base_url + "/",
            f"/v2/projects/{project_id}/import"
        )
        headers = {
            "Content-Type": "application/octet-stream",
        }
        if self._auth_header:
            headers["Authorization"] = self._auth_header

        req = Request(url, data=data, headers=headers, method="POST")
        try:
            with urlopen(req, timeout=120) as resp:
                return json.loads(resp.read().decode())
        except HTTPError as e:
            logger.error(f"Import failed {e.code}: {e.reason}")
            raise
        except URLError as e:
            raise ConnectionError(
                f"Cannot reach GNS3 server: {e.reason}"
            ) from e

    def resolve_node_mappings(self, node_mappings):
        """
        Enrich node mappings with real template_id values from the server.

        Returns a new dict with the same keys, each mapping updated with
        ``template_id`` if a matching template is found.  Also returns a
        list of template names that could NOT be resolved.
        """
        templates = self.list_templates()
        by_name = {}
        for t in templates:
            by_name[t.get("name", "").lower()] = t

        enriched = {}
        missing = []

        for node_type, mapping in node_mappings.items():
            enriched[node_type] = dict(mapping)
            tpl_name = mapping.get("gns3_template", "")
            server_tpl = by_name.get(tpl_name.lower())
            if server_tpl:
                enriched[node_type]["template_id"] = server_tpl.get("template_id")
                logger.debug(
                    f"Resolved '{tpl_name}' -> {server_tpl.get('template_id')}"
                )
            else:
                missing.append(tpl_name)

        return enriched, missing
