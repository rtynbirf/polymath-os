#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
polymath_agent.py — рабочее ядро целостного агента v1.2.8 «Арсенал+Цепь» (восстановлено из базы v2 после сброса среды 28.08.2026; v1.2.2–v1.2.8 — закалка 10 живыми огнями кампании цепей).
Единый файл. Только стандартная библиотека Python 3.9+. Внешних зависимостей НЕТ.

=== v1.2: ТЕЛО = АРСЕНАЛ + ПЕРЕМЕННАЯ $last_output ===
  CatalogBridge: каталог 2444 декларирует — shutil.which подтверждает — Governor выпускает через run_cli;
  констрейнт вывода: JSON Schema (maxLength-бюджеты) в нативный /api/chat, GBNF-эквивалент для llama.cpp;
  гейт релевантности процедурной памяти; запрет пустой записи; свидетель: токен-факты + (0 символов) не свидетель
  + контентная сверка литералов критерия с артефактом; PLAN_LOCK против план-лупа;
  $last_output: механическая подстановка вывода последнего успешного действия в args следующего
  v1.2.2: АТОМАРНОЕ РЕШЕНИЕ — maxItems 3→1 (огни 5a1b0a7390/106c586e47: два действия в одном
  act не влезли в num_predict, JSON обрезан посреди, мозг умер) + честный диагноз обреза JSON;
  v1.2.3: непробиваемый план-замок — второй фингерпринт по нормализованному thought (огонь
  05a5fef056: обход замка перефразированием, шаги 2≡3 и 7≡8);
  v1.2.4: ВЕЧНАЯ ЛЕНТА ФАКТОВ — накопленные успехи в контексте каждого такта (огонь
  1406a05ad5: 6 переспросов wc после исчезновения вывода шага №1 из контекста);
  v1.2.5/6: ПЛАН-ГИГИЕНА — повторный plan отклоняется на валидации, streak-счётчик (огонь
  accb1c587c: 7 планов подряд);
  v1.2.7: ДЕДУП-КЭШ — повтор физически не исполняется, но возвращает кэш-наблюдение с
  маркером (огонь 9c177a7aa4: отказ дедупа читался как «команда не выполнена»);
  v1.2.8: ПЛАН ВСЕГДА ВИДЕН + маркер «НЕ планируй заново» (огни f15e64b15b/32fba99ad2:
  скрытие плана лишило модель навигации — «перезапуск шага 1»; план = GPS, не провокация);
  RAM-гейт стенда: state-save промпт-кэша ~250 MiB/шаг убивал llama-server (66c4119357),
  лечение: OLLAMA_KEEP_ALIVE=1s (холодный запрос 2.8 с — веса в page-cache).
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
from dataclasses import dataclass, field
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
        with urllib.request.urlopen(req, timeout=cfg.net_timeout_s) as resp:
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
        self._seen_side_effect: Dict[str, Tuple[int, Observation]] = {}

    # --- реестр: промпт документируется ТОЛЬКО отсюда (анти-Ф4) ---
    def _register_builtin_tools(self):
        reg = self.registry
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
        idem_key: Optional[str] = None   # v1.2.7: ключ дедуп-кэша (заполняется для не-READ)
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
            idem_key = idem
            prior = self._seen_side_effect.get(idem)
            if prior is not None:
                prior_step, prev_obs = prior
                self.audit.append({"task_id": task_id, "step": step_idx, "action": name,
                                   "verdict": "deduped", "first_seen_step": prior_step})
                # v1.2.7: дедуп-КЭШ вместо штрафного отказа (огонь 9c177a7aa4: 1.7b читал
                # отказ дедупа как «команда не выполнена» и стучался в дедуп 6+ раз).
                # Идемпотентность цела: физически НЕ исполняется, но модель получает
                # результат первого исполнения с честным маркером кэша.
                return Observation(True, prev_obs.kind,
                                   f"(уже исполнено на шаге {prior_step}, результат из кэша — "
                                   "не исполнялось повторно; ЭТУ КОМАНДУ БОЛЬШЕ НЕ ВЫЗЫВАЙ — "
                                   "вывод уже в $last_output; твоё следующее действие — "
                                   "СЛЕДУЮЩЕЕ действие плана, для вывода команд передавай "
                                   "content=\"$last_output\") " + prev_obs.content,
                                   meta={"dedup": True, "first_step": prior_step,
                                         **prev_obs.meta}), None   # fp=None: не новый артефакт
            self._seen_side_effect[idem_key] = (step_idx, None)   # кэш заполнится после исполнения

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
            if p and Path(p).exists():
                artifact_fp = sha256_hex(Path(p).read_bytes())[:16]
        # v1.2.7: заполняем кэш дедупа наблюдением первого исполнения
        if spec.risk != "READ" and idem_key is not None and obs.ok:
            self._seen_side_effect[idem_key] = (step_idx, obs)
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
            # v1.2.2: атомарное решение — ровно одно действие (защита от обреза JSON
            # по num_predict: два действия с why/thought ~450 токенов > бюджета у 1.7b)
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
    # v1.2.8: ПЛАН ВСЕГДА ВИДЕН — это GPS модели. Скрытие плана (промежуточная
    # закалка v1.2.5) лишило модель навигации: «начиная с первого действия» = перезапуск
    # шага 1 (огни f15e64b15b/32fba99ad2). Успешные C1 и Task 7 шли по всегда видимому плану.
    if state.get("plan"):
        plan_header = ("ПЛАН (уже принят — НЕ планируй заново, выходи в act по следующему "
                       "незавершённому пункту):" if state.get("_plan_streak", 0) >= 1
                       else "ПЛАН:")
        parts.append(plan_header + "\n"
                     + "\n".join(f"{i+1}. {s}" for i, s in enumerate(state["plan"])))

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
    # Огонь 1406a05ad5: «единственный источник фактов» показывал только последний такт —
    # модель переспрашивала исполненные команды. Факты в промпте закрывают переспросы.
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
        if not isinstance(acts, list) or not (1 <= len(acts) <= 3):
            return "при status=act поле actions обязано быть списком из 1..3 действий"
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


class Agent:
    def __init__(self, cfg: Config, brain: Any, gov: Governor, audit: AuditChain):
        self.cfg = cfg
        self.brain = brain
        self.gov = gov
        self.audit = audit

    def solve(self, task_text: str) -> Dict[str, Any]:
        task_id = sha256_hex(task_text + now_iso())[:10]
        Path(self.cfg.workspace).mkdir(parents=True, exist_ok=True)
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
            "_plan_streak": 0,       # v1.2.6: планы подряд без действий между ними
        }
        self.gov.mem.save_working(state)
        started = time.monotonic()
        last_observations: List[Tuple[int, Observation]] = []
        stall = 0
        last_fp: Optional[str] = None
        last_thought_fp: Optional[str] = None   # v1.2.3: нормализованная мысль последнего плана
        error_feedback: Optional[str] = None

        log("AGENT", f"Задача {task_id}: {task_text}")

        while len(state["ledger"]) < self.cfg.max_steps:
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
                    return self._finalize(task_id, state, "aborted", f"Мозг недоступен: {e}", started)
                problem = validate_decision(raw)
                # v1.2.5/6: план-гигиена — повторный plan при принятых двух подряд
                # отклоняется НА ВАЛИДАЦИИ (repair-раунд с честным фидбеком), а не просто
                # директивой на следующий такт (огонь accb1c587c: 7 планов подряд)
                if problem is None and raw.get("status") == "plan" and state.get("_plan_streak", 0) >= 2:
                    problem = ("ПЛАН-ГИГИЕНА: два плана подряд уже приняты без действий между "
                               "ними; статус plan механически запрещён — верни status=act с "
                               "ровно одним действием, продвигающим ближайший незавершённый "
                               "пункт плана")
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
                # v1.2.6: streak растёт на КАЖДОМ принятом плане; два подряд без act — запрет
                state["_plan_streak"] = state.get("_plan_streak", 0) + 1
                state["criteria"] = decision.get("success_criteria", state["criteria"])
                state["plan"] = decision.get("plan", state["plan"])
                state["ledger"].append({"step": step_idx, "action": "(план)", "ok": True,
                                        "kind": "orient", "obs_brief": decision["thought"][:300]})
                progress_fp = sha256_hex(canonical_json([state["criteria"], state["plan"]]))
                # v1.2.3: второй, независимый фингерпринт — НОРМАЛИЗОВАННАЯ мысль.
                # Огонь 05a5fef056: 1.7b обходил замок, перефразируя пункты плана и
                # критерии при идентичной мысли. fp-плана + fp-мысли закрывают оба вектора.
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
                state["_plan_streak"] = 0   # v1.2.6: действие сбрасывает серию планов
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
                        obs, fp = self.gov.run(task_id, step_idx, act["name"], act_args)
                    obs_list.append((step_idx, obs))
                    state["ledger"].append({"step": step_idx, "action": act["name"],
                                            "ok": obs.ok, "kind": obs.kind,
                                            "obs_brief": obs.brief(280)})
                    if fp:
                        new_artifact = True
                        state.setdefault("_artifacts", []).append(fp)
                    if obs.kind == "read" and obs.ok:
                        new_artifact = True      # чтение даёт новую информацию = прогресс
                    if obs.ok and not obs.meta.get("dedup"):
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
                    missing = self._unwitnessed_criteria(state)
                    if state.get("criteria") and missing:
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
                return self._finalize(task_id, state,
                                      decision["outcome"],
                                      decision.get("final_answer", ""),
                                      started,
                                      lesson=decision.get("lesson", ""))

            self.gov.mem.save_working(state)

        return self._finalize(task_id, state, "aborted",
                              "Исчерпан лимит шагов до объявления финала.", started)

    @staticmethod
    def _unwitnessed_criteria(state: Dict[str, Any]) -> List[str]:
        """Критерий «увиден», если хотя бы один значимый токен критерия совпал
        с любым успешным наблюдением за ВСЮ историю задачи (кумулятивно),
        ЛИБО если литерал из критерия ('hi', "git version…") реально содержится
        в артефакте на диске (контентная сверка, закалено эпизодом 83311d5bde).
        Отвергает имитацию успеха; факт пустой записи «(0 символов)» свидетелем
        НЕ признаётся — наблюдение было, содержимого не было."""
        facts_blob = " ".join(f for f in state.get("facts", [])
                              if "(0 символов)" not in f).lower()
        art_blob = ""
        for pth in state.get("_artifact_paths", []):
            try:
                art_blob += Path(pth).read_text(encoding="utf-8",
                                                errors="replace").lower() + "\n"
            except Exception:
                pass
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
            "criteria_verified": len(set()) if outcome != "verified" else len(state.get("criteria", [])),
            "lesson": lesson,
            "answer_preview": answer[:400],
        }
        self.gov.mem.write_episode(episode)
        self.gov.mem.save_working(state)
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
            errs = []
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
            ac2 = AuditChainVerifyProbe
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
            # v1.2.7: повтор физически не исполняется, но возвращает кэш-наблюдение
            assert obs1.ok, f"первое исполнение сломано: {obs1.brief()}"
            assert obs2.ok and obs2.meta.get("dedup") and "side-effect" in obs2.content, \
                f"дедуп-кэш не вернул результат: {obs2.brief()}"
            audit_lines = (Path(tmp) / "a.jsonl").read_text(encoding="utf-8")
            assert '"verdict": "deduped"' in audit_lines, "аудит не отметил дедуп"
            return "повторный EXEC не исполняется физически: кэш-наблюдение + 'deduped' в аудите"

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
            # (v1.2.7: дедуп возвращает кэш с маркером, физического повтора нет)
            obs3, _ = gov.run("t11", 3, "run_cli",
                              {"bin": "python3", "args": ["-c", "print(40+2)"], "stdin": ""})
            assert obs3.ok and obs3.meta.get("dedup") and "42" in obs3.content, \
                f"канонизация дедупа не сработала: {obs3.brief()}"
            digest = bridge.arsenal_digest("посчитать хеш sha256 через python3")
            assert "python3" in digest, "дайджест не релевантен"
            return (f"мост: run_cli исполнен (python3), вне арсенала отклонён, "
                    f"дубликаты схлопнуты, дайджест релевантен")

    def t_arsenal_real() -> str:
        cpath = os.environ.get("POLY_CATALOG") or "./tool_catalog.json"
        assert Path(cpath).exists(), f"реальный каталог не найден: {cpath}"
        bridge = CatalogBridge(cpath)
        assert bridge.total >= 2400, f"мало записей: {bridge.total}"
        assert bridge.categories == 34, f"категорий {bridge.categories}, ожидалось 34"
        assert bridge.bins >= 1500, f"мало бинарей: {bridge.bins}"
        assert bridge.available >= 1, "ни одного исполнимого бинаря на машине"
        return (f"реальный арсенал: {bridge.total}/34, бинарей {bridge.bins}, "
                f"исполнимо здесь {bridge.available}")

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

    def _ledger_of(cfg):   # локальный хелпер проб план-гигиены
        import json as _json
        return _json.loads((Path(cfg.data_dir) / "working.json").read_text(encoding="utf-8")).get("ledger", [])

    def t_plan_hygiene() -> str:
        """v1.2.5: третий план подряд при двух принятых отклоняется НА ВАЛИДАЦИИ,
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
            agent = Agent(cfg, QueueBrain([plan_t, plan_t, plan_t, act_d, {
                "thought": "выходим", "status": "final", "outcome": "aborted",
                "final_answer": "стоп", "lesson": "гигиена"}]), gov, audit)
            res = agent.solve("тестовая задача план-гигиены")
            plans = [r for r in _ledger_of(cfg) if r.get("action") == "(план)"]
            acts = [r for r in _ledger_of(cfg) if r.get("action") == "write_file"]
            assert len(plans) == 2, f"планов в журнале {len(plans)} (ожидалось ровно 2)"
            assert len(acts) == 1, "repair не вывел модель в act после отказа плана"
            assert res["outcome"] == "aborted", f"не aborted: {res}"
            return "повторный план отклонён на валидации; repair вывел в act"

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
    check("T12 реальный арсенал 2444", t_arsenal_real)
    check("T13 грамматика и OllamaNativeBrain", t_grammar)
    check("T14 гейт процедурной памяти", t_proc_gate)
    check("T15 запрет пустой записи и честность свидетеля", t_empty_write_ban)
    check("T16 переменная $last_output", t_last_output)
    check("T17 непробиваемый план-замок", t_plan_lock)
    check("T18 вечная лента фактов", t_persistent_facts)
    check("T19 план-гигиена: отказ повторного плана", t_plan_hygiene)

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
        workspace=args.workspace, data_dir=args.data_dir)
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
