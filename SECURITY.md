# Security Policy

## Supported versions

This project follows semantic versioning. Security patches are released for:

| Version        | Supported |
| -------------- | --------- |
| 0.1.x (latest) | ✓         |
| <0.1.0         | ✗         |

## Reporting a vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

If you discover a security vulnerability, please report it privately by emailing
**lukaszolszewski96@gmail.com** with the subject line `[SECURITY] image-quality-auditor`.

Include in your report:

- Description of the vulnerability
- Steps to reproduce
- Affected versions
- Potential impact (data exposure, code execution, denial of service, etc.)
- Suggested mitigation if you have one

### What to expect

- **Acknowledgment** within 72 hours
- **Initial assessment** within 7 days, including severity rating
- **Fix timeline** communicated based on severity
- **Public disclosure** coordinated with the reporter after the fix is released
- **Credit** in the security advisory (unless you prefer to remain anonymous)

## Security considerations for this project

This tool processes image files, which carries inherent risks:

### Image parsing vulnerabilities

This project depends on **OpenCV** and **Pillow** for image decoding. Both libraries
have had CVE-published vulnerabilities historically (buffer overflows on malformed
images, ZIP-bomb-style decompression attacks).

**Mitigation in this project:**

- Dependencies pinned via `uv.lock` for reproducible audits
- File size limits enforced before parsing (configurable, default 50MB)
- Resolution limits enforced (configurable, default 50 megapixels)
- Failed decodes are caught and reported, never silently ignored

### Handling sensitive data

This tool is designed with medical/biometric data in mind:

- **No data leaves the local machine** — no telemetry, no cloud uploads
- **Filename anonymization** (SHA256) is provided as a built-in feature
- **Original filenames are never written to logs** unless `--verbose` is set
- **The `.gitignore` excludes** `data/`, `patients/`, and `photos/` directories
  to prevent accidental commits of sensitive material

### Dependency security

- Dependencies are regularly updated via `uv lock --upgrade`
- GitHub Dependabot is enabled for the repository
- Pre-commit hook `detect-private-key` blocks accidental commits of credentials

## Out of scope

The following are explicitly out of scope for security reports:

- Attacks requiring physical access to the user's machine
- Social engineering of the user
- Vulnerabilities in dependencies for which a CVE is already published and a
  patch is available (please update first, report if still vulnerable)

## Hall of fame

Security researchers who have responsibly disclosed issues will be credited here
(with permission).

_No reports to date._
