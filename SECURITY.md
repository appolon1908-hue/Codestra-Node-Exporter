# Security policy

Report suspected vulnerabilities privately through GitHub Security Advisories for this repository. Do not put credentials, private keys, mTLS material, tokens, or exploit details in public issues.

The production artifact must be built only from a protected production SHA through the canonical Telemetry reusable workflow. Both build images are digest-pinned, the final image is scanned before release labeling, and release evidence includes SBOM, signature, provenance, source revision, and exact digest verification. Runtime credentials are mounted files; no secret value belongs in Git or Compose environment values.
