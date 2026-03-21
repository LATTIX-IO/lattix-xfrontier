# Agent Development

1. Run `lattix agent scaffold --name my-agent`.
2. Implement `handle()` in the generated `agent.py`.
3. Add tools in `tools.py`.
4. Update `config.json` and `system_prompt.md`.
5. Test locally through the A2A server contract.
6. Deploy with the included Dockerfile and Kubernetes templates.
