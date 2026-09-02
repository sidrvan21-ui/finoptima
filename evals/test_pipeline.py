from agents.graph import _parse_verdict, new_thread_id, start_audit


def test_parse_verdict():
    assert _parse_verdict("VERDICT: PASS\nREASON: copied FACTS") is True
    assert _parse_verdict("VERDICT: FAIL\nREASON: invented 99999") is False
    assert _parse_verdict("") is False


def test_pipeline_replay():
    tid = new_thread_id()
    out = start_audit(tid)
    vals = out["values"]
    memo = vals.get("memo") or ""

    assert "apply_decision" in (out.get("next") or [])

    cloud = vals.get("cloud_flags") or []
    saas = vals.get("saas_flags") or []
    assert cloud or saas

    hits = vals.get("policy_hits") or []
    assert hits
    assert hits[0].get("heading")

    assert cloud
    row = max(cloud, key=lambda r: r.get("over_usd", 0) or 0)
    actual = str(int(float(row["actual"])))
    over = str(int(float(row["over_usd"])))
    assert actual in memo, f"memo missing actual {actual}"
    assert over in memo, f"memo missing over_usd {over}"

    for flag in saas:
        email = str(flag.get("owner_email") or "")
        if "@" in email:
            assert "***" in email

    assert vals.get("judge_ok") is True, vals.get("judge_reason")
