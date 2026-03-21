"""Cross-platform sandboxing primitives for Frontier tool execution."""

__all__ = [
    "ExecutionResult",
    "ExecutionSpec",
    "HostPlatform",
    "IsolationStrategy",
    "SandboxPlan",
    "SandboxPolicy",
    "ToolJailService",
    "detect_host_platform",
]


def __getattr__(name: str):
    if name in {"ExecutionResult", "ExecutionSpec", "SandboxPlan"}:
        from lattix_frontier.sandbox.executor import ExecutionResult, ExecutionSpec, SandboxPlan

        return {
            "ExecutionResult": ExecutionResult,
            "ExecutionSpec": ExecutionSpec,
            "SandboxPlan": SandboxPlan,
        }[name]
    if name == "ToolJailService":
        from lattix_frontier.sandbox.manager import ToolJailService

        return ToolJailService
    if name in {"HostPlatform", "IsolationStrategy", "SandboxPolicy", "detect_host_platform"}:
        from lattix_frontier.sandbox.policy import HostPlatform, IsolationStrategy, SandboxPolicy, detect_host_platform

        return {
            "HostPlatform": HostPlatform,
            "IsolationStrategy": IsolationStrategy,
            "SandboxPolicy": SandboxPolicy,
            "detect_host_platform": detect_host_platform,
        }[name]
    raise AttributeError(name)
