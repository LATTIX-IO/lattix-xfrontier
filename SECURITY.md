# Security Policy

## Supported scope

This repository is intended to contain only:

- public application code
- public contracts and schemas
- public-safe deployment references
- sample/demo agent assets suitable for local-first development

It must not contain:

- secrets
- customer data
- internal-only prompts
- private Lattix agent definitions
- environment-specific production credentials or overlays

## Reporting a vulnerability

Please report security issues privately to the project maintainers through your established Lattix security contact or private disclosure channel.

Do not include exploit details in public issues or pull requests.

## Secure local-first expectations

The local-first stack is designed to remain functional and secure by default:

- `.env` is local-only and ignored by git
- demo agents are sourced from `examples/agents/`
- proprietary agent assets should be injected via `FRONTIER_AGENT_ASSETS_ROOT`
- local compose should not require public users to access private repositories
