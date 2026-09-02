# FinOptima Corporate Cloud Spending Guidelines
**Document owner:** VP Finance | **Applies to:** all legal entities | **Version:** 5.0

Public-cloud spend is recorded in USD equivalents in the billing extract. Variance = (actual − limit) / limit, computed per legal entity and cost center.

## 1. Budget variance and audit

### Rule 1.1 — Material variance (15%)
If a cost center’s actual cloud spend for a calendar month exceeds its approved monthly limit by **more than 15%**, Finance Operations must open an automated audit trail. The trail must include: legal entity, department, cost center code, actual, limit, variance %, and top services by spend.

### Rule 1.2 — Absolute overrun ($5,000)
If the dollar overrun (actual − limit) is **greater than $5,000**, the cost-center owner must attach a **mandatory mitigation plan** within 5 business days (reduce, reallocate, or obtain a budget exception filed under Rule 5.x).

### Rule 1.3 — Observability and data-platform concentration
Unplanned spikes in observability (e.g. Datadog/logging) or warehouse (e.g. Snowflake) above **40% of that department’s monthly cloud total** require a platform-engineering review. This does not replace 1.1 or 1.2.

### Rule 1.4 — Multi-environment production
Production (`prod`) spend is in-scope for 1.1 and 1.2. CI/sandbox spend is tracked but does not by itself trigger a mitigation plan unless it also trips 1.1.

### Rule 1.5 — Entity-level rollup
If any single legal entity’s combined cloud variance exceeds **10%** of that entity’s combined monthly limits, Group FP&A must be copied on the audit trail even when no individual department trips 1.2.

### Rule 1.6 — Shared-service reallocation
Shared platforms (EKS, Snowflake, Datadog) used by more than one department must carry a documented allocation key. Unallocated shared spend is charged to the hosting cost center and is still in-scope for 1.1 / 1.2.

## 2. Related controls
See `audit_framework.md` (Rule 2.x), `vendor_and_shadow_it.md` (Rule 3.x), `intercompany_and_fx.md` (Rule 4.x), and `control_exceptions.md` (Rule 5.x).
