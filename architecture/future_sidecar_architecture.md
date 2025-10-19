```mermaid
graph LR
    subgraph Campaign Control Plane
        A[AgentEval API / Orchestrator\n(Tracer + Meter SDK)]
        B[Persona Agents\n(Routed via HTTPX + OTLP)]
        C[Red Team Agents\n(Attack Simulation)]
        D[Judge Agents\n(Scoring + RCA)]
    end

    subgraph Target Systems
        E[Demo Chatbot / Customer GenAI App\n(FastAPI + OTel SDK)]
    end

    %% Sidecar pairs
    subgraph AgentEval Task (ECS / K8s Pod)
        A --- SA1((Sidecar Collector))
        B --- SA1
        C --- SA1
        D --- SA1
        SA1:::collector
    end

    subgraph Target Task (ECS / K8s Pod)
        E --- SE1((Sidecar Collector))
        SE1:::collector
    end

    %% Optional shared services (mTLS / OTLP)
    SA1 -- OTLP gRPC/HTTP --> RC[Regional Aggregation Collector\n(tail sampling, enrichment)]
    SE1 -- OTLP gRPC/HTTP --> RC

    RC -- Traces --> XRay[AWS X-Ray]
    RC -- Metrics --> CW[CloudWatch Metrics / AMP]
    RC -- Logs --> CWL[CloudWatch Logs]
    RC -- Optional --> PRM[Prometheus / Grafana Cloud]

    %% Trace & metric linkage
    classDef collector fill:#1f2937,stroke:#0ea5e9,color:#f9fafb;
    classDef storage fill:#134e4a,stroke:#10b981,color:#ecfdf5;

    class RC,XRay,CW,CWL,PRM storage;
    class SA1,SE1 collector;

    %% Context propagation
    A -- traceparent + baggage --> E
    B -- traceparent + baggage --> E
    C -- traceparent + baggage --> E
    D -- traceparent + baggage --> E

    %% Feedback loop
    CW -- SLO Alerts --> A
    PRM -- Dashboards --> Ops[Operations & QA]
    XRay -- RCA Visuals --> Judges[Judge Agents / Analysts]

    %% Legend
    subgraph Legend
        direction LR
        L1[Workload]:::default
        L2((Sidecar Collector)):::collector
        L3[Telemetry Backend]:::storage
    end
```
