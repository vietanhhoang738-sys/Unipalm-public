# GitHub Actions templates

These workflow files are intentionally inert in the public source snapshot.
They were validated before export but are stored outside `.github/workflows/`
so a public clone cannot accidentally execute production/staging automation.

Before activating any workflow, review its required secrets, variables,
permissions, destination resources, and production-safety gates. Copy only
the workflow you explicitly intend to enable into `.github/workflows/`.
