from __future__ import annotations
import json
import os
from typing import Any, Dict, Optional
from urllib import request

from ..layer2.contracts import Envelope
from ..security.jwt import issue_token


def post_envelope(url: str, env: Envelope, sub: str = "orchestrator", token: Optional[str] = None, ca_bundle: Optional[str] = None) -> Dict[str, Any]:
    data = env.to_json().encode("utf-8")
    headers = {"Content-Type": "application/json"}
    tok = token or issue_token(sub=sub)
    headers["Authorization"] = f"Bearer {tok}"
    # Propagate correlation id for cross-service tracing
    headers["X-Correlation-ID"] = env.correlation_id

    req = request.Request(url, data=data, headers=headers, method="POST")
    # Optional: support custom CA bundle via certifi-style hook
    if ca_bundle:
        os.environ["SSL_CERT_FILE"] = ca_bundle
    with request.urlopen(req, timeout=10) as resp:  # nosec - demo scaffolding
        body = resp.read().decode("utf-8")
        try:
            return json.loads(body)
        except Exception:
            return {"status": resp.status, "body": body}
