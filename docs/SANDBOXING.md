# Sandboxing

Lattix xFrontier now includes a cross-platform sandbox subsystem under `lattix_frontier/sandbox/`.

## Goals

- kernel-level or VM-backed isolation per host platform
- strong filesystem confinement through ephemeral workspaces
- mediated local Docker egress
- real tool execution through a jail abstraction instead of direct host subprocesses

## Current implementation

- Linux uses hardened Docker planning with read-only rootfs, capability drop, no-new-privileges, and Docker seccomp defaults.
- macOS and Windows use Docker Desktop VM-backed isolation with the same filesystem and egress topology.
- Tool execution is planned and optionally executed through `ToolJailService`.
- Local Docker egress is mediated through `sandbox-egress-gateway` on the `frontier-sandbox-internal` network.

## Install/autodetect groundwork

The future install capability can use `lattix_frontier.sandbox.install.recommend_installation()` to detect the OS and choose the right isolation prerequisites.

## Security model

- read-only root filesystem by default
- explicit input staging and output collection
- allowlisted executable set
- allowlisted destination hosts
- OPA-backed policy checks for filesystem, network, and jail posture
