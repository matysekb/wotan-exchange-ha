# 0.3.0 (release candidate)

- Read-only list_mail_folders with primary/archive scope and account-bound stable references.
- Existing search_mail accepts discovered mail folder references alongside standard aliases; maximum 25 targets.
- Offline folder protocol tests in ARM64 CI; no state migration or launcher/dependency changes.
- Live archive and ARM64 verification required before production upgrade.

# 0.2.0

- Replace incomplete prototype with a read-only Home Assistant options keyring.
- Preserve upstream 0.9.0 source and its 11 production tools unchanged.
- Pin Python image digest, Linux ARM64 dependency wheel hashes and official tunnel-client 0.0.16 checksum.
- Add EWS-only preflight mode and manual startup for safe migration.
- Persist upstream configuration, attachments and SQLite workflow state in /data.
- Restrict output to lifecycle status; do not forward raw EWS or tunnel logs.
- Add offline adapter tests, real stdio smoke test and ARM64 build workflow.
