# SBOM attestation and build provenance plan

**Status:** design only; no OIDC permission or external attestation has been enabled.  
**Scope:** public AI-Toolbox repository and its CI-generated source inventory.  
**Owner:** repository maintainers.

## Current baseline

- Syft 1.57.1 is pinned and tested in GitHub-hosted Ubuntu Linux x86_64 CI.
- CI generates a non-empty CycloneDX JSON SBOM from the repository checkout.
- Cosign 3.1.5 is installed and tested only for local ephemeral-key detached-signature verification and tamper detection.
- The existing security workflow has `contents: read` only. It does not request an OIDC token, publish signatures, or create GitHub artifact attestations.
- These checks establish tool behavior in CI, not a signed claim about the repository's release or a production environment.

## Recommended next-stage design

Use GitHub artifact attestations for a dedicated, trusted-branch workflow rather than extending the general pull-request smoke-test job.

1. Trigger on pushes to the protected default branch and optional manual dispatch. Do not run the signing job for pull requests or untrusted fork code.
2. Generate a CycloneDX SBOM with the pinned Syft release.
3. Create a deterministic source archive for the exact commit that the SBOM describes. Record the commit SHA and archive SHA-256 as workflow outputs/log evidence.
4. Attest the source archive and attach the SBOM using the official `actions/attest` action. Keep the subject immutable and digest-addressed.
5. Scope permissions to that job only:
   - `contents: read`
   - `id-token: write`
   - `attestations: write`
   - Add `artifact-metadata: write` only if repository artifact storage records are intentionally required.
6. Pin third-party actions to reviewed full commit SHAs. Do not use mutable action references in a security-critical workflow.
7. Verify the generated attestation with GitHub CLI from a separate verification step or clean runner. Check the expected repository, signer workflow identity, source commit, subject digest, and SBOM predicate type. A cryptographically valid signature from an unexpected workflow identity must fail policy.
8. Retain the SBOM and attestation bundle as CI artifacts for a defined period. Review the SBOM for sensitive package names and paths before making it publicly downloadable.

## Security boundaries

- OIDC `id-token: write` allows the job to request an identity token. Grant it only to the isolated attestation job; do not add it to the repository-wide workflow permissions.
- The attestation action uses short-lived Sigstore signing identity and stores the attestation with the repository. It does not require a long-lived private signing key in GitHub Secrets.
- A signature proves who signed a particular digest under the verified identity policy. It does not prove that source code is safe, that the SBOM is complete, or that the build process is free of compromise.
- The SBOM is an inventory, not a vulnerability report. Continue running Trivy and dependency audits separately.
- Do not attest private project source, trading-engine code, credentials, customer data, or server backups from this public repository workflow.
- Do not treat this workflow as server hardening. Production VPS security requires a separate approved host-specific assessment.

## Rollout gates

Before enabling the workflow:

- Confirm that the repository is intended to remain public and that publishing its SBOM metadata is acceptable.
- Review the exact `actions/attest` release and pin its immutable commit SHA.
- Confirm the exact CycloneDX predicate type emitted by the action and use that exact value for verification.
- Add an explicit signer-identity verification test and a negative test for an unexpected repository/workflow identity.
- Confirm that pull-request workflows remain unable to mint OIDC attestations.
- Run once on a trusted branch, inspect the resulting attestation, then verify it from a clean environment.
- Update tool records only after the end-to-end test passes; distinguish generated SBOM, signed SBOM attestation, and verified build provenance as separate capabilities.

## Official references

- GitHub: [Using artifact attestations to establish provenance](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations)
- GitHub: [actions/attest](https://github.com/actions/attest)
- GitHub: [Workflow permissions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)
- GitHub: [Verifying attestations offline](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/verify-attestations-offline)
