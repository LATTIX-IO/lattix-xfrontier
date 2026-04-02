from __future__ import annotations

"""
Template for a Layer 3 agent runtime handler.
Usage:
- Place this module on PYTHONPATH (e.g., under runtime/agents/<agent_id>_handler.py)
- Set agent's AGENTS/<agent>/agent.runtime.json with topics and module path
"""
from runtime.layer2.contracts import Envelope
from runtime.layer2.reporting import add_tokens, add_log


def handle(env: Envelope) -> None:
    if env.topic != "gtm.content":  # adjust per agent.runtime.json
        return
    # Perform domain logic; call tools/models as needed.
    add_log(env, "agent", "processed by example runtime handler")
    add_tokens(env, 120)  # report token usage if applicable
    env.payload.setdefault("artifacts", []).append({"by": "example-agent", "note": "ok"})
