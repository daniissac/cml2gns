"""
GNS3 server HTTP API client.

Connects to a running GNS3 server to fetch template IDs, validate
appliance availability, and optionally import projects.
"""

import json
import logging
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlsplit
import base64

logger = logging.getLogger(__name__)

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 3080


class GNS3APIClient:
    """
    Lightweight GNS3 server API client using only stdlib urllib.
    """

    def __init__(
        self,
        host=None,
        port=None,
        user=None,
        password=None,
        token=None,
        protocol="http",
    ):
        host = host or DEFAULT_HOST
        if "://" in host:
            parsed = urlsplit(host)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError(f"Invalid GNS3 server URL: {host}")
            if parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise ValueError(
                    "GNS3 server URL must not contain credentials, a query, or a fragment"
                )
            if parsed.path not in {"", "/"}:
                raise ValueError("GNS3 server URL must not contain a path")
            self.base_url = host.rstrip("/")
        else:
            self.base_url = (
                f"{protocol}://{host}:{port if port is not None else DEFAULT_PORT}"
            )
        self._auth_header = None
        if token:
            self._auth_header = f"Bearer {token}"
        elif user:
            creds = base64.b64encode(f"{user}:{password or ''}".encode()).decode()
            self._auth_header = f"Basic {creds}"

        parsed_base = urlsplit(self.base_url)
        if (
            self._auth_header
            and parsed_base.scheme == "http"
            and parsed_base.hostname not in {"127.0.0.1", "::1", "localhost"}
        ):
            logger.warning(
                "GNS3 credentials are being sent over unencrypted HTTP to %s",
                parsed_base.hostname,
            )

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
                payload = resp.read()
                if not payload:
                    return None
                return json.loads(payload.decode())
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

    def create_project(self, name, project_id=None):
        """Create a project and return the server's project object."""
        body = {"name": name}
        if project_id:
            body["project_id"] = project_id
        return self._request("/v2/projects", method="POST", body=body)

    def delete_project(self, project_id):
        """Delete a project, primarily for transactional rollback."""
        project_id = quote(str(project_id), safe="")
        return self._request(f"/v2/projects/{project_id}", method="DELETE")

    def create_node_from_template(self, project_id, template_id, name, x, y):
        """Create a project node from an installed GNS3 template."""
        project_id = quote(str(project_id), safe="")
        template_id = quote(str(template_id), safe="")
        return self._request(
            f"/v2/projects/{project_id}/templates/{template_id}",
            method="POST",
            body={"name": name, "x": int(x), "y": int(y)},
        )

    def create_link(self, project_id, endpoints, link_type="ethernet"):
        """Create a link between two server-side node endpoints."""
        project_id = quote(str(project_id), safe="")
        return self._request(
            f"/v2/projects/{project_id}/links",
            method="POST",
            body={
                "nodes": endpoints,
                "link_type": link_type,
                "suspend": False,
            },
        )

    def create_drawing(self, project_id, drawing):
        """Create a drawing from a GNS3Drawing-compatible dictionary."""
        project_id = quote(str(project_id), safe="")
        return self._request(
            f"/v2/projects/{project_id}/drawings",
            method="POST",
            body=drawing,
        )

    def import_project(self, project_id, gns3project_path):
        """Import a .gns3project portable archive into the server."""
        with open(gns3project_path, "rb") as f:
            data = f.read()

        project_id = quote(str(project_id), safe="")
        url = urljoin(self.base_url + "/", f"/v2/projects/{project_id}/import")
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
            raise ConnectionError(f"Cannot reach GNS3 server: {e.reason}") from e

    def resolve_node_mappings(self, node_mappings):
        """
        Enrich node mappings with real template_id values from the server.

        Returns a new dict with the same keys, each mapping updated with
        ``template_id`` if a matching template is found.  Also returns a
        list of template names that could NOT be resolved.
        """
        templates = self.list_templates()
        by_name = {}
        by_id = {}
        for t in templates:
            by_name[t.get("name", "").lower()] = t
            if t.get("template_id"):
                by_id[t["template_id"]] = t

        enriched = {}
        missing = []

        for node_type, mapping in node_mappings.items():
            enriched[node_type] = dict(mapping)
            tpl_name = mapping.get("gns3_template", "")
            requested_id = mapping.get("template_id")
            server_tpl = (
                by_id.get(requested_id)
                if requested_id
                else by_name.get(tpl_name.lower())
            )
            if server_tpl:
                enriched[node_type]["template_id"] = server_tpl.get("template_id")
                logger.debug(
                    f"Resolved '{tpl_name}' -> {server_tpl.get('template_id')}"
                )
            else:
                missing.append(tpl_name)

        return enriched, missing
