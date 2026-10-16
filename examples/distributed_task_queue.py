"""examples/distributed_task_queue.py — Real-world SINGULYAR EIR usage.

Demonstrates a distributed task queue where N workers coordinate via the
SINGULYAR EIR kernel + lead/lease. Each worker:
1. Acquires lead on the shared SQLite ledger
2. Picks the next task from the queue (an Intent waiting in WAITING_FOR_HUMAN)
3. Executes it via its Adapter
4. Releases lead so the next worker can pick up

This is the "execution side" of ADR-0007 (research=parallel, execution=single+verifier).
The kernel's invariant "one writer at a time" is enforced by SQLite advisory lock,
NOT by an external coordinator service (Redis, etcd, Kubernetes).

Run:
    python3 examples/distributed_task_queue.py --workers 3 --tasks 10

Output: JSON report with per-task execution trace + final ledger state.

This example proves the sovereignty thesis: the queue works offline, on
LAN, with zero external dependencies (pure Python stdlib + SQLite).
"""
import argparse, json, os, sqlite3, sys, tempfile, threading, time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNTIME_SRC = REPO_ROOT / "runtime" / "src"
sys.path.insert(0, str(RUNTIME_SRC))
sys.path.insert(0, str(RUNTIME_SRC / "adapters"))

from singulyar_runtime import Runtime, Policy, Capability, Intent
from sqlite_ledger import SQLiteEvidenceLedger
from adapters.llm_local_adapter import LLMLocalAdapter, CAPABILITIES as LLM_CAPS


class TaskQueue:
    """In-memory task queue. In production, would be SQLite-backed."""

    def __init__(self, tasks: list):
        self._tasks = list(tasks)
        self._lock = threading.Lock()
        self._next = 0

    def take(self):
        with self._lock:
            if self._next >= len(self._tasks):
                return None
            task = self._tasks[self._next]
            self._next += 1
            return task


def worker(worker_id: int, queue: TaskQueue, ledger_path: str, results: list, ready, go):
    ready.set()
    go.wait()
    started = time.time()
    ledger = SQLiteEvidenceLedger(ledger_path)
    holder = f"worker-{worker_id}"
    adapter = LLMLocalAdapter()
    caps = list(LLM_CAPS)
    rt = Runtime(caps, [adapter], Policy({"execute_command", "answer_question", "generate_response", "check_status"}),
                 ledger=ledger, redaction_key=b"task-queue-key-0123456789abcdef")
    tasks_done = 0
    while True:
        # Acquire lead before taking a task (exclusive writer)
        acquired = False
        attempts = 0
        while not acquired and attempts < 50:
            acquired = ledger.lead_acquire(holder=holder, ttl_ms=5000)
            if not acquired:
                time.sleep(0.05)
                attempts += 1
        if not acquired:
            break  # give up after 2.5s
        task = queue.take()
        if task is None:
            ledger.lead_release(holder=holder)
            break
        # Execute the task via SINGULYAR EIR Runtime
        intent = Intent(
            intent_id=f"task-{task['id']}",
            description=task["description"],
            operation="execute_command",
            payload={"phrase": task["phrase"]},
            expected={},
        )
        try:
            st = rt.run(intent)
            results.append({
                "worker": worker_id,
                "task_id": task["id"],
                "state": st.name,
                "duration_ms": int((time.time() - started) * 1000),
            })
            tasks_done += 1
        except Exception as e:
            results.append({
                "worker": worker_id,
                "task_id": task["id"],
                "error": str(e),
            })
        ledger.lead_release(holder=holder)
    ledger.close()
    return tasks_done


def main():
    p = argparse.ArgumentParser(description="Distributed task queue with SINGULYAR EIR")
    p.add_argument("--workers", "-w", type=int, default=3)
    p.add_argument("--tasks", "-t", type=int, default=10)
    args = p.parse_args()

    tasks = [
        {"id": i, "description": f"task {i}", "phrase": "пинг" if i % 3 == 0 else "статус"}
        for i in range(args.tasks)
    ]
    queue = TaskQueue(tasks)

    with tempfile.TemporaryDirectory() as tmp:
        ledger_path = str(Path(tmp) / "ledger.db")
        bootstrap = SQLiteEvidenceLedger(ledger_path)
        bootstrap.close()

        results = []
        threads = []
        ready_events = []
        go = threading.Event()
        for i in range(args.workers):
            ready = threading.Event()
            ready_events.append(ready)
            t = threading.Thread(target=worker, args=(i, queue, ledger_path, results, ready, go))
            threads.append(t)
            t.start()
            ready.wait()
        print(f"[queue] {args.workers} workers ready — firing")
        started = time.time()
        go.set()
        for t in threads:
            t.join(timeout=60)
        total_ms = int((time.time() - started) * 1000)

        final_ledger = SQLiteEvidenceLedger(ledger_path)
        event_count = len(final_ledger.events)
        final_ledger.close()

        report = {
            "workers": args.workers,
            "tasks_total": args.tasks,
            "tasks_completed": len([r for r in results if "state" in r]),
            "tasks_errored": len([r for r in results if "error" in r]),
            "total_time_ms": total_ms,
            "final_ledger_events": event_count,
            "per_task": sorted(results, key=lambda r: r.get("task_id", 0)),
        }
        print(json.dumps(report, indent=2))
        sys.exit(0 if report["tasks_completed"] == args.tasks else 1)


if __name__ == "__main__":
    main()
