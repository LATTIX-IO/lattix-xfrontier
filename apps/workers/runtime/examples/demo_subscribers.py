from __future__ import annotations
from typing import Any, Dict

from ..layer2.contracts import Envelope
from ..layer2.event_bus import EventBus


def _log(prefix: str, env: Envelope) -> None:
    print(f"[{prefix}] topic={env.topic} type={env.msg_type} payload={env.payload}")


def register_demo_subscribers(bus: EventBus) -> None:
    # GTM content pipeline demo subscribers
    def brand_listener(env: Envelope) -> None:
        if env.topic != "gtm.content":
            return
        _log("brand", env)
        env.payload.setdefault("drafts", []).append({"by": "brand", "title": "Brand POV"})

    def marketing_listener(env: Envelope) -> None:
        if env.topic != "gtm.content":
            return
        _log("marketing", env)
        env.payload.setdefault("drafts", []).append({"by": "marketing", "cta": "Join waitlist"})

    def blog_listener(env: Envelope) -> None:
        if env.topic != "gtm.content":
            return
        _log("blog", env)
        env.payload["blog_post"] = {"status": "draft", "sections": ["intro", "features", "cta"]}

    # Security compliance demo subscribers
    def compliance_mapper(env: Envelope) -> None:
        if env.topic != "security.compliance":
            return
        _log("mapper", env)
        env.payload["controls"] = ["AC-2", "AU-6"]

    def ssp_builder(env: Envelope) -> None:
        if env.topic != "security.compliance":
            return
        _log("ssp", env)
        env.payload["ssp"] = {"status": "draft", "sections": ["overview", "controls"]}

    def sar_builder(env: Envelope) -> None:
        if env.topic != "security.compliance":
            return
        _log("sar", env)
        env.payload["sar"] = {"status": "draft", "tests": ["access-review", "audit-logging"]}

    # Register
    bus.subscribe("gtm.content", brand_listener)
    bus.subscribe("gtm.content", marketing_listener)
    bus.subscribe("gtm.content", blog_listener)

    bus.subscribe("security.compliance", compliance_mapper)
    bus.subscribe("security.compliance", ssp_builder)
    bus.subscribe("security.compliance", sar_builder)

    # Personnel actions
    def personnel_hr(env: Envelope) -> None:
        if env.topic != "people.personnel":
            return
        _log("hr", env)
        env.payload.setdefault("actions", []).append({"type": "onboard", "owner": "HR"})

    def personnel_it(env: Envelope) -> None:
        if env.topic != "people.personnel":
            return
        _log("it", env)
        env.payload.setdefault("actions", []).append({"type": "provision", "owner": "IT"})

    bus.subscribe("people.personnel", personnel_hr)
    bus.subscribe("people.personnel", personnel_it)

    # Contract review
    def legal_intake(env: Envelope) -> None:
        if env.topic != "legal.contract":
            return
        _log("legal-intake", env)
        env.payload["intake"] = {"status": "received", "risk": "medium"}

    def legal_review(env: Envelope) -> None:
        if env.topic != "legal.contract":
            return
        _log("legal-review", env)
        env.payload["review"] = {"status": "in-progress", "clauses": ["NDA", "DPA"]}

    bus.subscribe("legal.contract", legal_intake)
    bus.subscribe("legal.contract", legal_review)

    # Project initiation
    def pmo_intake(env: Envelope) -> None:
        if env.topic != "ops.project":
            return
        _log("pmo", env)
        env.payload["project"] = {"stage": "intake", "id": env.id[:8]}

    def eng_scoping(env: Envelope) -> None:
        if env.topic != "ops.project":
            return
        _log("eng-scope", env)
        env.payload.setdefault("requirements", []).extend(["milestone-1", "milestone-2"])

    bus.subscribe("ops.project", pmo_intake)
    bus.subscribe("ops.project", eng_scoping)

    # Sales process
    def sales_qualification(env: Envelope) -> None:
        if env.topic != "sales.pipeline":
            return
        _log("sales-qual", env)
        env.payload["lead"] = {"stage": "qualified", "score": 0.82}

    def sales_proposal(env: Envelope) -> None:
        if env.topic != "sales.pipeline":
            return
        _log("sales-proposal", env)
        env.payload["proposal"] = {"status": "draft"}

    bus.subscribe("sales.pipeline", sales_qualification)
    bus.subscribe("sales.pipeline", sales_proposal)
