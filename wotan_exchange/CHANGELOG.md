# 0.2.0

- Replace incomplete prototype with a read-only Home Assistant options keyring.
- Preserve upstream 0.9.0 source and its 11 production tools unchanged.
- Pin Python image digest, Linux ARM64 dependency wheel hashes and official tunnel-client 0.0.16 checksum.
- Add EWS-only preflight mode and manual startup for safe migration.
- Persist upstream configuration, attachments and SQLite workflow state in /data.
- Restrict output to lifecycle status; do not forward raw EWS or tunnel logs.
- Add offline adapter tests, real stdio smoke test and ARM64 build workflow.
