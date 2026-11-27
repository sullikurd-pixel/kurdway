# Security policy
Status: requirements, not implemented controls.
Keep credentials out of Git and rotate exposed secrets. Require MFA for maintainers, least privilege, protected main, reviewed PRs, pinned CI dependencies, dependency and secret scanning. TLS only in production. Threat model targeted surveillance, account takeover, malicious uploads and location disclosure. Report vulnerabilities privately using GitHub private vulnerability reporting once enabled; never post sensitive details publicly. Block releases for unresolved critical/high risks; document remediation and retest.
