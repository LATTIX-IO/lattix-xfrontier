"""Federation topology metadata service."""

from __future__ import annotations

from pydantic import BaseModel, Field

from lattix_frontier.config import Settings, get_settings


class FederationPeer(BaseModel):
    """Configured federation peer."""

    endpoint: str


class FederationStatus(BaseModel):
    """Current federation configuration exposed by the control plane."""

    enabled: bool = False
    cluster_name: str
    region: str
    peers: list[FederationPeer] = Field(default_factory=list)


class FederationTopologyService:
    """Resolve federation metadata from runtime settings."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def status(self) -> FederationStatus:
        """Return the current federation topology metadata."""

        peer_values = [item.strip() for item in self.settings.federation_peer_endpoints.split(",") if item.strip()]
        return FederationStatus(
            enabled=self.settings.federation_enabled,
            cluster_name=self.settings.federation_cluster_name,
            region=self.settings.federation_region,
            peers=[FederationPeer(endpoint=peer) for peer in peer_values],
        )
