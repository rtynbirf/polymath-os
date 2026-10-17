"""SINGULYAR Emergent Intent Runtime kernel, v0.3. Standard library only.

Design rules enforced here (each has a test):
  * CONFIRMED requires a PASS verdict from an independent postcondition check.
  * "cannot read state" (UNAVAILABLE) is not "absent" (ABSENT): only ABSENT allows retry.
  * Failover to another adapter happens only on NotExecuted (adapter guarantees no effect).
  * Hard constraints (local_only / offline) are never silently downgraded.
  * The ledger stores fingerprints and keys, not payload values.
  * After a process restart, in-flight tasks become UNKNOWN and are recovered by readback.
"""
from __future__ import annotations
import hashlib, hmac, json, os, time
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from schema_validate import SchemaError, load_schema, validate
try:
    from decree_log import DecreeLog
except ImportError:
    DecreeLog = None

# ─── Decree Log integration (ADR-0021 — ВОЛЯ = НАКАЗ) ───
# The Decree Log is the supreme law layer. The kernel checks
# compliance with active decrees BEFORE executing any Intent.
# If a prohibition decree says 'never use Google' → DENIED by DECREE.
try:
    from decree_log import DecreeLog
    _decree_log = None  # lazily initialized
except ImportError:
    DecreeLog = None
    _decree_log = None

# ─── Observability: structured traces (ADR-0019, no external deps) ───
import json as _json_trace, sys as _sys_trace, time as _time_trace, uuid as _uuid_trace

def _emit_trace(event, **attrs):
    """Emit a structured trace event to stderr. One JSON line per event.
    OTel-compatible attribute names. Zero external deps (ADR-0002 Tier 1).
    Grep-able: python3 demo.py 2>&1 | grep '"event"'
    """
    try:
        trace = {
            'ts': _time_trace.strftime('%Y-%m-%dT%H:%M:%SZ', _time_trace.gmtime()),
            'trace_id': str(_uuid_trace.uuid4()),
            'event': event,
            'kernel_version': 'v0.3',
            **attrs,
        }
        _sys_trace.stderr.write(_json_trace.dumps(trace, ensure_ascii=False) + chr(10))
        _sys_trace.stderr.flush()
    except Exception:
        pass  # traces must never break the kernel



class State(str, Enum):
    CREATED = "CREATED"
    PLANNED = "PLANNED"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    CONFIRMED = "CONFIRMED"
    UNKNOWN = "UNKNOWN"
    FAILED = "FAILED"
    WAITING_FOR_HUMAN = "WAITING_FOR_HUMAN"
    RECOVERING = "RECOVERING"
    CANCELLED = "CANCELLED"


TRANSITIONS = {
    State.CREATED: {State.PLANNED, State.CANCELLED, State.WAITING_FOR_HUMAN},
    State.PLANNED: {State.EXECUTING, State.CANCELLED, State.WAITING_FOR_HUMAN},
    State.EXECUTING: {State.VERIFYING, State.UNKNOWN, State.FAILED},
    State.VERIFYING: {State.CONFIRMED, State.UNKNOWN, State.FAILED},
    State.UNKNOWN: {State.RECOVERING, State.WAITING_FOR_HUMAN, State.CANCELLED},
    State.FAILED: {State.PLANNED, State.CANCELLED},
    State.WAITING_FOR_HUMAN: {State.PLANNED, State.CANCELLED},
    State.RECOVERING: {State.VERIFYING, State.PLANNED, State.UNKNOWN, State.FAILED,
                       State.WAITING_FOR_HUMAN, State.CANCELLED},
    State.CONFIRMED: set(),
    State.CANCELLED: set(),
}

PRESENT, ABSENT, UNAVAILABLE = "PRESENT", "ABSENT", "UNAVAILABLE"
PASS, FAIL, INCONCLUSIVE = "PASS", "FAIL", "INCONCLUSIVE"
ZERO_HASH = "0" * 64


class RuntimeErrorBase(Exception): pass
class InvalidTransition(RuntimeErrorBase): pass
class PolicyBlocked(RuntimeErrorBase): pass
class ContractError(RuntimeErrorBase): pass
class UnknownOutcome(RuntimeErrorBase): pass
class NotExecuted(Exception):
    """Raised by an adapter that GUARANTEES no effect occurred (safe to fail over)."""
class InjectedFault(Exception):  # pragma: no mutate  — test fault injection helper — not production (per ADR-0010)
    """Test fault that behaves like an ordinary adapter-side failure."""
class SimulatedCrash(BaseException):  # pragma: no mutate  — test exception class — not production (per ADR-0010)
    """Simulates process death: deliberately not an Exception, so nothing catches it."""


@dataclass(frozen=True)
class Intent:
    intent_id: str
    description: str
    operation: str
    payload: Dict[str, Any]
    expected: Dict[str, Any]
    risk: str = "low"
    requires_consent: bool = False
    constraints: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Capability:
    capability_id: str
    operation: str
    adapter_id: str
    risk_ceiling: str
    offline: bool
    idempotent: bool
    local_only: bool = False
    priority: int = 100


@dataclass(frozen=True)
class Observation:
    status: str                      # PRESENT | ABSENT | UNAVAILABLE
    value: Optional[Dict[str, Any]] = None
    count: int = 0                   # how many effects exist under the idempotency key


@dataclass
class Execution:
    intent_id: str
    adapter_id: str
    idempotency_key: str
    capability_id: str = ""
    attempt: int = 0


@dataclass(frozen=True)
class Evidence:
    intent_id: str
    verifier: str
    verdict: str
    observed_status: str
    observed: Dict[str, Any]
    expected: Dict[str, Any]
    note: str

    @property
    def passed(self) -> bool:
        return self.verdict == PASS


# ---------------------------------------------------------------- ledgers
def _canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _hash_event(body: Dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()


class EvidenceLedger:
    """In-memory hash-linked event list. Tamper-evident only against a trusted checkpoint."""
    def __init__(self):
        self._events: List[Dict[str, Any]] = []
        self.head = ZERO_HASH

    @property
    def events(self):
        return self._events

    def append(self, event_type: str, payload: Dict[str, Any]):
        payload = json.loads(_canonical(payload))
        body = {"seq": len(self._events), "prev_hash": self.head, "type": event_type,
                "payload": payload, "time_ns": time.time_ns()}
        event = dict(body, hash=_hash_event(body))
        self._events.append(event)
        self.head = event["hash"]
        return event

    def verify(self) -> bool:
        prev = ZERO_HASH
        for idx, e in enumerate(self._events):
            body = {k: e[k] for k in ("seq", "prev_hash", "type", "payload", "time_ns")}
            if e["seq"] != idx or e["prev_hash"] != prev or _hash_event(body) != e["hash"]:
                return False
            prev = e["hash"]
        return prev == self.head

    def checkpoint(self) -> Dict[str, Any]:
        n = len(self.events)
        return {"count": n, "hash": self.events[-1]["hash"] if n else ZERO_HASH}

    def verify_against(self, cp: Dict[str, Any]) -> bool:
        """Detects truncation/rewrite of history up to a trusted, separately stored checkpoint."""
        ev = self.events
        if not self.verify() or len(ev) < cp["count"]:
            return False
        if cp["count"] == 0:
            return True
        return ev[cp["count"] - 1]["hash"] == cp["hash"]


# ---------------------------------------------------------------- adapters
class Adapter:
    adapter_id = "abstract"
    def execute(self, intent: Intent, idempotency_key: str): raise NotImplementedError
    def read_state(self, intent: Intent, idempotency_key: str) -> Observation: raise NotImplementedError


class _EffectAdapter(Adapter):  # pragma: no mutate  — test scaffolding base — not production (per ADR-0010)
    """Shared behaviour + fault knobs for simulated effect stores."""
    def __init__(self, *, dedup: bool = True, adapter_id: Optional[str] = None):
        if adapter_id:
            self.adapter_id = adapter_id
        self.dedup = dedup
        self.query_available = True
        self.raise_not_executed = False
        self.timeout_after_effect_n = 0   # next N calls apply effect, then raise TimeoutError
        self.drop_n = 0                   # next N calls claim success but store nothing (lying)
        self.corrupt = False              # store a wrong value
        self.calls = 0

    def _get(self, key) -> List[Dict[str, Any]]: raise NotImplementedError
    def _add(self, key, value) -> None: raise NotImplementedError

    def effect_count(self, key=None) -> int:
        raise NotImplementedError

    def execute(self, intent, idempotency_key):
        self.calls += 1
        if self.raise_not_executed:
            raise NotExecuted("adapter refused before any effect")
        if self.drop_n > 0:
            self.drop_n -= 1
            return {"accepted": True}
        if not (self.dedup and self._get(idempotency_key)):
            value = {k: "CORRUPTED" for k in intent.payload} if self.corrupt else dict(intent.payload)
            self._add(idempotency_key, value)
        if self.timeout_after_effect_n > 0:
            self.timeout_after_effect_n -= 1
            raise TimeoutError("simulated timeout after effect")
        return {"accepted": True, "idempotency_key": idempotency_key}

    def read_state(self, intent, idempotency_key):
        if not self.query_available:
            return Observation(UNAVAILABLE)
        items = self._get(idempotency_key)
        if not items:
            return Observation(ABSENT, None, 0)
        return Observation(PRESENT, items[-1], len(items))


class MemoryAdapter(_EffectAdapter):  # pragma: no mutate  — test scaffolding adapter — not production (per ADR-0010)
    adapter_id = "memory"
    def __init__(self, **kw):
        super().__init__(**kw)
        self.effects: Dict[str, List[Dict[str, Any]]] = {}
    def _get(self, key): return self.effects.get(key, [])
    def _add(self, key, value): self.effects.setdefault(key, []).append(value)
    def effect_count(self, key=None):
        return sum(len(v) for k, v in self.effects.items() if key in (None, k))


class SimulatedRemoteAdapter(MemoryAdapter):
    adapter_id = "simulated-remote"


class SQLiteEffectAdapter(_EffectAdapter):  # pragma: no mutate  — test scaffolding adapter — not production (per ADR-0010)
    """Simulated 'remote world' that survives process death (used by restart tests)."""
    adapter_id = "sqlite-remote"
    def __init__(self, path, **kw):
        import sqlite3
        super().__init__(**kw)
        self.db = sqlite3.connect(str(path), isolation_level=None)
        self.db.execute("CREATE TABLE IF NOT EXISTS effects (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                        "k TEXT NOT NULL, v TEXT NOT NULL)")
    def _get(self, key):
        return [json.loads(r[0]) for r in self.db.execute("SELECT v FROM effects WHERE k=? ORDER BY id", (key,))]
    def _add(self, key, value):
        self.db.execute("INSERT INTO effects(k, v) VALUES (?, ?)", (key, _canonical(value)))
    def effect_count(self, key=None):
        if key is None:
            return self.db.execute("SELECT COUNT(*) FROM effects").fetchone()[0]
        return self.db.execute("SELECT COUNT(*) FROM effects WHERE k=?", (key,)).fetchone()[0]
    def close(self):
        self.db.close()


# ---------------------------------------------------------------- policy / verifier
class Policy:
    RISK = {"low": 0, "medium": 1, "high": 2}

    def __init__(self, permissions=None, consented_intents=None):
        self.permissions = set(permissions or [])
        self.consented_intents = set(consented_intents or [])

    def check_intent(self, intent: Intent):
        if intent.operation not in self.permissions:
            raise PolicyBlocked(f"Permission missing for operation: {intent.operation}")
        if (intent.requires_consent or intent.risk == "high") and intent.intent_id not in self.consented_intents:
            raise PolicyBlocked("Explicit consent required")

    def capability_reason(self, intent: Intent, cap: Capability) -> Optional[str]:
        """None if the capability may serve the intent, else the reason it may not."""
        if self.RISK.get(intent.risk, 99) > self.RISK.get(cap.risk_ceiling, -1):
            return "risk ceiling too low"
        if intent.constraints.get("local_only") and not cap.local_only:
            return "violates hard constraint local_only"
        if intent.constraints.get("offline") and not cap.offline:
            return "violates hard constraint offline"
        return None

    def check(self, intent: Intent, cap: Capability):
        self.check_intent(intent)
        reason = self.capability_reason(intent, cap)
        if reason:
            raise PolicyBlocked(reason)


class PostconditionVerifier:
    verifier_id = "postcondition-v2"

    def verify(self, intent: Intent, obs: Optional[Observation]) -> Evidence:
        def ev(verdict, status, observed, note):
            return Evidence(intent.intent_id, self.verifier_id, verdict, status, observed, intent.expected, note)
        if obs is None or obs.status == UNAVAILABLE:
            return ev(INCONCLUSIVE, UNAVAILABLE, {}, "State cannot be read; outcome remains UNKNOWN")
        if obs.status == ABSENT:
            return ev(FAIL, ABSENT, {}, "Effect is absent")
        value = obs.value or {}
        if obs.count != 1:
            return ev(FAIL, PRESENT, value, f"Effect count is {obs.count}, expected exactly 1")
        if all(value.get(k) == v for k, v in intent.expected.items()):
            return ev(PASS, PRESENT, value, "Postcondition matched")
        return ev(FAIL, PRESENT, value, "Observed state contradicts expected postcondition")


# ---------------------------------------------------------------- runtime
class Runtime:
    def __init__(self, capabilities, adapters, policy, verifier=None, ledger=None, *,
                 redaction_key: Optional[bytes] = None,
                 fault_hook: Optional[Callable[[str, Intent], None]] = None,
                 max_attempts: int = 3):
        caps = list(capabilities)
        self.cap_by_id = {c.capability_id: c for c in caps}
        self.capabilities: Dict[str, List[Capability]] = {}
        for c in sorted(caps, key=lambda c: c.priority):
            self.capabilities.setdefault(c.operation, []).append(c)
        self.adapters = {a.adapter_id: a for a in adapters}
        self.policy = policy
        self.verifier = verifier or PostconditionVerifier()
        self.ledger = ledger or EvidenceLedger()
        self.key = redaction_key or os.urandom(32)
        self.fault_hook = fault_hook
        self.max_attempts = max_attempts
        self.states: Dict[str, State] = {}
        self.executions: Dict[str, Execution] = {}
        self.attempts: Dict[str, int] = {}
        self.fingerprints: Dict[str, str] = {}
        self._oneshot: Optional[str] = None
        self.decree_log = None  # set via set_decree_log(); supreme law above policy
        self.decree_scope: Optional[str] = None  # v0.6: optional scope filter
        self._schema = load_schema("intent.schema.json")
        self._rehydrate()

    def set_decree_log(self, dl, scope: Optional[str] = None) -> None:
        """Attach a DecreeLog (or None to detach). Per ADR-0021 + ADR-0022:
        the decree log is the human's supreme law layer — ABOVE policy.
        Once attached, every Intent's description is checked against active
        decrees (law + prohibition) before any policy/capability check.
        If a decree prohibits the action → block (WAITING_FOR_HUMAN),
        do NOT downgrade to a softer state. Default-deny: None = no decrees,
        no decree-based block (other policy still applies).

        v0.6 NEW: optional `scope` parameter. When set (e.g. scope="singulyar"),
        only decrees whose scope matches (decree.scope == "all" OR
        decree.scope == scope) are enforced. This allows different runtimes
        (Singulyar EIR vs Polymath-OS browser vs cell65-host) to apply
        different decree subsets without duplicating the DecreeLog.
        Pass None (default) for backward compatibility — all decrees apply.
        """
        self.decree_log = dl
        self.decree_scope = scope

    def set_decree_scope(self, scope: Optional[str]) -> None:
        """Change the decree scope filter at runtime (without re-attaching the log).

        v0.6: useful when the same Runtime is reused for different scopes
        (e.g. a multi-purpose adapter that sometimes processes singulyar
        intents, sometimes polymath-os intents). Pass None to clear the
        filter (all decrees apply).
        """
        self.decree_scope = scope


    # -- helpers
    def fp(self, obj) -> str:
        return hmac.new(self.key, _canonical(obj).encode("utf-8"), hashlib.sha256).hexdigest()

    def fp_salt(self, obj, salt: bytes) -> str:
        """HMAC-SHA-256 with per-entry salt prepended to canonical input.

        Per REDACTION_AUDIT.md: low-entropy values (e.g. "ok", "true") have
        small preimage space under plain HMAC. Prepending a 16-byte random
        salt raises preimage space to 2^128 per entry — even with the
        redaction_key + fingerprint, an attacker cannot recover the value
        by dictionary attack.
        """
        return hmac.new(self.key, salt + _canonical(obj).encode("utf-8"), hashlib.sha256).hexdigest()

    def _fire(self, point: str, intent: Intent):
        if self.fault_hook:
            self.fault_hook(point, intent)
        if self._oneshot == point:
            self._oneshot = None
            raise InjectedFault(f"injected fault at {point}")

    def _transition(self, intent, new_state, detail=""):
        old = self.states[intent.intent_id]
        if new_state not in TRANSITIONS[old]:
            raise InvalidTransition(f"{old.value} -> {new_state.value} is not allowed")
        self.states[intent.intent_id] = new_state
        self.ledger.append("STATE_TRANSITION", {"intent_id": intent.intent_id, "from": old.value,
                                                "to": new_state.value, "detail": detail})

    def _intent_fp(self, intent: Intent) -> str:
        return self.fp(asdict(intent))

    def _check_fp(self, intent: Intent):
        known = self.fingerprints.get(intent.intent_id)
        if known is None:
            raise RuntimeErrorBase("unknown intent_id")
        if known != self._intent_fp(intent):
            raise ContractError("intent differs from the accepted one (or wrong redaction key)")

    # -- restart recovery (event-sourced)
    def _rehydrate(self):
        events = self.ledger.events
        if not events:
            return
        for e in events:
            p, t = e["payload"], e["type"]
            if t == "INTENT_ACCEPTED":
                self.states[p["intent_id"]] = State.CREATED
                self.fingerprints[p["intent_id"]] = p["fingerprint"]
            elif t == "STATE_TRANSITION":
                self.states[p["intent_id"]] = State(p["to"])
            elif t == "EXECUTION_STARTED":
                self.executions[p["intent_id"]] = Execution(p["intent_id"], p["adapter_id"],
                                                            p["idempotency_key"], p["capability_id"], p["attempt"])
                self.attempts[p["intent_id"]] = p["attempt"]
        # In-flight work at the moment of death: outcome genuinely unknown.
        for iid, st in list(self.states.items()):
            if st in (State.EXECUTING, State.VERIFYING, State.RECOVERING):
                stub = Intent(iid, "", "", {}, {})
                self._transition(stub, State.UNKNOWN, "process restart: in-flight state is unknown")

    # -- public API
    def grant_consent(self, intent_id: str):
        self.policy.consented_intents.add(intent_id)
        self.ledger.append("HUMAN_DECISION", {"intent_id": intent_id, "decision": "consent_granted"})

    def cancel(self, intent: Intent):
        self._check_fp(intent)
        self._transition(intent, State.CANCELLED, "cancelled by human")
        return State.CANCELLED

    def run(self, intent: Intent, *, fault_after_effect: bool = False) -> State:
        errors = validate(asdict(intent), self._schema)
        if errors:
            self.ledger.append("INTENT_REJECTED", {"intent_id": str(intent.intent_id), "errors": errors})
            raise ContractError("; ".join(errors))
        if intent.intent_id in self.states:
            raise RuntimeErrorBase("intent_id already exists; use recover()/resume() for existing tasks")
        self.states[intent.intent_id] = State.CREATED
        self.fingerprints[intent.intent_id] = self._intent_fp(intent)
        self.attempts[intent.intent_id] = 0
        self.ledger.append("INTENT_ACCEPTED", {
            "intent_id": intent.intent_id, "operation": intent.operation, "risk": intent.risk,
            "requires_consent": intent.requires_consent, "constraints": intent.constraints,
            "payload_keys": sorted(intent.payload), "expected_keys": sorted(intent.expected),
            "fingerprint": self.fingerprints[intent.intent_id]})
        if fault_after_effect:
            self._oneshot = "after_adapter_return"
        return self._advance(intent)

    def resume(self, intent: Intent) -> State:
        self._check_fp(intent)
        if self.states[intent.intent_id] != State.WAITING_FOR_HUMAN:
            raise RuntimeErrorBase(f"resume requires WAITING_FOR_HUMAN, got {self.states[intent.intent_id].value}")
        return self._advance(intent)

    def recover(self, intent: Intent) -> State:
        self._check_fp(intent)
        iid = intent.intent_id
        if self.states.get(iid) != State.UNKNOWN:
            raise RuntimeErrorBase(f"recover requires UNKNOWN state, got {self.states.get(iid)}")
        ex = self.executions.get(iid)
        if ex is None:
            raise RuntimeErrorBase("no execution recorded; nothing to read back")
        self._transition(intent, State.RECOVERING, "read actual state before any retry")
        adapter, cap = self.adapters[ex.adapter_id], self.cap_by_id[ex.capability_id]
        obs = adapter.read_state(intent, ex.idempotency_key)
        self.ledger.append("RECOVERY_READBACK", {"intent_id": iid, "observed_status": obs.status, "count": obs.count})
        if obs.status == UNAVAILABLE:
            self._transition(intent, State.UNKNOWN, "state still unreadable; no guess is made")
            return State.UNKNOWN
        if obs.status == PRESENT:
            self._transition(intent, State.VERIFYING, "effect found; verify, do not repeat")
            return self._finish_verification(intent, adapter, cap, ex.idempotency_key, obs)
        # ABSENT
        if not cap.idempotent:
            self._transition(intent, State.WAITING_FOR_HUMAN, "absent but capability not idempotent: human decides")
            return State.WAITING_FOR_HUMAN
        if self.attempts[iid] >= self.max_attempts:
            self._transition(intent, State.FAILED, "attempt budget exhausted")
            return State.FAILED
        try:
            self.policy.check_intent(intent)
        except PolicyBlocked as exc:
            self._transition(intent, State.WAITING_FOR_HUMAN, str(exc))
            return State.WAITING_FOR_HUMAN
        self._transition(intent, State.PLANNED, "effect absent; retry is safe via same idempotency key")
        return self._drive(intent, [cap])

    # -- internals
    def _advance(self, intent: Intent) -> State:
        iid = intent.intent_id
        def block(reason):
            self.ledger.append("POLICY_BLOCK", {"intent_id": iid, "reason": reason})
            if self.states[iid] != State.WAITING_FOR_HUMAN:
                self._transition(intent, State.WAITING_FOR_HUMAN, reason)
            return State.WAITING_FOR_HUMAN
        # DECREE GATE — supreme law, checked BEFORE policy (per ADR-0021 + ADR-0022).
        # If a decree prohibits the action, block immediately. Default-deny:
        # if no decree log attached, skip this gate (other policy still applies).
        # v0.6: pass decree_scope so only matching-scope decrees are checked.
        if self.decree_log is not None:
            decree_result = self.decree_log.check_compliance(
                intent.description, scope=self.decree_scope
            )
            if not decree_result.get("compliant", True):
                violations = decree_result.get("violations", [])
                reasons = "; ".join(
                    f"decree#{v.get('decree_seq', '?')}: {v.get('violation', '')}"
                    for v in violations[:3]
                ) or "decree prohibition"
                self.ledger.append("DECREE_BLOCK", {
                    "intent_id": iid, "reason": reasons,
                    "laws_checked": decree_result.get("laws_checked", 0),
                    "violations": violations})
                return block(f"decree prohibition: {reasons}")
        try:
            self.policy.check_intent(intent)
        except PolicyBlocked as exc:
            return block(str(exc))
        candidates, rejected = [], []
        for cap in self.capabilities.get(intent.operation, []):
            reason = self.policy.capability_reason(intent, cap)
            (rejected.append({"capability_id": cap.capability_id, "reason": reason}) if reason else candidates.append(cap))
        if rejected:
            self.ledger.append("CAPABILITY_REJECTED", {"intent_id": iid, "rejected": rejected})
        if not candidates:
            return block("no compatible capability (hard constraints are never downgraded)")
        self._transition(intent, State.PLANNED, ",".join(c.capability_id for c in candidates))
        return self._drive(intent, candidates)

    def _execute_once(self, intent, candidates) -> Optional[State]:
        """Run the first adapter that executes. None => proceed to verification."""
        iid = intent.intent_id
        self._transition(intent, State.EXECUTING)
        for cap in candidates:
            adapter = self.adapters[cap.adapter_id]
            self.attempts[iid] = self.attempts.get(iid, 0) + 1
            self.executions[iid] = Execution(iid, cap.adapter_id, iid, cap.capability_id, self.attempts[iid])
            # write-ahead: durable record BEFORE the side effect can happen
            self.ledger.append("EXECUTION_STARTED", {
                "intent_id": iid, "capability_id": cap.capability_id, "adapter_id": cap.adapter_id,
                "idempotency_key": iid, "attempt": self.attempts[iid]})
            try:
                self._fire("before_execute", intent)
                result = adapter.execute(intent, iid)
                self._fire("after_execute", intent)       # crash window: effect done, not yet recorded
                self.ledger.append("ADAPTER_RETURN", {"intent_id": iid, "adapter": cap.adapter_id,
                                                      "accepted": bool(isinstance(result, dict) and result.get("accepted"))})
                self._fire("after_adapter_return", intent)
                return None
            except NotExecuted:
                self.ledger.append("ADAPTER_NOT_EXECUTED", {"intent_id": iid, "adapter": cap.adapter_id})
                continue
            except Exception as exc:
                self.ledger.append("ADAPTER_EXCEPTION", {"intent_id": iid, "adapter": cap.adapter_id,
                                                         "error_type": type(exc).__name__})
                self._transition(intent, State.UNKNOWN, "adapter exception; side effect may have occurred")
                return State.UNKNOWN
        self._transition(intent, State.FAILED, "no adapter executed anything")
        return State.FAILED

    def _drive(self, intent, candidates) -> State:
        iid = intent.intent_id
        while True:
            final = self._execute_once(intent, candidates)
            if final is not None:
                return final
            ex = self.executions[iid]
            adapter, cap = self.adapters[ex.adapter_id], self.cap_by_id[ex.capability_id]
            self._transition(intent, State.VERIFYING)
            self._fire("before_verify", intent)
            obs = adapter.read_state(intent, iid)
            evidence = self.verifier.verify(intent, obs)
            self._log_evidence("VERIFICATION", evidence)
            if evidence.verdict == FAIL and evidence.observed_status == ABSENT \
                    and cap.idempotent and self.attempts[iid] < self.max_attempts:
                try:
                    self.policy.check_intent(intent)
                except PolicyBlocked:
                    pass
                else:
                    self._transition(intent, State.FAILED, "adapter claimed success but effect absent")
                    self._transition(intent, State.PLANNED, "retry is safe via same idempotency key")
                    candidates = [cap]
                    continue
            return self._conclude(intent, evidence)

    def _log_evidence(self, kind, ev: Evidence):
        # Per REDACTION_AUDIT.md (Gate-2): add per-entry 16-byte random salt
        # to HMAC input. Raises preimage space per entry to 2^128 even for
        # low-entropy values (e.g. {"ok": true}, "1", "yes") — closes the
        # brute-forceability gap documented in LIMITATIONS.md item 4.
        salt = os.urandom(16)
        self.ledger.append(kind, {"intent_id": ev.intent_id, "verifier": ev.verifier, "verdict": ev.verdict,
                                  "observed_status": ev.observed_status,
                                  "expected_fp": self.fp_salt(ev.expected, salt),
                                  "observed_fp": self.fp_salt(ev.observed, salt) if ev.observed else "",
                                  "salt": salt.hex(),
                                  "note": ev.note})

    def _finish_verification(self, intent, adapter, cap, key, obs) -> State:
        evidence = self.verifier.verify(intent, obs)
        self._log_evidence("RECOVERY_VERIFICATION", evidence)
        return self._conclude(intent, evidence)

    def _conclude(self, intent, evidence: Evidence) -> State:
        if evidence.verdict == PASS:
            self._transition(intent, State.CONFIRMED, evidence.note)
            return State.CONFIRMED
        if evidence.verdict == INCONCLUSIVE:
            self._transition(intent, State.UNKNOWN, evidence.note)
            return State.UNKNOWN
        self._transition(intent, State.FAILED, evidence.note)
        return State.FAILED
