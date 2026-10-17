# Acceptance criteria → tests (v0.3)

| # | Criterion | Test |
|---|---|---|
| 1 | CONFIRMED only after verification | `test_normal_task_confirms_only_after_verification` |
| 2 | High risk blocked without consent; resumes after consent | `test_high_risk_without_consent_blocked_then_resumes_after_consent` |
| 3 | Missing permission blocks | `test_missing_permission_blocked` |
| 4 | Fault after effect → UNKNOWN | `test_fault_after_effect_is_unknown_not_success` |
| 5 | Recovery reads back, no duplicate | `test_recovery_readback_confirms_without_duplicate` |
| 6 | Unreadable state stays UNKNOWN, no blind retry | `test_unreadable_state_stays_unknown_and_never_retries` |
| 7 | Adapter OK + unreadable state is not CONFIRMED | `test_adapter_says_ok_but_state_unreadable_is_unknown_not_confirmed` |
| 8 | ABSENT ≠ UNAVAILABLE; safe retry | `test_absent_is_distinct_from_unavailable_and_retry_is_safe` |
| 9 | Lying adapter ends FAILED within budget | `test_persistent_lying_adapter_ends_failed_not_success` |
| 10 | Wrong value / duplicate effects fail verification | `test_wrong_final_state_fails_verification`, `test_duplicate_effects_are_detected_by_verifier` |
| 11 | Non-idempotent absent → human | `test_non_idempotent_absent_goes_to_human_not_retry` |
| 12 | Failover only on no-effect guarantee | `test_failover_when_primary_guarantees_no_effect`, `test_no_failover_after_ambiguous_failure` |
| 13 | Hard constraints never downgraded | `test_local_only_constraint_is_never_downgraded`, `test_no_compatible_capability_waits_for_human` |
| 14 | Invalid intent rejected before state | `test_invalid_intent_rejected_by_schema_before_any_state` |
| 15 | No payload values in ledger | `test_ledger_never_contains_payload_values` |
| 16 | Intent cannot be altered after acceptance | `test_changed_intent_cannot_resume_or_recover_an_accepted_task` |
| 17 | Ledger tamper / truncation detected | `test_ledger_detects_tampering_and_truncation`, `test_tampered_payload_is_rejected_on_open`, `test_tail_truncation_needs_checkpoint` |
| 18 | Durable across restart; real process death | `RestartTests` (4 tests) |
| 19 | Consent not restored; wrong key refused | `test_consent_is_not_restored_after_restart_fail_closed`, `test_wrong_redaction_key_cannot_bind_to_existing_task` |
| 20 | Each ablation link is load-bearing; outputs fresh | `tests/test_experiment.py` |

Acceptance is not security certification or production readiness.
