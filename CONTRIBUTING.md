# Contributing

Thanks for improving `cml2gns`.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest -q
```

Before opening a pull request, also verify the distributions:

```bash
python -m build
python -m twine check dist/*
```

## Change guidelines

- Add a regression test for behavior changes.
- Keep offline project generation and server deployment semantics distinct.
- Do not add vendor images, credentials, exported device secrets, or proprietary lab files.
- Preserve startup configurations unless a user explicitly opts into a documented transformation.
- Base GNS3 project-format changes on the upstream GNS3 schema or API documentation.

## Pull requests

Describe the user-facing problem, the fix, and the validation performed. Keep unrelated refactors out of the same change.
