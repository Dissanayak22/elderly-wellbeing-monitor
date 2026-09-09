# Optional blockchain audit layer (future)

Keep this module **off** for Progress-1 (`ENABLE_BLOCKCHAIN_AUDIT=false`).

Intended design:

- Hash each saved observation payload (expression, confidence, timestamp, session_id).
- Append hash to a simple local chain file or permissioned ledger.
- Never block core monitoring if the ledger is unavailable.

This is for **data integrity / audit**, not healthcare claims.
