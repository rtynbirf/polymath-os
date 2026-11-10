# Example — one claim, mixed lineage

Claim: `CLM-001` — "The service returned HTTP 503 at 12:03 UTC."

- `OBS-01`: original raw client log from independent client A.
- `OBS-02`: original raw monitor record from independent monitor B.
- `ART-03`: incident blog post derived from OBS-01 and OBS-02.
- `COPY-04`: syndication copy of ART-03.
- `SUMMARY-05`: AI summary derived from ART-03 and COPY-04.

OBS-01 and OBS-02 may be two independent acquisition paths (verify clock, network, endpoint, and shared logging infrastructure). ART-03, COPY-04, and SUMMARY-05 are not three further independent confirmations of the 503 claim. They are derivative artifacts. They may be evidence for what was published or how the incident was represented.

A content hash can show that COPY-04 bytes match a known snapshot. It does not prove that the original log is accurate or that the event happened.
