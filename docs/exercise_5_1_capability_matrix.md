# Bài tập 5.1 — Ma trận Capability Governance

## 1. Tool nào mỗi agent được gọi

| Agent | Allowed Tools | Transport |
|-------|--------------|-----------|
| **orchestrator** | `search_documents`, `sql_query`, `summarize_text` (MCP) + `suggest_routing` (local) | MCP stdio + local |
| **search_agent** | `search_web` | A2A local |
| **database_agent** | `run_sql_query` | A2A local |
| **synthesis_agent** | `synthesize_report` | A2A local |

### Orchestrator A2A Dispatch Matrix

| Source → Target | Allowed? |
|----------------|----------|
| orchestrator → search_agent | ✅ |
| orchestrator → database_agent | ✅ |
| orchestrator → synthesis_agent | ✅ |
| orchestrator → email_agent | ❌ (not in allowlist) |
| search_agent → database_agent | ❌ (no allowed_targets) |

## 2. Hành động cần phê duyệt người (HITL)

| Tình huống | Verdict | Ví dụ |
|------------|---------|-------|
| PII trong SQL query | `hitl_required` | `SELECT * FROM agent_metrics WHERE email = 'user@vinuni.edu.vn'` |
| Chi phí vượt trần ($10) | `hitl_required` | Tổng cost > `cost_ceiling_usd` |
| A2A dispatch thiếu trace_id | `hitl_required` | orchestrator → database_agent (không có trace_id) |
| A2A dispatch đến agent chưa đăng ký | `hitl_required` | Dispatch đến agent không tồn tại |

## 3. Rate limit theo agent

| Agent | Rate Limit | Scope |
|-------|-----------|-------|
| **Tất cả agents** | 30 calls/phút | Per actor (in-memory sliding window 60s) |

## 4. Số lần gọi tool và thời gian thực thi tối đa

| Giới hạn | Giá trị | Mục đích |
|----------|---------|----------|
| `max_tool_calls_per_task` | 50 | Chống chạy vô hạn (runaway prevention) |
| `max_execution_seconds` | 300 (5 phút) | Timeout toàn task |
| `cost_ceiling_usd` | $10.00 | Trần chi phí API per task |
| `rate_limit_per_minute` | 30 | Rate limit sliding window |

## Sơ đồ luồng kiểm soát

```
User Request
    ↓
Orchestrator (before_agent_callback → init trace_id, task_id)
    ↓
before_tool_callback
    ├── transfer_to_agent? → authorize_a2a_dispatch()
    │     ├── Check allowed_targets
    │     ├── Check allowed_callers
    │     ├── Check trace_id requirement
    │     └── Rate limit + task limit
    ├── MCP tool? → authorize_mcp_tool()
    │     ├── Check allowed_callers
    │     ├── Check tool in capability matrix
    │     ├── SQL: read-only, allowed_tables
    │     ├── search: max_query_length, blocked_keywords
    │     ├── summarize: max_input_chars
    │     ├── PII detection
    │     └── Rate limit + task limit
    └── A2A tool? → authorize_agent_tool()
          ├── Check allowed_tools
          ├── SQL governance (if run_sql_query)
          └── Rate limit
    ↓
AuditLogger → logs/governance_audit.jsonl
    ↓
Execute tool / Dispatch A2A
```
