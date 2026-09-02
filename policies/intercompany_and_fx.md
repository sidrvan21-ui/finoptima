# FinOptima Intercompany Chargeback and FX Policy
**Document owner:** Group Controller | **Version:** 1.8

Applies to FinOptima US Inc, FinOptima Ireland Ltd, and FinOptima India Pvt Ltd. Cloud and SaaS amounts in the warehouse are **USD equivalents**.

## 4. Intercompany and currency

### Rule 4.1 — Intercompany cloud allocation
When Ireland or India consume US-hosted platforms (EKS, Snowflake), Group Controller posts a monthly intercompany charge at **cost, no markup**, using the documented allocation key (Rule 1.6). Missing allocations do not hide a US Operations 1.1 / 1.2 breach.

### Rule 4.2 — FX on vendor invoices
Vendor invoices in EUR or INR are booked at month-end group rate. FX gains/losses over **$2,000** on a single vendor in a month need a controller comment. This is not an idle-login rule.

### Rule 4.3 — Transfer-price freeze
SaaS seats recharged to another entity must use the same ARR as the paying entity. Inflating recharge to move budget between entities is prohibited.

### Rule 4.4 — Data-residency spend
EU personal data processing must stay on `eu-west-1` (or equivalent) unless Legal has a transfer addendum. Extra multi-region replicas for EU data follow Rule 1.1 if they drive variance.

### Rule 4.5 — Idle cross-entity licenses
If a license paid by US Inc is unused in Ireland or India for **30 consecutive days**, Procurement applies Rule 3.1; Audit still files Rule 2.1 evidence. Do not treat this as an FX issue (Rule 4.2).
