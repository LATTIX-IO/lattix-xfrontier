from __future__ import annotations

from pydantic import BaseModel


class Settings(BaseModel):
    FEDERATION_ENABLED: bool = False
    FEDERATION_CLUSTER_NAME: str = ""
    FEDERATION_REGION: str = ""
    FEDERATION_PEER_ENDPOINTS: str = ""
    FRONTIER_STATE_STORE: str = ".frontier/runtime-state.json"
    A2A_JWT_SECRET: str = "unit-test-super-secret-value-32bytes"
