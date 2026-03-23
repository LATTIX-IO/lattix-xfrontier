# Sandboxing

Lattix xFrontier now includes a cross-platform sandbox boundary centered on the secure worker/runtime topology under `apps/workers/` plus the hardened local Docker network defined in `docker-compose.yml`.

## Goals

- kernel-level or VM-backed isolation per host platform
- strong filesystem confinement through ephemeral workspaces
- mediated local Docker egress
- real tool execution through a jail abstraction instead of direct host subprocesses

## Current implementation

- Linux uses hardened Docker planning with read-only rootfs, capability drop, no-new-privileges, and Docker seccomp defaults.
- macOS and Windows use Docker Desktop VM-backed isolation with the same filesystem and egress topology.
- Tool execution is expected to be routed through the worker/runtime sandbox boundary rather than direct host subprocess calls.
- Local Docker egress is mediated through `sandbox-egress-gateway` on the `frontier-sandbox-internal` network.

## Install/autodetect groundwork

The installer and CLI helpers can detect host prerequisites and select the appropriate Docker-backed isolation path for the current OS.

## Security model

- read-only root filesystem by default
- explicit input staging and output collection
- allowlisted executable set
- allowlisted destination hosts
- OPA-backed policy checks for filesystem, network, and jail posture
