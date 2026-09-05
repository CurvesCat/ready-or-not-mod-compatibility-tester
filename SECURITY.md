# Security Policy

## Supported versions

Security fixes are applied to the latest stable release and to `main`.

| Version | Supported |
| ------- | --------- |
| 0.4.x   | Yes       |
| < 0.4   | No        |

## Reporting a vulnerability

Please do **not** open a public issue for security problems.

Use GitHub's private vulnerability reporting on the repository's **Security**
tab, or contact the maintainer privately through GitHub. When reporting,
include:

- Affected RoNCT version and Windows version
- A minimal description of the issue
- Steps to reproduce, if possible
- Any files needed to reproduce (without API keys or personal data)

## What we take seriously

- Accidental exposure or logging of the Nexus API key
- Unsafe file paths / destructive operations on game or user directories
- Network requests beyond the documented Nexus endpoints
- Credential or configuration leakage in releases

## Handling

The maintainer will acknowledge reports as soon as possible, investigate the
impact, and coordinate a fix and release. Security-sensitive details stay
private until a fix is available.

## Disclosures

After a fix is released, a public advisory or changelog entry may be published
with enough detail to help users update.
