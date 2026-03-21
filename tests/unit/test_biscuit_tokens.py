from lattix_frontier.security.biscuit_tokens import CapabilityMinter, CapabilityVerifier, build_default_keypair


def test_capability_token_round_trip() -> None:
    keypair = build_default_keypair()
    minter = CapabilityMinter(keypair)
    verifier = CapabilityVerifier(keypair)
    token = minter.mint_agent_token("research", ["execute_step"], [], [], 1)
    assert verifier.verify(token, "execute_step", "research") is True


def test_capability_token_rejects_non_allowlisted_action() -> None:
    keypair = build_default_keypair()
    minter = CapabilityMinter(keypair)
    verifier = CapabilityVerifier(keypair)
    token = minter.mint_agent_token("research", ["search"], [], [], 1)
    assert verifier.verify(token, "execute_step", "research") is False
