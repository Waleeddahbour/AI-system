# Section A — Architecture Design

## Multitenant Answering over External Data

I would design a **multitenant, production-grade “Answering over External Data” system** combining **RAG for tenant-owned knowledge** with a **small agentic layer for live tools**. Users ask through an API; a planner chooses direct answer, tenant-scoped retrieval, external tools such as web search, weather, currency, or CRM APIs, or retrieval plus tools. The answer is grounded in chunks/tool outputs, cites sources, and returns latency, token usage, tools used, and trace ID.

I would run it on **Azure**: **Azure Container Apps** for API/agent runtime, **Azure OpenAI** for LLMs and embeddings, **Azure AI Search** for hybrid retrieval, **Azure Blob Storage** for raw documents, **PostgreSQL** for app/audit data, **Azure Cache for Redis**, **Azure Key Vault**, and **Application Insights with OpenTelemetry**.

## 1. Data Ingestion and Indexing

The ingestion pipeline supports file uploads and connectors to SharePoint, Confluence, Google Drive, CRM platforms, ticketing systems, and internal databases. Raw files go to Blob Storage. Workers extract text, normalize formats, detect language, and attach `tenant_id`, document ID, ACLs, source URL, owner, timestamps, version, and retention policy.

Documents use **structure-aware chunking**, not only fixed splits, preserving headings, sections, paragraphs, and tables where possible. Each chunk has a stable ID and parent metadata for exact citations. Azure OpenAI creates embeddings; Azure AI Search stores vector and keyword fields. **Hybrid search** combines BM25 for exact terms, IDs, names, and codes with vector search for semantic similarity. An optional reranker improves high-value queries.

Retrieval is filtered **before ranking** by `tenant_id`, document ACLs, allowed scopes, and freshness constraints, because prompts cannot enforce isolation. Incremental indexing versions chunks, re-embeds changes, and deletes stale chunks when documents are removed or access is revoked.

## 2. Agentic Layer

The request context includes `tenant_id`, `user_id`, `the question`, `recent conversation history`, and `allowed scopes`. The planner receives context, tools, and routing policy, then returns structured JSON for direct answer, retrieval, tools, or both.

The explicit application loop is:

1. Validate the request and load tenant/user context.
2. Ask the planner whether retrieval, tools, both, or direct answer are needed.
3. Execute retrieval and validated tool calls, preferably in parallel when independent.
4. Generate a grounded final answer using only retrieved chunks and tool outputs.
5. Return citations, tools used, step latency, token usage, and trace ID.

Tools live in a tenant-specific **registry** with names, descriptions, input/output schemas, timeout, retry, cache TTL, and authorization policy. Examples: enterprise search, web search, weather, currency conversion, CRM lookup, ticket lookup, and internal database query. Invalid arguments or unauthorized tools are rejected before execution, keeping planning controllable instead of hiding routing, retries, and permissions in a black-box agent framework.

## 3. Cost, Latency, and Caching

Use **smaller models for planning and routing** and reserve larger models for synthesis only when needed. The planner should avoid unnecessary tools and skip final generation for simple direct responses. Retrieval and independent tools run in parallel with bounded concurrency, timeouts, and partial-failure handling.

Caching is layered:

- **Prompt cache** for repeated system/policy prompts
- **Vector/retrieval cache** for repeated normalized queries and query embeddings
- **HTTP/tool cache** for external APIs such as weather or currency, with short TTLs
- **Redis** for shared cache state across replicas

The key trade-off is **freshness versus cost**. Weather, currency, and web results need short TTLs; unchanged policies can be cached longer. If retrieval/tools are slow or partly unavailable, return a clearly degraded answer rather than invent facts.

## 4. Security and Multitenancy

Authentication should happen before the agent runtime, for example through **Azure AD / Entra ID**. Authorization uses **RBAC** at the API layer plus row-level or query-level filtering in PostgreSQL and Azure AI Search. Every database/search request includes `tenant_id`; every chunk carries tenant and ACL metadata; every tool call is checked against tenant, role, and scopes.

Secrets are never stored in code or prompts. Azure Key Vault stores model credentials, search keys, and API tokens. Managed identities are preferred for Azure access. External tools should use allowlists, egress controls, request signing where available, and per-tenant rate limits.

The system writes **audit logs** for user questions, retrieved document IDs, tool calls, admin actions, permission changes, and answer delivery. Sensitive content and PII should be redacted or tokenized. For regulated tenants, retention/deletion must propagate to Blob Storage, PostgreSQL, caches, and search indexes.

## 5. Observabilty

Use **OpenTelemetry** to assign and propagate a trace ID across API, planner, retrieval, tool calls, LLM calls, and database writes.

Send infrastructure/service telemetry to **Application Insights** for health monitoring, metrics, and alerting. Use **Langfuse** for LLM/agent observability: planner decisions, retrieved chunks, tool calls, answers, citations, token usage, latency, cost, and evaluation signals.

Dashboards should track:

- per-step latency
- token usage and model cost
- cache hit rate
- retrieval count and retrieval miss rate
- tool error and timeout rate
- no-source / low-grounding answers
- tenant-level usage and failure spikes

Quality should be validated through offline evals, regression tests, and production analysis. Tests should cover planner routing, tool schemas, tenant filtering, cache behavior, ingestion, retrieval quality, grounded generation, tool failures, and security checks proving tenant isolation.

## 6. Deployment

The system is **containerized** and deployed through CI/CD. CI runs linting, unit tests, integration tests, migrations, and a small evaluation suite. Infrastructure is separated by environment; production uses **canary or blue/green deployment**, health checks, autoscaling, rollback, and controlled migrations.

The first production version should keep a **single explicit planner loop** because it is easier to test, monitor, and restrict. Specialized agents can come later only when evaluation shows that added complexity improves answer quality enough to justify the operational risk.

## Trade-offs

- **RAG plus tools improves flexibility**, but is harder to test, secure, and operate than simple RAG.
- **An explicit planner loop improves control/debugging**, but requires more orchestration logic.
- **Strong tenant isolation protects data**, but can complicate retrieval and reduce coverage.
- **Hybrid search improves retrieval quality**, but requires tuning, metadata quality, and evaluation.
- **Structure-aware chunking improves citations/accuracy**, but makes ingestion harder across formats.
- **Fresh data improves accuracy**, but live APIs add latency, cost, timeouts, and dependency failures.
- **Smaller models reduce cost/latency**, but may weaken planning, routing, and tool selection.
- **Parallel execution improves speed**, but increases concurrency, rate-limit, and failure-handling risk.
- **Detailed observability improves debugging/quality**, but increases telemetry cost and privacy risk.
- **Azure-managed services speed deployment**, but reduce portability and increase Azure dependency.
