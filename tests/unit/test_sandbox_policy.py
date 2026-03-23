from frontier_runtime.sandbox import HostPlatform, IsolationStrategy, SandboxPolicy, detect_host_platform


def test_detect_host_platform_macos() -> None:
    assert detect_host_platform("Darwin") == HostPlatform.MACOS


def test_linux_policy_defaults_to_hardened_container() -> None:
    policy = SandboxPolicy(platform=HostPlatform.LINUX)
    assert policy.strategy == IsolationStrategy.LINUX_HARDENED_CONTAINER
    assert policy.capabilities().strict_syscalls is True
