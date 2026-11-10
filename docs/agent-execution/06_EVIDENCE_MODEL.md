# 06 — Evidence, Claims, and Provenance

## Separate what exists from what is said about it

Maintain separate records for:

- **referent** — object/event/process under discussion;
- **source/producer** — observer, instrument, author, software system;
- **capture activity** — measurement, observation, interview, export, crawl, build;
- **information artifact** — original record or work;
- **derivation activity** — copy, translation, transformation, summary, inference, model generation;
- **claim** — a specific proposition that can be supported or challenged;
- **evidence** — material relevant to that claim;
- **verification run** — a recorded test or reproduction;
- **decision** — a choice made on the basis of explicit evidence and policy.

A web page is an artifact; its author/publisher is an agent; publication is an activity; its assertions are claims. Search result snippets are discovery clues, not primary evidence by default.

## Provenance graph

Represent provenance as a graph, not a flat `source_url` string. Minimum relations:

- `observed_by`, `measured_by`, `authored_by`, `recorded_by`;
- `generated_from`, `derived_from`, `copied_from`, `translated_from`, `summarizes`, `quotes`;
- `supports`, `contradicts`, `qualifies`, `reproduces`;
- `stored_at`, `published_at`, `retrieved_at`.

A reprint chain is one lineage unless independent collection is demonstrated. Document-level lineage can be insufficient: record provenance at claim level when a document mixes direct observation, press release, interview, and copied claims.

## Evidence levels

- `E0_UNKNOWN`: not inspected / no evidence.
- `E1_DECLARED`: author, README, agent, or UI says so.
- `E2_OBSERVED`: directly seen in source, config, artifact, or log.
- `E3_EXECUTED`: operation/test executed with run record.
- `E4_INDEPENDENTLY_REPRODUCED`: another context/agent/person reproduced it.

These levels are not universal truth scores. Evidence quality also depends on relevance, method, uncertainty, bias, recency, and independence.

## Claim lifecycle

`OPEN → SUPPORTED | REFUTED | QUALIFIED | CONFLICTED | UNKNOWN`

Do not use `SUPPORTED` without linking evidence. Do not delete contradictory evidence. A claim may be supported for one scope/version/time and false for another.

## Independence

Count independent acquisition paths, not the number of URLs or copies. For independent confirmation, record separate origin, method, collection time, and shared dependencies. Common source, shared sensor, copied dataset, or shared upstream press release can create dependence.

## Integrity vs truth

Hashes and signatures can establish that bytes match a recorded digest or signer under specified assumptions. They do not establish that the content is true, that the first origin is authentic, or that the observation was accurate.
