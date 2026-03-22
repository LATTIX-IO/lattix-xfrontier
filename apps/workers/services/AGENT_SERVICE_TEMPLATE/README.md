Agent Service Template

Purpose
- Containerized microservice wrapper for a single agent. Exposes HTTP APIs for A2A/MCP and subscribes to topics via the runtime bus if running in-process.

Endpoints
- POST /v1/envelope — accept an Envelope JSON and process
- GET /healthz — liveness check
- GET /readyz — readiness check

Security
- Authorization: Bearer JWT (A2A). See `runtime/security/jwt.py` for issuer/verification.
- mTLS (optional): terminate at ingress; forward identity via headers and enforce JWT.

Run locally
- `pip install -r requirements.txt`
- `uvicorn app:app --host 0.0.0.0 --port 8080`

Container
- `docker build -t agent-service:dev .`
- `docker run -p 8080:8080 agent-service:dev`

Kubernetes
- See `k8s/deployment.yaml` and `k8s/service.yaml` (adjust image and env).

