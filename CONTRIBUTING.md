# Contributing to RoNCT

Thanks for your interest in improving RoNCT. Bug reports, feature requests,
documentation fixes, and code contributions are all welcome.

Questions or maintainer contact:
[ronct.dev@icloud.com](mailto:ronct.dev@icloud.com).

## Before you start

- Check the [README](README.md) and [CHANGELOG](CHANGELOG.md) first.
- Search existing issues to avoid duplicates.
- For behavior changes or larger UI redesigns, open an issue to discuss the
  approach before writing code.

## Bug reports and feature requests

Use the GitHub issue templates:

- [Bug report](.github/ISSUE_TEMPLATE/bug_report.yml)
- [Feature request](.github/ISSUE_TEMPLATE/feature_request.yml)

When reporting a bug, include:

1. Windows version and RoNCT version.
2. Steps to reproduce.
3. Expected vs. actual behavior.
4. Relevant parts of `debug.log` (never paste your Nexus API key).

## Development setup

```powershell
git clone https://github.com/CurvesCat/ready-or-not-mod-compatibility-tester.git
cd ready-or-not-mod-compatibility-tester
python -m pip install -r requirements.txt
python run_gui.py
```

Run a quick syntax check before submitting:

```powershell
python -m compileall ron_mod_tester run_gui.py
```

## Code style

- Python 3.10+ with type hints on public functions.
- Keep the GUI strings localized through `ron_mod_tester/i18n.py`; add both
  Chinese and English entries when introducing UI text.
- Do not log or print API keys or other secrets.
- Keep generated files inside the software directory (cache, reports, backups,
  quarantine, logs).
- Name commits with conventional prefixes: `feat:`, `fix:`, `docs:`,
  `refactor:`, `chore:`.

## Pull requests

1. Fork the repository and create a feature branch.
2. Make focused commits.
3. Run the compile check and the GUI once locally.
4. Open a pull request using the template.

By submitting a pull request, you agree that your contribution may be used
under the repository's [license](LICENSE).
