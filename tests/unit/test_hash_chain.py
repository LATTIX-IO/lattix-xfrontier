from lattix_frontier.events.event_models import AgentEvent
from lattix_frontier.events.hash_chain import HashChain


def test_hash_chain_verifies() -> None:
    chain = HashChain()
    first = chain.append(AgentEvent(event_type="demo", source="tester"))
    second = chain.append(AgentEvent(event_type="demo", source="tester"))
    valid, index = HashChain().verify([first, second])
    assert valid is True
    assert index is None
