# SBOM attestation and build provenance

**Status:** end-to-end verified on `main` on 2026-11-27. Both CycloneDX SBOM and SLSA provenance attestations were created and verified.  
**Scope:** public `HOADF-Team/AI-Toolbox` source archive and CycloneDX SBOM only.

## Workflow behavior

- Runs on source/CI changes pushed to `main` and on manual dispatch. The job has an explicit `refs/heads/main` guard, so pull requests, forks, tags and dispatches from other branches cannot mint attestations. Documentation-only and catalog-metadata-only commits do not trigger redundant attestations.
- Checks out the exact source commit with `actions/checkout` pinned to full commit SHA `11bd71901bbe5b1630ceea73d27597364c9af683`, with persisted Git credentials disabled.
- Validates the Skill-to-Tool map against the canonical `Personal-AI-Library` `main` branch before generating or signing artifacts.
- Installs Syft 1.57.1 from the official release archive and verifies both the checksum manifest and binary archive SHA-256.
- Generates and validates a non-empty CycloneDX JSON SBOM from that checkout.
- Creates a source archive from the exact commit using `git archive`; records commit SHA and archive SHA-256 in the workflow summary.
- Uses `actions/attest` pinned to reviewed full commit SHA `1e69f48acb82d1966a394da916b4c1698aa569d6` to create:
  1. a CycloneDX SBOM attestation (`https://cyclonedx.org/bom`);
  2. a SLSA build provenance attestation (`https://slsa.dev/provenance/v1`).
- Verifies both attestations using GitHub CLI, requiring the expected repository and exact signer workflow path `.github/workflows/sbom-attestation.yml`.

## Permissions and trust boundary

Only the `attest` job receives:
- `contents: read`
- `id-token: write`
- `attestations: write`

The workflow does not grant `artifact-metadata: write`, `packages: write`, or repository-wide OIDC permissions. No long-lived signing key or secret is used. The existing pull-request security smoke-test workflow remains read-only and now runs when the attestation workflow file changes.

## Verification policy

The workflow verifies:
- source archive digest binding;
- GitHub repository association;
- signer workflow identity;
- SLSA provenance predicate type;
- CycloneDX SBOM predicate type.

The latest trusted-branch run passed all steps, including canonical Skill-map validation. Run: [45953226471](https://github.com/HOADF-Team/AI-Toolbox/actions/runs/45953226471). Source commit: `19433a1df285538e6590b1583af870a7d6e1e182`. Both predicate types were verified with `gh attestation verify`, requiring the repository and exact signer workflow identity. The Syft catalog record now reflects this scoped result.

## Security limits

- Attestations prove a signed claim about a digest and workflow identity; they do not prove that source code is safe, that the SBOM is complete, or that the runner/build process was uncompromised.
- SBOM inventory is not a vulnerability scan. Trivy and dependency audits remain separate.
- This workflow does not attest private project source, trading-engine code, credentials, customer data, backups, container images or production server state.
- This is not VPS hardening or production incident-response validation.

## References

- [GitHub artifact attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations)
- [actions/attest](https://github.com/actions/attest)
- [GitHub CLI attestation verification](https://cli.github.com/manual/gh_attestation_verify)
- [CycloneDX in-toto predicate](https://github.com/in-toto/attestation/blob/main/spec/predicates/cyclonedx.md)
