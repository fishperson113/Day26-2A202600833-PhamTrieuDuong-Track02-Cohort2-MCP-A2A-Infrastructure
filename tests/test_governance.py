"""Tests cho governance — Bài tập 5.2 (Nâng cao) + kiểm tra policy."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lab_utils.governance.guard import GovernanceGuard
from lab_utils.governance.models import GovernanceVerdict


def test_invalid_caller_denied_mcp_connection():
    """Bài tập 5.2 (Nâng cao): Caller không hợp lệ không mở được kết nối MCP."""
    guard = GovernanceGuard()
    decision = guard.authorize_mcp_connection("unauthorized_agent")
    assert decision.blocked, f"Expected DENY but got {decision.verdict.value}"
    assert decision.verdict == GovernanceVerdict.DENY
    print(f"✓ Invalid caller denied: {decision.reason}")


def test_valid_caller_allowed_mcp_connection():
    """Orchestrator (valid caller) được phép mở kết nối MCP."""
    guard = GovernanceGuard()
    decision = guard.authorize_mcp_connection("orchestrator")
    assert decision.allowed, f"Expected ALLOW but got {decision.verdict.value}"
    assert "allowed_tools" in decision.metadata
    print(f"✓ Valid caller allowed: tools={decision.metadata['allowed_tools']}")


def test_blocked_keyword_password_in_search():
    """Bài tập 5.2: Từ khóa 'password' bị chặn trong search_documents."""
    guard = GovernanceGuard()
    decision = guard.authorize_mcp_tool(
        "orchestrator", "search_documents", {"query": "find password reset docs"}
    )
    assert decision.blocked, f"Expected DENY but got {decision.verdict.value}"
    assert "password" in decision.reason.lower()
    print(f"✓ Blocked keyword 'password': {decision.reason}")


def test_normal_search_allowed():
    """Truy vấn search_documents bình thường được cho phép."""
    guard = GovernanceGuard()
    decision = guard.authorize_mcp_tool(
        "orchestrator", "search_documents", {"query": "MCP transport options"}
    )
    assert decision.allowed, f"Expected ALLOW but got {decision.verdict.value}"
    print(f"✓ Normal search allowed: {decision.reason}")


def test_sql_drop_blocked():
    """SQL DROP TABLE bị chặn."""
    guard = GovernanceGuard()
    decision = guard.authorize_mcp_tool(
        "orchestrator", "sql_query", {"sql": "DROP TABLE agent_metrics"}
    )
    assert decision.blocked, f"Expected DENY but got {decision.verdict.value}"
    print(f"✓ DROP TABLE blocked: {decision.reason}")


def test_sql_select_allowed():
    """SQL SELECT hợp lệ được phép."""
    guard = GovernanceGuard()
    decision = guard.authorize_mcp_tool(
        "orchestrator", "sql_query", {"sql": "SELECT * FROM agent_metrics"}
    )
    assert decision.allowed, f"Expected ALLOW but got {decision.verdict.value}"
    print(f"✓ SELECT allowed: {decision.reason}")


def test_pii_requires_hitl():
    """PII trong SQL yêu cầu HITL."""
    guard = GovernanceGuard()
    decision = guard.authorize_mcp_tool(
        "orchestrator", "sql_query",
        {"sql": "SELECT * FROM agent_metrics WHERE email = 'user@vinuni.edu.vn'"}
    )
    assert decision.needs_approval, f"Expected HITL_REQUIRED but got {decision.verdict.value}"
    print(f"✓ PII requires HITL: {decision.reason}")


def test_a2a_dispatch_allowed_target():
    """A2A dispatch đến target hợp lệ được phép."""
    guard = GovernanceGuard()
    for target in ["search_agent", "database_agent", "synthesis_agent"]:
        decision = guard.authorize_a2a_dispatch(
            "orchestrator", target, trace_id="test-trace-001"
        )
        assert decision.allowed, f"Expected ALLOW for {target} but got {decision.verdict.value}"
        print(f"✓ A2A dispatch to {target}: allowed")


def test_a2a_dispatch_blocked_target():
    """A2A dispatch đến target không trong allowlist bị chặn."""
    guard = GovernanceGuard()
    decision = guard.authorize_a2a_dispatch(
        "orchestrator", "email_agent", trace_id="test-trace-001"
    )
    assert decision.blocked, f"Expected DENY but got {decision.verdict.value}"
    print(f"✓ A2A dispatch to email_agent blocked: {decision.reason}")


def test_a2a_dispatch_missing_trace_id():
    """A2A dispatch thiếu trace_id → HITL required."""
    guard = GovernanceGuard()
    decision = guard.authorize_a2a_dispatch("orchestrator", "database_agent")
    assert decision.needs_approval, f"Expected HITL_REQUIRED but got {decision.verdict.value}"
    print(f"✓ Missing trace_id → HITL: {decision.reason}")


def test_audit_log_summary():
    """Audit log ghi đủ sự kiện."""
    guard = GovernanceGuard()
    # Trigger allow
    guard.authorize_mcp_tool("orchestrator", "search_documents", {"query": "test"})
    # Trigger deny
    guard.authorize_mcp_tool("orchestrator", "sql_query", {"sql": "DROP TABLE x"})
    # Trigger hitl
    guard.authorize_a2a_dispatch("orchestrator", "search_agent")

    summary = guard.audit.summary()
    print(f"✓ Audit summary: {summary}")
    assert summary.get("allow", 0) > 0, "Expected allow events"
    assert summary.get("deny", 0) > 0, "Expected deny events"
    assert summary.get("hitl_required", 0) > 0, "Expected hitl_required events"


if __name__ == "__main__":
    tests = [
        test_invalid_caller_denied_mcp_connection,
        test_valid_caller_allowed_mcp_connection,
        test_blocked_keyword_password_in_search,
        test_normal_search_allowed,
        test_sql_drop_blocked,
        test_sql_select_allowed,
        test_pii_requires_hitl,
        test_a2a_dispatch_allowed_target,
        test_a2a_dispatch_blocked_target,
        test_a2a_dispatch_missing_trace_id,
        test_audit_log_summary,
    ]
    passed = 0
    failed = 0
    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"✗ {test_fn.__name__}: {e}")
            failed += 1

    print(f"\n{'=' * 50}")
    print(f"Kết quả: {passed} passed, {failed} failed / {len(tests)} total")
    if failed == 0:
        print("✓ Tất cả test đều ĐẠT!")
    else:
        print("✗ Một số test CHƯA ĐẠT")
