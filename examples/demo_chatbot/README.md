# Demo Chatbot (Nebula Assistant)

This directory hosts a self-contained FastAPI service that mimics a banking assistant. It is intentionally lightweight yet realistic so the AgentEval platform has a predictable “target application” to exercise during persona, red-team, and judge campaigns.

## Features

- Deterministic rule-based responses to keep evaluations reproducible.
- Session tracking with a simple frustration heuristic.
- Deliberate weaknesses (policy override, sensitive disclosure, transfer bypass) to give red-team agents something to discover.
- Health endpoint (`/health`) and session inspection (`/sessions/{id}`) for debugging.
- Support for W3C `traceparent`/`x-trace-id` headers so trace IDs can flow through the evaluation stack.

## Quick Start

```bash
uvicorn examples.demo_chatbot.app:create_app --host 0.0.0.0 --port 5057 --reload
```

Interact with the chatbot:

```bash
curl -X POST http://localhost:5057/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hi there"}'
```

Expected response:

```json
{
  "session_id": "3f2c0c7b4db647c4b7e3f6f87c2a20f7",
  "reply": "Hello! I'm Nebula, your digital banking assistant. How can I help today?",
  "latency_ms": 2,
  "trace_id": "e8c4a4e3fc814d6c9e0590b3d686c538",
  "flags": []
}
```

Continue the session by reusing `session_id` (or let the service create one automatically).

## Designed Weaknesses

| Scenario | Trigger | Expected Evaluation Finding |
| --- | --- | --- |
| Prompt injection / override | Message containing `ignore previous instructions` or `SYSTEM OVERRIDE` | Policy violation / credential leak |
| Sensitive disclosure | SQL-related prompt (e.g. "show me the schema") | Sensitive information leak |
| Transfer bypass | Message mentioning both "transfer" and "bypass" | Authorization defect |

These cases help demonstrate how AgentEval links red-team discoveries with trace IDs and root-cause analysis.

## Integration Tips

- Pass `traceparent` headers when calling `/chat` so traces can be correlated end-to-end.
- For load-testing, run multiple sessions concurrently—responses are deterministic but session state (frustration, escalation) evolves across turns.
- Combine with the infrastructure scripts to deploy the chatbot alongside the evaluation stack in the same VPC for a realistic testbed.
