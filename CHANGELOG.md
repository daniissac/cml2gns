# Changelog

## 0.2.0

- Correct GNS3 project nodes to use `node_type` and stop generating fake template IDs.
- Add transactional deployment through installed GNS3 server templates.
- Use the official `.gns3project` extension for portable archives.
- Preserve startup configurations by default and remove secret-rewriting behavior.
- Support current CML exports with root-level topology data, nested lab metadata,
  and named configuration records.
- Improve CML, GNS3, and containerlab parsing and reverse-conversion fidelity.
- Move package metadata to `pyproject.toml` and separate CI from release publishing.
- Refresh the project positioning and documentation.
