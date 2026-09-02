# FinOptima Internal Audit Framework — Subscriptions and Evidence
**Document owner:** Internal Audit + Procurement | **Version:** 4.0

This document is the **control catalog**. Vendor commercial actions (cancel, downgrade, RFP) also appear in `vendor_and_shadow_it.md`. Wording is similar on purpose so retrieval must pick the correct clause.

## 2. Subscription hygiene

### Rule 2.1 — Idle seat / idle product
A subscription with **zero meaningful logins for 30 consecutive days** (stored as `last_active_days_ago >= 30`) **must be flagged** on the internal audit workpaper before auto-renewal. This is an **audit evidence** requirement, not a procurement action by itself.

### Rule 2.2 — High commercial exposure
If **ARR is greater than $10,000** AND Rule 2.1 also applies, severity is **P1** (CFO + Internal Audit queue). Below $10,000 ARR, idle tools are **P2** (local controller queue).

### Rule 2.3 — Churn-risk score
If `risk_score` is **greater than 7.0**, Internal Audit must sample the contract even if logins are recent. Risk is a composite of idle time, duplicate tools, and renewal proximity.

### Rule 2.4 — Named owner
Every contract must have an `owner_email`. Ownerless or bounced owners are treated as control failures regardless of usage.

### Rule 2.5 — Multi-entity license stacking
The same vendor billed to two legal entities without a group MSA must be listed on the quarterly license-stacking schedule. Stacking is not the same as idle (Rule 2.1).

## 3. Renewal window
Tools renewing within **60 days** that also trip 2.1 or 2.2 cannot be auto-renewed without HITL approval in FinOptima.

## 4. Evidence
Auditors must show: legal entity, vendor, ARR, last activity, owner, risk score, and the clause ID cited in the memo.
