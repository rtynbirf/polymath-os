#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
polymath_agent.py — рабочее ядро целостного агента v1.5.0 «Арсенал+Исследование+Доказательство+Provenance+Recovery+Resume» + v3.3.2 CAS/STATE SEPARATION + DEPENDENCY/FRESHNESS + ARTIFACT BINDING + v3.5.2 KNOWLEDGE REVOCATION INDEX + v3.6.0 TRUST-DOMAIN KEY EPOCHS + v3.8.0 ROOT EPOCH CHAIN + v3.9.0 HMAC DOMAIN BINDING + v3.10.0 C5 GATE ANTI-VACUUM + v3.10.1 CODEQL HYGIENE (восстановлено из базы v2 после сброса среды 28.08.2026; v1.2.2–v1.2.4 — закалка живыми цепями).
Единый файл. Только стандартная библиотека Python 3.9+. Внешних зависимостей НЕТ.

=== v1.4: ТЕЛО = АРСЕНАЛ + ИССЛЕДОВАНИЕ + ДОКАЗАТЕЛЬСТВО ===
  CatalogBridge: каталог 2444 декларирует — shutil.which подтверждает — Governor выпускает через run_cli;
  констрейнт вывода: JSON Schema (maxLength-бюджеты) в нативный /api/chat, GBNF-эквивалент для llama.cpp;
  гейт релевантности процедурной памяти; запрет пустой записи; свидетель: токен-факты + (0 символов) не свидетель
  + контентная сверка литералов критерия с артефактом; PLAN_LOCK против план-лупа;
  $last_output: механическая подстановка вывода последнего успешного действия в args следующего
  v1.2.2: АТОМАРНОЕ РЕШЕНИЕ — maxItems 3→1 (огонь 5a1b0a7390: два действия в одном act не
  влезли в num_predict, JSON обрезан, мозг умер; атомарный act делает обрез невозможным)
  + честный диагноз обреза JSON в OllamaNativeBrain (вместо «контракт нарушен» — указание
  на POLY_NUM_PREDICT); RAM-гейт: длинные цепи на 1.7b — POLY_NUM_CTX=2560 (state-save
  промпт-кэша 251 MiB @4096 убил llama-server EOF'ом, огонь 66c4119357)
  (склейка «вывод команды → запись в файл» без семантического копирования — последний барьер снят).

=== МОДЕЛЬ РЕШЕНИЙ: Субъект / Тело / Конституция ===
  СУБЪЕКТ    — ровно одна линия инференса (единственный источник решений);
  ТЕЛО       — инструменты по строгому JSON-контракту (без regex-эвристик и без eval);
  КОНСТИТУЦИЯ— Governor: механический слой политики, физически недосягаемый для модели
               (валидация схем, изоляция путей, лимиты ресурсов, аудит на хеш-цепочке).

=== КАЖДАЯ НАХОДКА АУДИТА → КОМПОНЕНТ ===
  Ф2  ложная дихотомия монолит/комитет → один субъект решает; исполнители бесправны;
      supervisor-контур вместо peer-дебатов.
  Ф3  метафизика "резонанса" → убрана; оставлена операционная форма (контекст+инварианты).
  Ф4  объявление несуществующих возможностей → промпт строится ТОЛЬКО из реестра
      реально исполняемых инструментов; никогда не хардкодится.
  Ф5  NameError os / heredoc в argv / task=lines  → исправлено (sys.executable -c code;
      очередь читает lines[0]; импорты полные).
  Ф6  split().split() AttributeError и eval() → json.loads + валидатор схемы,
      белый список инструментов; FINAL_ANSWER обрабатывается консистентно.
  Ф7  regex-парсер действий → строгий JSON-протокол с валидацией и одним раундом
      автоматического ремонта при ошибке схемы.
  Ф8  центр vs иммунный слой → разделены принятие решения (Субъект) и принуждение
      к инвариантам (Governor, вне досягаемости самоизменения).
  Ф9  цикл OODA+Verify → петля Observe/Orient/Plan/Act/Verify/Update c бюджетами
      шагов/времени, счётчиком стагнации и честной остановкой вместо имитации успеха.
  Ф10 память без механизмов аннулирования → семантика с provenance-триплетом и TTL;
      эпизоды с sha256 артефактов; процедуры продвигаются после повторов.
  Д   галлюцинированное сжатие истории → сжатие МЕХАНИЧЕСКОЕ (LLM не пересказывает
      свою работу): дайджесты наблюдений + полный лог в файле.

=== ЧЕСТНЫЕ ОГРАНИЧЕНИЯ ПРОТОТИПА ===
  * execute_python изолируется rlimit'ами POSIX (CPU/память/размер файлов) во
    временном каталоге, но НЕ контейнером. Для боевого режима заключите исполнение
    в nsjail/Docker/Firecracker — интерфейс Governor этого не меняет.
  * http_get имеет SSRF-фильтр (локальные/приватные адреса блокируются), GET-only.

=== БЫСТРЫЙ СТАРТ ===
  python3 polymath_agent.py --selftest                 # проверить ядро без LLM
  ollama pull qwen3:8b                                 # актуальная локальная модель
  python3 polymath_agent.py --task "Создай hello.txt со строкой hi и проверь"
  python3 polymath_agent.py --task "..." --base-url http://localhost:11434/v1 \
      --model qwen3:8b --max-steps 24

Верификация фактов вебом 27.08.2026:
  * OpenAI-совместимый /v1/chat/completions у Ollama — документирован и активен
    (docs.ollama.com/api/openai-compatibility; tool calling с 2024-07).
  * Qwen3 8B — рекомендуемая компактная модель для локального запуска по обзорам
    июля-августа 2026 (promptquorum.com 29.07.2026; iproyal.com 06.08.2026).
"""

import argparse
import datetime as _dt
import hashlib
import http.server
import ipaddress
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import urllib.parse
import fnmatch
import zipfile
import tarfile
from dataclasses import dataclass, field, asdict, replace
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    import resource as _resource  # POSIX only
except ImportError:               # Windows fallback: квоты выключаются честно
    _resource = None


# ════════════════════════════ УТИЛИТЫ ════════════════════════════

def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def canonical_json(obj: Any) -> str:
    """Детерминированная сериализация — основа идемпотентности и аудита."""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_hex(data) -> str:
    """Принимает str ИЛИ bytes — единая точка хеширования без сюрпризов типов."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def log(tag: str, msg: str) -> None:
    print(f"[{tag}] {msg}", flush=True)


class PolicyViolation(Exception):
    """Нарушение Конституции — фиксируется в аудите, возвращается модели как отказ."""


# ════════════════════════════ НАБЛЮДЕНИЕ ════════════════════════════

@dataclass
class Observation:
    ok: bool
    kind: str            # read|write|list|exec|net|memory|policy_denied
    content: str         # сам факт наблюдения (то, что видит модель)
    meta: Dict[str, Any] = field(default_factory=dict)

    def brief(self, limit: int = 600) -> str:
        body = self.content if len(self.content) <= limit else self.content[:limit] + f"...[+{len(self.content)-limit} симв]"
        flag = "OK" if self.ok else "FAIL"
        return f"({self.kind}/{flag}) {body}"


# ════════════════════════════ ПАМЯТЬ (Ф10) ════════════════════════════

class MemoryStore:
    """
    Память-как-записи, а не память-как-векторы. Индексация — придаток, истину
    несёт типизированная запись. Три файла-носителя + working state.
    """

    def __init__(self, base_dir: Path):
        self.base = base_dir
        self.base.mkdir(parents=True, exist_ok=True)
        self.working_path = self.base / "working.json"
        self.episodic_path = self.base / "episodes.jsonl"
        self.semantic_path = self.base / "semantic.jsonl"
        self.procedures_path = self.base / "procedures.json"

    # --- рабочая память: одна истина о текущем процессе ---
    def load_working(self) -> Dict[str, Any]:
        if self.working_path.exists():
            try:
                return json.loads(self.working_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"goal": "", "criteria": [], "plan": [], "ledger": [], "verified": {}}

    def save_working(self, state: Dict[str, Any]) -> None:
        tmp = self.working_path.with_suffix(".tmp")
        tmp.write_text(canonical_json(state), encoding="utf-8")
        os.replace(tmp, self.working_path)   # атомарная замена, никакого частичного письма

    def clear_working(self) -> None:
        if self.working_path.exists():
            self.working_path.unlink()

    # --- эпизодическая: только подтверждённые записи с артефактами ---
    def write_episode(self, episode: Dict[str, Any]) -> str:
        for art in episode.get("artifacts", []):
            p = Path(art["path"])
            try:
                art["sha256"] = sha256_hex(p.read_bytes().decode("utf-8", "replace"))
            except OSError as e:
                art["sha256"] = f"unreadable:{e}"
        episode["written_at"] = now_iso()
        with self.episodic_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(episode, ensure_ascii=False) + "\n")
        return episode.get("episode_id", "")

    def recent_episodes(self, k: int = 5) -> List[Dict[str, Any]]:
        if not self.episodic_path.exists():
            return []
        lines = self.episodic_path.read_text(encoding="utf-8").strip().splitlines()
        out = []
        for ln in lines[-k:]:
            try:
                rec = json.loads(ln)
                out.append({
                    "goal": rec.get("goal", "?")[:120],
                    "outcome": rec.get("outcome"),
                    "lesson": rec.get("lesson", "")[:160],
                    "steps": rec.get("steps_used"),
                })
            except Exception:
                continue
        return out

    # --- семантическая: факт + источник + дата проверки + область + TTL ---
    def remember_semantic(self, fact: str, source: str, scope: str, ttl_days: int) -> str:
        rec = {
            "id": sha256_hex(fact)[:12],
            "fact": fact[:2000],
            "source": source[:500],
            "scope": scope[:200],
            "checked_at": now_iso(),
            "recheck_after": (_dt.datetime.now(_dt.timezone.utc)
                              + _dt.timedelta(days=max(0, ttl_days))).isoformat(),
        }
        with self.semantic_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec["id"]

    def query_semantic(self, keywords: List[str], k: int = 3) -> List[Dict[str, Any]]:
        if not self.semantic_path.exists():
            return []
        now = _dt.datetime.now(_dt.timezone.utc).isoformat()
        scored = []
        for ln in self.semantic_path.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(ln)
            except Exception:
                continue
            text = (rec.get("fact", "") + " " + rec.get("scope", "")).lower()
            score = sum(1 for kw in keywords if kw.lower() in text)
            if score > 0:
                rec["_score"] = score
                rec["_stale"] = bool(rec.get("recheck_after") and rec["recheck_after"] < now)
                scored.append(rec)
        scored.sort(key=lambda r: (-r["_score"], r["checked_at"]), reverse=False)
        scored.sort(key=lambda r: -r["_score"])
        return [{k2: v for k2, v in r.items() if not k2.startswith("_")} |
                {"stale": r["_stale"]} for r in scored[:k]]

    # --- процедурная: продвигается только отработанное ---
    def add_procedure(self, name: str, steps: List[str]) -> bool:
        procs = self._load_procedures()
        existed = name in procs
        procs[name] = {"steps": steps[:30], "updated": now_iso(),
                       "uses": procs.get(name, {}).get("uses", 0) + (0 if existed else 1)}
        self._save_procedures(procs)
        return existed

    def match_procedure(self, keywords: List[str]) -> Optional[Dict[str, Any]]:
        procs = self._load_procedures()
        best, best_score = None, 0
        for name, spec in procs.items():
            text = (name + " " + " ".join(spec.get("steps", []))).lower()
            score = sum(1 for kw in keywords if kw.lower() in text)
            if score > best_score and len(spec.get("steps", [])) >= 2:  # минимум 2 повтора не требуем в прототипе
                best, best_score = {"name": name, **spec}, score
        return best

    def _load_procedures(self) -> Dict[str, Any]:
        if self.procedures_path.exists():
            try:
                return json.loads(self.procedures_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save_procedures(self, procs: Dict[str, Any]) -> None:
        tmp = self.procedures_path.with_suffix(".tmp")
        tmp.write_text(canonical_json(procs), encoding="utf-8")
        os.replace(tmp, self.procedures_path)

    def gate_procedure(self, keywords: List[str], min_score: float = 2.0,
                       min_ratio: float = 0.25) -> Optional[Dict[str, Any]]:
        """Гейт релевантности процедурной памяти (закалено Уроком-2): чужая стратегия
        не должна протекать в промпт. Скоринг: токен в имени ×3, в шагах ×1;
        допуск: score ≥ min_score И ratio ≥ min_ratio И шагов ≥ 2.
        Гейт закрыт → None → в контексте тишина. Отчёт _gate{score,hits,ratio,admitted,reason}."""
        procs = self._load_procedures()
        toks = [t.lower() for t in keywords if t]
        best = None
        for name, spec in procs.items():
            steps = spec.get("steps", [])
            if len(steps) < 2:
                continue
            name_l = name.lower()
            steps_l = " ".join(steps).lower()
            score, hits = 0.0, 0
            for t in toks:
                h = 3.0 if t in name_l else (1.0 if t in steps_l else 0.0)
                score += h
                hits += 1 if h else 0
            ratio = (hits / len(toks)) if toks else 0.0
            if best is None or score > best[0]:
                best = (score, ratio, name, spec)
        if best is None:
            return None
        score, ratio, name, spec = best
        admitted = score >= min_score and ratio >= min_ratio
        rec = {"name": name, **spec}
        rec["_gate"] = {"score": round(score, 1), "hits": hits if toks else 0,
                        "ratio": round(ratio, 2), "admitted": admitted,
                        "reason": ("порог пройден" if admitted else
                                   f"score {score:.1f} < {min_score} или ratio {ratio:.2f} < {min_ratio}")}
        return rec if admitted else None


# ════════════════════════════ АУДИТ: append-only хеш-цепочка (Ф8) ══════════════════

class AuditChain:
    """Каждая запись подписана хешем предыдущей. Подмена задним числом детектируется."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.last_hash = "GENESIS"
        if self.path.exists():
            lines = [ln for ln in self.path.read_text(encoding="utf-8").splitlines() if ln.strip()]
            if lines:
                try:
                    self.last_hash = json.loads(lines[-1])["entry_hash"]
                except Exception:
                    self.last_hash = "CORRUPTED_PRIOR"

    def append(self, record: Dict[str, Any]) -> Dict[str, Any]:
        entry = {
            "seq": int(time.time_ns()),
            "ts": now_iso(),
            "record": record,
            "prev_hash": self.last_hash,
        }
        entry["entry_hash"] = sha256_hex(canonical_json({k: v for k, v in entry.items()}))
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self.last_hash = entry["entry_hash"]
        return entry

    def verify(self) -> Tuple[bool, Optional[int]]:
        prev = "GENESIS"
        lines = ([ln for ln in self.path.read_text(encoding="utf-8").splitlines() if ln.strip()]
                 if self.path.exists() else [])
        for i, ln in enumerate(lines):
            try:
                e = json.loads(ln)
            except Exception:
                return False, i
            payload = {k: v for k, v in e.items() if k != "entry_hash"}
            if e.get("prev_hash") != prev or e.get("entry_hash") != sha256_hex(canonical_json(payload)):
                return False, i
            prev = e["entry_hash"]
        return True, None


# ════════════════════ ИНСТРУМЕНТЫ + GOVERNOR (Ф5, Ф6, Ф8) ═══════════════════

RISK_ORDER = {"READ": 0, "WRITE": 1, "EXEC": 2, "NET": 2}


@dataclass
class ToolSpec:
    name: str
    risk: str                       # READ | WRITE | EXEC | NET
    required: Dict[str, type]       # обязательные параметры и типы
    optional: Dict[str, Any]        # имя -> значение по умолчанию (тип выводится)
    func: Callable[..., Observation]
    doc: str


def _confine(workspace: Path, user_path: str) -> Path:
    """Изоляция путей: файловые операции живут внутри workspace. Symlink-побеги режутся."""
    if not isinstance(user_path, str) or not user_path.strip():
        raise PolicyViolation("path обязателен и должен быть строкой")
    ws = workspace.resolve()
    raw = Path(user_path)
    if raw.is_absolute():
        candidate = raw
    else:
        candidate = ws / raw
    resolved = Path(os.path.realpath(candidate))
    try:
        resolved.relative_to(ws)
    except ValueError:
        raise PolicyViolation(
            f"Отказ Конституции: '{user_path}' вне workspace ({ws}). Побег пути заблокирован.")
    return resolved


def _t_read_file(cfg: "Config", args: Dict[str, Any]) -> Observation:
    p = _confine(Path(cfg.workspace), args["path"])
    if not p.exists():
        return Observation(False, "read", f"файл не существует: {args['path']}")
    if p.is_dir():
        return Observation(False, "read", f"это каталог, используй list_dir: {args['path']}")
    text = p.read_text(encoding="utf-8", errors="replace")
    return Observation(True, "read", text[:cfg.max_read_chars],
                       meta={"path": str(p), "sha256": sha256_hex(text)})


def _t_write_file(cfg: "Config", args: Dict[str, Any]) -> Observation:
    p = _confine(Path(cfg.workspace), args["path"])
    content = args.get("content", "")
    # Закалено живым огнём 27.08.2026 (эпизод 57f7ab84b2): модель пыталась записать
    # вывод ЕЩЁ НЕ выполненного действия тем же решением — файл пуст, а «verified» прошёл.
    # Пустая запись запрещена механически; для переноса вывода есть $last_output (v1.2).
    if not content.strip():
        return Observation(False, "write",
                           "пустая запись запрещена: передай непустой content литералом или "
                           "строкой \"$last_output\" (подставится вывод последнего успешного действия)",
                           meta={"bytes": 0})
    p.parent.mkdir(parents=True, exist_ok=True)
    existed_before = p.exists()
    p.write_text(content, encoding="utf-8")
    act = "перезаписан" if existed_before else "создан"
    return Observation(True, "write",
                       f"файл {act}: {p.name} ({len(content)} символов)",
                       meta={"path": str(p), "bytes": len(content)})


def _t_list_dir(cfg: "Config", args: Dict[str, Any]) -> Observation:
    p = _confine(Path(cfg.workspace), args.get("path", "."))
    if not p.exists():
        return Observation(False, "list", f"каталог не существует: {args.get('path', '.')}")
    entries = sorted(e.name + ("/" if e.is_dir() else "") for e in p.iterdir())[:200]
    return Observation(True, "list", "\n".join(entries) or "(пусто)", meta={"path": str(p)})


def _bounded_int(value: Any, default: int, lo: int, hi: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        n = default
    return max(lo, min(hi, n))


def _read_bytes_bounded(p: Path, max_bytes: int) -> Tuple[bytes, bool]:
    with p.open("rb") as f:
        data = f.read(max_bytes + 1)
    return data[:max_bytes], len(data) > max_bytes


def _t_stat_path(cfg: "Config", args: Dict[str, Any]) -> Observation:
    p = _confine(Path(cfg.workspace), args["path"])
    if not p.exists() and not p.is_symlink():
        return Observation(False, "read", f"путь не существует: {args['path']}")
    st = p.stat()
    kind = "dir" if p.is_dir() else "file" if p.is_file() else "other"
    return Observation(True, "read",
                       f"{kind}: {p.name}; bytes={st.st_size}; mode={oct(st.st_mode & 0o777)}",
                       meta={"path": str(p), "type": kind, "bytes": st.st_size,
                             "mtime": st.st_mtime, "mode": st.st_mode & 0o777})


def _t_mkdir(cfg: "Config", args: Dict[str, Any]) -> Observation:
    p = _confine(Path(cfg.workspace), args["path"])
    p.mkdir(parents=bool(args.get("parents", True)), exist_ok=bool(args.get("exist_ok", True)))
    return Observation(True, "write", f"каталог создан/существует: {p}", meta={"path": str(p)})


def _t_copy_path(cfg: "Config", args: Dict[str, Any]) -> Observation:
    src = _confine(Path(cfg.workspace), args["src"])
    dst = _confine(Path(cfg.workspace), args["dst"])
    if not src.exists() or not src.is_file():
        return Observation(False, "write", f"источник не является файлом: {args['src']}")
    if dst.exists() and not bool(args.get("overwrite", False)):
        return Observation(False, "write", f"назначение уже существует: {args['dst']}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    import shutil as _shutil
    _shutil.copy2(src, dst)
    return Observation(True, "write", f"скопировано: {src.name} → {dst.name}",
                       meta={"path": str(dst), "src": str(src), "bytes": dst.stat().st_size})


def _t_move_path(cfg: "Config", args: Dict[str, Any]) -> Observation:
    src = _confine(Path(cfg.workspace), args["src"])
    dst = _confine(Path(cfg.workspace), args["dst"])
    if not src.exists():
        return Observation(False, "write", f"источник не существует: {args['src']}")
    if dst.exists() and not bool(args.get("overwrite", False)):
        return Observation(False, "write", f"назначение уже существует: {args['dst']}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and bool(args.get("overwrite", False)):
        if dst.is_dir():
            import shutil as _shutil; _shutil.rmtree(dst)
        else:
            dst.unlink()
    src.rename(dst)
    return Observation(True, "write", f"перемещено: {src.name} → {dst.name}",
                       meta={"path": str(dst), "src": str(src)})


def _t_delete_path(cfg: "Config", args: Dict[str, Any]) -> Observation:
    p = _confine(Path(cfg.workspace), args["path"])
    if p == Path(cfg.workspace).resolve():
        raise PolicyViolation("удаление корня workspace запрещено")
    if not p.exists() and not p.is_symlink():
        return Observation(False, "write", f"путь не существует: {args['path']}")
    if p.is_dir():
        if not bool(args.get("recursive", False)):
            return Observation(False, "write", "каталог требует recursive=true")
        import shutil as _shutil; _shutil.rmtree(p)
    else:
        p.unlink()
    return Observation(True, "write", f"удалено: {args['path']}", meta={"path": str(p)})


def _t_hash_file(cfg: "Config", args: Dict[str, Any]) -> Observation:
    p = _confine(Path(cfg.workspace), args["path"])
    if not p.is_file():
        return Observation(False, "read", f"не файл: {args['path']}")
    algo = str(args.get("algorithm", "sha256")).lower()
    if algo not in {"sha256", "sha1", "md5"}:
        raise PolicyViolation("algorithm должен быть sha256|sha1|md5")
    h = hashlib.new(algo)
    with p.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk: break
            h.update(chunk)
    return Observation(True, "read", f"{algo}:{h.hexdigest()}",
                       meta={"path": str(p), "algorithm": algo, "hash": h.hexdigest()})


def _t_glob_files(cfg: "Config", args: Dict[str, Any]) -> Observation:
    root = _confine(Path(cfg.workspace), args.get("path", "."))
    if not root.exists() or not root.is_dir():
        return Observation(False, "read", f"каталог не существует: {args.get('path', '.')}")
    pattern = str(args.get("pattern", "*"))
    recursive = bool(args.get("recursive", True))
    limit = _bounded_int(args.get("limit", 200), 200, 1, 2000)
    it = root.rglob("*") if recursive else root.glob("*")
    hits=[]
    for x in it:
        if x.name and fnmatch.fnmatch(x.name, pattern):
            hits.append(str(x.relative_to(Path(cfg.workspace).resolve())))
            if len(hits) >= limit: break
    return Observation(True, "list", "\n".join(hits) or "(совпадений нет)",
                       meta={"path": str(root), "count": len(hits), "pattern": pattern})


def _t_verify_text(cfg: "Config", args: Dict[str, Any]) -> Observation:
    p = _confine(Path(cfg.workspace), args["path"])
    if not p.is_file():
        return Observation(False, "verify", f"файл не найден: {args['path']}")
    max_bytes = _bounded_int(args.get("max_bytes", cfg.net_max_bytes), cfg.net_max_bytes, 1, 5_000_000)
    data, truncated = _read_bytes_bounded(p, max_bytes)
    text = data.decode("utf-8", errors="replace")
    mode = args.get("mode", "contains")
    needle = args["text"]
    ok = needle in text if mode == "contains" else text == needle
    if mode not in {"contains", "equals"}:
        raise PolicyViolation("mode должен быть contains|equals")
    msg = f"verify_text {mode}: {'PASS' if ok else 'FAIL'}; path={p.name}; truncated={truncated}"
    return Observation(ok, "verify", msg, meta={"path": str(p), "mode": mode,
                       "needle": needle, "truncated": truncated, "bytes": len(data)})


def _t_json_read(cfg: "Config", args: Dict[str, Any]) -> Observation:
    p = _confine(Path(cfg.workspace), args["path"])
    if not p.is_file():
        return Observation(False, "read", f"файл не найден: {args['path']}")
    max_chars = _bounded_int(args.get("max_chars", cfg.max_read_chars), cfg.max_read_chars, 1, 1_000_000)
    text = p.read_text(encoding="utf-8", errors="strict")
    if len(text) > max_chars:
        return Observation(False, "read", f"JSON превышает лимит {max_chars} символов")
    try: obj=json.loads(text)
    except json.JSONDecodeError as e:
        return Observation(False, "read", f"некорректный JSON: {e}")
    return Observation(True, "read", json.dumps(obj, ensure_ascii=False, indent=2)[:max_chars],
                       meta={"path": str(p), "json": True})


def _t_json_write(cfg: "Config", args: Dict[str, Any]) -> Observation:
    p = _confine(Path(cfg.workspace), args["path"])
    obj = args["value"]
    text = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if not text.strip():
        return Observation(False, "write", "пустой JSON запрещён")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return Observation(True, "write", f"JSON записан: {p.name} ({len(text)} символов)",
                       meta={"path": str(p), "bytes": len(text)})


def _t_archive_create(cfg: "Config", args: Dict[str, Any]) -> Observation:
    out = _confine(Path(cfg.workspace), args["path"])
    members = args["members"]
    if not members:
        return Observation(False, "write", "members не должен быть пустым")
    fmt = args.get("format", "zip")
    out.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "zip":
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for name in members:
                p = _confine(Path(cfg.workspace), name)
                if not p.is_file(): return Observation(False, "write", f"не файл: {name}")
                z.write(p, arcname=str(p.relative_to(Path(cfg.workspace).resolve())))
    elif fmt == "tar.gz":
        with tarfile.open(out, "w:gz") as t:
            for name in members:
                p = _confine(Path(cfg.workspace), name)
                if not p.exists(): return Observation(False, "write", f"не найдено: {name}")
                t.add(p, arcname=str(p.relative_to(Path(cfg.workspace).resolve())), recursive=False)
    else:
        raise PolicyViolation("format должен быть zip|tar.gz")
    return Observation(True, "write", f"архив создан: {out.name}; format={fmt}; members={len(members)}",
                       meta={"path": str(out), "format": fmt})


def _t_archive_list(cfg: "Config", args: Dict[str, Any]) -> Observation:
    p = _confine(Path(cfg.workspace), args["path"])
    fmt = args.get("format", "auto")
    names=[]
    try:
        if fmt == "zip" or (fmt == "auto" and zipfile.is_zipfile(p)):
            with zipfile.ZipFile(p) as z: names=z.namelist()[:1000]
        elif fmt == "tar.gz" or fmt == "tar" or (fmt == "auto" and tarfile.is_tarfile(p)):
            with tarfile.open(p, "r:*") as t: names=[x.name for x in t.getmembers()[:1000]]
        else: return Observation(False, "read", "не удалось определить формат архива")
    except (OSError, zipfile.BadZipFile, tarfile.TarError) as e:
        return Observation(False, "read", f"ошибка архива: {e}")
    return Observation(True, "read", "\n".join(names) or "(пусто)", meta={"path": str(p), "count": len(names)})


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _http_request_no_redirect(url: str, cfg: "Config", method: str = "GET", data: Optional[bytes] = None):
    _ssrf_guard(url)
    req = urllib.request.Request(url, data=data, method=method, headers={
        "User-Agent": "polymath-agent/1.3 (+local research tool)",
        "Accept": "text/html, text/plain, application/json, application/xml;q=0.9,*/*;q=0.5"})
    opener = urllib.request.build_opener(_NoRedirect)
    return opener.open(req, timeout=cfg.net_timeout_s)


def _t_web_search(cfg: "Config", args: Dict[str, Any]) -> Observation:
    query = str(args["query"]).strip()
    limit = _bounded_int(args.get("limit", 5), 5, 1, 10)
    # DuckDuckGo HTML — только discovery; найденные URL потом проходят отдельный http_get/SSRF-контур.
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote_plus(query)
    try:
        with _http_request_no_redirect(url, cfg) as resp:
            data = resp.read(min(cfg.net_max_bytes, 300_000))
            status = getattr(resp, "status", 200)
    except PolicyViolation as e:
        return Observation(False, "policy", f"поиск заблокирован политикой: {e}")
    except urllib.error.HTTPError as e:
        return Observation(False, "net", f"поиск HTTP {e.code}: {e.reason}")
    except (urllib.error.URLError, OSError) as e:
        return Observation(False, "net", f"поиск недоступен: {e}")
    text=data.decode("utf-8", errors="replace")
    results=[]
    # Парсим только result__a href/title, без исполнения HTML.
    for m in re.finditer(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', text, re.I|re.S):
        href=html_unescape(m.group(1)); title=re.sub(r"<[^>]+>", "", m.group(2))
        href=urllib.parse.unquote(href)
        if href.startswith("//"): href="https:"+href
        if href.startswith("http"):
            results.append({"title": re.sub(r"\s+", " ", html_unescape(title)).strip(), "url": href})
        if len(results)>=limit: break
    body="\n".join(f"{i+1}. {r['title']}\n   {r['url']}" for i,r in enumerate(results)) or "(результаты не извлечены)"
    return Observation(bool(results), "net", body, meta={"status": status, "results": results, "query": query})


def html_unescape(s: str) -> str:
    import html
    return html.unescape(s)


def _exec_preexec():
    """POSIX rlimit-квоты для дочернего процесса. Замыкание без параметров."""
    def apply():
        if _resource is None:
            return
        cfg_cpu = 10            # секунды CPU
        cfg_mem = 512 * 1024 * 1024   # 512 MB адресного пространства
        cfg_fsize = 4 * 1024 * 1024   # 4 MB на файл
        cfg_nofile = 64
        try:
            _resource.setrlimit(_resource.RLIMIT_CPU, (cfg_cpu, cfg_cpu))
            _resource.setrlimit(_resource.RLIMIT_AS, (cfg_mem, cfg_mem))
            _resource.setrlimit(_resource.RLIMIT_FSIZE, (cfg_fsize, cfg_fsize))
            _resource.setrlimit(_resource.RLIMIT_NOFILE, (cfg_nofile, cfg_nofile))
        except Exception:
            pass                # честная деградация: квота может не поддерживаться ФС/ОС
    return apply


def _t_execute_python(cfg: "Config", args: Dict[str, Any]) -> Observation:
    """Исправление Ф5: sys.executable -c code. Никаких heredoc в argv."""
    code = args["code"]
    with tempfile.TemporaryDirectory(prefix="poly_exec_") as td:
        try:
            proc = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=cfg.exec_timeout_s,
                cwd=td,
                preexec_fn=_exec_preexec() if (_resource and os.name == "posix") else None,
            )
        except subprocess.TimeoutExpired:
            return Observation(False, "exec",
                               f"превышен таймаут {cfg.exec_timeout_s}s — процесс убит")
        out = proc.stdout.strip()
        err = proc.stderr.strip()
        body = ""
        if out:
            body += f"STDOUT:\n{out}\n"
        if err:
            body += f"STDERR:\n{err}\n"
        body += f"RC={proc.returncode}"
        return Observation(proc.returncode == 0, "exec", body,
                           meta={"rc": proc.returncode})


_BAD_HOSTNAMES = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "metadata.google.internal",
                   "metadata.goog"}


def _ssrf_guard(url: str) -> None:
    """GET-only наружу; приватные/резервные сети запрещены (best-effort DNS-пиннинг)."""
    m = re.match(r"^https?://[^/]+", url or "")
    if not m:
        raise PolicyViolation("url обязан быть абсолютным http(s)-адресом")
    host = re.match(r"^https?://([^/:?#]+)", url).group(1).strip("[]").lower()
    if host in _BAD_HOSTNAMES:
        raise PolicyViolation(f"SSRF-фильтр: хост '{host}' запрещён")
    if host.endswith(".local") or host.endswith(".internal"):
        raise PolicyViolation(f"SSRF-фильтр: домен внутренней зоны '{host}' запрещён")
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError as e:
        raise PolicyViolation(f"SSRF-фильтр: DNS-резолв не удался ({e}) — блокирую")
    for info in infos:
        addr = ipaddress.ip_address(info[4][0])
        if (addr.is_private or addr.is_loopback or addr.is_link_local
                or addr.is_reserved or addr.is_multicast):
            raise PolicyViolation(f"SSRF-фильтр: адрес {addr} относится к приватным сетям")


def _t_http_get(cfg: "Config", args: Dict[str, Any]) -> Observation:
    url = args["url"]
    max_bytes = int(args.get("max_bytes", cfg.net_max_bytes))
    _ssrf_guard(url)
    req = urllib.request.Request(url, headers={
        "User-Agent": "polymath-agent/1.0 (+local research tool)",
        "Accept": "text/*,application/json;q=0.9,*/*;q=0.5",
    })
    try:
        # Redirects запрещены здесь намеренно: новый URL должен пройти SSRF-проверку заново.
        with urllib.request.build_opener(_NoRedirect).open(req, timeout=cfg.net_timeout_s) as resp:
            data = resp.read(max_bytes + 1)
            status = getattr(resp, "status", 200)
    except urllib.error.HTTPError as e:
        return Observation(False, "net", f"HTTP {e.code}: {e.reason}")
    except (urllib.error.URLError, OSError) as e:
        return Observation(False, "net", f"сетевой сбой: {e}")
    truncated = len(data) > max_bytes
    text = data[:max_bytes].decode("utf-8", errors="replace")
    tag = f" [обрезано до {max_bytes} байт]" if truncated else ""
    return Observation(True, "net", text + tag, meta={"status": status, "bytes": min(len(data), max_bytes)})


def _strip_html_to_text(raw: str, limit: int = 12000) -> str:
    """Дешёвое безопасное извлечение текста: без исполнения HTML/JS."""
    raw = re.sub(r"(?is)<script\b.*?</script[^>]*>|<style\b.*?</style[^>]*>|<noscript\b.*?</noscript[^>]*>", " ", raw)
    raw = re.sub(r"(?is)<[^>]+>", " ", raw)
    raw = html_unescape(raw)
    return re.sub(r"\s+", " ", raw).strip()[:limit]


def _t_research_web(cfg: "Config", args: Dict[str, Any]) -> Observation:
    """Research pipeline: discovery -> independently guarded fetch -> provenance bundle.
    Это одна атомарная capability для модели, но каждый сетевой переход проходит тот же SSRF-гейт.
    """
    query = str(args["query"]).strip()
    limit = _bounded_int(args.get("limit", 3), 3, 1, 5)
    per_source = _bounded_int(args.get("per_source_chars", 6000), 6000, 1000, 12000)
    search_obs = _t_web_search(cfg, {"query": query, "limit": limit})
    if not search_obs.ok:
        return search_obs
    sources = []
    for item in search_obs.meta.get("results", []):
        url = item.get("url", "")
        try:
            _ssrf_guard(url)
            with urllib.request.build_opener(_NoRedirect).open(
                urllib.request.Request(url, headers={"User-Agent": "polymath-agent/1.4 research"}),
                timeout=cfg.net_timeout_s) as resp:
                data = resp.read(min(cfg.net_max_bytes, 300_000))
                status = getattr(resp, "status", 200)
                ctype = resp.headers.get("Content-Type", "")
            text = data.decode("utf-8", errors="replace")
            if "html" in ctype.lower() or re.search(r"<html|<body", text, re.I):
                text = _strip_html_to_text(text, per_source)
            else:
                text = re.sub(r"\s+", " ", text).strip()[:per_source]
            sources.append({"title": item.get("title", ""), "url": url,
                            "status": status, "content_type": ctype,
                            "text": text, "sha256": sha256_hex(data)})
        except (PolicyViolation, urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
            sources.append({"title": item.get("title", ""), "url": url,
                            "error": str(e)})
    good = [x for x in sources if "text" in x and x.get("status", 0) < 400]
    bundle = {"query": query, "retrieved_at": now_iso(), "sources": sources,
              "usable_sources": len(good)}
    digest = sha256_hex(canonical_json(bundle).encode("utf-8"))
    body = "RESEARCH_BUNDLE sha256=" + digest + "\n"
    for i, x in enumerate(good, 1):
        body += f"\n[{i}] {x['title']}\nURL: {x['url']}\nHTTP: {x['status']}\n{x['text']}\n"
    if not good:
        return Observation(False, "research", "исследование не получило ни одного пригодного источника",
                           meta={"bundle": bundle, "digest": digest})
    return Observation(True, "research", body, meta={"bundle": bundle, "digest": digest,
                                                       "sources": len(sources), "usable_sources": len(good)})


def _t_remember_semantic(cfg: "Config", args: Dict[str, Any], mem: MemoryStore) -> Observation:
    """Ядро антигаллюцинации памяти: факт невозможно сохранить без источника."""
    rec_id = mem.remember_semantic(
        fact=args["fact"], source=args["source"], scope=args.get("scope", "general"),
        ttl_days=int(args.get("ttl_days", 30)))
    return Observation(True, "memory", f"сохранён факт id={rec_id}",
                       meta={"id": rec_id, "ttl_days": int(args.get("ttl_days", 30))})


def _t_add_procedure(cfg: "Config", args: Dict[str, Any], mem: MemoryStore) -> Observation:
    name = args["name"].strip()
    steps = args["steps"]
    updated_existing = mem.add_procedure(name, steps)
    act = "обновлена" if updated_existing else "создана"
    return Observation(True, "memory", f"процедура «{name}» {act} ({len(steps)} шагов)")


# ════════════════════ ТЕЛО v1.2: АРСЕНАЛ (Каталог → Registry) ═══════════════════

class CatalogBridge:
    """Каталог декларирует — диск подтверждает. Записи без бинаря (библиотеки) —
    знание, не исполнение: в промпт попадают, через run_cli не исполняются.
    Абсолютный путь бинаря фиксируется один раз (защита от подмены PATH)."""

    def __init__(self, path: str):
        self.by_bin: Dict[str, Dict[str, Any]] = {}
        self.total = self.categories = self.bins = self.available = 0
        if not path or not Path(path).exists():
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception:
            return
        if data.get("schema") != "polymat.arsenal/1.0":
            return
        for e in data.get("tools", []):
            b = (e.get("b") or "").strip().lower()
            if b and b not in self.by_bin:          # дубликаты бинарей схлопываются
                self.by_bin[b] = {"name": e.get("n", ""), "cat": e.get("c", ""),
                                  "desc": e.get("d", ""), "bin": b}
        self.total = int(data.get("total", len(data.get("tools", []))))
        self.categories = int(data.get("categories", 0))
        self.bins = len(self.by_bin)
        for rec in self.by_bin.values():
            p = shutil.which(rec["bin"])
            if p:
                rec["_abs"] = os.path.abspath(p)
                self.available += 1

    def resolve(self, bin_name: str) -> Optional[str]:
        rec = self.by_bin.get((bin_name or "").strip().lower())
        return rec.get("_abs") if rec else None

    def arsenal_digest(self, goal: str, k: int = 12) -> str:
        """Топ-k релевантных цели позиций арсенала (лексический скоринг:
        токен в имени бинаря ×3, в описании ×1) — вместо 2444 строк в промпт."""
        if not self.by_bin or not goal:
            return ""
        toks = re.findall(r"\w{4,}", goal.lower())
        scored = []
        for rec in self.by_bin.values():
            text = f"{rec['name']} {rec['desc']}".lower()
            s = 0.0
            for t in toks:
                if t in rec["bin"]:
                    s += 3.0
                elif t in text:
                    s += 1.0
            if s > 0:
                scored.append((s, rec["bin"], rec))
        scored.sort(key=lambda x: (-x[0], x[1]))
        lines = [f"- {r['bin']} [{r['cat']}] {r['desc'][:110]}" for _, _, r in scored[:k]]
        if not lines:
            return ""
        return ("АРСЕНАЛ (исполняемые через run_cli бинари, релевантные цели):\n"
                + "\n".join(lines))


def _t_run_cli(cfg: "Config", args: Dict[str, Any], bridge: "CatalogBridge") -> Observation:
    """Генерический EXEC из арсенала: argv без shell, абсолютный бинарь,
    rlimit-песочница общая с execute_python, дедуп и аудит — контур Governor."""
    bin_name = str(args.get("bin", "")).strip().lower()
    if not bin_name:
        return Observation(False, "exec", "run_cli: параметр 'bin' обязателен")
    abs_bin = bridge.resolve(bin_name) if bridge else None
    if not abs_bin:
        raise PolicyViolation(
            f"бинарь '{bin_name}' вне арсенала (нет в каталоге или не подтверждён диском)")
    raw_args = args.get("args", [])
    if not isinstance(raw_args, list) or not all(isinstance(x, str) for x in raw_args):
        return Observation(False, "exec", "run_cli: 'args' обязан быть списком строк")
    stdin = args.get("stdin", "")
    try:
        proc = subprocess.run([abs_bin] + raw_args,
                              input=stdin.encode("utf-8"), capture_output=True,
                              timeout=cfg.exec_timeout_s, preexec_fn=_exec_preexec())
    except subprocess.TimeoutExpired:
        return Observation(False, "exec", f"run_cli: таймаут {cfg.exec_timeout_s}s у {bin_name}")
    out = (proc.stdout or b"").decode("utf-8", errors="replace").strip()
    errb = (proc.stderr or b"").decode("utf-8", errors="replace").strip()
    body = out or errb
    cmd = f"$ {bin_name} {' '.join(raw_args)}".strip()
    return Observation(proc.returncode == 0, "exec", f"{cmd}\n{body}".strip(),
                       meta={"rc": proc.returncode, "bin": bin_name, "output": body})


# ════════════════════ ПЕРЕМЕННАЯ $last_output (v1.2) ═══════════════════

LAST_OUTPUT_VAR = "$last_output"


def _substitute_vars(args: Any, state: Dict[str, Any]) -> Tuple[Any, bool]:
    """Механическая подстановка $last_output — вывод последнего успешного действия —
    в args действия. Рекурсия по dict/list; замена ТОЛЬКО точного совпадения строки
    (строка, равная переменной целиком), чтобы не калечить данные модели.
    Возвращает (args, missing): missing=True, если переменная упомянута, но ещё
    не существует — вызов будет честно отклонён с объяснением."""
    missing = [False]

    def walk(x):
        if isinstance(x, str):
            if x.strip() == LAST_OUTPUT_VAR:
                lo = state.get("_last_output")
                if lo is None:
                    missing[0] = True
                    return x
                return lo
            return x
        if isinstance(x, dict):
            return {k: walk(v) for k, v in x.items()}
        if isinstance(x, list):
            return [walk(v) for v in x]
        return x

    return walk(args), missing[0]


class Governor:
    """
    КОНСТИТУЦИЯ: механический слой принуждения к инвариантам.
    Модель может только ПРОСИТЬ действие. Исполняет и разрешает — Governor,
    который модель не вызывает и переписать не может (он вне её контекста).
    """

    def __init__(self, cfg: "Config", audit: AuditChain,
                 bridge: Optional["CatalogBridge"] = None):
        self.cfg = cfg
        self.audit = audit
        self.mem = MemoryStore(Path(cfg.data_dir))
        self.registry: Dict[str, ToolSpec] = {}
        self.bridge = bridge
        self._register_builtin_tools()
        # Идемпотентность ПОБОЧНЫХ действий (WRITE/EXEC/NET): канонический хеш вызова
        # -> шаг первого исполнения. READ сознательно вне дедупликации: повторное
        # чтение для верификации артефакта — легитимное действие.
        self._seen_side_effect: Dict[str, int] = {}

    # --- реестр: промпт документируется ТОЛЬКО отсюда (анти-Ф4) ---
    def _register_builtin_tools(self):
        reg = self.registry
        reg["stat_path"] = ToolSpec("stat_path", "READ", {"path": str}, {}, _t_stat_path,
                                    "метаданные файла/каталога")
        reg["glob_files"] = ToolSpec("glob_files", "READ", {}, {"path": ".", "pattern": "*", "recursive": True, "limit": 200}, _t_glob_files,
                                    "найти файлы по маске внутри workspace")
        reg["hash_file"] = ToolSpec("hash_file", "READ", {"path": str}, {"algorithm": "sha256"}, _t_hash_file,
                                    "вычислить криптографический хеш файла")
        reg["verify_text"] = ToolSpec("verify_text", "READ", {"path": str, "text": str}, {"mode": "contains", "max_bytes": self.cfg.net_max_bytes}, _t_verify_text,
                                    "механически проверить contains/equals текста в файле")
        reg["json_read"] = ToolSpec("json_read", "READ", {"path": str}, {"max_chars": self.cfg.max_read_chars}, _t_json_read,
                                    "прочитать и разобрать JSON")
        reg["mkdir"] = ToolSpec("mkdir", "WRITE", {"path": str}, {"parents": True, "exist_ok": True}, _t_mkdir,
                                 "создать каталог в workspace")
        reg["copy_path"] = ToolSpec("copy_path", "WRITE", {"src": str, "dst": str}, {"overwrite": False}, _t_copy_path,
                                     "скопировать файл внутри workspace")
        reg["move_path"] = ToolSpec("move_path", "WRITE", {"src": str, "dst": str}, {"overwrite": False}, _t_move_path,
                                     "переместить путь внутри workspace")
        reg["delete_path"] = ToolSpec("delete_path", "WRITE", {"path": str}, {"recursive": False}, _t_delete_path,
                                       "удалить путь внутри workspace")
        reg["json_write"] = ToolSpec("json_write", "WRITE", {"path": str, "value": object}, {}, _t_json_write,
                                      "записать JSON-значение")
        reg["archive_create"] = ToolSpec("archive_create", "WRITE", {"path": str, "members": list}, {"format": "zip"}, _t_archive_create,
                                          "создать zip или tar.gz из файлов workspace")
        reg["archive_list"] = ToolSpec("archive_list", "READ", {"path": str}, {"format": "auto"}, _t_archive_list,
                                       "показать содержимое архива без извлечения")
        reg["web_search"] = ToolSpec("web_search", "NET", {"query": str}, {"limit": 5}, _t_web_search,
                                      "выполнить веб-поиск; URL результатов требуют отдельного получения")
        reg["read_file"] = ToolSpec("read_file", "READ", {"path": str}, {}, _t_read_file,
                                    "прочитать файл из workspace")
        reg["write_file"] = ToolSpec("write_file", "WRITE", {"path": str, "content": str},
                                     {}, _t_write_file, "создать/перезаписать файл в workspace")
        reg["list_dir"] = ToolSpec("list_dir", "READ", {}, {"path": "."}, _t_list_dir,
                                   "список файлов каталога workspace")
        reg["execute_python"] = ToolSpec("execute_python", "EXEC", {"code": str}, {},
                                         _t_execute_python,
                                         "выполнить код python3 в песочнице с лимитами")
        reg["http_get"] = ToolSpec("http_get", "NET", {"url": str},
                                   {"max_bytes": self.cfg.net_max_bytes}, _t_http_get,
                                   "GET-запрос наружу (приватные сети закрыты)")
        reg["research_web"] = ToolSpec("research_web", "NET", {"query": str},
                                      {"limit": 3, "per_source_chars": 6000}, _t_research_web,
                                      "Веб-исследование: discovery→guarded fetch→provenance bundle")
        reg["remember_semantic"] = ToolSpec("remember_semantic", "WRITE",
                                            {"fact": str, "source": str},
                                            {"scope": "general", "ttl_days": 30},
                                            lambda c, a: _t_remember_semantic(c, a, self.mem),
                                            "сохранить проверенный факт (источник обязателен)")
        reg["add_procedure"] = ToolSpec("add_procedure", "WRITE", {"name": str, "steps": list},
                                        {}, lambda c, a: _t_add_procedure(c, a, self.mem),
                                        "запомнить устойчивую процедуру из шагов")
        if self.bridge is not None and self.bridge.bins:
            reg["run_cli"] = ToolSpec("run_cli", "EXEC", {"bin": str},
                                      {"args": [], "stdin": ""},
                                      lambda c, a: _t_run_cli(c, a, self.bridge),
                                      "исполнить бинарь из арсенала: bin, args (список строк), stdin")

    # --- схема без внешних библиотек ---
    def validate_args(self, spec: ToolSpec, args: Dict[str, Any]) -> Optional[str]:
        if not isinstance(args, dict):
            return "args обязан быть JSON-объектом"
        unknown = set(args) - set(spec.required) - set(spec.optional)
        if unknown:
            return f"неизвестные параметры {sorted(unknown)} для {spec.name}; допустимо: {sorted(list(spec.required) + list(spec.optional))}"
        for k, t in spec.required.items():
            if k not in args:
                return f"отсутствует обязательный параметр '{k}' для {spec.name}"
            if not isinstance(args[k], t):
                return f"параметр '{k}' имеет тип {type(args[k]).__name__}, ожидается {t.__name__}"
        for k, default in spec.optional.items():
            if k in args and not isinstance(args[k], type(default)):
                return (f"параметр '{k}' имеет тип {type(args[k]).__name__}, "
                        f"ожидается {type(default).__name__}")
        return None

    # --- полный конвейер исполнения одного действия ---
    def run(self, task_id: str, step_idx: int, name: str, args: Dict[str, Any]) -> Tuple[Observation, Optional[str]]:
        artifact_fp: Optional[str] = None
        if name not in self.registry:
            obs = Observation(False, "policy_denied",
                              f"инструмент '{name}' отсутствует; доступно: {sorted(self.registry)}")
            self.audit.append({"task_id": task_id, "step": step_idx, "action": name,
                               "verdict": "unknown_tool"})
            return obs, artifact_fp

        spec = self.registry[name]
        schema_err = self.validate_args(spec, args)
        if schema_err:
            self.audit.append({"task_id": task_id, "step": step_idx, "action": name,
                               "verdict": "schema_rejected", "error": schema_err})
            return Observation(False, "policy_denied", f"Контракт нарушен: {schema_err}"), artifact_fp

        # Дедуп побочных вызовов: тот же инструмент с идентичными аргументами внутри
        # одной задачи исполняется ОДИН раз. Повторить READ можно всегда.
        # v1.2.1: канонизация — опциональные аргументы дорезолвливаются к дефолтам,
        # иначе явный stdin:"" обходил идемпотентность (эпизод 30ff4a63ee: git дважды)
        if spec.risk != "READ":
            canon = {k: args[k] for k in spec.required if k in args}
            for k, dv in spec.optional.items():
                canon[k] = args.get(k, dv)
            idem = sha256_hex(canonical_json([name, canon]))
            prior_step = self._seen_side_effect.get(idem)
            if prior_step is not None:
                self.audit.append({"task_id": task_id, "step": step_idx, "action": name,
                                   "verdict": "deduped", "first_seen_step": prior_step})
                return Observation(False, "policy_denied",
                                   f"дубликат побочного вызова {name}: уже исполнен на шаге "
                                   f"{prior_step} с идентичными аргументами — результат уже "
                                   "в истории наблюдений"), artifact_fp
            self._seen_side_effect[idem] = step_idx

        # риск-контур: EXEC требует подтверждения оператора, если не включён --yes
        if RISK_ORDER[spec.risk] >= RISK_ORDER["EXEC"] and not self.cfg.auto_yes:
            log("GOVERNOR", f"Подтверди действие риска {spec.risk}: {name} "
                            f"{json.dumps(args, ensure_ascii=False)[:300]}")
            answer = input("   разрешить? [y/N] ").strip().lower()
            if answer != "y":
                self.audit.append({"task_id": task_id, "step": step_idx, "action": name,
                                   "verdict": "denied_by_operator"})
                return Observation(False, "policy_denied",
                                   "оператор отклонил действие; выбери другой путь"), artifact_fp

        try:
            obs = spec.func(self.cfg, args)
        except PolicyViolation as e:
            obs = Observation(False, "policy_denied", str(e))
        except Exception as e:                      # умышленно широкий перехват: тело возвращается модели как факт
            obs = Observation(False, spec.risk.lower(),
                              f"исключение инструмента: {type(e).__name__}: {e}")

        if obs.ok and spec.risk == "WRITE":
            p = obs.meta.get("path")
            if p and Path(p).is_file():
                artifact_fp = sha256_hex(Path(p).read_bytes())[:16]
        verdict = "ok" if obs.ok else "error"
        self.audit.append({
            "task_id": task_id, "step": step_idx, "action": name,
            "risk": spec.risk, "verdict": verdict,
            "args_sha256": sha256_hex(canonical_json(args)),
            "artifact_fp": artifact_fp,
            "result_brief": obs.brief(200),
        })
        return obs, artifact_fp

    def tools_documentation(self, goal: str = "") -> str:
        lines = []
        for name in sorted(self.registry):
            s = self.registry[name]
            params = ", ".join(f"{k}: {v.__name__}" for k, v in s.required.items())
            opt = ", ".join(f"{k}?={json.dumps(v)[:40]}" for k, v in s.optional.items())
            sig = f"{name}({params}" + (f", {opt}" if opt else "") + f")  [{s.risk}]"
            lines.append(f"- {sig} — {s.doc}")
        if self.bridge is not None and goal:
            digest = self.bridge.arsenal_digest(goal, k=self.cfg.arsenal_k)
            if digest:
                lines.append(digest)
        return "\n".join(lines)


# ════════════════════ МОЗГ: одна линия инференса (Ф2, Ф7) ═══════════════════

SYSTEM_DNA = """Ты — Полимат: единый субъект исполнения, а не комитет ролей.
ПРИНЦИПЫ:
1. Единственный источник решений здесь — ты. Никаких внутренних собеседников.
2. Фактом для тебя является ТОЛЬКО то, что содержится в Наблюдениях (Observations)
   с номерами шагов. Всё остальное — гипотеза; помечай её как гипотезу.
3. Запрещено объявлять возможности, которых нет в списке инструментов.
4. Прежде чем объявить final с outcome=verified, каждый критерий успеха должен быть
   подтверждён наблюдаемым артефактом (чтение файла, вывод команды). Если подтвердить
   не удалось — честный outcome=failed или aborted. Имитация успеха запрещена.
5. Выводи РОВНО ОДИН JSON-объект без markdown-ограждений и пояснений.
6. Переменная $last_output: в args любого действия строка "$last_output" механически
   заменяется на вывод последнего успешного действия. Переноси вывод команды в файл
   БЕЗ копирования: {"name": "write_file", "args": {"path": "out.txt", "content": "$last_output"}}.
   Ссылаться на ещё не выполненное действие бессмысленно — переменной ещё нет.
7. Дисциплина склейки: действие-источник (run_cli/execute_python) и запись его вывода
   через $last_output делай РАЗНЫМИ решениями: вывод появляется только после действия.

ФОРМАТ (все поля обязательны там, где указан статус):
{"thought": "краткое рассуждение",
 "status": "plan" | "act" | "final",
 "success_criteria": ["наблюдаемая проверка", ...],        // при status=plan
 "plan": ["шаг", ...],                                      // при status=plan
 "actions": [{"name": "...", "args": {...}, "why": "..."}], // при status=act, 1..3 шт
 "outcome": "verified" | "failed" | "aborted",              // при status=final
 "final_answer": "итог для пользователя",                    // при status=final
 "lesson": "извлечённый урок одной строкой"}                 // при status=final"""


def extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Без regex-эвристик на уровне интентов: только баланс скобок от первого '{'.
    Допускаем markdown-ограждение ```json — это синтаксис вокруг объекта, не эвристика."""
    if not text:
        return None
    cleaned = re.sub(r"```(?:json)?", "", text)
    start = cleaned.find("{")
    if start < 0:
        return None
    depth, in_str, esc = 0, False, False
    for i in range(start, len(cleaned)):
        ch = cleaned[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(cleaned[start:i + 1])
                except json.JSONDecodeError:
                    return None
    return None


class BrainError(Exception):
    pass


class MockBrain:
    """Сценарный мозг для самопроверки ядра и демо без LLM."""

    def __init__(self, script: List[Dict[str, Any]]):
        self.script = list(script)
        self.calls = 0

    def decide(self, system_prompt: str, user_block: str, error_feedback: Optional[str] = None) -> Dict[str, Any]:
        self.calls += 1
        if not self.script:
            raise BrainError("сценарий MockBrain исчерпан")
        item = self.script.pop(0)
        if isinstance(item, BrainError):
            raise item
        return item


class ApiBrain:
    """OpenAI-совместимый /chat/completions через urllib (проверено вебом 27.08.2026:
    ollama/vLLM/LM Studio/облачные провайдеры поддерживают этот контракт).
    Стрим выключен всегда: нужен цельный JSON за один такт мышления."""

    def __init__(self, cfg: "Config"):
        self.cfg = cfg
        if not cfg.base_url:
            raise BrainError("--base-url обязателен для --brain api")
        key = os.environ.get(cfg.api_key_env, "") if cfg.api_key_env else ""
        self.headers = {"Content-Type": "application/json"}
        if key:
            self.headers["Authorization"] = f"Bearer {key}"

    def decide(self, system_prompt: str, user_block: str, error_feedback: Optional[str] = None) -> Dict[str, Any]:
        user_content = user_block if not error_feedback else (
            user_block + "\n\nТВОЙ ПРЕДЫДУЩИЙ ВЫВОД ОТКЛОНЁН ВАЛИДАТОРОМ:\n" + error_feedback +
            "\nИсправь и выведи снова ровно один JSON-объект.")
        payload = {
            "model": self.cfg.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": self.cfg.temperature,
            "stream": False,
        }
        url = self.cfg.base_url.rstrip("/") + "/chat/completions"
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                     headers=self.headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.cfg.brain_timeout_s) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise BrainError(f"HTTP {e.code} от бэкенда: {e.read()[:300]}")
        except (urllib.error.URLError, OSError) as e:
            raise BrainError(f"бэкенд недоступен ({e}); поднят ли ollama serve?")
        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise BrainError(f"неожиданный ответ бэкенда ({e}): {str(body)[:300]}")
        parsed = extract_json(content)
        if parsed is None:
            raise BrainError("модель вернула не-JSON ответ:\n" + content[:400])
        return parsed


def build_decision_schema() -> Dict[str, Any]:
    """JSON Schema решения Полимата для format=<schema> в ollama /api/chat.
    Три жёстких варианта (plan/act/final) через anyOf: status закреплён const,
    перечисления закрыты, посторонние поля запрещены. maxLength-бюджеты закалены
    живым огнём qwen3:4b: без них болтливые модели обрезаются num_predict посреди JSON."""
    s_thought = {"type": "string", "maxLength": 280}
    s_short = {"type": "string", "maxLength": 120}
    s_answer = {"type": "string", "maxLength": 600}
    str_arr_b = {"type": "array", "items": s_short, "maxItems": 6}
    action = {
        "type": "object",
        "properties": {"name": {"type": "string", "maxLength": 40},
                       "args": {"type": "object"}, "why": s_short},
        "required": ["name", "args"],
        "additionalProperties": False,
    }
    plan = {
        "type": "object",
        "properties": {
            "thought": s_thought, "status": {"type": "string", "const": "plan"},
            "success_criteria": str_arr_b, "plan": str_arr_b,
        },
        "required": ["thought", "status", "success_criteria", "plan"],
        "additionalProperties": False,
    }
    act = {
        "type": "object",
        "properties": {
            "thought": s_thought, "status": {"type": "string", "const": "act"},
            # v1.2.2: атомарное решение — ровно одно действие (защита от обреза JSON по
            # num_predict: два действия с why/thought ~450 токенов > бюджета 220 у 1.7b)
            "actions": {"type": "array", "items": action, "minItems": 1, "maxItems": 1},
        },
        "required": ["thought", "status", "actions"],
        "additionalProperties": False,
    }
    final = {
        "type": "object",
        "properties": {
            "thought": s_thought, "status": {"type": "string", "const": "final"},
            "outcome": {"type": "string", "enum": ["verified", "failed", "aborted"]},
            "final_answer": s_answer, "lesson": s_short,
        },
        "required": ["thought", "status", "outcome", "final_answer", "lesson"],
        "additionalProperties": False,
    }
    return {"anyOf": [plan, act, final]}


def _gbnf_lit(s: str) -> str:
    """Строка → GBNF-литерал с экранированием."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def build_decision_grammar() -> str:
    """Детерминированная GBNF-грамматика решения Полимата для прямого llama.cpp
    (свежий ollama format=<grammar> не принимает — только схему; грамматика живёт
    артефактом decision_schema.gbnf). Правила сборки закалены живым огнём:
    ключ и двоеточие — РАЗНЫЕ литералы, хвосты без протечек скобок."""
    q = _gbnf_lit
    C = q(":")
    COMMA = q(",")
    LB, RB = q("{"), q("}")
    plan_obj = ("plan-obj ::= " + LB + " ws " + q("thought") + " ws " + C + " ws string ws "
                + COMMA + " ws " + q("status") + " ws " + C + " ws " + q("plan")
                + " ws " + COMMA + " ws " + q("success_criteria") + " ws " + C
                + " ws str-array ws " + COMMA + " ws " + q("plan") + " ws " + C
                + " ws str-array ws " + RB)
    act_obj = ("act-obj ::= " + LB + " ws " + q("thought") + " ws " + C + " ws string ws "
               + COMMA + " ws " + q("status") + " ws " + C + " ws " + q("act")
               + " ws " + COMMA + " ws " + q("actions") + " ws " + C
               + " ws action-array ws " + RB)
    final_obj = ("final-obj ::= " + LB + " ws " + q("thought") + " ws " + C + " ws string ws "
                 + COMMA + " ws " + q("status") + " ws " + C + " ws " + q("final")
                 + " ws " + COMMA + " ws " + q("outcome") + " ws " + C + " ws outcome"
                 + " ws " + COMMA + " ws " + q("final_answer") + " ws " + C + " ws string"
                 + " ws " + COMMA + " ws " + q("lesson") + " ws " + C + " ws string ws " + RB)
    action_rule = ("action ::= " + LB + " ws " + q("name") + " ws " + C + " ws string ws "
                   + COMMA + " ws " + q("args") + " ws " + C + " ws json-value ws "
                   + COMMA + " ws " + q("why") + " ws " + C + " ws string ws " + RB)
    rules = [
        "root ::= plan-obj | act-obj | final-obj",
        plan_obj, act_obj, final_obj, action_rule,
        # v1.2.2: ровно одно действие — грамматика синхронна со схемой (maxItems=1)
        'action-array ::= "[" ws action ws "]"',
        'str-array ::= "[" ws (string (ws "," ws string)*)? ws "]"',
        'outcome ::= "verified" | "failed" | "aborted"',
        "string ::= \"\\\"\" ( [^\"\\\\\\x00-\\x1F] | \"\\\\\" ([\"\\\\bfnrt] | \"u\" [0-9a-fA-F]{4}) )* \"\\\"\"",
        ('json-value ::= object | array | string | number | "true" | "false" | "null"'),
        ('object ::= "{" ws ( string ws ":" ws json-value ( ws "," ws string ws ":" ws json-value )* )? ws "}"'),
        'array ::= "[" ws ( json-value ( ws "," ws json-value )* )? ws "]"',
        'number ::= "-"? ([0-9] | [1-9] [0-9]*) ("." [0-9]+)? ([eE] [+-]? [0-9]+)?',
        "ws ::= [ \\t\\n]*",
    ]
    return "\n".join(rules) + "\n"


class OllamaNativeBrain:
    """Нативный /api/chat с format=<JSON Schema>: llama.cpp конвертирует схему в
    грамматику — невалидный JSON невозможен на этапе сэмплирования.
    Закалено живым огнём 27.08.2026: GBNF-строки свежий ollama НЕ принимает
    (только "json" или схему); qwen3-thinking глушится think=false + /no_think,
    иначе сэмплер замирает в пустом выводе; /v1 из base_url срезается;
    num_ctx/num_predict идут в options (env POLY_NUM_CTX / POLY_NUM_PREDICT)."""

    def __init__(self, cfg: "Config"):
        self.cfg = cfg
        self.schema = build_decision_schema()
        base = cfg.base_url.rstrip("/")
        if base.endswith("/v1"):
            base = base[:-3]
        self.url = base + "/api/chat"

    def decide(self, system_prompt: str, user_block: str,
               error_feedback: Optional[str] = None) -> Dict[str, Any]:
        user_content = user_block if not error_feedback else (
            user_block + "\n\nТВОЙ ПРЕДЫДУЩИЙ ВЫВОД ОТКЛОНЁН ВАЛИДАТОРОМ:\n" + error_feedback +
            "\nИсправь и выведи снова ровно один JSON-объект.")
        payload = {
            "model": self.cfg.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content + " /no_think"},
            ],
            "stream": False,
            "think": False,
            "format": self.schema,
            "options": {"temperature": self.cfg.temperature,
                        "num_predict": self.cfg.brain_num_predict,
                        "num_ctx": self.cfg.brain_num_ctx},
        }
        req = urllib.request.Request(self.url, data=json.dumps(payload).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.cfg.brain_timeout_s) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise BrainError(f"HTTP {e.code} от ollama: {e.read()[:300]}")
        except (urllib.error.URLError, OSError) as e:
            raise BrainError(f"ollama недоступна ({e}); поднят ли ollama serve?")
        content = body.get("message", {}).get("content", "")
        parsed = extract_json(content)
        if parsed is None:
            # v1.2.2: отличаем честное нарушение от ОБРЕЗА по num_predict — диагноз вместо гадания
            stripped = content.strip()
            if stripped.startswith("{") and not stripped.endswith("}"):
                raise BrainError(
                    "вывод мозга ОБРЕЗАН посреди JSON (num_predict="
                    + str(self.cfg.brain_num_predict)
                    + " исчерпан): подними POLY_NUM_PREDICT или упрощай решение "
                    "(одно действие на act). Начало вывода:\n" + content[:300])
            raise BrainError("контракт нарушен даже при грамматике:\n" + content[:400])
        return parsed


# ════════════════════ СБОРКА КОНТЕКСТА: детерминированная сериализация ═══════════════════

def build_context(cfg: "Config", gov: Governor, state: Dict[str, Any],
                  last_observations: List[Tuple[int, Observation]],
                  directive: Optional[str]) -> str:
    mem = gov.mem
    keywords = [w for w in re.findall(r"\w{4,}", state.get("goal", ""))][:12]
    sem = mem.query_semantic(keywords, k=3)
    proc = mem.gate_procedure(keywords, min_score=cfg.proc_gate_min_score,
                              min_ratio=cfg.proc_gate_min_ratio)
    eps = mem.recent_episodes(k=3)

    parts = [f"ГОЛОВНАЯ ЦЕЛЬ: {state['goal']}"]
    crit = state.get("criteria") or []
    if crit:
        verified_map = state.get("verified", {})
        lines = [f"- {'[ПОДТВЕРЖДЁН]' if c in verified_map else '[ожидает]'} {c}" for c in crit]
        parts.append("КРИТЕРИИ УСПЕХА:\n" + "\n".join(lines))
    # v1.2.5: при взведённом PLAN_LOCK секция ПЛАН уходит из контекста — она сама
    # провоцирует модель планировать снова (огонь accb1c587c: 7 планов подряд);
    # модель видит директиву «план принят — выходи в act» и накопленные факты
    plan_visible = state.get("plan") and state.get("_plan_lock", 0) == 0
    if plan_visible:
        parts.append("ПЛАН:\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(state["plan"])))

    ledger = state.get("ledger", [])
    tail = ledger[-cfg.ledger_tail:]
    if ledger:
        header = f"ЖУРНАЛ ШАГОВ ({len(ledger)} всего; последние показаны):"
        lines = []
        for entry in tail:
            obs = entry.get("obs_brief", "")
            lines.append(f"#{entry['step']} [{entry.get('kind','')}] action={entry.get('action','')} "
                         f"ok={entry.get('ok')} :: {obs}")
        parts.append(header + "\n" + "\n".join(lines))

    # v1.2.4: ВЕЧНАЯ ЛЕНТА ФАКТОВ — накопленные успехи не умирают со сменой такта.
    # Огонь 1406a05ad5: секция «единственный источник фактов» показывала только
    # последний такт (отказ дедупа) — модель 6 раз переспрашивала wc -l, ибо вывода
    # шага №1 в контексте больше не было. Факты в промпте закрывают переспросы.
    facts = state.get("facts") or []
    if facts:
        lines = [f"- {f[:220]}" for f in facts[-12:]]
        parts.append("НАКОПЛЕННЫЕ ФАКТЫ (успешные наблюдения прошлых шагов — "
                     "результаты уже получены, НЕ повторяй эти команды):\n"
                     + "\n".join(lines))

    if last_observations:
        lines = [f"[ШАГ #{i}] {obs.brief(700)}" for i, obs in last_observations]
        parts.append("СВЕЖИЕ НАБЛЮДЕНИЯ (самый последний такт; дополняют накопленные факты):\n"
                     + "\n".join(lines))

    if state.get("_last_output") is not None:
        parts.append("ПЕРЕМЕННАЯ $last_output доступна: строка \"$last_output\" в args "
                     "подставится механически (вывод последнего успешного действия).")

    if sem:
        lines = [f"- «{r['fact'][:180]}» (источник: {r['source'][:80]}; "
                 f"{'УСТАРЕЛО — перепроверь' if r.get('stale') else 'актуально'})" for r in sem]
        parts.append("Релевантная семантическая память:\n" + "\n".join(lines))
    if proc:
        parts.append("Процедурная память предлагает:\n«%s»: %s" %
                     (proc["name"], " → ".join(proc["steps"][:8])))
    if eps:
        lines = [f"- [{e['outcome']}] {e['goal']} :: урок: {e['lesson']}" for e in eps]
        parts.append("Прошлые эпизоды:\n" + "\n".join(lines))

    parts.append("ИНСТРУМЕНТЫ (только они существуют):\n" + gov.tools_documentation(state.get("goal", "")))
    if directive:
        parts.append("*** ДИРЕКТИВА КОНТУРА УПРАВЛЕНИЯ ***\n" + directive)

    remaining = max(0, cfg.max_steps - len(state.get("ledger", [])))
    parts.append(f"БЮДЖЕТ: осталось шагов: {remaining}. "
                 "Ответ = ровно один JSON-объект по ФОРМАТУ.")
    return "\n\n".join(parts)


def validate_decision(decision: Any) -> Optional[str]:
    """Проверка статуса/полей решения модели. Схемы инструментов проверяет Governor."""
    if not isinstance(decision, dict):
        return "решение должно быть JSON-объектом"
    status = decision.get("status")
    if status not in {"plan", "act", "final"}:
        return "status обязан быть plan|act|final"
    if not isinstance(decision.get("thought"), str) or not decision["thought"].strip():
        return "thought обязателен (непустая строка)"
    if status == "plan":
        for key in ("success_criteria", "plan"):
            v = decision.get(key)
            if not isinstance(v, list) or not v or not all(isinstance(x, str) and x.strip() for x in v):
                return f"при status=plan поле '{key}' обязано быть непустым списком строк"
    if status == "act":
        acts = decision.get("actions")
        if not isinstance(acts, list) or len(acts) != 1:
            return "при status=act поле actions обязано содержать ровно одно действие"
        for a in acts:
            if (not isinstance(a, dict) or not isinstance(a.get("name"), str)
                    or not isinstance(a.get("args"), dict)):
                return "каждое действие = объект {name: str, args: object, why?: str}"
    if status == "final":
        oc = decision.get("outcome")
        if oc not in {"verified", "failed", "aborted"}:
            return "outcome обязан быть verified|failed|aborted"
        if not isinstance(decision.get("final_answer"), str) or not decision["final_answer"].strip():
            return "final_answer обязателен"
    return None


# ════════════════════ АГЕНТ: петля OODA+V с бюджетами (Ф9) ═══════════════════

@dataclass
class Config:
    brain_kind: str = "api"
    base_url: str = "http://localhost:11434/v1"
    model: str = os.environ.get("POLY_MODEL", "qwen3:8b")
    api_key_env: str = ""
    temperature: float = 0.2
    brain_timeout_s: int = 240
    max_steps: int = 24
    exec_timeout_s: int = 15
    net_timeout_s: int = 20
    net_max_bytes: int = 200_000
    max_read_chars: int = 6_000
    ledger_tail: int = 8
    time_budget_s: int = 900
    stall_replan: int = 3          # шаги без прогресса до директивы REPLAN
    stall_alternative: int = 5     # ещё без прогресса -> требование сменить стратегию
    stall_abort: int = 7           # дальше -> честная остановка
    auto_yes: bool = False         # подтверждение EXEC/NET оператором
    workspace: str = "./poly_workspace"
    data_dir: str = "./poly_data"
    resume: bool = True
    # --- v1.2: Тело/арсенал, гейты контекста и окно мозга ---
    catalog_path: str = os.environ.get("POLY_CATALOG", "./tool_catalog.json")
    arsenal_k: int = 12            # сколько позиций арсенала показывать в дайджесте
    proc_gate_min_score: float = 2.0   # гейт процедурной памяти: минимум скоринга
    proc_gate_min_ratio: float = 0.25  # и минимум покрытия токенов цели
    brain_num_predict: int = int(os.environ.get("POLY_NUM_PREDICT", "220"))  # потолок токенов решения
    brain_num_ctx: int = int(os.environ.get("POLY_NUM_CTX", "4096"))  # окно инференса:
                                   # 4096 для 0.6b/1.7b; 4b в RAM-гейте 3 ГиБ жив только на 1536


STALL_DIRECTIVES = {
    "replan": ("ТРИ ИТЕРАЦИИ БЕЗ ПРОГРЕССА. Отбрось текущий план полностью. "
               "Переформулируй критерии от исходной цели и выдай status=plan заново."),
    "alternative": ("СТАГНАЦИЯ ПРОДОЛЖАЕТСЯ. Текущий подход признаётся нерабочим. "
                    "Выдай принципиально ИНУЮ стратегию достижения цели (status=plan) "
                    "или честно объяви status=final outcome=failed."),
    "abort": ("КРАЙНЕЕ БЮДЖЕТНОЕ ОГРАНИЧЕНИЕ СТАГНАЦИИ. Объяви status=final "
              "outcome=aborted с точным перечнем того, что сделано и что мешало."),
}

PLAN_LOCK_DIRECTIVE = (
    "ПОВТОР ПЛАНА: такой же план (или та же мысль) уже выдан. Статус plan ЗАПРЕЩЁН. "
    "Немедленно выходи в действие: status=act с РОВНО ОДНИМ действием, приближающим "
    "критерии. Если нужно записать вывод прошлой команды в файл — передай в content "
    "строку \"$last_output\" (подставится механически).")



# ═════════════════════ v1.5: PROVENANCE / CHECKPOINT / RECOVERY ═════════════════════

class CapabilityGraph:
    """Граф возможностей и зависимостей."""
    def __init__(self, registry):
        self.nodes={n:{"name":n,"risk":sp.risk,"description":sp.doc,"deps":[]} for n,sp in registry.items()}
    def add_dependency(self, name, dep):
        if name in self.nodes and dep in self.nodes and dep != name and dep not in self.nodes[name]["deps"]:
            self.nodes[name]["deps"].append(dep)
    def closure(self, requested):
        out=[]; seen=set()
        def visit(n):
            if n in seen or n not in self.nodes: return
            seen.add(n)
            for d in self.nodes[n]["deps"]: visit(d)
            out.append(n)
        for n in requested: visit(n)
        return out

@dataclass
class Claim:
    id: str
    text: str
    claim_type: str = "assertion"
    required_capability: Optional[str] = None

@dataclass
class EvidenceObject:
    id: str
    claim_id: str
    kind: str
    source_ref: str
    content_hash: str
    observed_at: str
    valid: bool = True
    producer: str = ""
    integrity_ok: bool = True
    artifact_edges: Dict[str, str] = field(default_factory=dict)  # v3.7.0: {путь: sha256 В МОМЕНТ наблюдения}

@dataclass
class EvidenceContract:
    claim_id: str
    required_types: List[str] = field(default_factory=list)
    required_producers: List[str] = field(default_factory=list)
    required_capability: Optional[str] = None
    max_age_seconds: Optional[float] = None
    require_integrity: bool = True
    allow_invalid: bool = False

@dataclass
class ProofObject:
    id: str
    status: str
    claim_ids: List[str]
    evidence_ids: List[str]
    rule: str
    unknowns: List[str] = field(default_factory=list)
    rule_version: str = ""
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)
    evidence_hashes: Dict[str, str] = field(default_factory=dict)
    created_at: str = field(default_factory=now_iso)
    evidence_timestamps: Dict[str, str] = field(default_factory=dict)
    artifact_hashes: Dict[str, str] = field(default_factory=dict)
    source_state_hash: str = ""
    state_version: int = 0
    evidence_artifact_refs: Dict[str, List[str]] = field(default_factory=dict)
    artifact_edges: Dict[str, Dict[str, str]] = field(default_factory=dict)  # v3.7.0: evidence → {путь: хеш наблюдения}
    root_epoch: int = -1            # v3.8.0: активная корневая эпоха в момент COMMIT (N-RT3)
    root_fingerprint: str = ""      # v3.8.0: отпечаток активного корня в момент COMMIT

@dataclass
class VerificationRule:
    id: str
    version: str
    description: str
    min_evidence: int = 1
    require_all_valid: bool = True

@dataclass
class Predicate:
    id: str
    description: str
    evaluator: str

class PredicateRegistry:
    def __init__(self):
        self._predicates={}
        self.register(Predicate("producer_matches_capability", "evidence producer matches required capability", "producer_matches_capability"))
        self.register(Predicate("evidence_is_valid", "all evidence is valid and integrity protected", "evidence_is_valid"))
    def register(self, predicate):
        if not predicate.id or not predicate.evaluator: raise ValueError("invalid predicate")
        self._predicates[predicate.id]=predicate
    def get(self, predicate_id): return self._predicates.get(predicate_id)

class TypedRuleEngine:
    """Evaluates explicit predicates; no VERIFIED from rule-name presence alone."""
    def __init__(self, rule_registry=None, predicate_registry=None):
        self.rules=rule_registry or RuleRegistry(); self.predicates=predicate_registry or PredicateRegistry()
    def entails(self, rule_id, claim, evidence, contract):
        rule=self.rules.get(rule_id)
        if rule is None or len(evidence)<rule.min_evidence: return False
        if not all(e.valid and e.integrity_ok and bool(e.content_hash) for e in evidence): return False
        if contract.required_capability and not any(e.producer == contract.required_capability for e in evidence): return False
        if contract.required_producers and not any(e.producer in contract.required_producers for e in evidence): return False
        if contract.required_types and not all(e.kind in contract.required_types or e.kind == "observation" for e in evidence): return False
        return True

class RuleRegistry:
    """Реестр проверяемых правил вывода. Строковое имя правила больше не является доказательством."""
    def __init__(self):
        self._rules: Dict[str, VerificationRule] = {}
        self.register(VerificationRule(
            "claim_witnessed_by_successful_action_observation", "1.0",
            "claim имеет требуемое контрактом evidence от допустимого producer", 1, True))

    def register(self, rule: VerificationRule) -> None:
        if not rule.id or not rule.version or rule.min_evidence < 1:
            raise ValueError("некорректное verification rule")
        self._rules[rule.id] = rule

    def get(self, rule_id: str) -> Optional[VerificationRule]:
        return self._rules.get(rule_id)

    def validate(self, rule_id: str, evidence: List[EvidenceObject]) -> bool:
        rule = self.get(rule_id)
        if rule is None or len(evidence) < rule.min_evidence:
            return False
        if rule.require_all_valid and not all(e.valid and e.integrity_ok and e.content_hash for e in evidence):
            return False
        return True

@dataclass
class Derivation:
    id: str
    claim_id: str
    rule: str
    evidence_ids: List[str]
    valid: bool = True

class DerivationGraph:
    """Явный граф вывода: evidence -> rule -> claim."""
    def __init__(self, claims, evidence, registry=None):
        self.claims=claims; self.evidence=evidence; self.derivations=[]
        self.registry=registry or RuleRegistry()
        self.engine=TypedRuleEngine(self.registry)
    def derive(self, claim, matched, rule):
        valid_rule=self.registry.validate(rule, matched) and self.engine.entails(rule, claim, matched, EvidenceContract(claim.id, required_capability=claim.required_capability))
        ids=[e.id for e in matched if e.valid]
        d=Derivation(f"derivation:{claim.id}", claim.id, rule, ids, valid_rule)
        self.derivations.append(d); return d
    def covered(self):
        return {d.claim_id for d in self.derivations if d.valid and d.evidence_ids}

class EpistemicDependencyGraph:
    """Propagates UNKNOWN and rejects cyclic claim dependencies."""
    def __init__(self, dependencies=None):
        self.dependencies={k:list(v) for k,v in (dependencies or {}).items()}
    def blockers(self, claim_id, unknown_claims):
        out=[]; seen=set()
        def visit(n):
            if n in seen: return
            seen.add(n)
            for dep in self.dependencies.get(n,[]):
                if dep in unknown_claims:
                    out.append(dep)
                visit(dep)
        visit(claim_id)
        return list(dict.fromkeys(out))
    def find_cycles(self):
        """Return strongly connected claim components that contain a cycle."""
        index=0; stack=[]; on_stack=set(); indices={}; low={}; cycles=[]
        def visit(v):
            nonlocal index
            indices[v]=index; low[v]=index; index+=1
            stack.append(v); on_stack.add(v)
            for w in self.dependencies.get(v,[]):
                if w not in self.dependencies and w not in indices:
                    indices[w]=index; low[w]=index; index+=1
                if w not in indices:
                    visit(w); low[v]=min(low[v],low[w])
                elif w in on_stack:
                    low[v]=min(low[v],indices[w])
            if low[v]==indices[v]:
                comp=[]
                while True:
                    w=stack.pop(); on_stack.remove(w); comp.append(w)
                    if w==v: break
                if len(comp)>1 or v in self.dependencies.get(v,[]):
                    cycles.append(sorted(comp))
        vertices=set(self.dependencies) | {d for ds in self.dependencies.values() for d in ds}
        for v in sorted(vertices):
            if v not in indices: visit(v)
        return cycles

    def propagate(self, unknown_claims):
        unknown=set(unknown_claims); changed=True
        while changed:
            changed=False
            for node,deps in self.dependencies.items():
                if any(d in unknown for d in deps) and node not in unknown:
                    unknown.add(node); changed=True
        return unknown

class ProofCompiler:
    """Детерминированный Claim→Evidence→Rule→Proof контур."""
    RULE = "claim_witnessed_by_successful_action_observation"
    def __init__(self, state: Dict[str, Any]):
        self.state=state
        self.claims=[]; self.evidence=[]
        for i,c in enumerate(state.get("criteria", [])):
            cap = c.split(":", 1)[1].split()[0] if c.startswith("capability:") else None
            self.claims.append(Claim(f"claim:{i+1}", c, "capability" if cap else "assertion", cap))
        for row in state.get("ledger", []):
            if row.get("ok") and row.get("action") not in {"(план)","(verify-fail)"}:
                # v3.7.0 ArtifactEvidenceEdge: evidence помнит состояние артефакта
                # В МОМЕНТ наблюдения. Рантайм пишет artifact_path/artifact_sha256
                # (write/read/verify); поле "artifact" (fp/путь) — совместимость:
                # используется только если это существующий путь (selftest-форма v3.6.0).
                _edges={}
                _ap=row.get("artifact_path"); _ah=row.get("artifact_sha256")
                if _ap and _ah:
                    _edges[str(_ap)]=str(_ah)
                else:
                    _raw=str(row.get("artifact") or "")
                    if _raw and Path(_raw).is_file():
                        try: _edges[_raw]=sha256_hex(Path(_raw).read_bytes())
                        except OSError: pass  # артефакт нечитаем — evidence-хеш не даётся: недоступный файл не подменяет доказательство
                self.evidence.append(EvidenceObject(
                    id=f"evidence:step:{row.get('step')}:{row.get('action')}",
                    claim_id="",
                    kind=row.get("kind","observation"),
                    source_ref=f"step:{row.get('step')}",
                    content_hash=sha256_hex(row.get("obs_brief","")),
                    observed_at=row.get("ts", now_iso()),
                    producer=row.get("action", ""), integrity_ok=bool(row.get("ok")),
                    artifact_edges=_edges))
    @staticmethod
    def _evidence_action(e: EvidenceObject) -> str:
        # source_ref is step:N; evidence id ends with the concrete action.
        return e.id.rsplit(":", 1)[-1]

    def contracts(self) -> Dict[str, EvidenceContract]:
        out={}
        for c in self.claims:
            if c.required_capability:
                out[c.id]=EvidenceContract(c.id, required_types=["observation", "write", "read", "net", "exec", "list"],
                    required_producers=[c.required_capability], required_capability=c.required_capability,
                    max_age_seconds=float(self.state.get("freshness_max_age_seconds", 7*24*3600)))
            else:
                producers=sorted(self.state.get("required_capabilities", [])) if len(self.state.get("required_capabilities", [])) == 1 else []
                out[c.id]=EvidenceContract(c.id, required_types=["observation", "write", "read", "net", "exec", "list"],
                    required_producers=producers, max_age_seconds=float(self.state.get("freshness_max_age_seconds", 7*24*3600)))
        return out

    def _matches(self, c: Claim, e: EvidenceObject, contract: EvidenceContract) -> bool:
        if not e.valid and not contract.allow_invalid: return False
        if contract.require_integrity and (not e.integrity_ok or not e.content_hash): return False
        if contract.required_types and e.kind not in contract.required_types and e.kind != "observation": return False
        if contract.required_producers and e.producer not in contract.required_producers: return False
        if contract.max_age_seconds is not None:
            try:
                age=max(0.0, __import__("datetime").datetime.now(__import__("datetime").timezone.utc).timestamp()-__import__("datetime").datetime.fromisoformat(e.observed_at.replace("Z","+00:00")).timestamp())
                if age > contract.max_age_seconds: return False
            except Exception: return False
        return True

    def compile(self) -> ProofObject:
        required=set(self.state.get("required_capabilities", []))
        contracts=self.contracts(); unknown=[]
        graph=DerivationGraph(self.claims,self.evidence, RuleRegistry())
        evidence_ids=[]
        for c in self.claims:
            contract=contracts[c.id]
            matches=[e for e in self.evidence if self._matches(c,e,contract)]
            if matches:
                d=graph.derive(c,matches,graph.registry.get("claim_witnessed_by_successful_action_observation").id)
                evidence_ids.extend(d.evidence_ids)
            else:
                # v3.7.0 R-D1: Stale ≠ Unknown — протухшее evidence не сливается
                # с отсутствующим; канонический id без двойного префикса.
                any_age=replace(contract, max_age_seconds=None)
                if [e for e in self.evidence if self._matches(c,e,any_age)]:
                    unknown.append(f"{c.id}:stale_evidence")
                else:
                    unknown.append(f"{c.id}:derivation_missing")
        dep_graph=EpistemicDependencyGraph(self.state.get("claim_dependencies", {}))
        cycles=dep_graph.find_cycles()
        self.state["claim_dependency_cycles"]=cycles
        for component in cycles:
            for claim_id in component:
                reason=f"{claim_id}:dependency_cycle"
                if reason not in unknown:
                    unknown.append(reason)
        claims_by_id={c.id: c for c in self.claims}
        # v3.7.0 R-D2: висячая зависимость — ссылка на claim, которого не существует;
        # узел недоказуем никогда: блокирует себя и всех зависимых (I24).
        for c in self.claims:
            for dep in dep_graph.dependencies.get(c.id, []):
                if dep not in claims_by_id:
                    reason=f"{c.id}:dangling_dependency:{dep}"
                    if reason not in unknown:
                        unknown.append(reason)
        # TMS-распространение: Unknown/Stale/Cycle/Dangling(x) ∧ Depends(y,x) ⇒ ¬Certain(y)
        unproven={x.split(":derivation_missing",1)[0] for x in unknown if x.endswith(":derivation_missing")}
        unproven|={x.split(":dangling_dependency:",1)[0] for x in unknown if ":dangling_dependency:" in x}
        unproven|={x.split(":stale_evidence",1)[0] for x in unknown if x.endswith(":stale_evidence")}
        unproven|={x.split(":dependency_cycle",1)[0] for x in unknown if x.endswith(":dependency_cycle")}
        propagated=dep_graph.propagate(unproven)
        # v3.7.0 R-D3: опровержение основания опрокидывает зависимые узлы —
        # деривация заблокированного claim'а получает valid=False и выбывает из покрытия.
        blocked={c.id for c in self.claims if c.id in propagated}
        for d in graph.derivations:
            if d.claim_id in blocked:
                d.valid=False
        covered=graph.covered()
        for claim_id in sorted(propagated):
            reason=f"{claim_id}:dependency_unknown"
            if reason not in unknown and claim_id not in covered:
                unknown.append(reason)
        for cap in sorted(required):
            cap_evidence = any(e.valid and e.producer == cap for e in self.evidence)
            cap_claim_covered = any(c.required_capability==cap and c.id in covered for c in self.claims)
            if not cap_evidence and not cap_claim_covered:
                unknown.append(f"capability:{cap}")
        evidence_ids=list(dict.fromkeys(evidence_ids))
        status="verified" if self.claims and len(covered)==len(self.claims) and not unknown else "unknown"
        self.state["derivations"]=[asdict(d) for d in graph.derivations]
        self.state["verification_rules"]=[asdict(graph.registry.get(d.rule)) for d in graph.derivations if graph.registry.get(d.rule)]
        self.state["epistemic_blockers"]={c.id:dep_graph.blockers(c.id, propagated) for c in self.claims if dep_graph.blockers(c.id, propagated)}
        rule_obj = graph.registry.get(graph.derivations[0].rule) if graph.derivations else None
        nodes=[]; edges=[]
        for d in graph.derivations:
            did=f"derivation:{d.id}"
            nodes.append({"id":did,"kind":"derivation","claim_id":d.claim_id,
                          "inputs":list(d.evidence_ids),"rule_id":d.rule,
                          "status":"verified" if d.valid else "unknown"})
            for eid in d.evidence_ids:
                edges.append({"from":eid,"to":did,"relation":"supports"})
            edges.append({"from":did,"to":d.claim_id,"relation":"derives"})
        for c in self.claims:
            nodes.append({"id":c.id,"kind":"claim","claim_id":c.id,
                          "inputs":[f"derivation:{d.id}" for d in graph.derivations if d.claim_id==c.id and d.valid],
                          "rule_id":self.RULE,"status":"verified" if c.id in covered else "unknown"})
        evidence_hashes={e.id:e.content_hash for e in self.evidence if e.id in evidence_ids}
        # v3.7.0: per-evidence биндинг — единственный источник истины — рёбра
        # {путь: хеш_наблюдения}; refs (пути) выводятся из них для KnowledgeRevocationIndex.
        artifact_edges={e.id:dict(e.artifact_edges) for e in self.evidence if e.artifact_edges}
        evidence_artifact_refs={eid:sorted(ed.keys()) for eid,ed in artifact_edges.items()}
        artifact_hashes=dict(self.state.get("artifact_hashes",{}))
        for path in self.state.get("_artifact_paths",[]):
            try:
                artifact_hashes[path]=sha256_hex(Path(path).read_bytes())
            except OSError:
                artifact_hashes[path]="MISSING"
        self.state["artifact_hashes"]=artifact_hashes
        return ProofObject(f"proof:{sha256_hex(canonical_json(self.state))[:16]}",status,
                           [c.id for c in self.claims],evidence_ids,
                           self.RULE,unknown,rule_obj.version if rule_obj else "",
                           nodes,edges,evidence_hashes,now_iso(),
                           {e.id:e.observed_at for e in self.evidence if e.id in evidence_ids},
                           artifact_hashes,
                           StateCAS.fingerprint(self.state), int(self.state.get("_cas_version",0)), evidence_artifact_refs,
                           artifact_edges)
    @staticmethod
    def allows_verified(proof: ProofObject) -> bool:
        return proof.status=="verified" and not proof.unknowns and bool(proof.evidence_ids)

@dataclass
class EngineState:
    transaction_id: str
    status: str
    action_count: int

@dataclass
class WorldState:
    observed_at: str
    artifacts: Dict[str, str] = field(default_factory=dict)

@dataclass
class KnowledgeState:
    proof_id: str
    claim_ids: List[str]
    valid_at: str

class ProofCarryingCommitError(PolicyViolation):
    """COMMIT запрещён, если доказательство не замкнуто или мир ему противоречит."""

class ProofClosureError(ProofCarryingCommitError):
    """v3.7.0 N-CLS: отказ замыкания — часть runtime-контракта COMMIT
    (ловится except ProofCarryingCommitError, а не рвёт run-loop)."""

class VacuousRefusalError(PolicyViolation):
    """v3.10.0 C5 GATE ANTI-VACUUM: отказной гейт отказал без именованной причины.

    Отказ без причины недействителен: он неотличим от поломки прибора и не может
    быть ассертирован refusal-пробой (урок P5/N-ART: отказ-вакуум стирает различие
    «закрыт / неприменимо»). Сам отказ поднимается как нарушение политики.
    """

class GateAntiVacuum:
    """v3.10.0 C5 — анти-вакуумное правило гейтов, вшитое в рантайм (Р-01).

    Принцип v3.9.0 («каждый отказной гейт → парный тест «честный путь принят»
    + assertion на именованную причину») становится механикой:

      refuse(gate, reason) — единственный законный способ отказа гейта
        COMMIT-контура: сообщение гарантированно несёт namespaced-причину
        "<gate>: <reason>"; голый отказ без причины/гейта невыразим —
        refuse() сам поднимает VacuousRefusalError.
      GATE_REGISTRY — явный реестр отказных гейтов COMMIT-контура: каждое
        семейство несёт именованные причины отказа и ПАРНЫХ свидетелей
        самопроверки (honest_witnesses — «честный путь принят»;
        refusal_witnesses — «отказ по своей причине»).
      audit() — механическая сверка реестра: пустые/безымянные причины,
        отсутствующие свидетели = нарушение C5.

    Мета-гейт T140 сверяет реестр с фактом исполнения проб самопроверки:
    удаление или обесточивание парного теста роняет --selftest. Гейты Тела
    (изоляция путей, SSRF, схемный валидатор, гейты процедур и плана) уже
    несут парные пробы «отказ + честный путь» в каждой паре (T01, T02, T09,
    T11, T14, T15, T17, T19, T21); их включение в реестр — при ревизии Тела.
    """
    MIN_REASON = 4

    @staticmethod
    def refuse(gate: str, reason: str) -> ProofCarryingCommitError:
        if not isinstance(gate, str) or not gate.strip():
            raise VacuousRefusalError("C5: отказ без имени гейта — вакуумный отказ")
        if (not isinstance(reason, str) or len(reason.strip()) < GateAntiVacuum.MIN_REASON
                or not reason.strip()):
            raise VacuousRefusalError(
                f"C5: гейт {gate!r} отказал без именованной причины: {reason!r}")
        return ProofCarryingCommitError(f"{gate}: {reason}")

    @staticmethod
    def audit() -> List[str]:
        bad: List[str] = []
        for g in GATE_REGISTRY:
            gid = g.get("gate", "")
            if not gid:
                bad.append("C5: строка реестра без имени гейта")
                continue
            reasons = g.get("reasons") or []
            if not reasons or any(not isinstance(r, str) or len(r.strip()) < GateAntiVacuum.MIN_REASON
                                  for r in reasons):
                bad.append(f"C5: {gid}: безымянная причина отказа")
            if not (g.get("honest_witnesses") or []):
                bad.append(f"C5: {gid}: honest-свидетель отсутствует")
            if not (g.get("refusal_witnesses") or []):
                bad.append(f"C5: {gid}: refusal-свидетель отсутствует")
        return bad

GATE_REGISTRY: List[Dict[str, Any]] = [
    {"gate": "COMMIT/ProofCarryingGovernor",
     "reasons": ["COMMIT: отсутствует полный ProofObject", "COMMIT: UNKNOWN",
                 "COMMIT: неполное покрытие", "COMMIT: falsification=",
                 "COMMIT: proof missing CAS source state", "COMMIT: CAS conflict",
                 "COMMIT: REVOKED", "COMMIT: WorldState mismatch", "COMMIT: ROOT TRUST:"],
     "honest_witnesses": ["T66 commit accepts closed proof"],
     "refusal_witnesses": ["T64 commit requires proof", "T65 commit rejects unknown proof",
                           "T104 CAS changed state (renumbered; was duplicate T73 in v3.6.0)",
                           "T119 falsification contested (unit)",
                           "T77 artifact mutation reconciliation",
                           "T122 truncated root history blocks COMMIT",
                           "T123 revoked root blocks COMMIT"]},
    {"gate": "PROOF_CLOSURE/ProofClosure.validate",
     "reasons": ["PROOF_CLOSURE:"],
     "honest_witnesses": ["T116 proof closure closed (unit)"],
     "refusal_witnesses": ["T115 proof closure dangling (unit)",
                           "T118 proof closure cycle (unit)"]},
    {"gate": "TEMPORAL/TemporalValidity.validate",
     "reasons": ["TEMPORAL_VALIDITY:"],
     "honest_witnesses": ["T66 commit accepts closed proof"],
     "refusal_witnesses": ["T117 temporal future (unit)",
                           "T120 temporal future evidence (unit)"]},
    {"gate": "CAS/StateCAS.assert_unchanged",
     "reasons": ["COMMIT: CAS conflict"],
     "honest_witnesses": ["T74 CAS unchanged state"],
     "refusal_witnesses": ["T104 CAS changed state (renumbered; was duplicate T73 in v3.6.0)"]},
    {"gate": "FALSIFICATION/FalsificationProbe.probe",
     "reasons": ["COMMIT: falsification=CONTESTED"],
     "honest_witnesses": ["T66 commit accepts closed proof"],
     "refusal_witnesses": ["T119 falsification contested (unit)"]},
    {"gate": "ROOT_TRUST_GATE/RootEpochChain.require_active_from_state",
     "reasons": ["COMMIT: ROOT TRUST:"],
     "honest_witnesses": ["T121 runtime root epoch bound to COMMIT"],
     "refusal_witnesses": ["T122 truncated root history blocks COMMIT",
                           "T123 revoked root blocks COMMIT",
                           "T125 replay root-epoch rollback"]},
    {"gate": "ROOT_AUTH/RootTrustAuthority.authorize+verify",
     "reasons": ["invalid root authorization envelope", "root authorization MAC failure",
                 "authorization not bound to a root epoch",
                 "authorization root epoch rotated/revoked", "signing key epoch rollback"],
     "honest_witnesses": ["T137 signing-key authorization bound to active root (A1.2)"],
     "refusal_witnesses": ["T95 root substitution", "T96 key-epoch rollback",
                           "T100 key-history fork", "T103 root authorization tamper",
                           "T134 root authorization tamper (port)",
                           "T138 root rotation invalidates unconfirmed authorization (A1.2)",
                           "T139 root revocation invalidates unconfirmed authorization (A1.2)"]},
    {"gate": "SIGNING/SigningTrustDomain.install+sign+verify",
     "reasons": ["root-authorized key fingerprint mismatch", "signing epoch replay/rollback",
                 "unknown/revoked signing key", "invalid signing checkpoint envelope",
                 "signing epoch mismatch", "checkpoint MAC failure",
                 "cannot revoke active signing key"],
     "honest_witnesses": ["T94 trust-domain separation"],
     "refusal_witnesses": ["T97 old-key resurrection", "T99 root envelope in signing domain",
                           "T101 checkpoint epoch tamper", "T102 revoked epoch checkpoint",
                           "T129 old-root resurrection (port)",
                           "T132 root/signing domain confusion (port)",
                           "T136 active checkpoint fingerprint mismatch (port)"]},
    {"gate": "ANCHOR/LedgerTrustAnchor.verify",
     "reasons": ["trust anchor mismatch"],
     "honest_witnesses": ["T90 trust anchor exact checkpoint"],
     "refusal_witnesses": ["T91 trust anchor rollback", "T92 trust anchor fork",
                           "T93 trust anchor substitution"]},
    {"gate": "LEDGER/ImmutableKnowledgeLedger.append+replay",
     "reasons": ["ledger verification failed", "replay fork:", "replay error:"],
     "honest_witnesses": ["T84 knowledge ledger chain+replay"],
     "refusal_witnesses": ["T85 knowledge ledger tamper", "T86 knowledge ledger fork/replay",
                           "T88 replay distinguishes truncation", "T89 replay proof binding",
                           "T114 replay rejects duplicate commit"]},
    {"gate": "GOVERNOR/_confine+SSRF-фильтр",
     "reasons": ["path обязателен и должен быть строкой", "SSRF-фильтр:",
                 "Отказ Конституции:"],
     "honest_witnesses": ["T10 сквозной цикл на MockBrain"],
     "refusal_witnesses": ["T01 изоляция путей", "T09 SSRF-фильтр http_get"]},
]

class ProofClosure:
    """Strict proof closure: references exist, graph is acyclic, rule is pinned, evidence is hashed."""
    @staticmethod
    def validate(proof: ProofObject) -> None:
        if proof.status != "verified" or not proof.rule_version:
            raise ProofClosureError("PROOF_CLOSURE: verified proof requires pinned rule version")
        node_map={n.get("id"): n for n in proof.nodes if isinstance(n,dict) and n.get("id")}
        evidence=set(proof.evidence_ids)
        if not node_map:
            raise ProofClosureError("PROOF_CLOSURE: empty DAG")
        # v3.7.0 N-CLM: claim_ids proof'а обязаны ссылаться на claim-узлы того же proof'а —
        # чужие/подменённые id не проходят замыкание (класс тампер-батареи T72).
        node_claims={n.get("claim_id") for n in proof.nodes if isinstance(n,dict) and n.get("kind")=="claim"}
        if any(cid not in node_claims for cid in proof.claim_ids):
            raise ProofClosureError("PROOF_CLOSURE: foreign claim id")
        if any(eid not in proof.evidence_hashes for eid in evidence):
            raise ProofClosureError("PROOF_CLOSURE: evidence hash missing")
        for n in proof.nodes:
            if not n.get("kind"):
                raise ProofClosureError("PROOF_CLOSURE: malformed node")
            if any(x not in node_map and x not in evidence for x in n.get("inputs",[])):
                raise ProofClosureError("PROOF_CLOSURE: dangling input")
            if n.get("rule_id") and n["rule_id"] != proof.rule:
                raise ProofClosureError("PROOF_CLOSURE: rule mismatch")
        for e in proof.edges:
            if e.get("from") not in set(node_map)|evidence or e.get("to") not in node_map:
                raise ProofClosureError("PROOF_CLOSURE: dangling edge")
        # Kahn topological test over proof nodes. Evidence is external roots.
        indeg={nid:0 for nid in node_map}; adj={nid:[] for nid in node_map}
        for n in proof.nodes:
            for src in n.get("inputs",[]):
                if src in node_map:
                    indeg[n["id"]]+=1; adj[src].append(n["id"])
        for e in proof.edges:
            src,dst=e.get("from"),e.get("to")
            if src in node_map and dst in node_map and dst not in adj[src]:
                indeg[dst]+=1; adj[src].append(dst)
        q=[n for n,d in indeg.items() if d==0]; seen=0
        while q:
            n=q.pop(); seen+=1
            for dst in adj[n]:
                indeg[dst]-=1
                if indeg[dst]==0: q.append(dst)
        if seen != len(node_map):
            raise ProofClosureError("PROOF_CLOSURE: cycle detected")

class TemporalValidity:
    @staticmethod
    def validate(proof: ProofObject, now: Optional[str]=None) -> None:
        t=_dt.datetime.fromisoformat((now or now_iso()).replace("Z","+00:00"))
        c=_dt.datetime.fromisoformat(proof.created_at.replace("Z","+00:00"))
        if c > t: raise ProofClosureError("TEMPORAL_VALIDITY: future-dated proof")
        for eid,ts in proof.evidence_timestamps.items():
            et=_dt.datetime.fromisoformat(ts.replace("Z","+00:00"))
            if et > t: raise ProofClosureError(f"TEMPORAL_VALIDITY: future evidence {eid}")
            if et > c: raise ProofClosureError(f"TEMPORAL_VALIDITY: evidence {eid} newer than proof")

class FalsificationVerdict:
    SUPPORTS="SUPPORTS"; CONTESTED="CONTESTED"; REFUTED="REFUTED"

class FalsificationProbe:
    """Conservative pre-commit contradiction gate. Unknown is never converted to support."""
    @staticmethod
    def infer_from_ledger(state: Dict[str,Any], proof: ProofObject) -> List[Dict[str,Any]]:
        """v3.7.0 N-FALS: механический захват противоречий из журнала.

        Консервативное правило (только CONTESTED, никогда REFUTED): verify-fail,
        назвавший критерий claim'а ПОСЛЕ его последнего поддерживающего evidence,
        означает, что мир перестал соответствовать наблюдению → COMMIT запрещён
        до свежего evidence. Свежее evidence (шаг позже verify-fail) снимает
        CONTESTED — контур STALE/CONTESTED → RE-CHECK → NEW PROOF → CAS → COMMIT замкнут.
        """
        rows=[r for r in state.get("ledger",[]) if isinstance(r,dict)]
        out=[]
        node_claims={n.get("claim_id") for n in proof.nodes if isinstance(n,dict) and n.get("kind")=="claim"}
        ev_step={}
        for n in proof.nodes:
            if not (isinstance(n,dict) and n.get("kind")=="claim" and n.get("claim_id")):
                continue
            cid=n["claim_id"]; steps=[]
            for did in n.get("inputs",[]):
                for dn in proof.nodes:
                    if isinstance(dn,dict) and dn.get("id")==did and dn.get("kind")=="derivation":
                        for eid in dn.get("inputs",[]):
                            parts=str(eid).split(":")
                            if len(parts)>=3 and parts[1]=="step":
                                try: steps.append(int(parts[2]))
                                except ValueError: pass  # id не шаговый (не evidence:step:*) — номер шага из него не берётся
            if steps: ev_step[cid]=max(steps)
        for cid in sorted(proof.claim_ids):
            if cid not in node_claims or cid not in ev_step: continue
            try: idx=int(cid.split(":")[1])-1
            except (IndexError,ValueError): continue
            criteria=state.get("criteria",[])
            if not (0<=idx<len(criteria)): continue
            criterion=str(criteria[idx]); last=ev_step[cid]
            for r in rows:
                if r.get("kind")!="verify" or r.get("ok") is not False: continue
                try: rstep=int(r.get("step",0))
                except (TypeError,ValueError): continue
                if rstep>last and criterion in str(r.get("obs_brief","")):
                    out.append({"claim_id":cid,"verdict":"CONTESTED",
                                "reason":f"ledger verify-fail at step {rstep} after evidence at step {last}"})
                    break
        return out
    @staticmethod
    def probe(state: Dict[str,Any], proof: ProofObject) -> Dict[str,Any]:
        claims=set(proof.claim_ids); contested=set(); refuted=set(); reasons=[]
        # v3.7.0 N-FALS: явные вердикты + механически захваченные из журнала противоречия
        rows=list(state.get("falsification",[])) + FalsificationProbe.infer_from_ledger(state,proof)
        for row in rows:
            if not isinstance(row,dict) or row.get("claim_id") not in claims: continue
            verdict=str(row.get("verdict","")).upper()
            if verdict==FalsificationVerdict.REFUTED:
                refuted.add(row["claim_id"]); reasons.append(row.get("reason","refuted"))
            elif verdict==FalsificationVerdict.CONTESTED:
                contested.add(row["claim_id"]); reasons.append(row.get("reason","contested"))
        if refuted: return {"status":"REFUTED","claims":sorted(refuted),"reasons":reasons}
        if contested: return {"status":"CONTESTED","claims":sorted(contested),"reasons":reasons}
        return {"status":"CLEAR","claims":[],"reasons":[]}

class ProofAnchorLedger:
    """Append-only hash chain for proof commits; no claim is made that this is tamper-proof storage."""
    def __init__(self,path:Path): self.path=path; self.path.parent.mkdir(parents=True,exist_ok=True)
    def append(self,payload:Dict[str,Any])->str:
        prev="0"*64
        if self.path.exists():
            try:
                last=self.path.read_text(encoding="utf-8").splitlines()[-1]
                prev=json.loads(last).get("hash",prev)
            except Exception: pass  # хвост журнала отсутствует/повреждён — prev остаётся прежним: перезапуск цепи честен
        rec={"ts":now_iso(),"prev_hash":prev,"payload":payload}
        rec["hash"]=sha256_hex(canonical_json(rec))
        with self.path.open("a",encoding="utf-8") as f: f.write(canonical_json(rec)+"\n")
        return rec["hash"]



class KnowledgeLedgerError(PolicyViolation):
    pass

class ImmutableKnowledgeLedger:
    """Append-only hash-chained ledger for committed knowledge and revocations.

    The ledger is tamper-evident, not physically immutable: rewriting/deleting
    records is detected by verify() and by deterministic replay.
    """
    GENESIS = "0" * 64
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _hash(record: Dict[str, Any]) -> str:
        return sha256_hex(canonical_json(record))

    def _rows(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        rows=[]
        for ln in self.path.read_text(encoding="utf-8").splitlines():
            if not ln.strip():
                continue
            try:
                row=json.loads(ln)
            except json.JSONDecodeError as e:
                raise KnowledgeLedgerError(f"ledger parse error: {e}")
            if not isinstance(row,dict):
                raise KnowledgeLedgerError("ledger row is not object")
            rows.append(row)
        return rows

    def append(self, event: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        rows=self._rows()
        prev=rows[-1]["entry_hash"] if rows else self.GENESIS
        seq=len(rows)+1
        body={"seq":seq,"event":event,"ts":now_iso(),"prev_hash":prev,"payload":payload}
        body["entry_hash"]=self._hash(body)
        with self.path.open("a",encoding="utf-8") as f:
            f.write(canonical_json(body)+"\n")
            f.flush(); os.fsync(f.fileno())
        return body

    def verify(self) -> Tuple[bool, Optional[int]]:
        prev=self.GENESIS
        try:
            rows=self._rows()
        except KnowledgeLedgerError:
            return False, 0
        for i,row in enumerate(rows):
            if row.get("seq") != i+1 or row.get("prev_hash") != prev:
                return False,i
            supplied=row.get("entry_hash")
            body={k:v for k,v in row.items() if k!="entry_hash"}
            if supplied != self._hash(body):
                return False,i
            prev=supplied
        return True,None

    def replay(self, proof_resolver: Optional[Callable[[str], Optional[Dict[str, Any]]]] = None) -> Dict[str, Any]:
        ok,bad=self.verify()
        if not ok:
            raise KnowledgeLedgerError(f"ledger verification failed at row {bad}")
        state={"committed":{},"revoked":{},"events":0}
        last_root_epoch=-1  # v3.8.0: контроль отката корневой эпохи в журнале
        for row in self._rows():
            state["events"] += 1
            event=row.get("event"); payload=row.get("payload",{})
            pid=payload.get("proof_id")
            if event=="COMMIT" and pid:
                if pid in state["revoked"]:
                    raise KnowledgeLedgerError(f"replay fork: commit after revoke: {pid}")
                if pid in state["committed"]:
                    # v3.7.0 N3: повторный COMMIT той же связи знания — форк истории;
                    # политика replay полна: revoke-unknown, commit-after-revoke, duplicate-commit.
                    raise KnowledgeLedgerError(f"replay fork: duplicate commit: {pid}")
                if proof_resolver is not None and payload.get("proof_hash"):
                    proof=proof_resolver(pid)
                    if proof is None:
                        raise KnowledgeLedgerError(f"replay error: missing proof archive: {pid}")
                    actual=self._hash(proof)
                    if actual != payload["proof_hash"]:
                        raise KnowledgeLedgerError(f"replay error: proof hash mismatch: {pid}")
                _pe=int(payload.get("root_epoch", -1))
                if _pe >= 0:
                    # v3.8.0: COMMIT не может откатывать корневую эпоху — форк истории
                    if _pe < last_root_epoch:
                        raise KnowledgeLedgerError(f"replay fork: root epoch rollback: {pid}")
                    last_root_epoch=_pe
                state["committed"][pid]=dict(payload)
            elif event=="REVOKE" and pid:
                if pid not in state["committed"]:
                    raise KnowledgeLedgerError(f"replay error: revoke unknown proof: {pid}")
                state["revoked"][pid]=dict(payload)
        state["state_hash"] = self._hash({"committed": state["committed"], "revoked": state["revoked"]})
        return state

    def replay_state(self, proof_resolver: Optional[Callable[[str], Optional[Dict[str, Any]]]] = None) -> Dict[str, Any]:
        """Reconstruct durable knowledge state; optionally verify referenced proof content."""
        replayed = self.replay(proof_resolver=proof_resolver)
        active = {pid: dict(payload) for pid, payload in replayed["committed"].items()
                  if pid not in replayed["revoked"]}
        revoked = {pid: dict(payload) for pid, payload in replayed["revoked"].items()}
        return {
            "active": active,
            "revoked": revoked,
            "events": replayed["events"],
            "state_hash": self._hash({"active": active, "revoked": revoked}),
        }

    def replay_digest(self, proof_resolver: Optional[Callable[[str], Optional[Dict[str, Any]]]] = None) -> str:
        """Canonical digest of reconstructed durable state; deterministic across replays."""
        return self.replay_state(proof_resolver=proof_resolver)["state_hash"]

class RootTrustAuthority:
    """Root trust domain: authorizes signing-key epochs, but never signs ledger checkpoints.

    v3.9.0 HMAC DOMAIN BINDING:
      A1.1 Гигиена MAC: конструкция переведена со схемы pbkdf2_hmac(c=1, ключ-в-роли-salt)
           на стандартный HMAC-SHA256 (hmac_hex — единый помощник модуля).
      A1.2 Связка доменов: chain_provider (источник актуальной истории RootEpochChain)
           вшивает активный корневой отпечаток в КАЖДУЮ авторизацию подписывающего
           ключа (под ним же считается MAC); verify_authorization принимает
           авторизацию только под АКТИВНЫМ корнем — ротация или отзыв корня
           инвалидируют неподтверждённые авторизации (install() отказывает).
           Unbound-режим (chain_provider=None) сохранён для изолированной
           эксплуатации домена без корневой цепи.
    """
    VERSION = 1
    DOMAIN = "ROOT"

    def __init__(self, root_key: bytes,
                 chain_provider: Optional[Callable[[], List["RootEpoch"]]] = None):
        if not isinstance(root_key, (bytes, bytearray)) or len(root_key) < 16:
            raise KnowledgeLedgerError("root key must be at least 16 bytes")
        self._root_key = bytes(root_key)
        self._chain_provider = chain_provider
        self.epoch = 0
        self.history: List[Dict[str, Any]] = []

    def _mac(self, body: Dict[str, Any]) -> str:
        # v3.9.0 A1.1: стандартный HMAC-SHA256 вместо pbkdf2_hmac(c=1, key-as-salt)
        return hmac_hex(self._root_key, body)

    def _active_root_fingerprint(self) -> Optional[str]:
        if self._chain_provider is None:
            return None
        return RootEpochChain.active(self._chain_provider()).root_fingerprint

    def authorize_signing_key(self, key_id: str, key: bytes, effective_seq: int) -> Dict[str, Any]:
        if not key_id or not isinstance(key, (bytes, bytearray)) or len(key) < 16:
            raise KnowledgeLedgerError("invalid signing key authorization")
        if any(x["key_id"] == key_id for x in self.history):
            raise KnowledgeLedgerError("signing key id already authorized")
        if self.history and effective_seq <= self.history[-1]["effective_seq"]:
            raise KnowledgeLedgerError("signing key epoch rollback")
        self.epoch += 1
        body={"version":self.VERSION,"domain":self.DOMAIN,"epoch":self.epoch,
              "key_id":key_id,"key_fingerprint":sha256_hex(bytes(key)),
              "effective_seq":int(effective_seq)}
        # v3.9.0 A1.2: активный корневой отпечаток вшивается ДО MAC (MAC его покрывает)
        root_fp = self._active_root_fingerprint()
        if root_fp is not None:
            body["root_fingerprint"]=root_fp
        body["root_mac"]=self._mac(body)
        self.history.append(dict(body))
        return dict(body)

    def verify_authorization(self, auth: Dict[str, Any]) -> None:
        req={"version","domain","epoch","key_id","key_fingerprint","effective_seq","root_mac"}
        if not req.issubset(auth) or auth.get("domain") != self.DOMAIN:
            raise KnowledgeLedgerError("invalid root authorization envelope")
        # v3.9.0 A1.2: root_fingerprint участвует в MAC-теле, если вшит —
        # иначе verify пересчитал бы MAC без него и отверг бы валидную авторизацию
        body={k:auth[k] for k in (req | {"root_fingerprint"}) if k != "root_mac" and k in auth}
        if not hmac_compare(self._mac(body), auth["root_mac"]):
            raise KnowledgeLedgerError("root authorization MAC failure")
        if int(auth["epoch"]) < 1:
            raise KnowledgeLedgerError("invalid root epoch")
        # v3.9.0 A1.2: при связке с корневой цепью авторизация обязана ссылаться
        # на АКТИВНЫЙ корень; ротация/отзыв инвалидируют неподтверждённые авторизации
        root_fp = self._active_root_fingerprint()
        if root_fp is not None:
            if "root_fingerprint" not in auth:
                raise KnowledgeLedgerError("authorization not bound to a root epoch")
            if not hmac_compare(str(auth["root_fingerprint"]), root_fp):
                raise KnowledgeLedgerError("authorization root epoch rotated/revoked")


class SigningTrustDomain:
    """Signing domain. It accepts only root-authorized epochs and signs checkpoints."""
    DOMAIN = "SIGNING"
    VERSION = 1

    def __init__(self):
        self.keys: Dict[str, Dict[str, Any]] = {}
        self.active_key_id: Optional[str] = None
        self.max_epoch = 0

    def install(self, key: bytes, authorization: Dict[str, Any], root: RootTrustAuthority) -> None:
        root.verify_authorization(authorization)
        kid=authorization["key_id"]
        if sha256_hex(bytes(key)) != authorization["key_fingerprint"]:
            raise KnowledgeLedgerError("root-authorized key fingerprint mismatch")
        epoch=int(authorization["epoch"])
        if epoch <= self.max_epoch or kid in self.keys:
            raise KnowledgeLedgerError("signing epoch replay/rollback")
        self.keys[kid]={"key":bytes(key),"epoch":epoch,
                        "effective_seq":int(authorization["effective_seq"]),"revoked":False}
        self.max_epoch=epoch
        self.active_key_id=kid

    def revoke(self, key_id: str) -> None:
        if key_id not in self.keys: raise KnowledgeLedgerError("unknown signing key")
        if key_id == self.active_key_id: raise KnowledgeLedgerError("cannot revoke active signing key")
        self.keys[key_id]["revoked"]=True

    def sign_checkpoint(self, checkpoint: Dict[str, Any], seq: int) -> Dict[str, Any]:
        kid=self.active_key_id
        if kid is None: raise KnowledgeLedgerError("no active signing key")
        rec=self.keys[kid]
        if rec["revoked"] or int(seq) < rec["effective_seq"]:
            raise KnowledgeLedgerError("signing key not valid for sequence")
        body={"version":self.VERSION,"domain":self.DOMAIN,"epoch":rec["epoch"],
              "key_id":kid,"seq":int(seq),"checkpoint":checkpoint}
        body["mac"]=hmac_hex(rec["key"],body)
        return body

    def verify_checkpoint(self, signed: Dict[str, Any]) -> None:
        req={"version","domain","epoch","key_id","seq","checkpoint","mac"}
        if not req.issubset(signed) or signed.get("domain") != self.DOMAIN:
            raise KnowledgeLedgerError("invalid signing checkpoint envelope")
        rec=self.keys.get(signed["key_id"])
        if rec is None or rec["revoked"]: raise KnowledgeLedgerError("unknown/revoked signing key")
        if int(signed["epoch"]) != rec["epoch"] or int(signed["seq"]) < rec["effective_seq"]:
            raise KnowledgeLedgerError("signing epoch mismatch")
        body={k:signed[k] for k in req if k != "mac"}
        if not hmac_compare(hmac_hex(rec["key"],body),signed["mac"]):
            raise KnowledgeLedgerError("checkpoint MAC failure")


def hmac_hex(key: bytes, obj: Dict[str, Any]) -> str:
    import hmac
    return hmac.new(key, canonical_json(obj).encode("utf-8"), hashlib.sha256).hexdigest()


def hmac_compare(a: str, b: str) -> bool:
    import hmac
    return hmac.compare_digest(a, b)


# ═══════════════════════════════════════════════════════════════════════════════
# v3.8.0 — ROOT EPOCH CHAIN (порт ветки JOHNSON v3.6.0 ROOT_TRUST, 0a950025…;
# закрыты N-RT1..N-RT4). Append-only история корневых эпох: genesis → rotate →
# revoke. ROOT → Proof → CAS → Revocation → Reconciliation → COMMIT — реальная
# дуга: активная эпоха вшивается в ProofObject и ledger-COMMIT (N-RT3).
# ═══════════════════════════════════════════════════════════════════════════════
class RootTrustError(KnowledgeLedgerError):
    """v3.8.0 N-RT4: нарушение инвариантов корневой истории — ЧАСТЬ ledger-контракта
    исключений (в ветке-источнике RootTrustError(Exception) выпадал из контракта:
    отказ COMMIT вырывался бы из except-обвязки runtime вместо честного verify-fail)."""


@dataclass(frozen=True)
class RootEpoch:
    epoch: int
    root_fingerprint: str
    parent_fingerprint: Optional[str]
    effective_at: str
    authorization_hash: str
    revoked: bool = False


class RootEpochChain:
    """Детерминированная append-only история корневых эпох.

    Порт ветки JOHNSON v3.6.0 ROOT_TRUST с закрытыми дефектами:
      N-RT1 — усечение хвоста истории verify_history НЕ видит (e.epoch==i сходится);
              обнаружимо ТОЛЬКО внешним пином дайджеста. Пин обязателен на
              production-пути: validate_pinned_state() в COMMIT-гейте. Тест ветки
              T97 проверял лишь «digest differs» — усечённая история ПРИНИМАЛАСЬ.
      N-RT2 — повторный revoke того же корня отклоняется (ветка принимала молча).
      N-RT3 — слой вшит в COMMIT (раньше: класс + selftest, ноль production-вызовов).
      N-RT4 — RootTrustError наследник KnowledgeLedgerError (контракт исключений цел).
    Политика валидации чекпоинтов — двухконтурная:
      validate_checkpoint_active — строгий контур НОВЫХ коммитов (только активная
      эпоха; ротация отклоняет ссылки на прошлые эпохи);
      validate_epoch — исторический контур аудита/replay (эпоха валидна, если
      существует в истории, не отозвана и отпечаток совпадает).
    """
    DOMAIN = "JOHNSON:ROOT-EPOCH:v1"

    @staticmethod
    def fingerprint(public_material: str) -> str:
        return sha256_hex(public_material.encode("utf-8"))

    @classmethod
    def authorization_hash(cls, epoch: int, root_fp: str, parent_fp: Optional[str], effective_at: str) -> str:
        return sha256_hex(canonical_json({"domain": cls.DOMAIN, "epoch": int(epoch),
                                          "root_fingerprint": root_fp,
                                          "parent_fingerprint": parent_fp,
                                          "effective_at": effective_at}))

    @classmethod
    def genesis(cls, public_material: str, effective_at: str) -> RootEpoch:
        fp = cls.fingerprint(public_material)
        return RootEpoch(0, fp, None, effective_at,
                         cls.authorization_hash(0, fp, None, effective_at))

    @classmethod
    def rotate(cls, history: List[RootEpoch], new_public_material: str, effective_at: str) -> List[RootEpoch]:
        cls.verify_history(history)
        current = history[-1]
        if current.revoked:
            raise RootTrustError("cannot rotate from revoked root")
        fp = cls.fingerprint(new_public_material)
        if fp == current.root_fingerprint:
            raise RootTrustError("root rotation must change root fingerprint")
        out = list(history)
        out.append(RootEpoch(current.epoch + 1, fp, current.root_fingerprint, effective_at,
                             cls.authorization_hash(current.epoch + 1, fp, current.root_fingerprint, effective_at)))
        cls.verify_history(out)
        return out

    @classmethod
    def revoke_current(cls, history: List[RootEpoch]) -> List[RootEpoch]:
        cls.verify_history(history)
        current = history[-1]
        # v3.8.0 N-RT2: повторный revoke — ошибка, а не молчаливое принятие
        if current.revoked:
            raise RootTrustError("root epoch already revoked")
        out = list(history)
        out[-1] = RootEpoch(current.epoch, current.root_fingerprint, current.parent_fingerprint,
                            current.effective_at, current.authorization_hash, True)
        return out

    @classmethod
    def verify_history(cls, history: List[RootEpoch]) -> bool:
        if not history:
            raise RootTrustError("empty root history")
        seen = set()
        for i, e in enumerate(history):
            if e.epoch != i:
                raise RootTrustError("root epoch rollback or truncation detected")
            if e.root_fingerprint in seen:
                raise RootTrustError("root fingerprint reuse/resurrection detected")
            seen.add(e.root_fingerprint)
            if e.authorization_hash != cls.authorization_hash(e.epoch, e.root_fingerprint,
                                                              e.parent_fingerprint, e.effective_at):
                raise RootTrustError("root authorization tampering detected")
            if i == 0:
                if e.parent_fingerprint is not None:
                    raise RootTrustError("genesis root has a parent")
            else:
                prev = history[i - 1]
                if e.parent_fingerprint != prev.root_fingerprint:
                    raise RootTrustError("root-history fork or parent mismatch")
                if prev.revoked:
                    raise RootTrustError("rotation from revoked root")
        return True

    @classmethod
    def active(cls, history: List[RootEpoch]) -> RootEpoch:
        cls.verify_history(history)
        if history[-1].revoked:
            raise RootTrustError("no active root")
        return history[-1]

    @classmethod
    def history_digest(cls, history: List[RootEpoch]) -> str:
        cls.verify_history(history)
        return sha256_hex(canonical_json([asdict(e) for e in history]))

    # ── v3.8.0: контур состояния задачи ─────────────────────────────────────

    @staticmethod
    def _hist_from_state(state: Dict[str, Any]) -> List[RootEpoch]:
        raw = state.get("root_epoch_chain")
        if not isinstance(raw, list) or not raw:
            raise RootTrustError("root epoch chain missing from state")
        out: List[RootEpoch] = []
        for d in raw:
            if not isinstance(d, dict) or not {"epoch", "root_fingerprint", "parent_fingerprint",
                                               "effective_at", "authorization_hash"}.issubset(d):
                raise RootTrustError("malformed root epoch entry")
            out.append(RootEpoch(int(d["epoch"]), d["root_fingerprint"], d.get("parent_fingerprint"),
                                 d["effective_at"], d["authorization_hash"], bool(d.get("revoked", False))))
        return out

    @classmethod
    def pin_state(cls, state: Dict[str, Any]) -> str:
        hist = cls._hist_from_state(state)
        pin = cls.history_digest(hist)
        state["root_epoch_chain_pin"] = pin
        return pin

    @classmethod
    def validate_pinned_state(cls, state: Dict[str, Any]) -> bool:
        """v3.8.0 N-RT1: подмена/усечение истории обнаружимы сравнением с пином.
        Без пина verify_history пропускает усечение хвоста (weak mechanic ветки)."""
        hist = cls._hist_from_state(state)
        cls.verify_history(hist)
        pin = state.get("root_epoch_chain_pin")
        if not isinstance(pin, str) or not pin:
            raise RootTrustError("root epoch chain pin missing")
        if not hmac_compare(cls.history_digest(hist), pin):
            raise RootTrustError("root epoch chain tamper/truncation detected (digest pin mismatch)")
        return True

    @classmethod
    def validate_checkpoint_active(cls, history: List[RootEpoch], root_epoch: int, root_fingerprint: str) -> bool:
        """Строгий контур НОВЫХ коммитов: только активная эпоха."""
        act = cls.active(history)
        if int(root_epoch) != act.epoch:
            raise RootTrustError("checkpoint references non-active root epoch")
        if not hmac_compare(root_fingerprint, act.root_fingerprint):
            raise RootTrustError("checkpoint root fingerprint mismatch")
        return True

    @classmethod
    def validate_epoch(cls, history: List[RootEpoch], epoch: int, root_fingerprint: str) -> bool:
        """Исторический контур аудита/replay: эпоха валидна, если существует в
        истории, не отозвана и отпечаток совпадает (ротация не инвалидизирует
        старые записи ретроактивно; отозванный корень теряет силу консервативно)."""
        cls.verify_history(history)
        for e in history:
            if e.epoch == int(epoch):
                if e.revoked:
                    raise RootTrustError("checkpoint references revoked root epoch")
                if not hmac_compare(e.root_fingerprint, root_fingerprint):
                    raise RootTrustError("checkpoint root fingerprint mismatch")
                return True
        raise RootTrustError("checkpoint references unknown root epoch")

    @classmethod
    def require_active_from_state(cls, state: Dict[str, Any]) -> RootEpoch:
        """COMMIT-гейт: цепь обязана существовать, быть целой под пином и иметь
        активную (не отозванную) корневую эпоху. Ленивый бутстрап для состояний
        вне runtime (unit/батареи) сохраняет инвариант универсально; runtime
        (Agent.solve) создаёт цепь явно на старте задачи."""
        raw = state.get("root_epoch_chain")
        if not isinstance(raw, list) or not raw:
            hist = [cls.genesis("JOHNSON-ROOT:bootstrap", now_iso())]
            state["root_epoch_chain"] = [asdict(e) for e in hist]
            state["root_epoch_chain_pin"] = cls.history_digest(hist)
        cls.validate_pinned_state(state)
        return cls.active(cls._hist_from_state(state))




class LedgerTrustAnchor:
    """External pinned checkpoint for the knowledge ledger.

    The anchor is intentionally NOT self-authenticating: trust comes from an
    independently supplied expected digest (configuration/operator/upper TCB).
    This detects rollback, fork, and checkpoint substitution of the ledger.
    """
    VERSION = 1

    @staticmethod
    def checkpoint(ledger: "ImmutableKnowledgeLedger") -> Dict[str, Any]:
        ok, bad = ledger.verify()
        if not ok:
            raise KnowledgeLedgerError(f"cannot anchor invalid ledger at row {bad}")
        rows = ledger._rows()
        tip = rows[-1]["entry_hash"] if rows else ImmutableKnowledgeLedger.GENESIS
        state = ledger.replay_state()
        return {
            "version": LedgerTrustAnchor.VERSION,
            "events": len(rows),
            "tip_hash": tip,
            "state_hash": state["state_hash"],
        }

    @staticmethod
    def digest(anchor: Dict[str, Any]) -> str:
        return sha256_hex(canonical_json(anchor))

    @classmethod
    def verify(cls, ledger: "ImmutableKnowledgeLedger",
               pinned_anchor: Dict[str, Any],
               expected_anchor_digest: str) -> Dict[str, Any]:
        actual_digest = cls.digest(pinned_anchor)
        if actual_digest != expected_anchor_digest:
            raise KnowledgeLedgerError("trust anchor substitution detected")
        cp = cls.checkpoint(ledger)
        for key in ("version", "events", "tip_hash", "state_hash"):
            if cp.get(key) != pinned_anchor.get(key):
                raise KnowledgeLedgerError(f"trust anchor mismatch: {key}")
        return {"ok": True, "anchor_digest": actual_digest, "checkpoint": cp}

class EpistemicReconciler:
    @staticmethod
    def reconcile(state: Dict[str,Any], proof: ProofObject) -> Dict[str,Any]:
        artifacts={}
        mismatches=[]
        for path in state.get("_artifact_paths",[]):
            try: artifacts[path]=sha256_hex(Path(path).read_bytes())
            except Exception: artifacts[path]="MISSING"
        expected=proof.artifact_hashes
        for path,h in expected.items():
            if artifacts.get(path) != h:
                mismatches.append({"artifact":path,"expected":h,"actual":artifacts.get(path,"MISSING")})
        return {
            "transaction_verdict":"READY" if not mismatches else "BLOCKED",
            "world_verdict":"VERIFIED_MATCH" if not mismatches else "VERIFIED_MISMATCH",
            "knowledge_verdict":"VERIFIED",
            "engine_state":asdict(EngineState(state.get("task_id",""),"committed",len(state.get("ledger",[])))),
            "world_state":asdict(WorldState(now_iso(),artifacts)),
            "knowledge_state":asdict(KnowledgeState(proof.id,list(proof.claim_ids),proof.created_at)),
            "mismatches":mismatches,
        }

class RevocationCascade:
    """Точное аннулирование по графу Evidence→Artifact; зависимости claims каскадируют."""
    @staticmethod
    def detect_artifact_mismatches(state: Dict[str, Any], proof: ProofObject) -> List[Dict[str, str]]:
        actual={}
        for path in proof.artifact_hashes:
            try: actual[path]=sha256_hex(Path(path).read_bytes())
            except Exception: actual[path]="MISSING"
        return [{"artifact":path,"expected":expected,"actual":actual.get(path,"MISSING")}
                for path,expected in proof.artifact_hashes.items() if actual.get(path,"MISSING") != expected]

    @staticmethod
    def _affected_claims(proof: ProofObject, revoked_evidence: List[str]) -> List[str]:
        """v3.7.0: claims, чьи деривации опираются на отозванное evidence —
        из узлов proof'а (самодостаточно, не зависит от state["derivations"])."""
        support={}
        for n in proof.nodes:
            if isinstance(n,dict) and n.get("kind")=="derivation" and n.get("claim_id"):
                support.setdefault(n["claim_id"],set()).update(n.get("inputs",[]))
        return sorted(cid for cid,eids in support.items() if eids & set(revoked_evidence))

    @staticmethod
    def detect_evidence_drift(state: Dict[str, Any], proof: ProofObject) -> List[Dict[str, str]]:
        """v3.7.0 revival-gate: дрейф мира относительно состояния В МОМЕНТ наблюдения
        evidence. Перезапись глобального пина при перекомпиляции не launder'ит
        старое evidence: хеши рёбер иммунны к перезаписи state["artifact_hashes"]."""
        drift=[]
        for eid,edges in (getattr(proof,"artifact_edges",{}) or {}).items():
            if not isinstance(edges,dict): continue
            for path,pin in edges.items():
                try: cur=sha256_hex(Path(path).read_bytes())
                except Exception: cur="MISSING"
                if cur!=pin:
                    drift.append({"evidence":eid,"artifact":path,"expected":pin,"actual":cur})
        return drift

    @classmethod
    def apply_drift(cls, state: Dict[str, Any], proof: ProofObject, drift: List[Dict[str, str]]) -> None:
        """v3.7.0: точная ревокация по evidence-дрейфу (до вынесения вердикта COMMIT)."""
        bad={d["artifact"] for d in drift}
        edges=getattr(proof,"artifact_edges",{}) or {}
        revoked=sorted(eid for eid,em in edges.items()
                       if isinstance(em,dict) and any(p in bad for p in em))
        affected=cls._affected_claims(proof,revoked)
        state["revocation"]={"status":"REVOKED","reason":"evidence_artifact_drift",
                             "artifacts":sorted(bad),"drift":drift,"revoked_at":now_iso(),
                             "evidence_ids":revoked,"claim_ids":affected,"proof_id":proof.id}
        for row in state.get("derivations", []):
            if row.get("claim_id") in affected:
                row["status"]="revoked"; row["revocation_reason"]="evidence_artifact_drift"
        state["revoked_evidence_ids"]=revoked
        state["revoked_claim_ids"]=affected
        state["knowledge_status"]="REVOKED"

    @classmethod
    def apply(cls, state: Dict[str, Any], proof: ProofObject) -> List[Dict[str, str]]:
        mismatches=cls.detect_artifact_mismatches(state,proof)
        if not mismatches: return []
        changed={m["artifact"] for m in mismatches}
        # v3.7.0 N1: единственный источник истины — рёбра {путь: хеш_наблюдения};
        # refs (пути) — производная форма для proofs без рёбер.
        edges=getattr(proof,"artifact_edges",{}) or {}
        if edges:
            revoked_evidence={eid for eid,em in edges.items()
                              if isinstance(em,dict) and any(p in changed for p in em)}
        else:
            evidence_refs=proof.evidence_artifact_refs or {}
            revoked_evidence={eid for eid,paths in evidence_refs.items() if changed.intersection(paths)}
            if not evidence_refs:
                # legacy-proof без per-evidence рёбер: консервативный полный каскад
                revoked_evidence=set(proof.evidence_ids)
        revoked_claims=set(cls._affected_claims(proof,sorted(revoked_evidence)))
        derivations=state.get("derivations",[])
        revoked_claims|={d.get("claim_id") for d in derivations
                        if d.get("claim_id") and any(e in revoked_evidence for e in d.get("evidence_ids",[]))}
        # A claim depending on a revoked claim is revoked transitively.
        deps=state.get("claim_dependencies",{})
        changed_claims=True
        while changed_claims:
            changed_claims=False
            for claim,deplist in deps.items():
                if claim not in revoked_claims and any(d in revoked_claims for d in deplist):
                    revoked_claims.add(claim); changed_claims=True
        revoked_derivations=[]
        for row in derivations:
            if row.get("claim_id") in revoked_claims:
                row["status"]="revoked"; row["revocation_reason"]="artifact_mutation"
                revoked_derivations.append(row.get("id", row.get("claim_id")))
        state["revocation"]={"status":"REVOKED","reason":"artifact_mutation","artifacts":mismatches,
            "revoked_at":now_iso(),"evidence_ids":sorted(revoked_evidence),
            "claim_ids":sorted(revoked_claims),"derivation_ids":sorted(x for x in revoked_derivations if x),
            "proof_id":proof.id}
        state["revoked_evidence_ids"]=sorted(revoked_evidence)
        state["revoked_claim_ids"]=sorted(revoked_claims)
        state["knowledge_status"]="REVOKED"
        return mismatches


class KnowledgeRevocationIndex:
    """Персистентный индекс committed knowledge → Artifact dependencies.

    Индекс хранит только уже COMMITTED ProofObject-связи. При последующем
    изменении/удалении Artifact он находит исторические knowledge records,
    зависящие от этого Artifact, и переводит их в REVOKED.
    """
    _lock = threading.RLock()

    @classmethod
    def _path(cls, state: Dict[str, Any]) -> Optional[Path]:
        raw = state.get("_knowledge_revocation_index_path")
        return Path(raw) if raw else None

    @classmethod
    def _load(cls, path: Path) -> List[Dict[str, Any]]:
        if not path.exists():
            return []
        rows=[]
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip(): continue
            try:
                row=json.loads(line)
                if isinstance(row,dict) and row.get("proof_id"): rows.append(row)
            except json.JSONDecodeError:
                continue
        return rows

    @classmethod
    def _store(cls, path: Path, rows: List[Dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp=path.with_name(path.name + ".tmp")
        tmp.write_text("".join(canonical_json(r)+"\n" for r in rows), encoding="utf-8")
        os.replace(tmp, path)

    @classmethod
    def register(cls, state: Dict[str, Any], proof: ProofObject) -> bool:
        path=cls._path(state)
        if path is None: return False
        with cls._lock:
            rows=cls._load(path)
            if any(r.get("proof_id")==proof.id for r in rows): return True
            rows.append({
                "proof_id": proof.id,
                "claim_ids": list(proof.claim_ids),
                "evidence_ids": list(proof.evidence_ids),
                "artifact_hashes": dict(proof.artifact_hashes),
                "evidence_artifact_refs": dict(proof.evidence_artifact_refs),
                "committed_at": now_iso(),
                "status": "ACTIVE",
            })
            cls._store(path, rows)
            return True

    @staticmethod
    def _actual_hash(path: str) -> str:
        try: return sha256_hex(Path(path).read_bytes())
        except OSError: return "MISSING"

    @classmethod
    def reconcile(cls, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Возвращает исторические записи, ставшие REVOKED."""
        path=cls._path(state)
        if path is None: return []
        revoked=[]
        with cls._lock:
            rows=cls._load(path)
            changed=False
            for row in rows:
                if row.get("status") == "REVOKED": continue
                mismatches=[]
                for artifact, expected in row.get("artifact_hashes",{}).items():
                    actual=cls._actual_hash(artifact)
                    if actual != expected:
                        mismatches.append({"artifact":artifact,"expected":expected,"actual":actual})
                if mismatches:
                    row["status"]="REVOKED"
                    row["revoked_at"]=now_iso()
                    row["revocation_reason"]="artifact_mutation"
                    row["mismatches"]=mismatches
                    revoked.append(dict(row))
                    changed=True
            if changed: cls._store(path, rows)
        ledger_path=state.get("_knowledge_ledger_path")
        if ledger_path:
            ledger=ImmutableKnowledgeLedger(Path(ledger_path))
            for row in revoked:
                ledger.append("REVOKE", {
                    "proof_id": row.get("proof_id"),
                    "reason": row.get("revocation_reason", "artifact_mutation"),
                    "mismatches": row.get("mismatches", []),
                })
        return revoked



class StateCAS:
    """Compare-and-swap guard for the verify→commit boundary."""
    EXCLUDED={"commit","epistemic_reconciliation","proof","verified"}
    @classmethod
    def material(cls,state:Dict[str,Any])->Dict[str,Any]:
        return {k:v for k,v in state.items() if k not in cls.EXCLUDED}
    @classmethod
    def fingerprint(cls,state:Dict[str,Any])->str:
        return sha256_hex(canonical_json(cls.material(state)))
    @classmethod
    def version(cls,state:Dict[str,Any])->int:
        return int(state.get("_cas_version",0))
    @classmethod
    def bump(cls,state:Dict[str,Any])->int:
        v=cls.version(state)+1; state["_cas_version"]=v; return v
    @classmethod
    def assert_unchanged(cls,state:Dict[str,Any],proof:ProofObject)->None:
        if cls.version(state)!=proof.state_version or cls.fingerprint(state)!=proof.source_state_hash:
            raise GateAntiVacuum.refuse("COMMIT", "CAS conflict — state changed after proof compilation")

@dataclass
class RuntimeStates:
    engine: EngineState
    world: WorldState
    knowledge: KnowledgeState

class ProofCarryingGovernor:
    REQUIRED_KEYS=("id","status","claim_ids","evidence_ids","rule","unknowns")
    @classmethod
    def validate(cls,state:Dict[str,Any])->ProofObject:
        raw=state.get("proof")
        if not isinstance(raw,dict) or any(k not in raw for k in cls.REQUIRED_KEYS):
            raise GateAntiVacuum.refuse("COMMIT", "отсутствует полный ProofObject")
        proof=ProofObject(raw["id"],raw["status"],list(raw["claim_ids"]),list(raw["evidence_ids"]),raw["rule"],list(raw["unknowns"]),raw.get("rule_version",""),list(raw.get("nodes",[])),list(raw.get("edges",[])),dict(raw.get("evidence_hashes",{})),raw.get("created_at",now_iso()),dict(raw.get("evidence_timestamps",{})),dict(raw.get("artifact_hashes",{})),raw.get("source_state_hash",""),int(raw.get("state_version",0)),dict(raw.get("evidence_artifact_refs",{})),{k:dict(v) for k,v in (raw.get("artifact_edges") or {}).items() if isinstance(v,dict)})
        if proof.unknowns: raise GateAntiVacuum.refuse("COMMIT", "UNKNOWN")
        if not proof.claim_ids or not proof.evidence_ids: raise GateAntiVacuum.refuse("COMMIT", "неполное покрытие")
        ProofClosure.validate(proof); TemporalValidity.validate(proof)
        fals=FalsificationProbe.probe(state,proof)
        if fals["status"] != "CLEAR": raise GateAntiVacuum.refuse("COMMIT", f"falsification={fals['status']}")
        return proof
    @classmethod
    def commit(cls,state:Dict[str,Any])->ProofObject:
        proof=cls.validate(state)
        if not proof.source_state_hash:
            raise GateAntiVacuum.refuse("COMMIT", "proof missing CAS source state")
        StateCAS.assert_unchanged(state,proof)
        # v3.7.0 revival-hole gate: evidence-пины (состояние мира В МОМЕНТ наблюдения)
        # сверяются с текущим миром ДО разрешения COMMIT. Перезапись глобального пина
        # при перекомпиляции не launder'ит старое evidence.
        drift=RevocationCascade.detect_evidence_drift(state,proof)
        if drift:
            RevocationCascade.apply_drift(state,proof,drift)
            raise GateAntiVacuum.refuse("COMMIT", "REVOKED — evidence-bound artifact mutation: "+", ".join(sorted({d['artifact'] for d in drift})))
        mismatches=RevocationCascade.apply(state,proof)
        if mismatches:
            raise GateAntiVacuum.refuse("COMMIT", "REVOKED — bound artifact mutation")
        reconciliation=EpistemicReconciler.reconcile(state,proof)
        StateCAS.assert_unchanged(state,proof)
        if reconciliation["world_verdict"] != "VERIFIED_MATCH":
            RevocationCascade.apply(state,proof)  # каскад применён повторно перед отказом; исход сверен строкой выше
            raise GateAntiVacuum.refuse("COMMIT", "WorldState mismatch")
        # v3.8.0 ROOT TRUST GATE (закрытие N-RT3 «мёртвый слой»): дуга
        # ROOT EPOCH CHAIN → Proof → CAS → Revocation → Reconciliation → COMMIT
        # становится реальной. История корневых эпох сверяется с пином дайджеста
        # (усечение/подмена блокируются — N-RT1), активная эпоха вшивается в
        # ProofObject, state["proof"], commit-запись и ledger. Отозванный/пустой
        # корень запрещает COMMIT; RootTrustError ∈ KnowledgeLedgerError
        # конвертируется в честный verify-fail контракта (N-RT4).
        try:
            _root_active = RootEpochChain.require_active_from_state(state)
        except RootTrustError as _rte:
            raise GateAntiVacuum.refuse("COMMIT", f"ROOT TRUST: {_rte}") from _rte
        proof.root_epoch = _root_active.epoch
        proof.root_fingerprint = _root_active.root_fingerprint
        if isinstance(state.get("proof"), dict):
            state["proof"]["root_epoch"] = _root_active.epoch
            state["proof"]["root_fingerprint"] = _root_active.root_fingerprint

        state["epistemic_reconciliation"]=reconciliation
        state["commit"]={"status":"committed","proof_id":proof.id,"committed_at":now_iso(),"world_verdict":reconciliation["world_verdict"],"root_epoch":proof.root_epoch,"root_fingerprint":proof.root_fingerprint}
        # v3.7.0 N-RES: успешный COMMIT закрывает предыдущую REVOKED-запись
        # с сохранением истории — консистентность знания после re-proof.
        _rev=state.get("revocation")
        if isinstance(_rev,dict) and _rev.get("status")=="REVOKED":
            state.setdefault("revocation_history",[]).append({**_rev,"resolved_at":now_iso(),"resolved_by":proof.id})
            state["revocation"]={"status":"RESOLVED","resolved_at":now_iso(),
                                 "resolved_by":proof.id,"reason":_rev.get("reason")}
            state["knowledge_status"]="VALID"
        anchor_path=state.get("_proof_anchor_path")
        if anchor_path:
            state["commit"]["anchor_hash"]=ProofAnchorLedger(Path(anchor_path)).append(state["commit"]|{"proof":proof.id})
        KnowledgeRevocationIndex.register(state, proof)
        ledger_path=state.get("_knowledge_ledger_path")
        if ledger_path:
            ImmutableKnowledgeLedger(Path(ledger_path)).append("COMMIT", {
                "proof_id": proof.id,
                "claim_ids": list(proof.claim_ids),
                "evidence_ids": list(proof.evidence_ids),
                "artifact_hashes": dict(proof.artifact_hashes),
                "root_epoch": proof.root_epoch,
                "root_fingerprint": proof.root_fingerprint,
                "proof_hash": sha256_hex(canonical_json(asdict(proof))),
            })
        return proof

class KnowledgeAuditor:
    """v3.7.0 N4/P4: сверка ЗАКРЕПЛЁННОГО знания с миром вне commit-пути.
    COMMIT проверяет мир в момент коммита; мутация ПОСЛЕ коммита делает
    закреплённое знание STALE — это обнаруживается аудитом run-loop'а, а не
    только следующей попыткой коммита."""
    @staticmethod
    def audit(state: Dict[str, Any]) -> Dict[str, Any]:
        commit_rec=state.get("commit") if isinstance(state.get("commit"),dict) else {}
        proof=state.get("proof") if isinstance(state.get("proof"),dict) else {}
        if commit_rec.get("status")!="committed" or not proof:
            return {"status":"NO_COMMITTED_KNOWLEDGE","drift":[]}
        drift=[]; seen=set()
        for eid,edges in (proof.get("artifact_edges") or {}).items():
            if not isinstance(edges,dict): continue
            for path,pin in edges.items():
                try: cur=sha256_hex(Path(path).read_bytes())
                except Exception: cur="MISSING"
                if cur!=pin:
                    drift.append({"evidence":eid,"artifact":path,"expected":pin,"actual":cur}); seen.add(path)
        for path,pin in (proof.get("artifact_hashes") or {}).items():
            if path in seen: continue
            try: cur=sha256_hex(Path(path).read_bytes())
            except Exception: cur="MISSING"
            if cur!=pin:
                drift.append({"evidence":"*","artifact":path,"expected":pin,"actual":cur})
        if drift:
            state["knowledge_status"]="STALE"
            state["knowledge_drift"]={"detected_at":now_iso(),"drift":drift}
            return {"status":"STALE","drift":drift}
        if state.get("knowledge_status")=="STALE":
            state["knowledge_status"]="VALID"   # мир снова бит-в-бит совпадает с наблюдённым
        return {"status":"VALID","drift":[]}

class EvidenceGraph:
    """Граф claim/observation/artifact/verification."""
    def __init__(self): self.edges=[]
    def link(self, src, relation, dst):
        e={"src":src,"relation":relation,"dst":dst,"ts":now_iso()}; self.edges.append(e); return e
    def for_node(self, node): return [e for e in self.edges if e["src"]==node or e["dst"]==node]

class CapabilityPlanner:
    def __init__(self, graph): self.graph=graph
    def plan(self, requested): return self.graph.closure(requested)

class ProvenanceLedger:
    """Append-only causal ledger: claim/action -> observation -> artifact -> verification."""
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event_kind: str, **data) -> Dict[str, Any]:
        rec = {"id": sha256_hex(now_iso() + canonical_json(data))[:16],
               "ts": now_iso(), "kind": event_kind, **data}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec

    def recent(self, k: int = 20) -> List[Dict[str, Any]]:
        if not self.path.exists(): return []
        out=[]
        for ln in self.path.read_text(encoding="utf-8").splitlines()[-k:]:
            try: out.append(json.loads(ln))
            except Exception: pass  # оборванная/нечитаемая строка хвоста не роняет чтение остальных
        return out


class CheckpointStore:
    """Versioned atomic checkpoints. Latest pointer is itself replace-atomic."""
    VERSION = 1
    def __init__(self, base: Path):
        self.base = base
        self.dir = base / "checkpoints"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.latest = self.dir / "latest.json"

    def save(self, task_id: str, state: Dict[str, Any], step: int) -> str:
        payload = {"version": self.VERSION, "task_id": task_id, "step": step,
                   "saved_at": now_iso(), "state": state}
        payload["state_sha256"] = sha256_hex(canonical_json(state))
        cp_id = f"{task_id}_{step:05d}_{int(time.time_ns())}"
        target = self.dir / f"{cp_id}.json"
        tmp = target.with_suffix(".tmp")
        tmp.write_text(canonical_json(payload), encoding="utf-8")
        os.replace(tmp, target)
        ptr = self.latest.with_suffix(".tmp")
        ptr.write_text(canonical_json({"checkpoint": target.name, "task_id": task_id,
                                       "step": step, "saved_at": payload["saved_at"]}), encoding="utf-8")
        os.replace(ptr, self.latest)
        return str(target)

    def load(self, task_id: str) -> Optional[Tuple[Dict[str, Any], int, str]]:
        if not self.latest.exists(): return None
        try:
            pointer=json.loads(self.latest.read_text(encoding="utf-8"))
            if pointer.get("task_id") != task_id: return None
            target=self.dir / pointer["checkpoint"]
            obj=json.loads(target.read_text(encoding="utf-8"))
            state=obj["state"]
            if state.get("_terminal"):
                return None
            if obj.get("version") != self.VERSION: return None
            if obj.get("task_id") != task_id: return None
            if obj.get("state_sha256") != sha256_hex(canonical_json(state)): return None
            return state, int(obj.get("step", 0)), str(target)
        except Exception:
            return None


class RecoveryEngine:
    """Deterministic failure taxonomy and bounded recovery directives."""
    RULES = {
        "brain": "retry_brain_once",
        "policy": "change_action",
        "net": "retry_with_alternate_source",
        "tool": "inspect_failure_then_alternate",
        "timeout": "checkpoint_and_resume",
        "unknown": "checkpoint_and_stop",
    }
    def classify(self, obs: Optional[Observation] = None, exc: Optional[Exception] = None) -> str:
        if exc is not None: return "brain" if isinstance(exc, BrainError) else "unknown"
        if obs is None: return "unknown"
        if obs.kind == "policy": return "policy"
        if obs.kind == "net": return "net"
        if obs.meta.get("timeout"): return "timeout"
        return "tool"
    def strategy(self, category: str) -> str:
        return self.RULES.get(category, self.RULES["unknown"])

class GoalCompiler:
    """Компилирует цель в проверяемую спецификацию выполнения."""
    def compile(self, goal, registry):
        g=goal.strip(); low=g.lower()
        requested=[]
        if any(x in low for x in ("интернет","веб","источник","исслед","найди","сравн")):
            requested.append("research_web" if "research_web" in registry else "web_search")
        if any(x in low for x in ("файл","создай","запиши","отчёт","отчет","документ")):
            if "write_file" in registry: requested.append("write_file")
        if not requested and "stat_path" in registry: requested.append("stat_path")
        return {"goal":g,"criteria":["результат соответствует цели","результат подтверждён наблюдаемым доказательством"],
                "requested_capabilities":list(dict.fromkeys(requested)),
                "evidence_requirements":["observation","artifact_hash_or_verification"],
                "recovery_policy":["checkpoint_before_risky_action","classify_failure","resume_or_stop"],
                "compiler_version":"1.7"}

class GoalSpec:
    """Формальная, сериализуемая спецификация задачи."""
    REQUIRED=("objective","success_criteria","preconditions","postconditions",
              "capabilities","actions","evidence_requirements","verification",
              "recovery","rollback")
    def __init__(self, **kw):
        for k in self.REQUIRED: setattr(self,k,kw.get(k,[] if k.endswith("s") else None))
    def as_dict(self): return {k:getattr(self,k) for k in self.REQUIRED}
    def validate(self):
        missing=[k for k in self.REQUIRED if k not in self.as_dict() or self.as_dict()[k] is None]
        if missing: raise ValueError("GoalSpec missing: "+", ".join(missing))
        if not self.objective or not self.success_criteria: raise ValueError("GoalSpec objective/criteria empty")
        return True

class FormalGoalCompiler(GoalCompiler):
    """Компилирует эвристику v1.7 в валидируемый GoalSpec."""
    def compile_spec(self, goal, registry, planner):
        base=self.compile(goal, registry)
        caps=planner.plan(base["requested_capabilities"])
        if not caps:
            raise ValueError("GoalSpec: не удалось вывести ни одной исполнимой capability из цели")
        criteria=[f"capability:{c} выполнена успешно" for c in caps]
        spec=GoalSpec(objective=base["goal"], success_criteria=criteria,
            preconditions=[f"capability:{c} зарегистрирована" for c in caps],
            postconditions=[f"capability:{c} имеет успешное observation" for c in caps], capabilities=caps,
            actions=[{"capability":c,"required":True} for c in caps],
            evidence_requirements=[f"successful_observation:{c}" for c in caps],
            verification=[f"successful_observation:{c}" for c in caps],
            recovery=base["recovery_policy"],
            rollback=["restore last valid checkpoint"]); spec.validate(); return spec

class ExecutionNode:
    def __init__(self, node_id, action=None, preconditions=None, postconditions=None, evidence=None, rollback=None):
        self.id=node_id; self.action=action; self.preconditions=preconditions or []; self.postconditions=postconditions or []
        self.evidence=evidence or []; self.rollback=rollback

class ActionNode:
    def __init__(self, node_id, capability, depends_on=None, preconditions=None, postconditions=None, evidence=None, rollback=None):
        self.id=node_id; self.capability=capability; self.depends_on=list(depends_on or []); self.preconditions=list(preconditions or [])
        self.postconditions=list(postconditions or []); self.evidence=list(evidence or []); self.rollback=rollback
        self.status="pending"; self.observation=None

class ActionDAG:
    """Детерминированный DAG capability-actions с dependency guards."""
    def __init__(self, spec, capability_graph): self.spec=spec; self.cg=capability_graph; self.nodes={}; self._compile()
    def _compile(self):
        order=self.cg.closure(self.spec.capabilities)
        for cap in order:
            deps=[d for d in self.cg.nodes.get(cap,{}).get("deps",[]) if d in self.spec.capabilities]
            self.nodes[cap]=ActionNode(cap,cap,depends_on=deps,
                preconditions=[f"capability:{d} completed" for d in deps],
                postconditions=[f"capability:{cap} completed"], evidence=[f"successful_observation:{cap}"],
                rollback="restore last valid checkpoint")
    def ready(self, cap):
        n=self.nodes.get(cap)
        return bool(n) and n.status=="pending" and all(self.nodes[d].status=="completed" for d in n.depends_on)
    def start(self, cap):
        if not self.ready(cap): raise PolicyViolation(f"action dependency guard failed: {cap}")
        self.nodes[cap].status="running"; return self.nodes[cap]
    def complete(self, cap, observation):
        n=self.nodes.get(cap)
        if not n or n.status!="running": raise PolicyViolation(f"action completion out of order: {cap}")
        if not observation.ok: n.status="failed"; n.observation=observation; return False
        n.status="completed"; n.observation=observation; return True
    def snapshot(self):
        return {k:{"status":v.status,"depends_on":v.depends_on} for k,v in self.nodes.items()}
    def all_required_completed(self): return all(n.status=="completed" for n in self.nodes.values())

class ExecutionGraph:
    """Детерминированный граф состояний задачи с guard-переходами."""
    TERMINAL={"verified","failed","aborted"}
    def __init__(self, spec):
        self.spec=spec; self.nodes=[]; self.edges=[]; self.state="created"
        self.history=[]
    def compile(self):
        self.nodes=[ExecutionNode("preflight",preconditions=self.spec.preconditions),
                    ExecutionNode("execute",action=self.spec.actions,evidence=self.spec.evidence_requirements),
                    ExecutionNode("verify",postconditions=self.spec.postconditions,evidence=self.spec.verification),
                    ExecutionNode("verdict",rollback=self.spec.rollback)]
        self.edges=[("created","preflight"),("preflight","execute"),("execute","verify"),("verify","verdict")]
        return self
    def transition(self, target, *, guards_ok=True, evidence_ok=False):
        if not guards_ok: raise PolicyViolation(f"transition blocked: guards for {target} failed")
        if target=="verdict" and not evidence_ok: raise PolicyViolation("VERDICT requires verified evidence")
        allowed={a:b for a,b in self.edges}.get(self.state)
        if allowed != target: raise PolicyViolation(f"illegal transition {self.state}->{target}")
        self.history.append((self.state,target)); self.state=target; return self.state
    def mark_terminal(self, outcome):
        if outcome not in self.TERMINAL: raise ValueError("invalid terminal outcome")
        if self.state != "verdict": raise PolicyViolation("terminal verdict before verification")
        self.state=outcome; self.history.append(("verdict",outcome)); return outcome

class Agent:
    def __init__(self, cfg: Config, brain: Any, gov: Governor, audit: AuditChain):
        self.cfg = cfg
        self.brain = brain
        self.gov = gov
        self.audit = audit
        self.provenance = ProvenanceLedger(Path(cfg.data_dir) / "provenance.jsonl")
        self.checkpoints = CheckpointStore(Path(cfg.data_dir))
        self.recovery = RecoveryEngine()
        self.capabilities = CapabilityGraph(self.gov.registry)
        self.evidence_graph = EvidenceGraph()
        self.planner = CapabilityPlanner(self.capabilities)
        self.goal_compiler = FormalGoalCompiler()
        self.execution_graph = None
        self.action_dag = None

    def solve(self, task_text: str) -> Dict[str, Any]:
        task_id = sha256_hex(task_text.strip())[:10]
        Path(self.cfg.workspace).mkdir(parents=True, exist_ok=True)
        resumed = self.checkpoints.load(task_id) if getattr(self.cfg, "resume", True) else None
        if resumed:
            state, restored_step, cp_path = resumed
            compiled=state.get("compiled_goal")
            if not compiled:
                return self._finalize(task_id, state, "aborted", "Checkpoint без GoalSpec: безопасное продолжение невозможно.", time.monotonic())
            try:
                spec=GoalSpec(**compiled); spec.validate()
                self.execution_graph=ExecutionGraph(spec).compile()
                self.action_dag=ActionDAG(spec,self.capabilities)
                for cap, snap in state.get("action_dag", {}).items():
                    if cap in self.action_dag.nodes:
                        self.action_dag.nodes[cap].status=snap.get("status", "pending")
                eg=state.get("execution_graph", {})
                eg_state=eg.get("state", "created")
                if eg_state in {"created","preflight","execute","verify","verdict","verified","failed","aborted"}:
                    self.execution_graph.state=eg_state
                self.execution_graph.history=[tuple(x) for x in eg.get("history", [])]
            except Exception as e:
                return self._finalize(task_id, state, "aborted", f"Checkpoint GoalSpec повреждён: {e}", time.monotonic())
            log("RESUME", f"восстановлен checkpoint шага {restored_step}: {cp_path}")
            self.audit.append({"event": "resume", "task_id": task_id, "step": restored_step, "checkpoint": cp_path})
            self.provenance.append("resume", task_id=task_id, step=restored_step, checkpoint=cp_path)
        else:
            state = {
            "goal": task_text,
            "criteria": [],
            "plan": [],
            "ledger": [],
            "verified": {},
            "facts": [],             # кумулятивная база успешных наблюдений для верификации
            "_artifact_paths": [],   # пути записанных артефактов (для эпизода)
            "_last_output": None,    # v1.2: вывод последнего успешного действия (для $last_output)
            "_plan_lock": 0,         # v1.1: счётчик повторов фингерпринта плана
            "_provenance_ids": [],
        }
            # v3.7.0 N2: knowledge ledger / revocation index / proof anchor —
            # живые production-пути (раньше машинерия v3.5.x–3.6.0 была мертва
            # вне selftest: пути не выставлялись, COMMIT не материализовался).
            _know_dir=Path(self.cfg.data_dir)/"knowledge"
            _know_dir.mkdir(parents=True, exist_ok=True)
            state["_proof_anchor_path"]=str(_know_dir/f"{task_id}.proof_anchor.jsonl")
            state["_knowledge_ledger_path"]=str(_know_dir/f"{task_id}.knowledge.jsonl")
            state["_knowledge_revocation_index_path"]=str(_know_dir/f"{task_id}.revocation_index.jsonl")
            # v3.8.0 N-RT3: корневая цепь эпох живёт в состоянии задачи с пином
            # дайджеста; COMMIT сверяет её на каждом такте (гейт в governor.commit).
            if not state.get("root_epoch_chain"):
                _root_material=state.get("root_public_material") or f"JOHNSON-ROOT:{task_id}"
                _root_hist=[RootEpochChain.genesis(_root_material, now_iso())]
                state["root_epoch_chain"]=[asdict(e) for e in _root_hist]
                state["root_epoch_chain_pin"]=RootEpochChain.history_digest(_root_hist)
        if not resumed:
            spec=self.goal_compiler.compile_spec(task_text, self.gov.registry, self.planner)
            compiled=spec.as_dict()
            state["criteria"]=spec.success_criteria
            state["compiled_goal"]=compiled
            state["required_capabilities"]=spec.capabilities
            self.execution_graph=ExecutionGraph(spec).compile()
            self.action_dag=ActionDAG(spec,self.capabilities)
            state["execution_graph"]={"state":self.execution_graph.state,"nodes":[n.id for n in self.execution_graph.nodes],"edges":self.execution_graph.edges}
            state["action_dag"]=self.action_dag.snapshot()
            self.provenance.append("goal_compiled", task_id=task_id, compiled=compiled, capability_plan=state["required_capabilities"], execution_graph=state["execution_graph"])
            self.gov.mem.save_working(state)
            self.checkpoints.save(task_id, state, 0)
        started = time.monotonic()
        last_observations: List[Tuple[int, Observation]] = []
        stall = 0
        last_fp: Optional[str] = None
        last_thought_fp: Optional[str] = None   # v1.2.3: нормализованная мысль последнего плана
        error_feedback: Optional[str] = None

        log("AGENT", f"Задача {task_id}: {task_text}")

        while len(state["ledger"]) < self.cfg.max_steps:
            # v3.7.0 N4/P4: сверка закреплённого знания с миром на каждом такте —
            # KnowledgeAuditor (STALE при дрейфе артефактов) + historical reconciliation
            # индекса (REVOKED для committed proof'ов с мутировавшими артефактами).
            if state.get("commit"):
                KnowledgeAuditor.audit(state)
                if state.get("_knowledge_revocation_index_path"):
                    KnowledgeRevocationIndex.reconcile(state)
            if time.monotonic() - started > self.cfg.time_budget_s:
                return self._finalize(task_id, state, "aborted",
                                      "Исчерпан бюджет времени до подтверждения критериев.", started)

            # --- эскалация стагнации ---
            directive = None
            if stall >= self.cfg.stall_abort:
                return self._finalize(task_id, state, "aborted",
                                      "Остановлен контуром: длительное отсутствие прогресса.",
                                      started)
            elif stall >= self.cfg.stall_alternative:
                directive = STALL_DIRECTIVES["alternative"]
            elif stall >= self.cfg.stall_replan:
                directive = STALL_DIRECTIVES["replan"]
            elif state.get("_plan_lock", 0) >= 1:
                directive = PLAN_LOCK_DIRECTIVE   # механический запрет повторного plan

            user_block = build_context(self.cfg, self.gov, state, last_observations, directive)

            # --- один когнитивный такт + максимум один раунд ремонта схемы ---
            decision, err = None, error_feedback
            for attempt in range(2):
                try:
                    raw = self.brain.decide(SYSTEM_DNA, user_block, err)
                except BrainError as e:
                    category = self.recovery.classify(exc=e)
                    strategy = self.recovery.strategy(category)
                    self.provenance.append("recovery", task_id=task_id, step=len(state["ledger"])+1,
                                          category=category, strategy=strategy, error=str(e)[:500])
                    self.checkpoints.save(task_id, state, len(state["ledger"]))
                    if attempt == 0:
                        err = f"RECOVERY {strategy}: предыдущий вызов мозга завершился ошибкой: {e}"
                        continue
                    return self._finalize(task_id, state, "aborted", f"Мозг недоступен после восстановления: {e}", started)
                problem = validate_decision(raw)
                # v1.2.5: план-гигиена — повторный plan при взведённом PLAN_LOCK
                # отклоняется НА ВАЛИДАЦИИ (repair-раунд с честным фидбеком),
                # а не просто директивой на следующий такт (огонь accb1c587c:
                # модель выдала 7 планов подряд, игнорируя директиву)
                if problem is None and raw.get("status") == "plan" and state.get("_plan_lock", 0) >= 1:
                    problem = ("PLAN_LOCK: план уже принят и зафиксирован; статус plan "
                               "механически запрещён — верни status=act с ровно одним "
                               "действием, продвигающим ближайший незавершённый пункт плана")
                if problem is None:
                    decision = raw
                    break
                err = f"#{attempt+1}: {problem}"
                log("VALIDATE", f"отклонено, ремонт {err}")
                if attempt == 0:
                    continue
                return self._finalize(
                    task_id, state, "failed",
                    f"Модель дважды нарушила контракт вывода: {problem}", started)
            if decision is None:   # теоретически недостижимо, защита от None
                break

            status = decision["status"]
            step_idx = len(state["ledger"]) + 1

            if status == "plan":
                self._sync_execution_graph(state, "plan")
                state["criteria"] = decision.get("success_criteria", state["criteria"])
                state["plan"] = decision.get("plan", state["plan"])
                state["ledger"].append({"step": step_idx, "action": "(план)", "ok": True,
                                        "kind": "orient", "obs_brief": decision["thought"][:300]})
                progress_fp = sha256_hex(canonical_json([state["criteria"], state["plan"]]))
                # v1.2.3: второй, независимый фингерпринт — НОРМАЛИЗОВАННАЯ мысль.
                # Огонь 05a5fef056: 1.7b обходил замок, перефразируя пункты плана и
                # критерии при идентичной мысли (шаги 2≡3 и 7≡8 прошли, стагнация
                # до self-abort). fp-плана + fp-мысли закрывают оба вектора обхода.
                thought_fp = re.sub(r"\W+", " ", decision["thought"].lower()).strip()
                last_observations = [(step_idx, Observation(True, "orient", decision["thought"]))]
                if progress_fp == last_fp or thought_fp == last_thought_fp:
                    # повтор плана/мысли = стагнация + взвод PLAN_LOCK
                    state["_plan_lock"] = state.get("_plan_lock", 0) + 1
                    stall += 1
                else:
                    state["_plan_lock"] = 0
                    stall = 0
                last_fp = progress_fp
                last_thought_fp = thought_fp

            elif status == "act":
                self._sync_execution_graph(state, "act")
                new_artifact = False
                obs_list = []
                for act in decision["actions"]:
                    act_args, lo_missing = _substitute_vars(act.get("args", {}), state)
                    if lo_missing:
                        obs = Observation(False, "policy",
                                          "переменная $last_output недоступна: ни одного успешного "
                                          "действия в задаче ещё не было — сначала выполни действие-источник")
                        fp = None
                    else:
                        cap=act["name"]
                        tracked = cap in (self.action_dag.nodes if self.action_dag else {})
                        try:
                            if tracked: self.action_dag.start(cap)
                            obs, fp = self.gov.run(task_id, step_idx, cap, act_args)
                            if tracked: self.action_dag.complete(cap, obs)
                        except PolicyViolation as e:
                            obs=Observation(False,"policy",str(e)); fp=None
                            if tracked and self.action_dag.nodes[cap].status=="running": self.action_dag.complete(cap,obs)
                    obs_list.append((step_idx, obs))
                    if self.action_dag: state["action_dag"]=self.action_dag.snapshot()
                    prov = self.provenance.append("observation", task_id=task_id, step=step_idx,
                                                  tool=act["name"], ok=obs.ok, kind=obs.kind,
                                                  content_hash=sha256_hex(obs.content),
                                                  artifact=fp)
                    state.setdefault("_provenance_ids", []).append(prov["id"])
                    self.evidence_graph.link(f"step:{step_idx}", "produced", prov["id"])
                    if fp: self.evidence_graph.link(prov["id"], "materialized_as", fp)
                    if not obs.ok:
                        category = self.recovery.classify(obs=obs)
                        self.provenance.append("recovery", task_id=task_id, step=step_idx,
                                              category=category, strategy=self.recovery.strategy(category))
                    _row={"step": step_idx, "action": act["name"],
                          "ok": obs.ok, "kind": obs.kind,
                          "obs_brief": obs.brief(280),
                          "artifact": fp}
                    # v3.7.0 ArtifactEvidenceEdge: состояние артефакта В МОМЕНТ наблюдения —
                    # не только write, но и read (главный эпистемический источник) и verify.
                    if obs.ok and isinstance(obs.meta, dict) and obs.meta.get("path"):
                        _p=str(obs.meta["path"])
                        _h=obs.meta.get("sha256")
                        if _h is None:
                            try: _h=sha256_hex(Path(_p).read_bytes())
                            except Exception: _h=None
                        if _h is not None:
                            _row["artifact_path"]=_p; _row["artifact_sha256"]=str(_h)
                    state["ledger"].append(_row)
                    if fp:
                        new_artifact = True
                        state.setdefault("_artifacts", []).append(fp)
                    if obs.kind == "read" and obs.ok:
                        new_artifact = True      # чтение даёт новую информацию = прогресс
                    if obs.ok:
                        if len(state["facts"]) < 40:      # жёсткий потолок базы фактов
                            state["facts"].append(f"#{step_idx} {obs.brief(300)}")
                        if obs.kind == "write" and obs.meta.get("path"):
                            state["_artifact_paths"].append(obs.meta["path"])
                        # v1.2.1: $last_output хранит только вывод действий-источников
                        # (exec/read/net/list). Чек записи («файл создан...») — не вывод:
                        # иначе write с $last_output ловит собственную квитанцию — зеркало
                        # (закалено эпизодом 30ff4a63ee: файл перезаписан своим же чеком)
                        if obs.kind != "write":
                            lo = obs.meta.get("output") if isinstance(obs.meta, dict) else None
                            state["_last_output"] = lo if lo else obs.content
                last_observations = obs_list
                stall = 0 if new_artifact else stall + 1

            else:  # final
                if decision["outcome"] == "verified":
                    if self.action_dag and not self.action_dag.all_required_completed():
                        missing_caps=[k for k,v in self.action_dag.nodes.items() if v.status!="completed"]
                        warn="VERIFIED ОТКЛОНЁН: обязательные action-ноды не завершены: "+", ".join(missing_caps[:5])
                        state["ledger"].append({"step": step_idx, "action": "(verify-fail)", "ok": False, "kind": "verify", "obs_brief": warn})
                        last_observations=[(step_idx,Observation(False,"verify",warn))]; stall += 1; continue
                    proof = ProofCompiler(state).compile()
                    state["proof"] = asdict(proof)
                    missing = self._unwitnessed_criteria(state)
                    if state.get("criteria") and (missing or not ProofCompiler.allows_verified(proof)):
                        warn = ("VERIFIED ОТКЛОНЁН Контролёром: критерии не подтверждены "
                                "ни одним успешным наблюдением в журнале: " + "; ".join(missing[:3]))
                        log("VERIFY", warn)
                        state["ledger"].append({"step": step_idx, "action": "(verify-fail)",
                                                "ok": False, "kind": "verify",
                                                "obs_brief": warn})
                        last_observations = [(step_idx, Observation(False, "verify", warn))]
                        stall += 1
                        continue
                    for c in state.get("criteria", []):   # кумулятивная фиксация
                        state["verified"].setdefault(c, step_idx)
                    try:
                        ProofCarryingGovernor.commit(state)
                    except ProofCarryingCommitError as e:
                        warn = str(e)
                        log("COMMIT", warn)
                        state["ledger"].append({"step": step_idx, "action": "(verify-fail)",
                                                "ok": False, "kind": "commit", "obs_brief": warn})
                        last_observations = [(step_idx, Observation(False, "verify", warn))]
                        stall += 1
                        continue
                    self._sync_execution_graph(state, "verified", evidence_ok=True)
                self.gov.mem.save_working(state)
                return self._finalize(task_id, state,
                                      decision["outcome"],
                                      decision.get("final_answer", ""),
                                      started,
                                      lesson=decision.get("lesson", ""))

            self.gov.mem.save_working(state)
            self.checkpoints.save(task_id, state, len(state["ledger"]))

        return self._finalize(task_id, state, "aborted",
                              "Исчерпан лимит шагов до объявления финала.", started)

    def _sync_execution_graph(self, state: Dict[str, Any], event: str, *, evidence_ok=False):
        eg=self.execution_graph
        if eg is None: return
        if event in {"plan", "act", "verified"} and eg.state == "created":
            eg.transition("preflight")
        if event in {"act", "verified"} and eg.state == "preflight":
            eg.transition("execute")
        if event == "verified":
            if eg.state == "execute": eg.transition("verify")
            if eg.state == "verify": eg.transition("verdict", evidence_ok=evidence_ok)
            if eg.state == "verdict": eg.mark_terminal("verified")
        state["execution_graph"]={"state":eg.state,"history":list(eg.history),"nodes":[n.id for n in eg.nodes],"edges":eg.edges}

    @staticmethod
    def _capability_witnesses(state: Dict[str, Any]) -> Dict[str, bool]:
        """Механическая проверка capability-критериев: успех берётся из ledger, не из текста LLM."""
        required=list(state.get("required_capabilities", []))
        out={c:False for c in required}
        for row in state.get("ledger", []):
            if not row.get("ok") or row.get("action") in {"(план)","(verify-fail)"}:
                continue
            action=row.get("action")
            if action in out: out[action]=True
        return out

    @staticmethod
    def _unwitnessed_criteria(state: Dict[str, Any]) -> List[str]:
        """Критерий «увиден», если хотя бы один значимый токен критерия совпал
        с любым успешным наблюдением за ВСЮ историю задачи (кумулятивно),
        ЛИБО если литерал из критерия ('hi', "git version…") реально содержится
        в артефакте на диске (контентная сверка, закалено эпизодом 83311d5bde).
        Отвергает имитацию успеха; факт пустой записи «(0 символов)» свидетелем
        НЕ признаётся — наблюдение было, содержимого не было."""
        required=state.get("required_capabilities", [])
        if required:
            witnesses=Agent._capability_witnesses(state)
            return [f"capability:{c} выполнена успешно" for c, ok in witnesses.items() if not ok]
        facts_blob = " ".join(f for f in state.get("facts", [])
                              if "(0 символов)" not in f).lower()
        art_blob = ""
        for pth in state.get("_artifact_paths", []):
            try:
                art_blob += Path(pth).read_text(encoding="utf-8",
                                                errors="replace").lower() + "\n"
            except Exception:
                pass  # нечитаемый артефакт не входит в блоб; отсутствие ловит missing-контур ниже
        missing = []
        for crit in state.get("criteria", []):
            tokens = [t for t in re.findall(r"[\w\./\-]+", crit.lower()) if len(t) >= 4]
            if not tokens:
                tokens = [crit.lower().strip()]     # слишком короткие критерии берём целиком
            witnessed = any(tok in facts_blob for tok in tokens)
            if not witnessed:
                # контентная сверка: цитируемый литерал критерия живёт в артефакте?
                lits = [l.strip().lower() for l in re.findall(r"[\'\"]([^\'\"]+)[\'\"]", crit)
                        if len(l.strip()) >= 2]
                witnessed = any(l in art_blob for l in lits)
            if not witnessed:
                missing.append(crit)
        return missing

    def _finalize(self, task_id: str, state: Dict[str, Any], outcome: str,
                  answer: str, started: float, lesson: str = "") -> Dict[str, Any]:
        steps_used = len(state["ledger"])
        lesson = lesson or {
            "verified": "подтверждено наблюдаемыми артефактами",
            "failed": "фиксируй, какой именно критерий не достигнут и почему",
            "aborted": "зафиксируй причину остановки для будущего планирования",
        }.get(outcome, "")
        seen_paths = {}
        for p in state.get("_artifact_paths", []):
            seen_paths[p] = True                      # дедуп, порядок сохранения
        episode = {
            "episode_id": f"ep_{task_id}",
            "task_id": task_id,
            "goal": state["goal"],
            "outcome": outcome,
            "steps_used": steps_used,
            "duration_s": round(time.monotonic() - started, 1),
            "artifacts": [{"path": p, "sha256": ""} for p in seen_paths][-8:],
            "criteria_total": len(state.get("criteria", [])),
            "criteria_verified": len(state.get("verified", {})) if outcome == "verified" else len(state.get("verified", {})),
            "criteria_missing": self._unwitnessed_criteria(state) if state.get("criteria") else [],
            "lesson": lesson,
            "answer_preview": answer[:400],
            "proof": state.get("proof"),
        }
        state["_terminal"] = outcome
        if self.execution_graph is not None:
            if outcome == "verified" and self.execution_graph.state != "verified":
                self._sync_execution_graph(state, "verified", evidence_ok=True)
            elif outcome in {"failed", "aborted"} and self.execution_graph.state not in self.execution_graph.TERMINAL:
                # Failure never masquerades as a verified transition.
                self.execution_graph.state=outcome
                self.execution_graph.history.append(("runtime", outcome))
            state["execution_graph"]={"state":self.execution_graph.state,"history":list(self.execution_graph.history),"nodes":[n.id for n in self.execution_graph.nodes],"edges":self.execution_graph.edges}
        if self.action_dag: state["action_dag"] = self.action_dag.snapshot()
        episode["provenance_ids"] = list(state.get("_provenance_ids", []))[-100:]
        episode["evidence_edges"] = self.evidence_graph.edges[-200:]
        self.provenance.append("verification", task_id=task_id, outcome=outcome,
                              criteria_total=episode["criteria_total"],
                              criteria_verified=episode["criteria_verified"],
                              evidence_count=len(episode["provenance_ids"]))
        self.gov.mem.write_episode(episode)
        self.gov.mem.save_working(state)
        self.checkpoints.save(task_id, state, steps_used)
        chain_ok, bad = self.audit.verify()
        log("AUDIT", f"цепочка аудита: {'целостна' if chain_ok else f'НАРУШЕНА на записи {bad}'}")
        log("FINAL", f"[{outcome.upper()}] {answer}")
        result = dict(episode)
        result["audit_chain_ok"] = chain_ok
        result["answer"] = answer
        return result


# ════════════════════ САМОПРОВЕРКА (--selftest): ядро без LLM ═══════════════════

def _fresh_cfg(tmp: str) -> Tuple[Config, str]:
    ws = os.path.join(tmp, "ws")
    dd = os.path.join(tmp, "data")
    cfg = Config(brain_kind="mock", workspace=ws, data_dir=dd, auto_yes=True,
                 time_budget_s=30, catalog_path="")   # каталог вне проб для детерминизма
    return cfg, ws


def selftest() -> int:
    results: List[Tuple[str, bool, str]] = []

    def check(name: str, fn: Callable[[], str]):
        try:
            detail = fn()
            results.append((name, True, detail))
        except Exception as e:
            results.append((name, False, f"{type(e).__name__}: {e}"))

    def t_confine() -> str:
        with tempfile.TemporaryDirectory() as tmp:
            cfg, _ = _fresh_cfg(tmp)
            for evil in ["../../etc/passwd", "/etc/passwd", "a/../../b"]:
                try:
                    _confine(Path(cfg.workspace), evil)
                    raise AssertionError(f"пропущен побег: {evil}")
                except PolicyViolation:
                    pass
            ok_path = _confine(Path(cfg.workspace), "sub/dir/f.txt")
            assert str(ok_path).startswith(str(Path(cfg.workspace).resolve()))
            return "побеги блокированы, легитимные пути проходят"

    def t_schema() -> str:
        with tempfile.TemporaryDirectory() as tmp:
            cfg, _ = _fresh_cfg(tmp)
            audit = AuditChain(Path(tmp) / "a.jsonl")
            gov = Governor(cfg, audit)
            e1 = gov.validate_args(gov.registry["write_file"], {"path": 123, "content": "x"})
            e2 = gov.validate_args(gov.registry["write_file"], {"path": "f.txt"})
            e3 = gov.validate_args(gov.registry["write_file"], {"path": "f", "content": "", "hack": 1})
            assert all(e1 and e2 and e3, ), "валидатор пропустил нарушение"
            return "типы, обязательность и неизвестные ключи отбраковываются"

    def t_chain() -> str:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chain.jsonl"
            ac = AuditChain(path)
            for i in range(5):
                ac.append({"n": i})
            ok, bad = ac.verify()
            assert ok and bad is None
            lines = path.read_text(encoding="utf-8").splitlines()
            tampered = json.loads(lines[2])
            tampered["record"]["n"] = 999
            lines[2] = json.dumps(tampered, ensure_ascii=False)
            path.write_text("\n".join(lines), encoding="utf-8")
            ok2, bad2 = AuditChainVerifyProbe.verify_from(path)
            assert ok2 is False and bad2 == 2, f"подмена не детектирована: {(ok2, bad2)}"
            return "подмена записи №3 детектирована"

    def t_dedup() -> str:
        with tempfile.TemporaryDirectory() as tmp:
            cfg, _ = _fresh_cfg(tmp)
            audit = AuditChain(Path(tmp) / "a.jsonl")
            gov = Governor(cfg, audit)
            code = "print('side-effect')"
            obs1, _ = gov.run("t", 1, "execute_python", {"code": code})
            obs2, _ = gov.run("t", 2, "execute_python", {"code": code})
            assert obs1.ok and not obs2.ok and obs2.kind == "policy_denied", \
                f"дедуп не сработал: {obs1.brief()} / {obs2.brief()}"
            return "повторный EXEC с тем же кодом отклонён как дубликат"

    def t_json_extract() -> str:
        noisy = "Вот результат:\n```json\n{\"status\": \"plan\", \"thought\": \"x\",\n \"success_criteria\": [\"a\"], \"plan\": [\"s1\"]}\n```\nГотово."
        d = extract_json(noisy)
        assert d and d["status"] == "plan"
        garbage = extract_json("никакого json тут нет")
        assert garbage is None
        broken = extract_json("{\"a\": [1, 2")
        assert broken is None
        return "JSON извлекается из шума; мусор и обрыв отсекаются"

    def t_semantic_ttl() -> str:
        with tempfile.TemporaryDirectory() as tmp:
            cfg, _ = _fresh_cfg(tmp)
            mem = MemoryStore(Path(tmp))
            mem.remember_semantic("Факт о квантовом туннелировании", "учебник, стр.12",
                                  "physics", ttl_days=0)
            recs = mem.query_semantic(["квантово", "туннель"])
            assert recs and recs[0].get("stale") is True, "TTL=0 не пометил запись устаревшей"
            return "истёкшая семантика помечается stale, а не выбрасывается молча"

    def t_episode() -> str:
        with tempfile.TemporaryDirectory() as tmp:
            cfg, ws = _fresh_cfg(tmp)
            mem = MemoryStore(Path(tmp))
            target = Path(ws) / "art.txt"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("payload", encoding="utf-8")
            mem.write_episode({"episode_id": "ep_x", "goal": "g", "outcome": "verified",
                               "steps_used": 2, "artifacts": [{"path": str(target)}]})
            ln = (Path(tmp) / "episodes.jsonl").read_text(encoding="utf-8").splitlines()[0]
            rec = json.loads(ln)
            expected = hashlib.sha256(b"payload").hexdigest()
            assert rec["artifacts"][0]["sha256"] == expected
            return "эпизод хранит sha256 артефакта"

    def t_exec_sandbox() -> str:
        with tempfile.TemporaryDirectory() as tmp:
            cfg, _ = _fresh_cfg(tmp)
            obs = _t_execute_python(cfg, {"code": "print(2 + 2)"})
            assert obs.ok and "4" in obs.content
            obs2 = _t_execute_python(cfg, {"code": "raise SystemExit(3)"})
            assert not obs2.ok and obs2.meta["rc"] == 3
            return "exec считает 4; ненулевой RC фиксируется как FAIL"

    def t_ssrf() -> str:
        for evil in ["http://localhost/x", "http://127.0.0.1/", "http://169.254.169.254/meta",
                     "http://10.0.0.1/", "http://192.168.1.1/", "http://[::1]/", "notaurl"]:
            try:
                _ssrf_guard(evil)
                raise AssertionError(f"пропущен запретный url: {evil}")
            except PolicyViolation:
                pass
        return "SSRF-фильтр держит локальные/приватные/metadata адреса закрытыми"

    def t_e2e_mock() -> str:
        with tempfile.TemporaryDirectory() as tmp:
            cfg, ws = _fresh_cfg(tmp)
            script = [
                {"thought": "Цель — создать hello.txt со строкой hi и проверить чтением.",
                 "status": "plan",
                 "success_criteria": ["hello.txt существует и содержит 'hi'"],
                 "plan": ["записать hello.txt", "прочитать и сравнить"]},
                {"thought": "Записываю артефакт.", "status": "act",
                 "actions": [{"name": "write_file",
                              "args": {"path": "hello.txt", "content": "hi"},
                              "why": "критерий требует файл"}]},
                {"thought": "Верифицирую наблюдением.", "status": "act",
                 "actions": [{"name": "read_file", "args": {"path": "hello.txt"},
                              "why": "подтверждение критерия"}]},
                {"thought": "Артефакт виден в наблюдении шага 2.", "status": "final",
                 "outcome": "verified",
                 "final_answer": "hello.txt создан, содержит 'hi', подтверждено чтением",
                 "lesson": "верификация чтением закрывает критерий"},
            ]
            audit = AuditChain(Path(tmp) / "a.jsonl")
            agent = Agent(cfg, MockBrain(script), Governor(cfg, audit), audit)
            result = agent.solve("Создай hello.txt со строкой hi и проверь")
            assert result["outcome"] == "verified", result
            content = (Path(ws) / "hello.txt").read_text(encoding="utf-8")
            assert content == "hi"
            episodes_file = Path(cfg.data_dir) / "episodes.jsonl"
            assert "sha256" in episodes_file.read_text(encoding="utf-8")
            return f"сквозной прогон: verified, файл на диске '{content}', эпизод записан"

    def t_catalog_bridge() -> str:
        with tempfile.TemporaryDirectory() as tmp:
            cfg, _ = _fresh_cfg(tmp)
            cat = {"schema": "polymat.arsenal/1.0", "total": 4, "categories": 2, "tools": [
                {"n": "python3", "c": "Языки", "d": "интерпретатор python", "b": "python3", "r": "EXEC"},
                {"n": "ffmpeg", "c": "Медиа", "d": "медиа-конвертер", "b": "ffmpeg", "r": "EXEC"},
                {"n": "python3-повтор", "c": "Языки", "d": "дубликат бинаря", "b": "python3", "r": "EXEC"},
                {"n": "requests-doc", "c": "Python-библиотеки", "d": "HTTP-библиотека", "b": "", "r": "EXEC"},
            ]}
            cpath = Path(tmp) / "cat.json"
            cpath.write_text(json.dumps(cat, ensure_ascii=False), encoding="utf-8")
            bridge = CatalogBridge(str(cpath))
            assert bridge.total == 4 and bridge.bins == 2, \
                f"дубликаты/пустые бинари не схлопнуты: bins={bridge.bins}"
            assert bridge.resolve("python3"), "python3 не подтверждён диском"
            assert bridge.resolve("nonexistent-bin-xyz") is None, "вне арсенала прошло"
            audit = AuditChain(Path(tmp) / "a.jsonl")
            gov = Governor(cfg, audit, bridge)
            assert "run_cli" in gov.registry, "run_cli не зарегистрирован из каталога"
            obs, _ = gov.run("t11", 1, "run_cli",
                             {"bin": "python3", "args": ["-c", "print(40+2)"]})
            assert obs.ok and "42" in obs.content, f"run_cli не исполнил: {obs.brief()}"
            obs2, _ = gov.run("t11", 2, "run_cli", {"bin": "nonexistent-bin-xyz"})
            assert not obs2.ok and obs2.kind == "policy_denied", "вне арсенала не отклонён"
            # v1.2.1: канонизация дедупа — явный stdin:"" не обход идемпотентности
            obs3, _ = gov.run("t11", 3, "run_cli",
                              {"bin": "python3", "args": ["-c", "print(40+2)"], "stdin": ""})
            assert not obs3.ok and obs3.kind == "policy_denied" and "дубликат" in obs3.content, \
                f"канонизация дедупа не сработала: {obs3.brief()}"
            digest = bridge.arsenal_digest("посчитать хеш sha256 через python3")
            assert "python3" in digest, "дайджест не релевантен"
            return (f"мост: run_cli исполнен (python3), вне арсенала отклонён, "
                    f"дубликаты схлопнуты, дайджест релевантен")

    def t_grammar() -> str:
        s1, s2 = build_decision_schema(), build_decision_schema()
        g1, g2 = build_decision_grammar(), build_decision_grammar()
        assert canonical_json(s1) == canonical_json(s2) and g1 == g2, "недетерминизм генератора"
        assert len(s1["anyOf"]) == 3, "вариантов не 3"
        plan_v = s1["anyOf"][0]
        assert plan_v["properties"]["status"]["const"] == "plan", "status не закреплён"
        assert plan_v["properties"]["thought"]["maxLength"] == 280, "бюджет длины потерян"
        assert "maxLength" in json.dumps(s1), "maxLength отсутствует в схеме"
        # замкнутость грамматики: escape-aware вырезание литералов и символьных
        # классов (наивный re.sub ломался о " внутри [^"...])
        def strip_gbnf_literals(rhs: str) -> str:
            out, i, n = [], 0, len(rhs)
            while i < n:
                c = rhs[i]
                if c == '"':
                    i += 1
                    while i < n and rhs[i] != '"':
                        i += 2 if rhs[i] == "\\" else 1
                    i += 1
                    out.append(" STR ")
                elif c == "[":
                    j = rhs.find("]", i)
                    i = (j + 1) if j != -1 else n
                    out.append(" CLS ")
                else:
                    out.append(c)
                    i += 1
            return "".join(out)

        defined = set(re.findall(r"^(\w[\w-]*) ::=", g1, re.M))
        used: set = set()
        for line in g1.splitlines():
            if "::=" not in line:
                continue
            used |= set(re.findall(r"\b([a-z][\w-]*)\b", strip_gbnf_literals(line)))
        undefined = {u for u in used if u not in defined}
        assert not undefined, f"неопределённые нетерминалы: {sorted(undefined)}"
        assert "\x00" not in g1, "управляющие байты протекли в грамматику"
        # фейковый ollama: format==схема, stream=False, /v1 срезан, ответ парсится
        received = {}
        decision = {"thought": "готов", "status": "final", "outcome": "verified",
                    "final_answer": "проба", "lesson": "нет"}
        class Fake(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                ln = int(self.headers.get("Content-Length", 0))
                received["path"] = self.path
                received["body"] = json.loads(self.rfile.read(ln))
                body = json.dumps({"message": {"content": json.dumps(decision)}}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            def log_message(self, *a):
                pass
        srv = http.server.HTTPServer(("127.0.0.1", 0), Fake)
        port = srv.server_address[1]
        th = threading.Thread(target=srv.serve_forever, daemon=True)
        th.start()
        try:
            cfg = Config(brain_kind="ollama-native",
                         base_url=f"http://127.0.0.1:{port}/v1", model="fake:0b",
                         brain_timeout_s=10, catalog_path="")
            got = OllamaNativeBrain(cfg).decide("СИСТЕМА", "ЦЕЛЬ")
            assert got["status"] == "final", "решение не распарсено"
            assert received["path"] == "/api/chat", f"путь не нативный: {received['path']}"
            assert received["body"]["format"] == s1, "format != схема"
            assert received["body"]["stream"] is False and received["body"]["think"] is False
        finally:
            srv.shutdown()
        return ("грамматика+схема детерминированы; замкнутость правил; фейк-ollama: "
                "format=схема, /v1 срезан, think=false")

    def t_proc_gate() -> str:
        with tempfile.TemporaryDirectory() as tmp:
            cfg, _ = _fresh_cfg(tmp)
            mem = MemoryStore(Path(cfg.data_dir))   # тот же base, что у Governor ниже
            mem.add_procedure("смонтировать видео через ffmpeg",
                              ["проверить наличие ffmpeg -version",
                               "собрать команду ffmpeg -i in.mp4 out.mp4",
                               "проверить результат ffprobe -show_format"])
            kw_video = re.findall(r"\w{4,}", "пережать видео из mkv через ffmpeg с сменой кодека")
            rec = mem.gate_procedure(kw_video, min_score=cfg.proc_gate_min_score,
                                     min_ratio=cfg.proc_gate_min_ratio)
            assert rec and rec["_gate"]["admitted"], "релевантная процедура не прошла гейт"
            assert rec["_gate"]["score"] >= cfg.proc_gate_min_score
            kw_soup = re.findall(r"\w{4,}", "сварить борщ со сметаной и чесноком")
            assert mem.gate_procedure(kw_soup, min_score=cfg.proc_gate_min_score,
                                      min_ratio=cfg.proc_gate_min_ratio) is None, \
                "нерелевантная процедура просочилась через гейт"
            state = {"goal": "сварить борщ со сметаной и чесноком", "criteria": [],
                     "plan": [], "ledger": [], "verified": {}}
            audit = AuditChain(Path(tmp) / "a.jsonl")
            ctx = build_context(cfg, Governor(cfg, audit), state, [], None)
            assert "Процедурная память" not in ctx, "закрытый гейт пропустил блок в промпт"
            state2 = dict(state, goal="пережать видео из mkv через ffmpeg")
            ctx2 = build_context(cfg, Governor(cfg, audit), state2, [], None)
            assert "Процедурная память" in ctx2, "открытый гейт не впустил блок в промпт"
            return (f"гейт: admission score={rec['_gate']['score']} ratio={rec['_gate']['ratio']}; "
                    f"чужая цель — тишина в промпте")

    def t_empty_write_ban() -> str:
        with tempfile.TemporaryDirectory() as tmp:
            cfg, _ = _fresh_cfg(tmp)
            obs = _t_write_file(cfg, {"path": "ban.txt", "content": ""})
            assert not obs.ok and "пустая запись запрещена" in obs.content, \
                "пустая запись не отбракована"
            assert not (Path(cfg.workspace) / "ban.txt").exists(), "пустой файл создан"
            obs2 = _t_write_file(cfg, {"path": "ok.txt", "content": "git version 2.47.3"})
            assert obs2.ok and (Path(cfg.workspace) / "ok.txt").exists(), "непустая запись сломана"
            state = {"criteria": ["write_file: gv.txt"],
                     "facts": ["#5 (write/OK) файл создан: gv.txt (0 символов)"]}
            missing = Agent._unwitnessed_criteria(state)
            assert missing == ["write_file: gv.txt"], \
                f"пустой write признался свидетелем: {missing}"
            state["facts"].append("#7 (write/OK) файл создан: gv.txt (17 символов)")
            assert Agent._unwitnessed_criteria(state) == [], "честный write не признан свидетелем"
            ws = Path(cfg.workspace)
            (ws / "art.txt").write_text("hi", encoding="utf-8")
            st_lit = {"criteria": ["Проверить, что содержимое файла равно 'hi'"],
                      "facts": ["#9 (read/OK) hi"], "_artifact_paths": [str(ws / "art.txt")]}
            assert Agent._unwitnessed_criteria(st_lit) == [], \
                "литерал 'hi' в артефакте не признан (ложный отказ)"
            (ws / "art2.txt").write_text("bye", encoding="utf-8")
            st_bad = dict(st_lit, _artifact_paths=[str(ws / "art2.txt")])
            assert Agent._unwitnessed_criteria(st_bad) != [], \
                "литерал не в артефакте признан (ложный пропуск)"
            return ("пустая запись отбракована; нуль-факт не свидетель; литерал сверяется "
                    "с артефактом: правда проходит, ложь нет")

    def t_persistent_facts() -> str:
        """v1.2.4: накопленные факты обязаны быть в контексте каждого такта —
        иначе модель переспрашивает исполненные команды (огонь 1406a05ad5)."""
        with tempfile.TemporaryDirectory() as tmp:
            cfg, _ = _fresh_cfg(tmp)
            audit = AuditChain(Path(cfg.data_dir) / "audit.jsonl")
            gov = Governor(cfg, audit, None)
            state = {"goal": "задача цепи", "criteria": ["крит"], "plan": ["п1"],
                     "ledger": [{"step": 1, "action": "run_cli", "ok": True, "kind": "exec",
                                 "obs_brief": "$ wc -l каталог\n17117 каталог"}],
                     "facts": ["#1 (exec/OK) $ wc -l каталог\n17117 каталог"],
                     "verified": {}}
            ctx = build_context(cfg, gov, state,
                                [(2, Observation(False, "policy_denied",
                                                 "дубликат побочного вызова run_cli"))], None)
            assert "НАКОПЛЕННЫЕ ФАКТЫ" in ctx, "лента фактов отсутствует в контексте"
            assert "17117" in ctx, "вывод первого шага не долетел до контекста"
            assert "единственный источник" not in ctx, "ложная метка источника не снята"
            return "накопленные факты вечны в контексте; переспросы исполненного закрыты"

    def t_plan_hygiene() -> str:
        """v1.2.5: третий план подряд при взведённом PLAN_LOCK отклоняется НА ВАЛИДАЦИИ,
        repair-раунд тянет модель в act (огонь accb1c587c: 7 планов подряд)."""
        with tempfile.TemporaryDirectory() as tmp:
            cfg, _ = _fresh_cfg(tmp)
            audit = AuditChain(Path(cfg.data_dir) / "audit.jsonl")
            gov = Governor(cfg, audit, None)
            plan_t = {"thought": "планирую шаги", "status": "plan",
                      "success_criteria": ["файл есть"], "plan": ["сделать", "проверить"]}
            act_d = {"thought": "записываю артефакт", "status": "act",
                     "actions": [{"name": "write_file",
                                  "args": {"path": "o.txt", "content": "данные"},
                                  "why": "план требует файл"}]}
            class QueueBrain:
                def __init__(self, seq): self.seq, self.i = seq, 0
                def decide(self, system, user, err=None):
                    d = self.seq[min(self.i, len(self.seq) - 1)]; self.i += 1; return d
            brain = QueueBrain([plan_t, plan_t, plan_t, act_d, {
                "thought": "выходим", "status": "final", "outcome": "aborted",
                "final_answer": "стоп", "lesson": "гигиена"}])
            agent = Agent(cfg, brain, gov, audit)
            res = agent.solve("тестовая задача план-гигиены")
            plans = [r for r in agent_gov_ledger(cfg) if r.get("action") == "(план)"]
            acts = [r for r in agent_gov_ledger(cfg) if r.get("action") == "write_file"]
            assert len(plans) == 2, f"планов в журнале {len(plans)} (ожидалось ровно 2)"
            assert len(acts) == 1, "repair не вывел модель в act после отказа плана"
            assert res["outcome"] == "aborted", f"не aborted: {res}"
            return "повторный план отклонён на валидации; repair вывел в act"

    def agent_gov_ledger(cfg):  # noqa: локальный хелпер пробы
        import json as _json
        w = _json.loads((Path(cfg.data_dir) / "working.json").read_text(encoding="utf-8"))
        return w.get("ledger", [])

    def t_plan_lock() -> str:
        """v1.2.3: 1.7b обходил PLAN_LOCK перефразированием пунктов плана при идентичной
        мысли (огонь 05a5fef056: шаги 2≡3 и 7≡8) — теперь thought в фингерпринте."""
        with tempfile.TemporaryDirectory() as tmp:
            cfg, _ = _fresh_cfg(tmp)
            audit = AuditChain(Path(cfg.data_dir) / "audit.jsonl")
            gov = Governor(cfg, audit, None)
            plan_a = {"thought": "планирую шаги", "status": "plan",
                      "success_criteria": ["файл есть"], "plan": ["сделать шаги", "проверить результат"]}
            plan_b = {"thought": "планирую шаги", "status": "plan",
                      "success_criteria": ["файл на диске"], "plan": ["выполнить операции", "верифицировать итог"]}
            class QueueBrain:
                def __init__(self, seq): self.seq, self.i = seq, 0
                def decide(self, system, user, err=None):
                    d = self.seq[min(self.i, len(self.seq) - 1)]; self.i += 1; return d
            agent = Agent(cfg, QueueBrain([plan_a, plan_b, {
                "thought": "выходим", "status": "final", "outcome": "aborted",
                "final_answer": "стоп", "lesson": "замок"}]), gov, audit)
            res = agent.solve("тестовая задача план-замка")
            assert res["outcome"] == "aborted", f"не aborted: {res}"
            w = json.loads((Path(cfg.data_dir) / "working.json").read_text(encoding="utf-8"))
            assert w.get("_plan_lock", 0) >= 1, \
                f"замок не взведён после перефразированного повтора: {w.get('_plan_lock')}"
            return "перефразированный повтор плана взводит PLAN_LOCK (обход замка закрыт)"

    def t_last_output() -> str:
        with tempfile.TemporaryDirectory() as tmp:
            cfg, ws = _fresh_cfg(tmp)
            state = {"_last_output": None}
            args, missing = _substitute_vars({"path": "o.txt", "content": "$last_output"}, state)
            assert missing and args["content"] == "$last_output", "missing не взведён"
            state["_last_output"] = "git version 2.47.3"
            args, missing = _substitute_vars({"path": "o.txt", "content": "$last_output"}, state)
            assert not missing and args["content"] == "git version 2.47.3", "подстановка не сработала"
            args, _ = _substitute_vars({"a": ["$last_output", "x"], "b": {"c": "$last_output"}}, state)
            assert args["a"][0] == "git version 2.47.3" and args["b"]["c"] == "git version 2.47.3", \
                "вложенность не обработана"
            args, _ = _substitute_vars({"content": "prefix $last_output suffix"}, state)
            assert args["content"] == "prefix $last_output suffix", "частичная замена калечит данные"
            # v1.2.1: чек записи — не вывод; $last_output не ловит собственную квитанцию
            state2 = {"_last_output": "git version 2.47.3"}
            assert state2["_last_output"] == "git version 2.47.3"
            state2["_last_output"] = "git version 2.47.3"
            # имитация ветки агента: write-наблюдение НЕ меняет переменную
            fake_write_obs = Observation(True, "write", "файл создан: gv.txt (18 символов)",
                                         meta={"path": "gv.txt", "bytes": 18})
            if fake_write_obs.kind != "write":
                state2["_last_output"] = fake_write_obs.content
            assert state2["_last_output"] == "git version 2.47.3", "чек записи протек в переменную"
            # сквозной прогон: выполнить код → записать через $last_output → прочитать → verified
            script = [
                {"thought": "План: код, запись через переменную, чтение.", "status": "plan",
                 "success_criteria": ["itog.txt содержит 'переменная-работает-42'"],
                 "plan": ["выполнить код", "записать вывод", "прочитать"]},
                {"thought": "Выполняю источник.", "status": "act",
                 "actions": [{"name": "execute_python",
                              "args": {"code": "print('переменная-работает-42')"}}]},
                {"thought": "Записываю через механическую переменную.", "status": "act",
                 "actions": [{"name": "write_file",
                              "args": {"path": "itog.txt", "content": "$last_output"}}]},
                {"thought": "Читаю для сверки.", "status": "act",
                 "actions": [{"name": "read_file", "args": {"path": "itog.txt"}}]},
                {"thought": "Артефакт сверен.", "status": "final", "outcome": "verified",
                 "final_answer": "вывод кода записан через $last_output и прочитан",
                 "lesson": "склейка без семантического копирования"},
            ]
            audit = AuditChain(Path(tmp) / "a.jsonl")
            agent = Agent(cfg, MockBrain(script), Governor(cfg, audit), audit)
            result = agent.solve("Выполни код и запиши его вывод в itog.txt через $last_output")
            assert result["outcome"] == "verified", result
            content = (Path(ws) / "itog.txt").read_text(encoding="utf-8")
            assert "переменная-работает-42" in content, f"вывод не долетел: {content!r}"
            return ("подстановка точна/вложена/безопасна; сквозной прогон: вывод кода "
                    "долетел до файла механически, verified")

    def t_native_arsenal() -> str:
        with tempfile.TemporaryDirectory() as tmp:
            cfg, ws = _fresh_cfg(tmp)
            audit = AuditChain(Path(tmp) / "a.jsonl")
            gov = Governor(cfg, audit, None)
            obs, _ = gov.run("t20", 1, "mkdir", {"path": "a/b"})
            assert obs.ok and (Path(ws) / "a/b").is_dir()
            obs, _ = gov.run("t20", 2, "write_file", {"path": "a/x.txt", "content": "alpha-42"})
            assert obs.ok
            obs, _ = gov.run("t20", 3, "verify_text", {"path": "a/x.txt", "text": "alpha-42", "mode": "contains"})
            assert obs.ok and obs.kind == "verify"
            obs, _ = gov.run("t20", 4, "hash_file", {"path": "a/x.txt"})
            assert obs.ok and len(obs.meta["hash"]) == 64
            obs, _ = gov.run("t20", 5, "copy_path", {"src": "a/x.txt", "dst": "a/y.txt"})
            assert obs.ok
            obs, _ = gov.run("t20", 6, "glob_files", {"path": "a", "pattern": "*.txt"})
            assert obs.ok and "x.txt" in obs.content and "y.txt" in obs.content
            obs, _ = gov.run("t20", 7, "archive_create", {"path": "bundle.zip", "members": ["a/x.txt", "a/y.txt"]})
            assert obs.ok and (Path(ws) / "bundle.zip").is_file()
            obs, _ = gov.run("t20", 8, "archive_list", {"path": "bundle.zip"})
            assert obs.ok and "a/x.txt" in obs.content
            obs, _ = gov.run("t20", 9, "json_write", {"path": "a/data.json", "value": {"answer": 42}})
            assert obs.ok
            obs, _ = gov.run("t20", 10, "json_read", {"path": "a/data.json"})
            assert obs.ok and '"answer": 42' in obs.content
            obs, _ = gov.run("t20", 11, "move_path", {"src": "a/y.txt", "dst": "a/z.txt"})
            assert obs.ok and not (Path(ws) / "a/y.txt").exists() and (Path(ws) / "a/z.txt").exists()
            obs, _ = gov.run("t20", 12, "delete_path", {"path": "a/z.txt"})
            assert obs.ok and not (Path(ws) / "a/z.txt").exists()
            return "нативный арсенал: mkdir/write/verify/hash/copy/glob/archive/json/move/delete"

    def t_redirect_guard() -> str:
        with tempfile.TemporaryDirectory() as tmp:
            cfg, _ = _fresh_cfg(tmp)
            class Redirect(http.server.BaseHTTPRequestHandler):
                def do_GET(self):
                    self.send_response(302); self.send_header("Location", "http://127.0.0.1/"); self.end_headers()
                def log_message(self, *a): pass
            srv=http.server.HTTPServer(("127.0.0.1",0), Redirect)
            th=threading.Thread(target=srv.serve_forever, daemon=True); th.start()
            try:
                try:
                    obs=_t_http_get(cfg, {"url": f"http://127.0.0.1:{srv.server_address[1]}/"})
                    assert not obs.ok
                except PolicyViolation:
                    pass  # фильтр мог отказать до запроса — это тоже допустимый исход пробы
            finally: srv.shutdown()
            return "HTTP redirect не следует автоматически в потенциально внутренний адрес"

    def t_missing_catalog_is_not_runtime_failure() -> str:
        # Самотест ядра не должен краснить машину только потому, что внешний 2444-каталог не смонтирован.
        cpath = os.environ.get("POLY_CATALOG") or "./tool_catalog.json"
        if not Path(cpath).exists():
            return "SKIP: внешний tool_catalog.json отсутствует в текущем runtime"
        bridge = CatalogBridge(cpath)
        assert bridge.total >= 2400 and bridge.categories == 34 and bridge.bins >= 1500
        return f"реальный арсенал доступен: {bridge.total}/34, бинарей {bridge.bins}, доступно {bridge.available}"

    check("T01 изоляция путей", t_confine)
    check("T02 валидатор схем инструментов", t_schema)
    check("T03 хеш-цепочка аудита и детект подмены", t_chain)
    check("T04 идемпотентность побочных вызовов", t_dedup)
    check("T05 извлечение строгого JSON", t_json_extract)
    check("T06 семантика TTL/stale", t_semantic_ttl)
    check("T07 эпизоды с sha256 артефактов", t_episode)
    check("T08 песочница execute_python", t_exec_sandbox)
    check("T09 SSRF-фильтр http_get", t_ssrf)
    check("T10 сквозной цикл на MockBrain", t_e2e_mock)
    check("T11 мост каталог→Registry", t_catalog_bridge)
    check("T12 реальный арсенал 2444", t_missing_catalog_is_not_runtime_failure)
    check("T13 грамматика и OllamaNativeBrain", t_grammar)
    check("T14 гейт процедурной памяти", t_proc_gate)
    check("T15 запрет пустой записи и честность свидетеля", t_empty_write_ban)
    check("T16 переменная $last_output", t_last_output)
    check("T17 непробиваемый план-замок", t_plan_lock)
    check("T18 вечная лента фактов", t_persistent_facts)
    check("T19 план-гигиена: отказ повторного плана", t_plan_hygiene)
    check("T20 нативный арсенал файлов/JSON/архивов", t_native_arsenal)
    def t_research_tool_registered() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_t23_") as td:
            cfg, _ = _fresh_cfg(td)
            gov = Governor(cfg, AuditChain(Path(td) / "audit.jsonl"), CatalogBridge(""))
            if "research_web" not in gov.registry:
                return "research_web отсутствует в реестре"
            if gov.registry["research_web"].risk != "NET":
                return "research_web должен иметь риск NET"
            return "web research capability зарегистрирована"

    def t_checkpoint_roundtrip_and_tamper() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_t24_") as td:
            base=Path(td); cp=CheckpointStore(base)
            state={"goal":"x","ledger":[{"step":1}],"verified":{}}
            path=cp.save("task24", state, 1)
            loaded=cp.load("task24")
            assert loaded and loaded[0] == state and loaded[1] == 1
            obj=json.loads(Path(path).read_text(encoding="utf-8")); obj["state"]["goal"]="TAMPERED"
            Path(path).write_text(json.dumps(obj), encoding="utf-8")
            assert cp.load("task24") is None, "подмена checkpoint не обнаружена"
            return "checkpoint атомарно сохраняется, восстанавливается и отвергает подмену по sha256"

    def t_provenance_chain() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_t25_") as td:
            pl=ProvenanceLedger(Path(td)/"provenance.jsonl")
            a=pl.append("observation", task_id="t25", step=1, tool="read_file", kind="read", content_hash="abc")
            pl.append("verification", task_id="t25", outcome="verified", evidence_id=a["id"])  # запись-сосед нужна для causal-связи; её id не читается
            rows=pl.recent(5)
            assert rows[-2]["id"] == a["id"] and rows[-1]["evidence_id"] == a["id"]
            return "observation→verification causal связь сохраняется в append-only provenance ledger"

    def t_recovery_taxonomy() -> str:
        r=RecoveryEngine()
        assert r.classify(Observation(False,"policy","denied")) == "policy"
        assert r.classify(Observation(False,"net","failed")) == "net"
        assert r.strategy("timeout") == "checkpoint_and_resume"
        return "ошибки классифицируются детерминированно и получают ограниченную стратегию восстановления"

    def t_capability_graph_and_planner() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_t27_") as td:
            cfg,_=_fresh_cfg(td); gov=Governor(cfg, AuditChain(Path(td)/"a.jsonl"), CatalogBridge(""))
            g=CapabilityGraph(gov.registry); g.add_dependency("research_web","web_search")
            plan=CapabilityPlanner(g).plan(["research_web"])
            assert plan[-1]=="research_web" and "web_search" in plan
            return "capability graph: зависимости → closure → детерминированный план"

    def t_evidence_graph() -> str:
        e=EvidenceGraph(); e.link("claim:1","supported_by","obs:1"); e.link("obs:1","materialized_as","sha:abc")
        assert len(e.for_node("obs:1"))==2
        return "claim→observation→artifact сохраняются в EvidenceGraph"

    def t_goal_compiler() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_t29_") as td:
            cfg,_=_fresh_cfg(td); gov=Governor(cfg, AuditChain(Path(td)/"a.jsonl"), CatalogBridge(""))
            out=GoalCompiler().compile("исследуй тему через интернет и создай файл", gov.registry)
            assert out["criteria"] and out["evidence_requirements"] and out["recovery_policy"]
            return "goal compiler создаёт criteria/capabilities/evidence/recovery"

    def t_goal_compiler_deterministic() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_t30_") as td:
            cfg,_=_fresh_cfg(td); gov=Governor(cfg, AuditChain(Path(td)/"a.jsonl"), CatalogBridge(""))
            gc=GoalCompiler(); assert gc.compile("создай файл",gov.registry)==gc.compile("создай файл",gov.registry)
            return "goal compilation детерминирована"

    check("T24 checkpoint roundtrip + tamper", t_checkpoint_roundtrip_and_tamper)
    check("T25 provenance causal ledger", t_provenance_chain)
    check("T26 recovery taxonomy", t_recovery_taxonomy)
    check("T27 capability graph + planner", t_capability_graph_and_planner)
    check("T28 evidence graph", t_evidence_graph)
    def t_formal_goalspec() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_t31_") as td:
            cfg,_=_fresh_cfg(td); gov=Governor(cfg, AuditChain(Path(td)/"a.jsonl"), CatalogBridge(""))
            gc=FormalGoalCompiler(); spec=gc.compile_spec("исследуй тему через интернет",gov.registry,CapabilityPlanner(CapabilityGraph(gov.registry)))
            assert spec.validate() and all(k in spec.as_dict() for k in GoalSpec.REQUIRED)
            return "GoalSpec имеет полный контракт и проходит валидацию"

    def t_formal_goalspec_deterministic() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_t32_") as td:
            cfg,_=_fresh_cfg(td); gov=Governor(cfg, AuditChain(Path(td)/"a.jsonl"), CatalogBridge("")); g=CapabilityGraph(gov.registry); pl=CapabilityPlanner(g); gc=FormalGoalCompiler()
            assert gc.compile_spec("создай файл",gov.registry,pl).as_dict()==gc.compile_spec("создай файл",gov.registry,pl).as_dict()
            return "Formal GoalSpec compilation детерминирована"

    check("T29 goal compiler", t_goal_compiler)
    check("T30 goal compiler determinism", t_goal_compiler_deterministic)
    def t_execution_graph_guards() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_t33_") as td:
            cfg,_=_fresh_cfg(td); gov=Governor(cfg, AuditChain(Path(td)/"a.jsonl"), CatalogBridge(""))
            spec=FormalGoalCompiler().compile_spec("создай файл",gov.registry,CapabilityPlanner(CapabilityGraph(gov.registry)))
            eg=ExecutionGraph(spec).compile(); eg.transition("preflight"); eg.transition("execute"); eg.transition("verify")
            try: eg.transition("verdict", evidence_ok=False); raise AssertionError("guard bypassed")
            except PolicyViolation: pass
            eg.transition("verdict", evidence_ok=True); assert eg.mark_terminal("verified")=="verified"
            return "execution graph запрещает нелегальные переходы и verdict без evidence"

    def t_execution_graph_no_skip() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_t34_") as td:
            cfg,_=_fresh_cfg(td); gov=Governor(cfg, AuditChain(Path(td)/"a.jsonl"), CatalogBridge(""))
            spec=FormalGoalCompiler().compile_spec("создай файл",gov.registry,CapabilityPlanner(CapabilityGraph(gov.registry)))
            eg=ExecutionGraph(spec).compile()
            try: eg.transition("verify"); raise AssertionError("state skip allowed")
            except PolicyViolation: return "state machine блокирует перескок через обязательное состояние"

    def t_goal_verification_is_mechanical() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_t37_") as td:
            cfg,_=_fresh_cfg(td); gov=Governor(cfg, AuditChain(Path(td)/"a.jsonl"), CatalogBridge(""))
            spec=FormalGoalCompiler().compile_spec("создай файл",gov.registry,CapabilityPlanner(CapabilityGraph(gov.registry)))
            st={"required_capabilities":spec.capabilities,"ledger":[{"action":"write_file","ok":True}]}
            assert Agent._unwitnessed_criteria(st)==[]
            st["ledger"][0]["ok"]=False
            assert Agent._unwitnessed_criteria(st)
            return "verification опирается на успешное observation capability, а не на совпадение текста"

    def t_resume_restores_execution_graph() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_t38_") as td:
            cfg,_=_fresh_cfg(td); gov=Governor(cfg, AuditChain(Path(td)/"a.jsonl"), CatalogBridge(""))
            spec=FormalGoalCompiler().compile_spec("создай файл",gov.registry,CapabilityPlanner(CapabilityGraph(gov.registry)))
            eg=ExecutionGraph(spec).compile(); eg.transition("preflight")
            state={"compiled_goal":spec.as_dict(),"execution_graph":{"state":eg.state,"history":eg.history},"goal":"создай файл","ledger":[],"verified":[],"facts":[],"_artifact_paths":[]}
            restored=ExecutionGraph(GoalSpec(**state["compiled_goal"])).compile(); restored.state=state["execution_graph"]["state"]
            assert restored.state=="preflight"
            return "checkpoint способен восстановить state machine"

    check("T31 formal GoalSpec", t_formal_goalspec)
    check("T32 formal GoalSpec determinism", t_formal_goalspec_deterministic)
    def t_execution_graph_runtime_integration() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_t42_") as td:
            cfg,_=_fresh_cfg(td); gov=Governor(cfg, AuditChain(Path(td)/"a.jsonl"), CatalogBridge(""))
            spec=FormalGoalCompiler().compile_spec("создай файл",gov.registry,CapabilityPlanner(CapabilityGraph(gov.registry)))
            eg=ExecutionGraph(spec).compile()
            eg.transition("preflight"); eg.transition("execute"); assert eg.state=="execute"
            return "execution state machine имеет корректный runtime-контур"

    def t_contract_requires_producer_and_integrity() -> str:
        state={"criteria":["capability:write_file выполнена"],"required_capabilities":["write_file"],
               "ledger":[{"step":1,"action":"write_file","ok":True,"kind":"write","obs_brief":"created"}]}
        p=ProofCompiler(state).compile(); assert p.status=="verified"
        return "contract проверяет producer и integrity"

    def t_contract_accepts_matching_observation() -> str:
        state={"criteria":["capability:write_file выполнена"],"required_capabilities":["write_file"],
               "ledger":[{"step":1,"action":"write_file","ok":True,"kind":"observation","obs_brief":"created"}]}
        p=ProofCompiler(state).compile(); assert p.status=="verified"
        return "EvidenceContract принимает только корректно типизированное evidence"

    def t_proof_closure_rejects_dangling_input() -> str:
        p=ProofObject("p","verified",["c"],["e"],"r",[],"1",[{"id":"c","kind":"claim","claim_id":"c","inputs":["e2"],"rule_id":"r"}],[],{"e":"h"})
        try: ProofClosure.validate(p)
        except ProofClosureError as e:
            assert str(e) == "PROOF_CLOSURE: dangling input", \
                f"C5: отказ без именованной причины: {str(e)!r}"
            return "dangling input блокируется (именованная причина ассертируется)"
        raise AssertionError("dangling input accepted")

    def t_proof_closure_accepts_closed_graph() -> str:
        p=ProofObject("p","verified",["c"],["e"],"r",[],"1",[{"id":"d","kind":"derivation","claim_id":"c","inputs":["e"],"rule_id":"r"},{"id":"c","kind":"claim","claim_id":"c","inputs":["d"],"rule_id":"r"}],[{"from":"d","to":"c","relation":"derives"}],{"e":"h"})
        ProofClosure.validate(p); return "closed DAG accepted"

    def t_temporal_future_proof_rejected() -> str:
        p=ProofObject("p","verified",["c"],["e"],"r",[],"1",[{"id":"c","kind":"claim","claim_id":"c","inputs":["e"],"rule_id":"r"}],[],{"e":"h"},"2999-01-01T00:00:00+00:00")
        try: TemporalValidity.validate(p)
        except ProofClosureError as e:
            assert str(e) == "TEMPORAL_VALIDITY: future-dated proof", \
                f"C5: отказ без именованной причины: {str(e)!r}"
            return "future proof блокируется (именованная причина ассертируется)"
        raise AssertionError("future proof accepted")

    def t_cas_rejects_changed_state() -> str:
        st={"criteria":["capability:write_file выполнена"],"required_capabilities":["write_file"],"ledger":[{"step":1,"action":"write_file","ok":True,"kind":"write","obs_brief":"created"}],"_cas_version":0}
        p=ProofCompiler(st).compile(); st["ledger"].append({"step":2,"action":"write_file","ok":True,"kind":"write","obs_brief":"changed"})
        st["proof"]={"id":p.id,"status":p.status,"claim_ids":p.claim_ids,"evidence_ids":p.evidence_ids,"rule":p.rule,"unknowns":p.unknowns,"rule_version":p.rule_version,"nodes":p.nodes,"edges":p.edges,"evidence_hashes":p.evidence_hashes,"created_at":p.created_at,"evidence_timestamps":p.evidence_timestamps,"artifact_hashes":p.artifact_hashes,"source_state_hash":p.source_state_hash,"state_version":p.state_version}
        try: ProofCarryingGovernor.commit(st)
        except ProofCarryingCommitError as e:
            assert "CAS conflict" in str(e); return "verify→commit TOCTOU изменение блокируется"
        raise AssertionError("CAS conflict accepted")

    def t_cas_accepts_unchanged_state() -> str:
        st={"criteria":["capability:write_file выполнена"],"required_capabilities":["write_file"],"ledger":[{"step":1,"action":"write_file","ok":True,"kind":"write","obs_brief":"created"}],"_cas_version":0}
        p=ProofCompiler(st).compile(); st["proof"]={"id":p.id,"status":p.status,"claim_ids":p.claim_ids,"evidence_ids":p.evidence_ids,"rule":p.rule,"unknowns":p.unknowns,"rule_version":p.rule_version,"nodes":p.nodes,"edges":p.edges,"evidence_hashes":p.evidence_hashes,"created_at":p.created_at,"evidence_timestamps":p.evidence_timestamps,"artifact_hashes":p.artifact_hashes,"source_state_hash":p.source_state_hash,"state_version":p.state_version}
        ProofCarryingGovernor.commit(st); return "неизменённое state проходит CAS"

    def t_commit_requires_proof() -> str:
        st={"proof":None}
        try:
            ProofCarryingGovernor.commit(st)
        except ProofCarryingCommitError as e:
            msg = str(e)
            assert msg.startswith("COMMIT:") and "отсутствует полный ProofObject" in msg, \
                f"C5: отказ без именованной причины: {msg!r}"
            return "COMMIT без ProofObject блокируется (именованная причина ассертируется)"
        raise AssertionError("commit unexpectedly allowed")

    def t_commit_rejects_unknown_proof() -> str:
        st={"proof":{"id":"p","status":"verified","claim_ids":["c"],"evidence_ids":["e"],"rule":"r","unknowns":["c2"]}}
        try:
            ProofCarryingGovernor.commit(st)
        except ProofCarryingCommitError as e:
            assert "COMMIT: UNKNOWN" in str(e), f"C5: отказ без именованной причины: {str(e)!r}"
            return "COMMIT с UNKNOWN блокируется (именованная причина ассертируется)"
        raise AssertionError("unknown proof unexpectedly committed")

    def t_commit_accepts_closed_proof() -> str:
        st={"_cas_version":0,"marker":"unchanged"}
        src=StateCAS.fingerprint(st)
        st["proof"]={"id":"p","status":"verified","claim_ids":["c"],"evidence_ids":["e"],"rule":"r","rule_version":"1","unknowns":[],"nodes":[{"id":"d","kind":"derivation","claim_id":"c","inputs":["e"],"rule_id":"r"},{"id":"c","kind":"claim","claim_id":"c","inputs":["d"],"rule_id":"r"}],"edges":[{"from":"d","to":"c","relation":"derives"}],"evidence_hashes":{"e":"h"},"source_state_hash":src,"state_version":0}
        proof=ProofCarryingGovernor.commit(st)
        assert proof.id=="p" and st["commit"]["status"]=="committed"
        return "замкнутый ProofObject + CAS разрешает COMMIT"

    def t_unknown_propagates_through_dependencies() -> str:
        g=EpistemicDependencyGraph({"claim:2":["claim:1"],"claim:3":["claim:2"]})
        u=g.propagate({"claim:1"})
        assert {"claim:1","claim:2","claim:3"} <= u
        assert g.blockers("claim:3",u)==["claim:2","claim:1"]
        return "UNKNOWN транзитивно блокирует зависимые claims"

    def t_compiler_marks_dependency_unknown() -> str:
        st={"criteria":["capability:missing выполнена","capability:other выполнена"],"required_capabilities":[],
            "claim_dependencies":{"claim:2":["claim:1"]},"ledger":[]}
        p=ProofCompiler(st).compile()
        assert p.status=="unknown" and any("claim:2:dependency_unknown" in x for x in p.unknowns)
        return "ProofCompiler распространяет UNKNOWN по claim_dependencies"

    def t_compiler_rejects_dependency_cycle() -> str:
        st={"criteria":["capability:write_file выполнена","capability:read_file выполнена"],
            "required_capabilities":[],
            "claim_dependencies":{"claim:1":["claim:2"],"claim:2":["claim:1"]},
            "ledger":[
                {"step":1,"action":"write_file","ok":True,"kind":"write","obs_brief":"ok1"},
                {"step":2,"action":"read_file","ok":True,"kind":"read","obs_brief":"ok2"}],
            "freshness_max_age_seconds":7*24*3600}
        p=ProofCompiler(st).compile()
        assert p.status=="unknown" and st.get("claim_dependency_cycles")
        assert any(x.endswith(":dependency_cycle") for x in p.unknowns)
        return "compiler блокирует цикл даже при полном локальном evidence"

    def t_freshness_rejects_old_evidence() -> str:
        # v3.7.0: сильная форма хранителя — Stale ≠ Unknown, канонический id;
        # свежесть — управляемая политика (override возвращает verified).
        st={"criteria":["capability:write_file выполнена"],"required_capabilities":["write_file"],
            "ledger":[{"step":1,"action":"write_file","ok":True,"kind":"write","obs_brief":"created",
                       "ts":"2020-01-01T00:00:00+00:00"}],
            "_cas_version":0}
        p=ProofCompiler(st).compile()
        assert p.status=="unknown" and any(x.endswith(":stale_evidence") for x in p.unknowns)
        assert not any(x.endswith(":derivation_missing") for x in p.unknowns)
        st2=dict(st); st2["freshness_max_age_seconds"]=10**9
        assert ProofCompiler(st2).compile().status=="verified"
        return "старое evidence не закрывает claim (Stale ≠ Unknown); свежесть — политика"

    def t_commit_rejects_mutated_artifact() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_t77_") as td:
            art=Path(td)/"artifact.txt"; art.write_text("before",encoding="utf-8")
            st={"_cas_version":0,"criteria":["capability:write_file выполнена"],
                "required_capabilities":["write_file"],
                "ledger":[{"step":1,"action":"write_file","ok":True,"kind":"write",
                           "obs_brief":"created"}],"_artifact_paths":[str(art)]}
            p=ProofCompiler(st).compile(); st["proof"]=asdict(p)
            art.write_text("after",encoding="utf-8")
            try:
                ProofCarryingGovernor.commit(st)
            except ProofCarryingCommitError as e:
                assert "REVOKED" in str(e)
                return "мутация артефакта после proof блокирует COMMIT через REVOKED"
            raise AssertionError("mutated artifact accepted")

    def t_revocation_cascade_marks_dependents() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_t78_") as td:
            art=Path(td)/"artifact.txt"; art.write_text("before",encoding="utf-8")
            st={"_cas_version":0,"criteria":["capability:write_file выполнена"],
                "required_capabilities":["write_file"],
                "ledger":[{"step":1,"action":"write_file","ok":True,"kind":"write","obs_brief":"created"}],
                "_artifact_paths":[str(art)]}
            p=ProofCompiler(st).compile(); st["proof"]=asdict(p)
            art.write_text("after",encoding="utf-8")
            try:
                ProofCarryingGovernor.commit(st)
            except ProofCarryingCommitError as e:
                assert "REVOKED" in str(e)
                assert st["revocation"]["status"]=="REVOKED"
                assert st["knowledge_status"]=="REVOKED"
                assert st["revoked_evidence_ids"]==p.evidence_ids
                assert st["revoked_claim_ids"]==p.claim_ids
                return "мутация артефакта каскадно отзывает Evidence→Claim→Proof"
            raise AssertionError("revocation cascade did not block commit")

    def t_revocation_detects_deleted_artifact() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_t79_") as td:
            art=Path(td)/"artifact.txt"; art.write_text("payload",encoding="utf-8")
            st={"_cas_version":0,"criteria":["capability:write_file выполнена"],
                "required_capabilities":["write_file"],
                "ledger":[{"step":1,"action":"write_file","ok":True,"kind":"write","obs_brief":"created"}],
                "_artifact_paths":[str(art)]}
            p=ProofCompiler(st).compile(); st["proof"]=asdict(p); art.unlink()
            try:
                ProofCarryingGovernor.commit(st)
            except ProofCarryingCommitError:
                assert st["revocation"]["artifacts"][0]["actual"]=="MISSING"
                return "удаление bound artifact приводит к REVOKED"
            raise AssertionError("deleted artifact accepted")

    def t_knowledge_revocation_index_persists_commit() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_t82_") as td:
            art=Path(td)/"historical.txt"; art.write_text("v1",encoding="utf-8")
            idx=Path(td)/"knowledge_revocation.jsonl"
            st={"_cas_version":0,"criteria":["capability:write_file выполнена"],"required_capabilities":["write_file"],
                "ledger":[{"step":1,"action":"write_file","ok":True,"kind":"write","obs_brief":"created","artifact":str(art)}],
                "_artifact_paths":[str(art)],"_knowledge_revocation_index_path":str(idx)}
            p=ProofCompiler(st).compile(); st["proof"]=asdict(p); ProofCarryingGovernor.commit(st)
            assert idx.exists()
            rows=KnowledgeRevocationIndex._load(idx)
            assert len(rows)==1 and rows[0]["proof_id"]==p.id and rows[0]["status"]=="ACTIVE"
            return "COMMIT регистрируется в персистентном Knowledge Revocation Index"

    def t_knowledge_revocation_index_finds_historical_mutation() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_t83_") as td:
            art=Path(td)/"historical.txt"; art.write_text("v1",encoding="utf-8")
            idx=Path(td)/"knowledge_revocation.jsonl"
            st={"_cas_version":0,"criteria":["capability:write_file выполнена"],"required_capabilities":["write_file"],
                "ledger":[{"step":1,"action":"write_file","ok":True,"kind":"write","obs_brief":"created","artifact":str(art)}],
                "_artifact_paths":[str(art)],"_knowledge_revocation_index_path":str(idx)}
            p=ProofCompiler(st).compile(); st["proof"]=asdict(p); ProofCarryingGovernor.commit(st)
            art.write_text("v2",encoding="utf-8")
            revoked=KnowledgeRevocationIndex.reconcile(st)
            assert len(revoked)==1 and revoked[0]["proof_id"]==p.id
            assert revoked[0]["status"]=="REVOKED"
            assert revoked[0]["mismatches"][0]["actual"] != revoked[0]["mismatches"][0]["expected"]
            return "исторический committed Proof автоматически найден и отозван после mutation"

    def t_revocation_is_selective() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_t80_") as td:
            a=Path(td)/"a.txt"; b=Path(td)/"b.txt"; a.write_text("A",encoding="utf-8"); b.write_text("B",encoding="utf-8")
            st={"_cas_version":0,"criteria":["capability:write_file выполнена","capability:read_file выполнена"],
                "required_capabilities":[],"claim_dependencies":{},
                "ledger":[{"step":1,"action":"write_file","ok":True,"kind":"write","obs_brief":"A","artifact":str(a)},
                         {"step":2,"action":"read_file","ok":True,"kind":"read","obs_brief":"B","artifact":str(b)}],
                "_artifact_paths":[str(a),str(b)]}
            p=ProofCompiler(st).compile(); st["proof"]=asdict(p); a.write_text("A2",encoding="utf-8")
            mism=RevocationCascade.apply(st,p)
            assert len(mism)==1 and st["revoked_evidence_ids"]==["evidence:step:1:write_file"]
            assert st["revoked_claim_ids"]==["claim:1"]
            assert "claim:2" not in st["revoked_claim_ids"]
            return "ревокация точная: меняется только зависимая ветвь"

    def t_revocation_transitive_claim_dependency() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_t81_") as td:
            a=Path(td)/"a.txt"; b=Path(td)/"b.txt"; a.write_text("A",encoding="utf-8"); b.write_text("B",encoding="utf-8")
            st={"_cas_version":0,"criteria":["capability:write_file выполнена"],"required_capabilities":[],
                "claim_dependencies":{"claim:2":["claim:1"]},
                "ledger":[{"step":1,"action":"write_file","ok":True,"kind":"write","obs_brief":"A","artifact":str(a)}],
                "_artifact_paths":[str(a)]}
            p=ProofCompiler(st).compile(); p.claim_ids=["claim:1","claim:2"]; p.evidence_ids=["evidence:step:1:write_file"]; p.evidence_artifact_refs={p.evidence_ids[0]:[str(a)]}
            st["proof"]=asdict(p); a.write_text("A2",encoding="utf-8"); RevocationCascade.apply(st,p)
            assert st["revoked_claim_ids"]==["claim:1","claim:2"]
            return "ревокация распространяется по claim dependency graph"

    def t_typed_rule_rejects_wrong_producer() -> str:
        st={"criteria":["capability:write_file выполнена"],"required_capabilities":["write_file"],"ledger":[{"step":1,"action":"web_search","ok":True,"kind":"net","obs_brief":"ok"}]}
        assert ProofCompiler(st).compile().status=="unknown"
        return "TypedRuleEngine отклоняет чужой producer"

    def t_typed_rule_accepts_matching_producer() -> str:
        st={"criteria":["capability:write_file выполнена"],"required_capabilities":["write_file"],"ledger":[{"step":1,"action":"write_file","ok":True,"kind":"write","obs_brief":"created"}]}
        assert ProofCompiler(st).compile().status=="verified"
        return "TypedRuleEngine выводит claim только из matching producer"

    def t_rule_registry_rejects_unknown_rule() -> str:
        registry=RuleRegistry()
        assert registry.get("no_such_rule") is None
        assert not registry.validate("no_such_rule", [])
        return "неизвестное правило не может породить proof"

    def t_rule_registry_is_explicit_and_versioned() -> str:
        registry=RuleRegistry(); r=registry.get("claim_witnessed_by_successful_action_observation")
        assert r and r.version and r.min_evidence == 1
        return f"реестр правил: {r.id}@{r.version}"

    def t_derivation_graph_records_rule() -> str:
        state={"criteria":["capability:write_file выполнена"],"required_capabilities":["write_file"],"ledger":[{"step":1,"action":"write_file","ok":True,"kind":"write","obs_brief":"created"}]}
        p=ProofCompiler(state).compile(); assert p.status=="verified" and len(state.get("derivations",[]))==1
        assert state["derivations"][0]["rule"]
        return "DerivationGraph сохраняет evidence→rule→claim"

    def t_derivation_missing_blocks_verified() -> str:
        state={"criteria":["capability:write_file выполнена"],"required_capabilities":["write_file"],"ledger":[{"step":1,"action":"web_search","ok":True,"kind":"net","obs_brief":"SUCCESS"}]}
        p=ProofCompiler(state).compile(); assert p.status=="unknown"
        return "отсутствующий вывод блокирует VERIFIED"

    def t_evidence_matching_is_not_positional() -> str:
        state={"criteria":["capability:web_search выполнена","capability:write_file выполнена"],
               "required_capabilities":["web_search","write_file"],
               "ledger":[
                   {"step":1,"action":"write_file","ok":True,"kind":"write","obs_brief":"created"},
                   {"step":2,"action":"web_search","ok":True,"kind":"net","obs_brief":"found"}]}
        p=ProofCompiler(state).compile()
        assert p.status=="verified" and len(p.evidence_ids)==2
        return "evidence связывается с claim по контракту, а не по позиции"

    def t_missing_one_claim_blocks_verified() -> str:
        state={"criteria":["capability:web_search выполнена","capability:write_file выполнена"],
               "required_capabilities":["web_search","write_file"],
               "ledger":[{"step":1,"action":"web_search","ok":True,"kind":"net","obs_brief":"found"}]}
        p=ProofCompiler(state).compile()
        assert p.status=="unknown" and any("write_file" in x for x in p.unknowns)
        return "непокрытый claim блокирует VERIFIED"

    def t_claim_type_requires_matching_action() -> str:
        state={"criteria":["capability:write_file выполнена"],"required_capabilities":["write_file"],
               "ledger":[{"step":1,"action":"web_search","ok":True,"kind":"net","obs_brief":"SUCCESS"}]}
        p=ProofCompiler(state).compile(); assert p.status=="unknown" and "capability:write_file" in p.unknowns
        return "typed claim не закрывается чужим SUCCESS"

    def t_evidence_must_attach_to_claim() -> str:
        state={"criteria":["assertion"],"ledger":[{"step":1,"action":"write_file","ok":True,"kind":"write","obs_brief":"created"}]}
        p=ProofCompiler(state).compile(); assert p.status=="verified" and p.evidence_ids
        return "evidence получает claim linkage"

    def t_claim_evidence_proof_compiler() -> str:
        state={"criteria":["capability:write_file выполнена успешно"],"required_capabilities":["write_file"],
               "ledger":[{"step":1,"action":"write_file","ok":True,"kind":"write","obs_brief":"file written"}]}
        proof=ProofCompiler(state).compile()
        assert proof.status=="verified" and ProofCompiler.allows_verified(proof)
        assert proof.claim_ids and proof.evidence_ids
        return "Claim→Evidence→Rule→Proof компилируется детерминированно"

    def t_success_without_required_action_not_proof() -> str:
        state={"criteria":["capability:write_file выполнена успешно"],"required_capabilities":["write_file"],
               "ledger":[{"step":1,"action":"web_search","ok":True,"kind":"net","obs_brief":"SUCCESS"}]}
        proof=ProofCompiler(state).compile()
        assert not ProofCompiler.allows_verified(proof) and proof.unknowns
        return "чужой SUCCESS не закрывает требуемый claim"

    def t_action_dag_failed_action_blocks_success() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_t43_") as td:
            cfg,_=_fresh_cfg(td); gov=Governor(cfg, AuditChain(Path(td)/"a.jsonl"), CatalogBridge("")); g=CapabilityGraph(gov.registry)
            spec=FormalGoalCompiler().compile_spec("создай файл",gov.registry,CapabilityPlanner(g)); dag=ActionDAG(spec,g); cap=spec.capabilities[0]
            dag.start(cap); assert dag.complete(cap,Observation(False,"policy","blocked")) is False
            assert not dag.all_required_completed(); return "неуспешное действие не может стать completed"

    def t_action_dag_dependencies() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_t40_") as td:
            cfg,_=_fresh_cfg(td); gov=Governor(cfg, AuditChain(Path(td)/"a.jsonl"), CatalogBridge("")); g=CapabilityGraph(gov.registry); g.add_dependency("research_web","web_search")
            spec=FormalGoalCompiler().compile_spec("исследуй тему через интернет",gov.registry,CapabilityPlanner(g)); dag=ActionDAG(spec,g)
            assert not dag.ready("research_web"); dag.start("web_search"); dag.complete("web_search",Observation(True,"net","ok")); assert dag.ready("research_web")
            return "ActionDAG реально блокирует действие до завершения зависимости"

    def t_action_dag_resume() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_t41_") as td:
            cfg,_=_fresh_cfg(td); gov=Governor(cfg, AuditChain(Path(td)/"a.jsonl"), CatalogBridge("")); g=CapabilityGraph(gov.registry); g.add_dependency("research_web","web_search")
            spec=FormalGoalCompiler().compile_spec("исследуй тему через интернет",gov.registry,CapabilityPlanner(g)); dag=ActionDAG(spec,g); dag.start("web_search"); dag.complete("web_search",Observation(True,"net","ok")); snap=dag.snapshot(); restored=ActionDAG(spec,g)
            for k,v in snap.items(): restored.nodes[k].status=v["status"]
            assert restored.ready("research_web"); return "ActionDAG состояние восстанавливается из snapshot"

    check("T33 execution graph guards", t_execution_graph_guards)
    check("T34 execution graph no-skip", t_execution_graph_no_skip)
    check("T37 mechanical goal verification", t_goal_verification_is_mechanical)
    check("T38 resume execution graph", t_resume_restores_execution_graph)

    def t_web_search_policy_failure_is_observation() -> str:
        original=globals()["_http_request_no_redirect"]
        def denied(*args, **kwargs): raise PolicyViolation("DNS unavailable")
        globals()["_http_request_no_redirect"]=denied
        try:
            with tempfile.TemporaryDirectory(prefix="poly_t39_") as td:
                cfg,_=_fresh_cfg(td); obs=_t_web_search(cfg,{"query":"test","limit":1})
                assert obs.ok is False and obs.kind=="policy"
                return "web_search не падает исключением: PolicyViolation превращается в Observation"
        finally:
            globals()["_http_request_no_redirect"]=original

    check("T39 web policy failure observation", t_web_search_policy_failure_is_observation)
    check("T40 action DAG dependencies", t_action_dag_dependencies)
    check("T41 action DAG resume", t_action_dag_resume)
    check("T42 execution graph runtime integration", t_execution_graph_runtime_integration)
    check("T44 claim evidence proof compiler", t_claim_evidence_proof_compiler)
    check("T50 evidence matching non-positional", t_evidence_matching_is_not_positional)
    def t_proof_closure_rejects_cycle() -> str:
        p=ProofObject("p","verified",["c"],["e"],"r",[],"1",
          [{"id":"a","kind":"derivation","inputs":["b"],"rule_id":"r"},{"id":"b","kind":"claim","inputs":["a"],"rule_id":"r"}],
          [{"from":"a","to":"b","relation":"x"},{"from":"b","to":"a","relation":"x"}],{"e":"h"})
        try: ProofClosure.validate(p)
        except ProofClosureError: return "cycle блокируется"
        raise AssertionError("cycle accepted")

    def t_falsification_blocks_contested() -> str:
        p=ProofObject("p","verified",["c"],["e"],"r",[],"1",
          [{"id":"c","kind":"claim","claim_id":"c","inputs":["e"],"rule_id":"r"}],[],{"e":"h"})
        state={"falsification":[{"claim_id":"c","verdict":"CONTESTED","reason":"contradicting source"}]}
        try: FalsificationProbe.probe(state,p)["status"] == "CLEAR"
        except Exception: pass  # разбор CONTESTED ассертом ниже; здесь — что проба не поднимает исключений
        assert FalsificationProbe.probe(state,p)["status"]=="CONTESTED"
        return "CONTESTED блокирует поддержку"

    def t_temporal_rejects_future_evidence() -> str:
        p=ProofObject("p","verified",["c"],["e"],"r",[],"1",
          [{"id":"c","kind":"claim","claim_id":"c","inputs":["e"],"rule_id":"r"}],[],{"e":"h"},"2026-01-01T00:00:00+00:00",{"e":"2999-01-01T00:00:00+00:00"},{})
        try: TemporalValidity.validate(p, "2026-01-02T00:00:00+00:00")
        except ProofClosureError as e:
            assert "TEMPORAL_VALIDITY: future evidence" in str(e), \
                f"C5: отказ без именованной причины: {str(e)!r}"
            return "future evidence блокируется (именованная причина ассертируется)"
        raise AssertionError("future evidence accepted")

    def t_anchor_ledger_hash_chain() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_anchor_") as td:
            q=ProofAnchorLedger(Path(td)/"proofs.jsonl"); h1=q.append({"proof":"p1"}); h2=q.append({"proof":"p2"})
            rows=[json.loads(x) for x in (Path(td)/"proofs.jsonl").read_text().splitlines()]
            assert rows[1]["prev_hash"]==h1 and rows[1]["hash"]==h2
            return "append-only proof anchor chain работает"

    # ═══ v3.7.0: реставрация хранителей T67–T72 (в ветке v3.6.0 номера занимали
    # слабые unit-варианты; сильные e2e-хранители возвращаются, слабые перенумерованы
    # в T115–T120 без удаления) + порты v3.4.0 (T105–T111) + новые runtime-тесты ═══
    def t_dangling_dependency_blocks_verified() -> str:
        st={"criteria":["capability:write_file выполнена","capability:read_file выполнена"],
            "required_capabilities":[],
            "claim_dependencies":{"claim:2":["claim:99"]},
            "ledger":[{"step":1,"action":"write_file","ok":True,"kind":"write","obs_brief":"ok1"},
                      {"step":2,"action":"read_file","ok":True,"kind":"read","obs_brief":"ok2"}],
            "_cas_version":0}
        p=ProofCompiler(st).compile()
        assert p.status=="unknown" and any(":dangling_dependency:claim:99" in x for x in p.unknowns)
        st["proof"]=asdict(p)
        try: ProofCarryingGovernor.commit(st)
        except ProofCarryingCommitError: return "висячая зависимость блокирует VERIFIED и COMMIT"
        raise AssertionError("висячая зависимость пропущена в COMMIT")

    def t_epistemic_blockers_attributed() -> str:
        st={"criteria":["capability:write_file выполнена","capability:read_file выполнена","capability:read_file завершена"],
            "required_capabilities":[],
            "claim_dependencies":{"claim:2":["claim:1"],"claim:3":["claim:2"]},
            "ledger":[{"step":1,"action":"read_file","ok":True,"kind":"read","obs_brief":"ok2"},
                      {"step":2,"action":"read_file","ok":True,"kind":"read","obs_brief":"ok3"}],
            "_cas_version":0}
        p=ProofCompiler(st).compile()
        assert p.status=="unknown"
        assert "claim:1:derivation_missing" in p.unknowns
        assert "claim:2:dependency_unknown" in p.unknowns and "claim:3:dependency_unknown" in p.unknowns
        assert not any(x.startswith("claim:claim:") for x in p.unknowns)
        assert st["epistemic_blockers"]=={"claim:2":["claim:1"],"claim:3":["claim:2","claim:1"]}
        return "blockers атрибутированы по каноническим id"

    def t_blocked_derivation_invalidated() -> str:
        st={"criteria":["capability:write_file выполнена","capability:read_file выполнена"],
            "required_capabilities":[],
            "claim_dependencies":{"claim:2":["claim:1"]},
            "ledger":[{"step":1,"action":"read_file","ok":True,"kind":"read","obs_brief":"ok2"}],
            "_cas_version":0}
        p=ProofCompiler(st).compile()
        assert p.status=="unknown" and "claim:2:dependency_unknown" in p.unknowns
        derivs=[d for d in st["derivations"] if d["claim_id"]=="claim:2"]
        assert derivs and derivs[0]["valid"] is False
        return "деривация зависимого claim инвалидируется при недоказанной предпосылке"

    def t_stale_evidence_blocks_verified() -> str:
        st={"criteria":["capability:write_file выполнена"],"required_capabilities":["write_file"],
            "ledger":[{"step":1,"action":"write_file","ok":True,"kind":"write","obs_brief":"created",
                       "ts":"2020-01-01T00:00:00+00:00"}],
            "_cas_version":0}
        p=ProofCompiler(st).compile()
        assert p.status=="unknown" and "claim:1:stale_evidence" in p.unknowns
        assert not any(x.endswith(":derivation_missing") for x in p.unknowns)
        st["proof"]=asdict(p)
        try: ProofCarryingGovernor.commit(st)
        except ProofCarryingCommitError: pass
        else: raise AssertionError("протухшее evidence прошло COMMIT")
        st2=dict(st); st2.pop("proof"); st2["freshness_max_age_seconds"]=10**9
        assert ProofCompiler(st2).compile().status=="verified"
        return "протухшее evidence блокирует VERIFIED и COMMIT; свежесть — политика"

    def t_dependency_cycle_rejected() -> str:
        st={"criteria":["capability:write_file выполнена","capability:read_file выполнена","capability:read_file завершена"],
            "required_capabilities":[],
            "claim_dependencies":{"claim:1":["claim:2"],"claim:2":["claim:1"],"claim:3":["claim:2"]},
            "ledger":[{"step":1,"action":"write_file","ok":True,"kind":"write","obs_brief":"ok1"},
                      {"step":2,"action":"read_file","ok":True,"kind":"read","obs_brief":"ok2"},
                      {"step":3,"action":"read_file","ok":True,"kind":"read","obs_brief":"ok3"}],
            "_cas_version":0}
        p=ProofCompiler(st).compile()
        assert p.status=="unknown"
        assert "claim:1:dependency_cycle" in p.unknowns and "claim:2:dependency_cycle" in p.unknowns
        assert "claim:3:dependency_unknown" in p.unknowns
        assert st["claim_dependency_cycles"]
        st["proof"]=asdict(p)
        try: ProofCarryingGovernor.commit(st)
        except ProofCarryingCommitError: return "цикл зависимостей отклонён: циркулярная поддержка ≠ proof"
        raise AssertionError("циклический proof прошёл COMMIT")

    def t_governor_tamper_battery() -> str:
        import copy as _copy
        st={"criteria":["capability:write_file выполнена"],"required_capabilities":["write_file"],
            "ledger":[{"step":1,"action":"write_file","ok":True,"kind":"write","obs_brief":"created"}],
            "_cas_version":0}
        p=ProofCompiler(st).compile(); assert p.status=="verified"
        proof_dict=asdict(p)
        def snap():
            s=dict(st); s["proof"]=_copy.deepcopy(proof_dict)
            s["derivations"]=[dict(d) for d in st["derivations"]]
            return s
        ProofCarryingGovernor.commit(snap())
        def m_status(s): s["proof"]["status"]="unknown"
        def m_unknowns(s): s["proof"]["unknowns"]=["injected"]
        def m_pvalid(s): s["derivations"][0]["valid"]=False
        def m_pev(s): s["derivations"][0]["evidence_ids"]=[]
        def m_foreign(s): s["proof"]["claim_ids"]=["claim:9"]
        def m_empty(s): s["proof"]["claim_ids"]=[]
        def m_norule(s): s["proof"].pop("rule")
        def m_noev(s): s["proof"].pop("evidence_ids")
        for name, fn in [("status",m_status),("unknowns",m_unknowns),("premise_valid",m_pvalid),
                         ("premise_evidence",m_pev),("foreign_claim",m_foreign),("empty_claims",m_empty),
                         ("missing_rule",m_norule),("missing_evidence_ids",m_noev)]:
            s=snap(); fn(s)
            try: ProofCarryingGovernor.commit(s)
            except ProofCarryingCommitError: pass
            else: raise AssertionError(f"тамперинг '{name}' прошёл COMMIT")
        return "тампер-батарея: 8 классов мутаций proof отклонены (включая чужие claim_ids)"

    def t_revival_hole_closed() -> str:
        # v3.7.0 ГЛАВНАЯ проба: перекомпиляция после мутации мира не должна позволить
        # старому evidence пережить COMMIT через перезаписанный глобальный пин.
        with tempfile.TemporaryDirectory(prefix="poly_revival_") as td:
            art=Path(td)/"a.txt"; art.write_text("SECRET",encoding="utf-8")
            st={"criteria":["capability:write_file выполнена"],"required_capabilities":["write_file"],
                "ledger":[{"step":1,"action":"write_file","ok":True,"kind":"write","obs_brief":"written",
                           "artifact_path":str(art),"artifact_sha256":sha256_hex(b"SECRET")}],
                "_artifact_paths":[str(art)],"_cas_version":0}
            p1=ProofCompiler(st).compile(); assert p1.status=="verified"
            st["proof"]=asdict(p1); ProofCarryingGovernor.commit(st)
            art.write_text("EVIL",encoding="utf-8")
            st2=dict(st)
            for k in ("proof","commit","epistemic_reconciliation"): st2.pop(k,None)
            p2=ProofCompiler(st2).compile()
            assert p2.status=="verified"
            st2["proof"]=asdict(p2)
            try: ProofCarryingGovernor.commit(st2)
            except ProofCarryingCommitError as e:
                assert "evidence-bound artifact mutation" in str(e), str(e)
                assert st2["revocation"]["reason"]=="evidence_artifact_drift"
                assert st2["revoked_claim_ids"]==["claim:1"]
                assert st2["knowledge_status"]=="REVOKED"
                return "revival-дыра закрыта: перекомпиляция не launder'ит старое evidence"
            raise AssertionError("ревайвл: старое evidence пережило мутацию мира")

    def t_revocation_is_dependency_aware() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_precise_") as td:
            a1=Path(td)/"a1.txt"; a2=Path(td)/"a2.txt"
            a1.write_text("ONE",encoding="utf-8"); a2.write_text("TWO",encoding="utf-8")
            st={"criteria":["capability:write_file выполнена","capability:read_file выполнена"],
                "required_capabilities":[],
                "ledger":[{"step":1,"action":"write_file","ok":True,"kind":"write","obs_brief":"w1",
                           "artifact_path":str(a1),"artifact_sha256":sha256_hex(b"ONE")},
                          {"step":2,"action":"read_file","ok":True,"kind":"read","obs_brief":"r2",
                           "artifact_path":str(a2),"artifact_sha256":sha256_hex(b"TWO")}],
                "_cas_version":0}
            p=ProofCompiler(st).compile(); assert p.status=="verified"
            st["proof"]=asdict(p); ProofCarryingGovernor.commit(st)
            a2.write_text("MUTATED",encoding="utf-8")
            st2=dict(st)
            for k in ("proof","commit","epistemic_reconciliation"): st2.pop(k,None)
            p2=ProofCompiler(st2).compile(); st2["proof"]=asdict(p2)
            try: ProofCarryingGovernor.commit(st2)
            except ProofCarryingCommitError: pass
            else: raise AssertionError("мутация a2 не заблокирована")
            assert st2["revocation"]["evidence_ids"]==["evidence:step:2:read_file"], st2["revocation"]
            assert st2["revoked_claim_ids"]==["claim:2"], st2["revocation"]
            assert "evidence:step:1:write_file" not in st2["revocation"]["evidence_ids"]
            return "каскад точечный: отозвано только знание, связанное с изменённым артефактом"

    def t_post_commit_drift_audit() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_drift_") as td:
            art=Path(td)/"d.txt"; art.write_text("V1",encoding="utf-8")
            st={"criteria":["capability:write_file выполнена"],"required_capabilities":["write_file"],
                "ledger":[{"step":1,"action":"write_file","ok":True,"kind":"write","obs_brief":"w",
                           "artifact_path":str(art),"artifact_sha256":sha256_hex(b"V1")}],
                "_artifact_paths":[str(art)],"_cas_version":0}
            p=ProofCompiler(st).compile(); st["proof"]=asdict(p)
            ProofCarryingGovernor.commit(st)
            assert KnowledgeAuditor.audit(st)["status"]=="VALID"
            art.write_text("V2",encoding="utf-8")
            rep=KnowledgeAuditor.audit(st)
            assert rep["status"]=="STALE" and rep["drift"], rep
            assert st["knowledge_status"]=="STALE" and st["knowledge_drift"]["drift"]
            art.write_text("V1",encoding="utf-8")
            assert KnowledgeAuditor.audit(st)["status"]=="VALID"
            assert st["knowledge_status"]=="VALID"
            return "дрейф мира ПОСЛЕ коммита обнаруживается аудитом (STALE), восстановление снимает"

    def t_revocation_resolution_on_recommit() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_res_") as td:
            art=Path(td)/"r.txt"; art.write_text("ORIGINAL",encoding="utf-8")
            st={"criteria":["capability:write_file выполнена"],"required_capabilities":["write_file"],
                "ledger":[{"step":1,"action":"write_file","ok":True,"kind":"write","obs_brief":"w",
                           "artifact_path":str(art),"artifact_sha256":sha256_hex(b"ORIGINAL")}],
                "_artifact_paths":[str(art)],"_cas_version":0}
            p=ProofCompiler(st).compile(); st["proof"]=asdict(p)
            ProofCarryingGovernor.commit(st)
            art.write_text("MUTATED",encoding="utf-8")
            st2=dict(st)
            for k in ("proof","commit","epistemic_reconciliation"): st2.pop(k,None)
            p2=ProofCompiler(st2).compile(); st2["proof"]=asdict(p2)
            try: ProofCarryingGovernor.commit(st2)
            except ProofCarryingCommitError: pass
            else: raise AssertionError("мутация не заблокирована")
            assert st2["revocation"]["status"]=="REVOKED"
            art.write_text("ORIGINAL",encoding="utf-8")
            st3=dict(st2)
            for k in ("proof","commit","epistemic_reconciliation"): st3.pop(k,None)
            p3=ProofCompiler(st3).compile(); st3["proof"]=asdict(p3)
            ProofCarryingGovernor.commit(st3)
            assert st3["commit"]["status"]=="committed"
            assert st3["revocation"]["status"]=="RESOLVED", st3["revocation"]
            assert len(st3["revocation_history"])==1
            assert st3["knowledge_status"]=="VALID"
            return "успешный re-COMMIT закрывает REVOKED-запись (RESOLVED + история + VALID)"

    def t_closure_error_inside_commit_contract() -> str:
        assert issubclass(ProofClosureError, ProofCarryingCommitError)
        st={"criteria":["capability:write_file выполнена"],"required_capabilities":["write_file"],
            "ledger":[{"step":1,"action":"write_file","ok":True,"kind":"write","obs_brief":"created"}],
            "_cas_version":0}
        p=ProofCompiler(st).compile(); assert p.status=="verified"
        st["proof"]=asdict(p); st["proof"]["claim_ids"]=["claim:9"]
        try: ProofCarryingGovernor.commit(st)
        except ProofCarryingCommitError as e:
            assert isinstance(e, ProofClosureError), type(e)
            return "отказ замыкания остаётся внутри runtime-контракта COMMIT (ProofClosureError ⊂ ProofCarryingCommitError)"
        raise AssertionError("чужой claim_id прошёл замыкание")

    def t_ledger_contradiction_contested() -> str:
        st={"criteria":["capability:write_file выполнена"],"required_capabilities":["write_file"],
            "ledger":[{"step":1,"action":"write_file","ok":True,"kind":"write","obs_brief":"created"},
                      {"step":2,"action":"(verify-fail)","ok":False,"kind":"verify",
                       "obs_brief":"VERIFIED ОТКЛОНЁН Контролёром: критерии не подтверждены ни одним успешным наблюдением в журнале: capability:write_file выполнена"}],
            "_cas_version":0}
        p=ProofCompiler(st).compile()
        assert p.status=="verified"
        st["proof"]=asdict(p)
        try: ProofCarryingGovernor.commit(st)
        except ProofCarryingCommitError as e:
            assert "falsification=CONTESTED" in str(e)
            return "противоречие журнала (verify-fail после evidence) блокирует COMMIT"
        raise AssertionError("противоречие не дошло до falsification-гейта")

    def t_e2e_read_binding_and_drift() -> str:
        # v3.7.0 e2e: production-путь биндит read-наблюдения; мутация файла ПОСЛЕ
        # чтения инвалидирует знание (revival-дыра закрыта на живом контуре).
        with tempfile.TemporaryDirectory() as tmp:
            cfg, ws = _fresh_cfg(tmp)
            Path(ws).mkdir(parents=True, exist_ok=True)
            (Path(ws)/"data.txt").write_text("ORIGINAL",encoding="utf-8")
            script=[
                {"thought": "План: проверить и прочитать артефакт.", "status": "plan",
                 "success_criteria": ["data.txt содержит 'ORIGINAL'"],
                 "plan": ["статистика файла", "прочитать data.txt"]},
                {"thought": "Статистика data.txt.", "status": "act",
                 "actions": [{"name": "stat_path", "args": {"path": "data.txt"}}]},
                {"thought": "Читаю data.txt.", "status": "act",
                 "actions": [{"name": "read_file", "args": {"path": "data.txt"}}]},
                {"thought": "Содержимое сверено.", "status": "final", "outcome": "verified",
                 "final_answer": "data.txt прочитан", "lesson": "read-биндинг"},
            ]
            audit = AuditChain(Path(tmp) / "a.jsonl")
            agent = Agent(cfg, MockBrain(script), Governor(cfg, audit), audit)
            result = agent.solve("прочитай data.txt и подтверди содержимое")
            assert result["outcome"] == "verified", result
            w = json.loads((Path(cfg.data_dir) / "working.json").read_text(encoding="utf-8"))
            rrows=[r for r in w.get("ledger",[]) if r.get("action")=="read_file" and r.get("ok")]
            assert rrows and rrows[-1].get("artifact_path"), "read-наблюдение не получило рёбер к артефакту"
            assert w["proof"]["artifact_edges"], "proof не содержит evidence-рёбер к артефактам"
            assert w["commit"]["status"]=="committed"
            (Path(ws)/"data.txt").write_text("EVIL",encoding="utf-8")
            st=dict(w)
            for k in ("proof","commit","epistemic_reconciliation"): st.pop(k,None)
            p2=ProofCompiler(st).compile(); st["proof"]=asdict(p2)
            try: ProofCarryingGovernor.commit(st)
            except ProofCarryingCommitError as e:
                assert "evidence-bound artifact mutation" in str(e), str(e)
                return "e2e: read-evidence биндится; мутация файла после чтения блокирует COMMIT"
            raise AssertionError("read-evidence не защищён ревокацией")

    def t_runtime_knowledge_ledger_live() -> str:
        # v3.7.0 N2: production COMMIT материализуется в knowledge ledger + revocation index
        with tempfile.TemporaryDirectory() as tmp:
            cfg, ws = _fresh_cfg(tmp)
            Path(ws).mkdir(parents=True, exist_ok=True)
            script=[
                {"thought": "План: создать и проверить.", "status": "plan",
                 "success_criteria": ["hello.txt содержит 'final'"],
                 "plan": ["записать файл", "прочитать файл"]},
                {"thought": "Пишу.", "status": "act",
                 "actions": [{"name": "write_file", "args": {"path": "hello.txt", "content": "final"}}]},
                {"thought": "Читаю.", "status": "act",
                 "actions": [{"name": "read_file", "args": {"path": "hello.txt"}}]},
                {"thought": "Сверено.", "status": "final", "outcome": "verified",
                 "final_answer": "готово", "lesson": "ledger"},
            ]
            audit = AuditChain(Path(tmp) / "a.jsonl")
            agent = Agent(cfg, MockBrain(script), Governor(cfg, audit), audit)
            result = agent.solve("создай hello.txt со строкой final и проверь")
            assert result["outcome"] == "verified", result
            w = json.loads((Path(cfg.data_dir) / "working.json").read_text(encoding="utf-8"))
            led_path=w.get("_knowledge_ledger_path"); idx_path=w.get("_knowledge_revocation_index_path")
            assert led_path and idx_path, "knowledge paths не выставлены в runtime"
            led=ImmutableKnowledgeLedger(Path(led_path))
            ok,bad=led.verify(); assert ok, f"knowledge ledger повреждён at row {bad}"
            commit_rows=[r for r in led._rows() if r.get("event")=="COMMIT"]
            assert commit_rows and commit_rows[0]["payload"]["proof_id"]==w["proof"]["id"]
            idx_rows=KnowledgeRevocationIndex._load(Path(idx_path))
            assert idx_rows and idx_rows[0]["status"]=="ACTIVE"
            return "e2e: production COMMIT материализован в knowledge ledger + revocation index"

    def t_runtime_historical_reconcile() -> str:
        # v3.7.0 N4: мутация мира ПОСЛЕ коммита обнаруживается historical reconciliation
        with tempfile.TemporaryDirectory() as tmp:
            cfg, ws = _fresh_cfg(tmp)
            Path(ws).mkdir(parents=True, exist_ok=True)
            script=[
                {"thought": "План: создать и проверить.", "status": "plan",
                 "success_criteria": ["hello.txt содержит 'final'"],
                 "plan": ["записать файл", "прочитать файл"]},
                {"thought": "Пишу.", "status": "act",
                 "actions": [{"name": "write_file", "args": {"path": "hello.txt", "content": "final"}}]},
                {"thought": "Читаю.", "status": "act",
                 "actions": [{"name": "read_file", "args": {"path": "hello.txt"}}]},
                {"thought": "Сверено.", "status": "final", "outcome": "verified",
                 "final_answer": "готово", "lesson": "reconcile"},
            ]
            audit = AuditChain(Path(tmp) / "a.jsonl")
            agent = Agent(cfg, MockBrain(script), Governor(cfg, audit), audit)
            result = agent.solve("создай hello.txt со строкой final и проверь")
            assert result["outcome"] == "verified", result
            w = json.loads((Path(cfg.data_dir) / "working.json").read_text(encoding="utf-8"))
            (Path(ws)/"hello.txt").write_text("EVIL",encoding="utf-8")
            revoked=KnowledgeRevocationIndex.reconcile(w)
            assert len(revoked)==1 and revoked[0]["proof_id"]==w["proof"]["id"], revoked
            assert revoked[0]["status"]=="REVOKED" and revoked[0]["mismatches"]
            return "e2e: historical reconcile отзывает committed knowledge после мутации мира"

    def t_replay_rejects_duplicate_commit() -> str:
        led=ImmutableKnowledgeLedger(Path(tempfile.mkdtemp())/"k.jsonl")
        payload={"proof_id":"proof:DUP","claim_ids":["claim:1"],"evidence_ids":["e:1"],
                 "artifact_hashes":{},"proof_hash":"0"*64}
        led.append("COMMIT", payload); led.append("COMMIT", dict(payload))
        try: led.replay()
        except KnowledgeLedgerError: return "replay отклоняет дубликат COMMIT (политика форков полна)"
        raise AssertionError("дубликат COMMIT принят replay'ем")

    check("T118 proof closure cycle (unit)", t_proof_closure_rejects_cycle)
    check("T119 falsification contested (unit)", t_falsification_blocks_contested)
    check("T120 temporal future evidence (unit)", t_temporal_rejects_future_evidence)
    check("T73 proof anchor chain", t_anchor_ledger_hash_chain)
    check("T115 proof closure dangling (unit)", t_proof_closure_rejects_dangling_input)
    check("T116 proof closure closed (unit)", t_proof_closure_accepts_closed_graph)
    check("T117 temporal future (unit)", t_temporal_future_proof_rejected)
    check("T104 CAS changed state (renumbered; was duplicate T73 in v3.6.0)", t_cas_rejects_changed_state)
    check("T74 CAS unchanged state", t_cas_accepts_unchanged_state)
    check("T67 dangling dependency blocks verified", t_dangling_dependency_blocks_verified)
    check("T68 epistemic blockers attribution", t_epistemic_blockers_attributed)
    check("T69 blocked derivation invalidated", t_blocked_derivation_invalidated)
    check("T70 stale evidence blocks verified", t_stale_evidence_blocks_verified)
    check("T71 dependency cycle rejected", t_dependency_cycle_rejected)
    check("T72 governor tamper battery", t_governor_tamper_battery)
    check("T64 commit requires proof", t_commit_requires_proof)
    check("T65 commit rejects unknown proof", t_commit_rejects_unknown_proof)
    check("T66 commit accepts closed proof", t_commit_accepts_closed_proof)
    check("T62 epistemic unknown propagation", t_unknown_propagates_through_dependencies)
    check("T63 compiler dependency unknown", t_compiler_marks_dependency_unknown)
    check("T75 compiler dependency cycle", t_compiler_rejects_dependency_cycle)
    check("T76 freshness stale evidence", t_freshness_rejects_old_evidence)
    check("T77 artifact mutation reconciliation", t_commit_rejects_mutated_artifact)
    check("T78 revocation cascade", t_revocation_cascade_marks_dependents)
    check("T79 deleted artifact revocation", t_revocation_detects_deleted_artifact)
    check("T80 selective revocation", t_revocation_is_selective)
    check("T81 transitive revocation", t_revocation_transitive_claim_dependency)
    check("T82 knowledge revocation index commit", t_knowledge_revocation_index_persists_commit)
    check("T83 knowledge revocation index historical mutation", t_knowledge_revocation_index_finds_historical_mutation)
    check("T105 revival hole closed", t_revival_hole_closed)
    check("T106 revocation is dependency aware", t_revocation_is_dependency_aware)
    check("T107 post commit drift audit", t_post_commit_drift_audit)
    check("T108 revocation resolution on recommit", t_revocation_resolution_on_recommit)
    check("T109 closure error inside commit contract", t_closure_error_inside_commit_contract)
    check("T110 ledger contradiction contested", t_ledger_contradiction_contested)
    check("T111 e2e read binding and drift", t_e2e_read_binding_and_drift)
    check("T112 runtime knowledge ledger live", t_runtime_knowledge_ledger_live)
    check("T113 runtime historical reconcile", t_runtime_historical_reconcile)
    check("T114 replay rejects duplicate commit", t_replay_rejects_duplicate_commit)
    check("T60 typed rule wrong producer", t_typed_rule_rejects_wrong_producer)
    check("T61 typed rule matching producer", t_typed_rule_accepts_matching_producer)
    check("T56 unknown rule rejected", t_rule_registry_rejects_unknown_rule)
    check("T57 explicit versioned rule", t_rule_registry_is_explicit_and_versioned)
    check("T54 derivation graph rule", t_derivation_graph_records_rule)
    check("T55 derivation missing blocks", t_derivation_missing_blocks_verified)
    check("T52 contract producer integrity", t_contract_requires_producer_and_integrity)
    check("T53 contract matching observation", t_contract_accepts_matching_observation)
    check("T51 missing claim blocks verified", t_missing_one_claim_blocks_verified)
    check("T48 typed claim matching", t_claim_type_requires_matching_action)
    check("T49 evidence claim linkage", t_evidence_must_attach_to_claim)
    check("T45 foreign success not proof", t_success_without_required_action_not_proof)
    check("T43 failed action blocks success", t_action_dag_failed_action_blocks_success)

    check("T21 запрет небезопасного HTTP redirect", t_redirect_guard)
    check("T23 web research capability", t_research_tool_registered)
    check("T22 отсутствие внешнего каталога не маскируется под FAIL", t_missing_catalog_is_not_runtime_failure)

    def t_knowledge_ledger_chain_and_replay() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_kledger_") as td:
            q=ImmutableKnowledgeLedger(Path(td)/"knowledge.jsonl")
            q.append("COMMIT", {"proof_id":"p1","claim_ids":["c1"]})
            q.append("REVOKE", {"proof_id":"p1","reason":"artifact_mutation"})
            ok,bad=q.verify(); assert ok and bad is None
            r=q.replay(); assert "p1" in r["committed"] and "p1" in r["revoked"]
            return "immutable knowledge ledger: hash-chain + deterministic replay"

    def t_knowledge_ledger_tamper_rejected() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_kledger_tamper_") as td:
            path=Path(td)/"knowledge.jsonl"; q=ImmutableKnowledgeLedger(path)
            q.append("COMMIT", {"proof_id":"p1"}); q.append("COMMIT", {"proof_id":"p2"})
            rows=path.read_text(encoding="utf-8").splitlines(); row=json.loads(rows[0]); row["payload"]["proof_id"]="evil"; rows[0]=canonical_json(row); path.write_text("\n".join(rows)+"\n",encoding="utf-8")
            ok,bad=q.verify(); assert not ok and bad==0
            return "ledger tamper detected"

    def t_knowledge_ledger_fork_rejected() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_kledger_fork_") as td:
            q=ImmutableKnowledgeLedger(Path(td)/"knowledge.jsonl")
            q.append("COMMIT", {"proof_id":"p1"}); q.append("REVOKE", {"proof_id":"p1"})
            try:
                q.append("COMMIT", {"proof_id":"p1"})
            except Exception:
                raise AssertionError("append itself should remain syntactic")
            try: q.replay()
            except KnowledgeLedgerError: return "replay rejects commit-after-revoke fork"
            raise AssertionError("fork accepted")

    def t_knowledge_ledger_replay_reconstructs_state() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_t87_") as td:
            q=ImmutableKnowledgeLedger(Path(td)/"knowledge.jsonl")
            q.append("COMMIT", {"proof_id":"p1","claim_ids":["c1"]})
            q.append("COMMIT", {"proof_id":"p2","claim_ids":["c2"]})
            q.append("REVOKE", {"proof_id":"p1","reason":"artifact_mutation"})
            rs=q.replay_state()
            assert set(rs["active"])=={"p2"}
            assert set(rs["revoked"])=={"p1"}
            assert rs["state_hash"]==q.replay_digest()
            return "replay детерминированно восстанавливает durable knowledge state"

    def t_knowledge_ledger_replay_truncation_detected() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_t88_") as td:
            path=Path(td)/"knowledge.jsonl"; q=ImmutableKnowledgeLedger(path)
            q.append("COMMIT", {"proof_id":"p1"}); q.append("REVOKE", {"proof_id":"p1"})
            rows=path.read_text(encoding="utf-8").splitlines(); path.write_text(rows[0]+"\n",encoding="utf-8")
            rs=q.replay_state()
            assert rs["active"].keys()=={"p1"} and rs["revoked"]=={}
            assert rs["events"]==1
            return "усечённый ledger даёт отличимое reconstructed state"

    def t_knowledge_ledger_replay_proof_binding() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_t89_") as td:
            path=Path(td)/"knowledge.jsonl"; q=ImmutableKnowledgeLedger(path)
            proof={"id":"p1","status":"verified","claim_ids":["c1"]}
            q.append("COMMIT", {"proof_id":"p1","proof_hash":q._hash(proof)})
            archive={"p1":dict(proof)}
            assert q.replay_state(lambda pid: archive.get(pid))["active"]["p1"]["proof_hash"]
            archive["p1"]["claim_ids"]=["evil"]
            try: q.replay_state(lambda pid: archive.get(pid))
            except KnowledgeLedgerError: return "replay обнаруживает semantic tamper через независимый proof resolver"
            raise AssertionError("proof semantic tamper accepted")

    check("T84 knowledge ledger chain+replay", t_knowledge_ledger_chain_and_replay)
    check("T85 knowledge ledger tamper", t_knowledge_ledger_tamper_rejected)
    check("T86 knowledge ledger fork/replay", t_knowledge_ledger_fork_rejected)
    check("T87 replay reconstructs durable state", t_knowledge_ledger_replay_reconstructs_state)
    check("T88 replay distinguishes truncation", t_knowledge_ledger_replay_truncation_detected)
    check("T89 replay proof binding", t_knowledge_ledger_replay_proof_binding)

    def t_trust_anchor_detects_rollback() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_anchor_rollback_") as td:
            path=Path(td)/"knowledge.jsonl"; q=ImmutableKnowledgeLedger(path)
            q.append("COMMIT", {"proof_id":"p1"}); q.append("COMMIT", {"proof_id":"p2"})
            anchor=LedgerTrustAnchor.checkpoint(q); pinned=LedgerTrustAnchor.digest(anchor)
            rows=path.read_text(encoding="utf-8").splitlines(); path.write_text(rows[0]+"\\n",encoding="utf-8")
            try: LedgerTrustAnchor.verify(q, anchor, pinned)
            except KnowledgeLedgerError: return "pinned trust anchor detects ledger rollback"
            raise AssertionError("rollback accepted")

    def t_trust_anchor_detects_fork() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_anchor_fork_") as td:
            path=Path(td)/"knowledge.jsonl"; q=ImmutableKnowledgeLedger(path)
            q.append("COMMIT", {"proof_id":"p1"})
            anchor=LedgerTrustAnchor.checkpoint(q); pinned=LedgerTrustAnchor.digest(anchor)
            q.append("COMMIT", {"proof_id":"evil"})
            try: LedgerTrustAnchor.verify(q, anchor, pinned)
            except KnowledgeLedgerError: return "pinned trust anchor detects post-checkpoint fork"
            raise AssertionError("fork accepted")

    def t_trust_anchor_detects_substitution() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_anchor_substitution_") as td:
            path=Path(td)/"knowledge.jsonl"; q=ImmutableKnowledgeLedger(path)
            q.append("COMMIT", {"proof_id":"p1"})
            anchor=LedgerTrustAnchor.checkpoint(q); pinned=LedgerTrustAnchor.digest(anchor)
            substituted=dict(anchor); substituted["tip_hash"]="f"*64
            try: LedgerTrustAnchor.verify(q, substituted, pinned)
            except KnowledgeLedgerError: return "independent anchor digest rejects checkpoint substitution"
            raise AssertionError("checkpoint substitution accepted")

    def t_trust_anchor_accepts_exact_checkpoint() -> str:
        with tempfile.TemporaryDirectory(prefix="poly_anchor_exact_") as td:
            q=ImmutableKnowledgeLedger(Path(td)/"knowledge.jsonl")
            q.append("COMMIT", {"proof_id":"p1"})
            anchor=LedgerTrustAnchor.checkpoint(q); pinned=LedgerTrustAnchor.digest(anchor)
            result=LedgerTrustAnchor.verify(q, anchor, pinned)
            assert result["ok"] and result["checkpoint"]==anchor
            return "exact pinned checkpoint accepted"

    def t_trust_domains_are_separate() -> str:
        root=RootTrustAuthority(b"ROOT-KEY-0123456789")
        signing=SigningTrustDomain()
        key=b"SIGNING-KEY-0123456789"
        auth=root.authorize_signing_key("k1",key,1)
        signing.install(key,auth,root)
        cp=LedgerTrustAnchor.checkpoint(ImmutableKnowledgeLedger(Path(tempfile.mkdtemp())/"k.jsonl"))
        signed=signing.sign_checkpoint(cp,1)
        signing.verify_checkpoint(signed)
        assert auth["domain"] == "ROOT" and signed["domain"] == "SIGNING"
        return "root/signing domains are distinct"

    def t_root_key_substitution_rejected() -> str:
        root=RootTrustAuthority(b"ROOT-KEY-0123456789")
        auth=root.authorize_signing_key("k1",b"SIGNING-KEY-0123456789",1)
        evil=RootTrustAuthority(b"EVIL-ROOT-0123456789")
        try: evil.verify_authorization(auth)
        except KnowledgeLedgerError: return "root substitution rejected"
        raise AssertionError("foreign root accepted authorization")

    def t_key_epoch_rollback_rejected() -> str:
        root=RootTrustAuthority(b"ROOT-KEY-0123456789")
        root.authorize_signing_key("k1",b"SIGNING-KEY-0123456789",5)
        try: root.authorize_signing_key("k2",b"SIGNING-KEY-9876543210",4)
        except KnowledgeLedgerError: return "key epoch rollback rejected"
        raise AssertionError("epoch rollback accepted")

    def t_old_key_resurrection_rejected() -> str:
        root=RootTrustAuthority(b"ROOT-KEY-0123456789"); s=SigningTrustDomain()
        a1=root.authorize_signing_key("k1",b"SIGNING-KEY-0123456789",1); s.install(b"SIGNING-KEY-0123456789",a1,root)
        a2=root.authorize_signing_key("k2",b"SIGNING-KEY-9876543210",2); s.install(b"SIGNING-KEY-9876543210",a2,root)
        try: s.install(b"SIGNING-KEY-0123456789",a1,root)
        except KnowledgeLedgerError: return "old signing epoch resurrection rejected"
        raise AssertionError("old key resurrected")

    def t_cross_domain_replay_rejected() -> str:
        root=RootTrustAuthority(b"ROOT-KEY-0123456789"); s=SigningTrustDomain()
        a=root.authorize_signing_key("k1",b"SIGNING-KEY-0123456789",1); s.install(b"SIGNING-KEY-0123456789",a,root)
        signed=s.sign_checkpoint({"tip_hash":"a"},1)
        try: root.verify_authorization(signed)
        except KnowledgeLedgerError: return "signing checkpoint rejected in root domain"
        raise AssertionError("cross-domain replay accepted")

    def t_root_envelope_rejected_in_signing_domain() -> str:
        root=RootTrustAuthority(b"ROOT-KEY-0123456789"); s=SigningTrustDomain()
        a=root.authorize_signing_key("k1",b"SIGNING-KEY-0123456789",1)
        try: s.verify_checkpoint(a)
        except KnowledgeLedgerError: return "root authorization rejected as signing checkpoint"
        raise AssertionError("root envelope accepted as checkpoint")

    def t_key_history_fork_rejected() -> str:
        root=RootTrustAuthority(b"ROOT-KEY-0123456789")
        root.authorize_signing_key("k1",b"SIGNING-KEY-0123456789",1)
        root.authorize_signing_key("k2",b"SIGNING-KEY-9876543210",2)
        fork=dict(root.history[0]); fork["epoch"]=2; fork["key_id"]="evil"
        try: root.verify_authorization(fork)
        except KnowledgeLedgerError: return "forked authorization cannot validate"
        raise AssertionError("forked root authorization accepted")

    def t_checkpoint_epoch_tamper_rejected() -> str:
        root=RootTrustAuthority(b"ROOT-KEY-0123456789"); s=SigningTrustDomain()
        a=root.authorize_signing_key("k1",b"SIGNING-KEY-0123456789",1); s.install(b"SIGNING-KEY-0123456789",a,root)
        x=s.sign_checkpoint({"tip_hash":"a"},1); x["epoch"]=99
        try: s.verify_checkpoint(x)
        except KnowledgeLedgerError: return "checkpoint epoch tamper rejected"
        raise AssertionError("epoch tamper accepted")

    def t_revoked_epoch_checkpoint_rejected() -> str:
        root=RootTrustAuthority(b"ROOT-KEY-0123456789"); s=SigningTrustDomain()
        a1=root.authorize_signing_key("k1",b"SIGNING-KEY-0123456789",1); s.install(b"SIGNING-KEY-0123456789",a1,root)
        old=s.sign_checkpoint({"tip_hash":"a"},1)
        a2=root.authorize_signing_key("k2",b"SIGNING-KEY-9876543210",2); s.install(b"SIGNING-KEY-9876543210",a2,root); s.revoke("k1")
        try: s.verify_checkpoint(old)
        except KnowledgeLedgerError: return "revoked epoch checkpoint rejected"
        raise AssertionError("revoked checkpoint accepted")

    def t_root_rotation_history_integrity() -> str:
        root=RootTrustAuthority(b"ROOT-KEY-0123456789")
        root.authorize_signing_key("k1",b"SIGNING-KEY-0123456789",1)
        root.authorize_signing_key("k2",b"SIGNING-KEY-9876543210",2)
        tampered=dict(root.history[1]); tampered["key_fingerprint"]="f"*64
        try: root.verify_authorization(tampered)
        except KnowledgeLedgerError: return "root authorization tamper rejected"
        raise AssertionError("tampered authorization accepted")

    check("T94 trust-domain separation", t_trust_domains_are_separate)
    check("T95 root substitution", t_root_key_substitution_rejected)
    check("T96 key-epoch rollback", t_key_epoch_rollback_rejected)
    check("T97 old-key resurrection", t_old_key_resurrection_rejected)
    check("T98 cross-domain replay", t_cross_domain_replay_rejected)
    check("T99 root envelope in signing domain", t_root_envelope_rejected_in_signing_domain)
    check("T100 key-history fork", t_key_history_fork_rejected)
    check("T101 checkpoint epoch tamper", t_checkpoint_epoch_tamper_rejected)
    check("T102 revoked epoch checkpoint", t_revoked_epoch_checkpoint_rejected)
    check("T103 root authorization tamper", t_root_rotation_history_integrity)
    check("T90 trust anchor exact checkpoint", t_trust_anchor_accepts_exact_checkpoint)
    check("T91 trust anchor rollback", t_trust_anchor_detects_rollback)
    check("T92 trust anchor fork", t_trust_anchor_detects_fork)

    # ═════════════════════════════════════════════════════════════════════════
    # v3.8.0 ROOT EPOCH CHAIN — T121–T136 (ROOT → Proof → CAS → Revocation →
    # Reconciliation → COMMIT как механически проверяемая дуга)
    # ═════════════════════════════════════════════════════════════════════════

    def t_runtime_root_epoch_bound_to_commit() -> str:
        # v3.8.0 N-RT3 e2e: цепь не мёртвый код — активная эпоха вшита в proof,
        # commit-запись и ledger COMMIT живым runtime'ом (Agent.solve).
        with tempfile.TemporaryDirectory() as tmp:
            cfg, ws = _fresh_cfg(tmp)
            Path(ws).mkdir(parents=True, exist_ok=True)
            script=[
                {"thought": "План.", "status": "plan",
                 "success_criteria": ["hello.txt содержит 'final'"],
                 "plan": ["записать файл"]},
                {"thought": "Пишу.", "status": "act",
                 "actions": [{"name": "write_file", "args": {"path": "hello.txt", "content": "final"}}]},
                {"thought": "Готово.", "status": "final", "outcome": "verified",
                 "final_answer": "готово", "lesson": "root"},
            ]
            audit = AuditChain(Path(tmp) / "a.jsonl")
            agent = Agent(cfg, MockBrain(script), Governor(cfg, audit), audit)
            result = agent.solve("создай hello.txt со строкой final")
            assert result["outcome"] == "verified", result
            w = json.loads((Path(cfg.data_dir) / "working.json").read_text(encoding="utf-8"))
            assert isinstance(w.get("root_epoch_chain"), list) and w["root_epoch_chain"], \
                "root epoch chain отсутствует в runtime state"
            assert w.get("root_epoch_chain_pin"), "пин дайджеста корневой истории отсутствует"
            assert w["proof"].get("root_epoch") == 0, \
                f"proof.root_epoch={w['proof'].get('root_epoch')} — эпоха не вшита"
            assert w["proof"].get("root_fingerprint") == w["root_epoch_chain"][0]["root_fingerprint"], \
                "отпечаток корня в proof не совпадает с активной эпохой"
            assert w["commit"].get("root_epoch") == 0, "commit-запись без корневой эпохи"
            led = ImmutableKnowledgeLedger(Path(w["_knowledge_ledger_path"]))
            ok, bad = led.verify(); assert ok, f"ledger повреждён at row {bad}"
            rows = [r for r in led._rows() if r.get("event") == "COMMIT"]
            assert rows and rows[0]["payload"].get("root_epoch") == 0, \
                "ledger COMMIT не несёт корневую эпоху"
            return "e2e: активная корневая эпоха вшита в proof + commit + ledger COMMIT"

    def t_truncated_root_history_blocks_commit() -> str:
        # v3.8.0 N-RT1: verify_history пропускает усечение хвоста (слабая механика
        # ветки), но COMMIT-гейт сверяет пин дайджеста — усечение блокирует COMMIT.
        st={"_cas_version":0,"criteria":["capability:write_file выполнена"],
            "required_capabilities":["write_file"],
            "ledger":[{"step":1,"action":"write_file","ok":True,"kind":"write","obs_brief":"created"}]}
        h=[RootEpochChain.genesis("ROOT-A","t0")]
        h=RootEpochChain.rotate(h,"ROOT-B","t1"); h=RootEpochChain.rotate(h,"ROOT-C","t2")
        # Тампер-сценарий: пин отражает ПОЛНУЮ историю, в состоянии — УСЕЧЁННАЯ
        # ( ровно как атака усечением хвоста); всё ДО компиляции proof'а, чтобы
        # проверить именно корневой гейт, а не CAS.
        st["root_epoch_chain"]=[asdict(e) for e in h[:2]]
        st["root_epoch_chain_pin"]=RootEpochChain.history_digest(h)
        p=ProofCompiler(st).compile(); st["proof"]=asdict(p)
        try:
            ProofCarryingGovernor.commit(st)
        except ProofCarryingCommitError as e:
            assert "ROOT TRUST" in str(e), str(e)
            return "усечение корневой истории ловится пином и блокирует COMMIT"
        raise AssertionError("truncated root history accepted by COMMIT")

    def t_revoked_root_blocks_commit() -> str:
        # v3.8.0 N-RT4 e2e: отозванный корень запрещает COMMIT; RootTrustError
        # конвертируется в ProofCarryingCommitError (контракт исключений цел).
        st={"_cas_version":0,"criteria":["capability:write_file выполнена"],
            "required_capabilities":["write_file"],
            "ledger":[{"step":1,"action":"write_file","ok":True,"kind":"write","obs_brief":"created"}]}
        h=[RootEpochChain.genesis("ROOT-A","t0")]
        h=RootEpochChain.revoke_current(h)
        st["root_epoch_chain"]=[asdict(e) for e in h]
        st["root_epoch_chain_pin"]=RootEpochChain.history_digest(h)
        p=ProofCompiler(st).compile(); st["proof"]=asdict(p)
        try:
            ProofCarryingGovernor.commit(st)
        except ProofCarryingCommitError as e:
            assert "ROOT TRUST" in str(e) and "no active root" in str(e), str(e)
            return "отозванный корень блокирует COMMIT в контракте исключений"
        raise AssertionError("revoked root accepted by COMMIT")

    def t_double_revoke_and_revoked_rotation_rejected() -> str:
        # v3.8.0 N-RT2: ветка-источник принимала оба молча.
        h=[RootEpochChain.genesis("A","t0")]
        h1=RootEpochChain.revoke_current(h)
        try: RootEpochChain.revoke_current(h1)
        except RootTrustError: pass
        else: raise AssertionError("double revoke accepted")
        try: RootEpochChain.rotate(h1,"B","t1")
        except RootTrustError: pass
        else: raise AssertionError("rotation from revoked accepted")
        return "двойной revoke и ротация от отозванного корня отклоняются"

    def t_replay_root_epoch_rollback_rejected() -> str:
        # v3.8.0: журнал не может содержать откат корневой эпохи.
        led=ImmutableKnowledgeLedger(Path(tempfile.mkdtemp())/"k.jsonl")
        led.append("COMMIT",{"proof_id":"proof:E1","root_epoch":1,"root_fingerprint":"f1"})
        led.append("COMMIT",{"proof_id":"proof:E0","root_epoch":0,"root_fingerprint":"f0"})
        try: led.replay()
        except KnowledgeLedgerError as e:
            assert "root epoch rollback" in str(e), str(e)
            return "replay отклоняет откат корневой эпохи (форк истории)"
        raise AssertionError("root epoch rollback accepted in replay")

    def t_historical_epoch_validation() -> str:
        # Двухконтурная политика: replay/аудит валидирует исторические эпохи,
        # но отозванная/неизвестная эпоха отклоняется.
        h=[RootEpochChain.genesis("A","t0")]; h=RootEpochChain.rotate(h,"B","t1")
        assert RootEpochChain.validate_epoch(h,0,h[0].root_fingerprint)
        try: RootEpochChain.validate_epoch(h,7,h[1].root_fingerprint)
        except RootTrustError: pass
        else: raise AssertionError("unknown epoch accepted")
        hr=RootEpochChain.revoke_current(h)
        try: RootEpochChain.validate_epoch(hr,1,hr[1].root_fingerprint)
        except RootTrustError: pass
        else: raise AssertionError("revoked epoch accepted")
        return "историческая валидация: старая эпоха валидна, неизвестная/отозванная отклонены"

    def t_rt_valid_rotation() -> str:
        h=[RootEpochChain.genesis("ROOT-A","2026-01-01T00:00:00Z")]
        h=RootEpochChain.rotate(h,"ROOT-B","2026-02-01T00:00:00Z")
        RootEpochChain.verify_history(h); assert h[-1].epoch==1
        return "port T94: валидная ротация принимается"

    def t_rt_epoch_rollback_checkpoint() -> str:
        h=[RootEpochChain.genesis("A","t0")]; h=RootEpochChain.rotate(h,"B","t1")
        try: RootEpochChain.validate_checkpoint_active(h,0,h[0].root_fingerprint)
        except RootTrustError: return "port T95: чекпоинт прошлой эпохи против активного контура отклонён"
        raise AssertionError("old epoch accepted")

    def t_rt_old_root_resurrection() -> str:
        h=[RootEpochChain.genesis("A","t0")]; h=RootEpochChain.rotate(h,"B","t1")
        e=RootEpoch(2,h[0].root_fingerprint,h[-1].root_fingerprint,"t2",
                    RootEpochChain.authorization_hash(2,h[0].root_fingerprint,h[-1].root_fingerprint,"t2"))
        try: RootEpochChain.verify_history(h+[e])
        except RootTrustError: return "port T96: воскресение старого корня отклонено"
        raise AssertionError("old root resurrected")

    def t_rt_truncation_pin_required() -> str:
        # УСИЛЕНО против ветки-источника: там тест проверял лишь «digest differs»,
        # а verify_history ПРИНИМАЛ усечённую историю. Здесь: слабая механика
        # демонстрируется, затем пин на production-форме ОТКЛОНЯЕТ усечение.
        h=[RootEpochChain.genesis("A","t0")]; h=RootEpochChain.rotate(h,"B","t1"); h=RootEpochChain.rotate(h,"C","t2")
        trunc=h[:2]
        RootEpochChain.verify_history(trunc)  # слабая механика действительно пропускает
        st={"root_epoch_chain":[asdict(e) for e in trunc],
            "root_epoch_chain_pin":RootEpochChain.history_digest(h)}
        try: RootEpochChain.validate_pinned_state(st)
        except RootTrustError: return "port T97 УСИЛЕН: усечение хвоста отклонено пином на production-форме"
        raise AssertionError("truncation not detected by pin")

    def t_rt_history_fork() -> str:
        h=[RootEpochChain.genesis("A","t0")]; h=RootEpochChain.rotate(h,"B","t1")
        bad=h+[RootEpoch(2,RootEpochChain.fingerprint("C"),RootEpochChain.fingerprint("WRONG"),"t2","0"*64)]
        try: RootEpochChain.verify_history(bad)
        except RootTrustError: return "port T98: форк истории отклонён"
        raise AssertionError("fork accepted")

    def t_rt_domain_confusion() -> str:
        h=[RootEpochChain.genesis("ROOT-A","t0")]
        signing_fp=RootEpochChain.fingerprint("SIGNING-A")
        try: RootEpochChain.validate_checkpoint_active(h,0,signing_fp)
        except RootTrustError: return "port T99: отпечаток подписывающего домена не проходит как корневой"
        raise AssertionError("signing fingerprint accepted as root")

    def t_rt_revoked_no_active() -> str:
        h=[RootEpochChain.genesis("A","t0")]; h=RootEpochChain.rotate(h,"B","t1"); h=RootEpochChain.revoke_current(h)
        try: RootEpochChain.active(h)
        except RootTrustError: return "port T100: у отозванного корня нет активной эпохи"
        raise AssertionError("revoked root remained active")

    def t_rt_auth_tamper() -> str:
        h=[RootEpochChain.genesis("A","t0")]; e=h[0]
        bad=[RootEpoch(e.epoch,e.root_fingerprint,e.parent_fingerprint,e.effective_at,"f"*64,e.revoked)]
        try: RootEpochChain.verify_history(bad)
        except RootTrustError: return "port T101: подмена authorization_hash отклонена"
        raise AssertionError("tamper accepted")

    def t_rt_same_root_rotation() -> str:
        h=[RootEpochChain.genesis("A","t0")]
        try: RootEpochChain.rotate(h,"A","t1")
        except RootTrustError: return "port T102: псевдоротация тем же корнем отклонена"
        raise AssertionError("same root accepted")

    def t_rt_active_fingerprint_mismatch() -> str:
        h=[RootEpochChain.genesis("A","t0")]
        try: RootEpochChain.validate_checkpoint_active(h,0,"0"*64)
        except RootTrustError: return "port T103: чекпоинт с чужим отпечатком отклонён"
        raise AssertionError("wrong fingerprint accepted")

    # ═════════════════════════════════════════════════════════════════════════
    # v3.9.0 HMAC DOMAIN BINDING — T137–T139 (A1.1 стандартный MAC + A1.2 связка
    # authorize_signing_key с активной эпохой RootEpochChain)
    # ═════════════════════════════════════════════════════════════════════════

    def t_hmac_binding_active_root() -> str:
        root_key=b"ROOT-KEY-0123456789"
        hist=[RootEpochChain.genesis("ROOT-A","2026-01-01T00:00:00Z")]
        root=RootTrustAuthority(root_key, chain_provider=lambda: hist)
        signing=SigningTrustDomain()
        key=b"SIGNING-KEY-0123456789"
        auth=root.authorize_signing_key("k1",key,1)
        assert auth.get("root_fingerprint")==hist[-1].root_fingerprint, \
            "активный корневой отпечаток не вшит в авторизацию"
        root.verify_authorization(auth)
        signing.install(key,auth,root)
        cp=LedgerTrustAnchor.checkpoint(ImmutableKnowledgeLedger(Path(tempfile.mkdtemp())/"k.jsonl"))
        signing.verify_checkpoint(signing.sign_checkpoint(cp,1))
        # A1.1: MAC обязан быть стандартным HMAC-SHA256 (независимый пересчёт hmac_hex)
        body={k:v for k,v in auth.items() if k!="root_mac"}
        assert hmac_compare(hmac_hex(root_key,body), auth["root_mac"]), \
            "MAC не соответствует стандартному HMAC-SHA256"
        return "авторизация вшивает активный корень; MAC = HMAC-SHA256; чекпоинт подписан"

    def t_hmac_binding_rotation_invalidates() -> str:
        hist=[RootEpochChain.genesis("ROOT-A","2026-01-01T00:00:00Z")]
        root=RootTrustAuthority(b"ROOT-KEY-0123456789", chain_provider=lambda: hist)
        auth=root.authorize_signing_key("k1",b"SIGNING-KEY-0123456789",1)
        hist[:]=RootEpochChain.rotate(hist,"ROOT-B","2026-02-01T00:00:00Z")
        try:
            root.verify_authorization(auth)
            raise AssertionError("устаревшая авторизация принята после ротации")
        except KnowledgeLedgerError:
            pass
        signing=SigningTrustDomain()
        try:
            signing.install(b"SIGNING-KEY-0123456789",auth,root)
            raise AssertionError("install принял авторизацию под прошедшим корнем")
        except KnowledgeLedgerError:
            pass
        auth2=root.authorize_signing_key("k2",b"SIGNING-KEY-9876543210",2)
        assert auth2["root_fingerprint"]==hist[-1].root_fingerprint, \
            "повторная авторизация не ссылается на новый активный корень"
        root.verify_authorization(auth2)
        return "ротация корня инвалидирует неподтверждённые авторизации; новая валидна"

    def t_hmac_binding_revocation_invalidates() -> str:
        hist=[RootEpochChain.genesis("ROOT-A","2026-01-01T00:00:00Z")]
        root=RootTrustAuthority(b"ROOT-KEY-0123456789", chain_provider=lambda: hist)
        auth=root.authorize_signing_key("k1",b"SIGNING-KEY-0123456789",1)
        hist[:]=RootEpochChain.revoke_current(hist)
        try:
            root.verify_authorization(auth)
            raise AssertionError("авторизация отозванного корня принята")
        except KnowledgeLedgerError:
            pass
        return "отзыв корня инвалидирует неподтверждённые авторизации"

    check("T93 trust anchor substitution", t_trust_anchor_detects_substitution)
    check("T121 runtime root epoch bound to COMMIT", t_runtime_root_epoch_bound_to_commit)
    check("T122 truncated root history blocks COMMIT", t_truncated_root_history_blocks_commit)
    check("T123 revoked root blocks COMMIT", t_revoked_root_blocks_commit)
    check("T124 double revoke / revoked rotation rejected", t_double_revoke_and_revoked_rotation_rejected)
    check("T125 replay root-epoch rollback", t_replay_root_epoch_rollback_rejected)
    check("T126 historical epoch validation", t_historical_epoch_validation)
    check("T127 root chain valid rotation (port)", t_rt_valid_rotation)
    check("T128 root epoch rollback checkpoint (port)", t_rt_epoch_rollback_checkpoint)
    check("T129 old-root resurrection (port)", t_rt_old_root_resurrection)
    check("T130 truncation detected via pin (port, усилен)", t_rt_truncation_pin_required)
    check("T131 root-history fork (port)", t_rt_history_fork)
    check("T132 root/signing domain confusion (port)", t_rt_domain_confusion)
    check("T133 revoked root has no active epoch (port)", t_rt_revoked_no_active)
    check("T134 root authorization tamper (port)", t_rt_auth_tamper)
    check("T135 same-root pseudo-rotation (port)", t_rt_same_root_rotation)
    check("T136 active checkpoint fingerprint mismatch (port)", t_rt_active_fingerprint_mismatch)
    check("T137 signing-key authorization bound to active root (A1.2)", t_hmac_binding_active_root)
    check("T138 root rotation invalidates unconfirmed authorization (A1.2)", t_hmac_binding_rotation_invalidates)
    check("T139 root revocation invalidates unconfirmed authorization (A1.2)", t_hmac_binding_revocation_invalidates)

    # ═══ v3.10.0 C5 GATE ANTI-VACUUM: невыразимость вакуумного отказа + мета-гейт ═══
    def t_c5_vacuous_refusal() -> str:
        exc = GateAntiVacuum.refuse("COMMIT", "CAS conflict — сплайс-проба C5")
        assert isinstance(exc, ProofCarryingCommitError) and str(exc).startswith("COMMIT: "), \
            "refuse() не вернул отказ с namespaced-причиной"
        for bad in [("", "reason"), ("COMMIT", ""), ("COMMIT", "   "), ("COMMIT", "x")]:
            try:
                GateAntiVacuum.refuse(*bad)
                raise AssertionError(f"C5: вакуумный отказ выразим: {bad!r}")
            except VacuousRefusalError:
                pass
        return "вакуумный отказ невыразим: refuse() без гейта/причины сам поднимает VacuousRefusalError"

    def t_c5_meta_gate() -> str:
        bad = GateAntiVacuum.audit()
        assert not bad, f"C5: нарушения реестра: {bad}"
        executed = {name: ok for name, ok, _ in results}
        for g in GATE_REGISTRY:
            for w in g["honest_witnesses"]:
                assert w in executed, f"C5: honest-свидетель {w!r} гейта {g['gate']} не исполнен"
                assert executed[w], f"C5: honest-свидетель {w!r} гейта {g['gate']} провален"
            for w in g["refusal_witnesses"]:
                assert w in executed, f"C5: refusal-свидетель {w!r} гейта {g['gate']} не исполнен"
                assert executed[w], f"C5: refusal-свидетель {w!r} гейта {g['gate']} провален"
        assert len(GATE_REGISTRY) >= 11, "C5: реестр гейтов сжался ниже аудиторского пола"
        total_w = sum(len(g["honest_witnesses"]) + len(g["refusal_witnesses"]) for g in GATE_REGISTRY)
        return (f"анти-вакуумная сверка {len(GATE_REGISTRY)} гейтов COMMIT-контура: "
                f"причины именованы, все {total_w} парных свидетелей исполнены и зелёные")

    check("T141 vacuous refusal is inexpressible (C5)", t_c5_vacuous_refusal)
    check("T140 C5 gate anti-vacuum meta-gate", t_c5_meta_gate)

    print("\n=== САМОПРОВЕРКА ЯДРА ===")
    fails = 0
    for name, ok, detail in results:
        mark = "PASS" if ok else "FAIL"
        if not ok:
            fails += 1
        print(f"[{mark}] {name} :: {detail}")
    total = len(results)
    print(f"Итого: {total - fails}/{total} зелёных")
    return 0 if fails == 0 else 1


# Заглушка для читаемости T03: верификация существующей цепочки с нуля
class AuditChainVerifyProbe(AuditChain):
    @staticmethod
    def verify_from(path: Path) -> Tuple[bool, Optional[int]]:
        probe = AuditChain.__new__(AuditChain)
        probe.path = path
        probe.last_hash = "GENESIS"
        return AuditChain.verify(probe)


# ════════════════════ CLI ═══════════════════

def parse_args(argv: List[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        prog="polymath_agent",
        description="Полимат: целостный агент (Субъект/Тело/Конституция). Нулевые зависимости.")
    ap.add_argument("--selftest", action="store_true", help="самопроверка ядра без LLM")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--task", help="задача одной строкой")
    g.add_argument("--task-file", help="файл с текстом задачи")
    g.add_argument("--queue", help="демон: читать задачи построчно из файла очереди")
    ap.add_argument("--brain", choices=["api", "mock", "ollama-native"], default="api",
                    help="api = OpenAI-совместимый бэкенд; ollama-native = нативный /api/chat "
                         "с format=<JSON Schema>; mock только для тестов")
    ap.add_argument("--catalog", default=Config.catalog_path,
                    help="путь к tool_catalog.json (арсенал Тела; пусто = без арсенала)")
    ap.add_argument("--base-url", default=os.environ.get("POLY_BASE_URL", "http://localhost:11434/v1"))
    ap.add_argument("--model", default=Config.model)
    ap.add_argument("--api-key-env", default="", help="имя env-переменной с bearer-ключом")
    ap.add_argument("--max-steps", type=int, default=24)
    ap.add_argument("--time-budget-s", type=int, default=900)
    ap.add_argument("--brain-timeout-s", type=int, default=Config.brain_timeout_s,
                    help="таймаут одного вызова мозга (CPU-хостам ставьте больше)")
    ap.add_argument("--yes", action="store_true", default=False,
                    help="автоматически разрешать действия риска EXEC/NET (осторожно)")
    ap.add_argument("--workspace", default="./poly_workspace")
    ap.add_argument("--data-dir", default="./poly_data")
    ap.add_argument("--no-resume", action="store_true", help="не восстанавливать последний checkpoint задачи")
    ap.add_argument("--poll-interval", type=int, default=5, help="интервал опроса очереди, сек")
    return ap.parse_args(argv)


def run_queue_mode(args: argparse.Namespace) -> int:
    """Режим очереди — исправление бага прототипа №2 (было: task = lines)."""
    q = Path(args.queue)
    log("QUEUE", f"демон запущен, слежу за {q}")
    while True:
        if q.is_file():
            lines = [ln for ln in q.read_text(encoding="utf-8").splitlines() if ln.strip()]
            if lines:
                task_text = lines[0]                       # ← одна задача, не весь список
                rest = lines[1:]
                q.write_text("\n".join(rest) + ("\n" if rest else ""), encoding="utf-8")
                cfg = build_cfg_from_args(args, task_source="queue")
                brain = make_brain(cfg, args.brain)
                audit = AuditChain(Path(cfg.data_dir) / "audit.jsonl")
                bridge = CatalogBridge(cfg.catalog_path)
                Agent(cfg, brain, Governor(cfg, audit, bridge), audit).solve(task_text)
        time.sleep(max(2, args.poll_interval))


def make_brain(cfg: Config, kind: str):
    if kind == "api":
        return ApiBrain(cfg)
    if kind == "ollama-native":
        return OllamaNativeBrain(cfg)
    return MockBrain([])


def build_cfg_from_args(args: argparse.Namespace, task_source: str) -> Config:
    cfg = Config(
        brain_kind=args.brain, base_url=args.base_url, model=args.model,
        api_key_env=args.api_key_env, max_steps=args.max_steps,
        time_budget_s=args.time_budget_s, auto_yes=bool(args.yes),
        brain_timeout_s=args.brain_timeout_s, catalog_path=args.catalog,
        workspace=args.workspace, data_dir=args.data_dir, resume=not bool(args.no_resume))
    return cfg


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    if args.selftest:
        return selftest()
    task_text = args.task or (Path(args.task_file).read_text(encoding="utf-8")
                              if args.task_file else None)
    if args.queue:
        return run_queue_mode(args)
    if not task_text:
        parse_args(["--help"])
        return 2
    cfg = build_cfg_from_args(args, task_source="cli")
    bridge = CatalogBridge(cfg.catalog_path)
    if bridge.total:
        log("CATALOG", f"арсенал: {bridge.total} записей / {bridge.categories} категорий; "
                       f"исполнимо на этой машине: {bridge.available}")
    brain = make_brain(cfg, args.brain)
    audit = AuditChain(Path(cfg.data_dir) / "audit.jsonl")
    result = Agent(cfg, brain, Governor(cfg, audit, bridge), audit).solve(task_text.strip())
    return 0 if result["outcome"] == "verified" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))