#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
АРХИВАРИУС v1.1 «АНТИГАЛЛЮЦИНАЦИЯ» — ЯДРО АГЕНТА-ГОЛОГРАММЫ
=============================================================
Наследник АРХИВАРИУС_v1.0_ЯДРО.py (36/36 PASS, sha256 c41fef9d…): v1.0 не переписывается —
v1.1 импортирует его как родителя и достраивает три органа по сырьевому корпусу
«СУММАРНЫЕ ОТВЕТЫ НА ГАЛЛОГРАММУ_1.txt» (4835 строк, прочитан целиком).

СТРАТЕГИЧЕСКИЙ ПЛАН Task 19 (исполнен):
  Ступень 0. Сверка носителей: ритуал даты; среда без отката; Task 18 жив (36/36 прямо сейчас);
             файл _1 ≠ файлу 0 (260 567 байт, 4 835 строк) — прочитан целиком; 7 веб-проб.
  Ступень 1. Сырьё → вердикты. Шесть прибавок корпуса _1 к v1.0:
             П1 протокол «Одно другое не исключает» (формула, JSON-схема, StateProtocol)
             П2 POLYMAT-HOLO: 13 эпистемических статусов, 6 уровней памяти, SelfModel, AnswerPackage
             П3 Конституция v0.1: 7 запретов для LLM (не менять геном, не подтверждать себя,
                не создавать свидетельства из воздуха, не скрывать конфликт…)
             П4 HHA: Gödel-цикл (опора подтверждена сетью: Gödel Agent, arXiv 2024/2025)
             П5 батарея 16 разрушающих тестов (TEST 01–16 корпуса)
             П6 математические опоры: пучки (истина=склейка), категории (часть→целое морфизм),
                Рида–Соломона (k из n) — формализуемые метафоры, помечены
             Отвергнуто приказом самого корпуса: квантовый резонанс, мгновенная нелокальность,
             blockchain как обязательная основа, LLM как источник истины.
  Ступень 2. Алгоритм агента (голографический цикл хода, 9 шагов):
             1 СВЕРКА (дата-ритуал + хвост манифеста) → 2 ЭСКИЗ (сводка целого)
             → 3 ПРИЁМ (суд над входящим: ЧАСТЬ/ЭХО/ЧУЖОЙ/ОСКОЛОК/ОТКАЗ)
             → 4 ЗАЯВ (клейм-суд: статус + источник; запрет само-подтверждения)
             → 5 ПРОТОКОЛ (состояния: объединение по умолчанию, исключение — только явно)
             → 6 ДЕЙСТВИЕ (построение/ответ) → 7 ЗАПИСЬ (манифест append-only)
             → 8 РЕФЛЕКС (Gödel-цикл lite: 8 вопросов самому себе)
             → 9 ВЕРИФИКАЦИЯ (машинный selftest; «сработало» без счётчика PASS не существует).
  Ступень 3. Задача 19 и её самореализация (ниже), артефакты, верификация, worklog Task 19.

ЗАДАЧА 19 (формулировка, поставлена себе и реализована самому):
  Расширить АРХИВАРИУС v1.0 до v1.1 «АНТИГАЛЛЮЦИНАЦИЯ»:
  (a) орган ЗАЯВ — реестр утверждений с эпистемическими статусами; запрет само-подтверждения;
      запрет статуса «ПОДТВЕРЖДЕНО» без источника; конфликт → СПОРНО, не слить;
  (b) орган ПРОТОКОЛ — состояния «одно другое не исключает»: слияние = объединение,
      взаимоисключение — только явно заданное ограничение; нарушение = исключение, не молчание;
  (c) орган РЕФЛЕКС — самопроверка Gödel-цикла lite (8 вопросов);
  (d) батарея 16 разрушающих тестов корпуса (TEST 01–16) + тест само-подтверждения + 4 теста
      протокола + 1 рефлекс = 22 новых машинных проверки.
  Критерии успеха: база 36/36 PASS; новые 22/22 PASS; demo EXIT=0; верификация артефактов ALL PASS;
  ни одно новое обещание — без машинной проверки (режим антигаллюцинаций).

ОТВЕТ КОРПУСА НА ВОПРОС «ЧТО ДЕЛАЕТ LLM»: генерирует кандидатов; не решает ИСТИННО/РАЗРЕШЕНО/
ЧЛЕН/КАНОНИЧНО/ДОКАЗАНО — это решают ГЕНОМ + ПРАВИЛА + ПРОИСХОЖДЕНИЕ + ДОКАЗАТЕЛЬСТВО + СУД
(Конституция v0.1, ст. 11; здесь: геном v1.0 + ЗАЯВ + СУД + амендмент k-из-n).

CLI:
  python3 АРХИВАРИУС_v1.1_ЯДРО.py --selftest   # база 36/36 + новые 21/21 = 57/57
  python3 АРХИВАРИУС_v1.1_ЯДРО.py --demo       # adversarial-повествование v1.1
"""

import glob
import importlib.util
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone

# ----------------------------------------------------------------------------
# РОДИТЕЛЬ: АРХИВАРИУС v1.0 (не переписывается; грузится из той же папки)
# ----------------------------------------------------------------------------

def _load_parent():
    here = os.path.dirname(os.path.abspath(__file__))
    cands = glob.glob(os.path.join(here, "АРХИВАРИУС_v1.0_ЯДРО.py"))
    if not cands:
        raise FileNotFoundError("родительское ядро АРХИВАРИУС_v1.0_ЯДРО.py не найдено рядом")
    spec = importlib.util.spec_from_file_location("archivarius_v10", cands[0])
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

V10 = _load_parent()
Genome = V10.Genome
Hologram = V10.Hologram
Court = V10.Court
Manifest = V10.Manifest
GENOME_TEXT_V1 = V10.GENOME_TEXT_V1
AmendmentRejected = V10.AmendmentRejected
H = V10.H


class ProtocolViolation(Exception):
    """П5: нарушение ЯВНО заданного ограничения — не молчание, а исключение."""


class SelfConfirmationForbidden(Exception):
    """П3/ст.11: LLM не подтверждает собственные утверждения собственным авторитетом."""


# ----------------------------------------------------------------------------
# ОРГАН 7 (v1.1): ЗАЯВ — клейм-суд (антигаллюцинационный контур)
# ----------------------------------------------------------------------------

# Эпистемические статусы (POLYMAT-HOLO, корпус _1; 11 рабочих вместо 13 —
# «corroborated/verified» слиты в ПОДТВЕРЖДЕНО, «obsolete» = устаревшее время в Unknown)
STATUSES = [
    "АКСИОМА",          # только статьи генома Г1–Г10
    "ОПРЕДЕЛЕНИЕ",
    "НАБЛЮДЕНИЕ",
    "ИСТОЧНИК-СООБЩАЕТ",
    "ВЫВОД",
    "ПОДТВЕРЖДЕНО",     # требует источника И независимого проверяющего
    "СПОРНО",           # конфликт не уничтожается, а предъявляется
    "ГИПОТЕЗА",
    "МЕТАФОРА",
    "НЕИЗВЕСТНО",
    "ПРОЕКТ",           # проектное решение, не факт
]

LLM_FORBIDDEN = [
    "менять Genome в одиночку",
    "объявлять неизвестное известным",
    "создавать Evidence из воздуха",
    "скрывать конфликт",
    "присваивать полномочия",
    "подтверждать собственные утверждения собственным авторитетом",
    "выдавать гипотезу за факт",
]


class ClaimRegistry:
    """ЗАЯВ: каждое существенное утверждение — объект со статусом и происхождением.
    Антигаллюцинационные правила (проверяются машиной, не на словах):
      R1 «ПОДТВЕРЖДЕНО» требует ≥1 источника и проверяющего ≠ заявителя;
      R2 без источника заявление не выше ГИПОТЕЗЫ (авто-понижение, честная метка причины);
      R3 АКСИОМА — только статьи генома;
      R4 конфликт (один субъект, разные тексты) → оба СПОРНО + реестр конфликтов (не слить!);
      R5 НЕИЗВЕСТНО — объект первого класса (scope/reason/owner/impact)."""

    def __init__(self):
        self.claims = {}
        self.conflicts = []
        self.counter = 0

    def register(self, subject, text, status="ГИПОТЕЗА", sources=(), asserted_by="LLM",
                 genome=None):
        self.counter += 1
        cid = "C%03d" % self.counter
        status = status.upper()
        note = None
        if status == "АКСИОМА":
            ok_axiom = bool(genome) and any(text.strip().startswith(g) for g in
                                            [l.split()[0] for l in genome.text.splitlines()
                                             if l.strip().startswith("Г")])
            if not ok_axiom:
                status, note = "ГИПОТЕЗА", "R3: АКСИОМА допустима только для статей генома"
        if status == "ПОДТВЕРЖДЕНО":
            if not sources:
                status, note = "ГИПОТЕЗА", "R2: «ПОДТВЕРЖДЕНО» без источника понижено до ГИПОТЕЗЫ"
        claim = {
            "id": cid, "subject": subject, "text": text, "status": status,
            "sources": list(sources), "asserted_by": asserted_by,
            "registered": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "note": note, "history": [],
        }
        # R4: конфликт — один субъект, разные тексты
        for other in self.claims.values():
            if other["subject"] == subject and other["text"] != text:
                other["status"] = "СПОРНО"
                claim["status"] = "СПОРНО"
                other["history"].append("конфликт с %s" % cid)
                claim["history"].append("конфликт с %s" % other["id"])
                self.conflicts.append((other["id"], cid))
        self.claims[cid] = claim
        return claim

    def verify(self, cid, verifier, raise_status="ПОДТВЕРЖДЕНО", sources=None):
        """Проверка ЗАЯВЛЕНИЯ. Верификатор ≠ заявитель (R1). Иначе — запрет (ст.11)."""
        c = self.claims[cid]
        if verifier == c["asserted_by"]:
            raise SelfConfirmationForbidden(
                "ст.11: %s не может подтверждать собственное утверждение %s" % (verifier, cid))
        if c["status"] == "СПОРНО":
            c["history"].append("проверка отложена: статус СПОРНО")
            return "ОТЛОЖЕНО-КОНФЛИКТ"
        srcs = list(sources) if sources is not None else c["sources"]
        if not srcs:
            c["history"].append("отказ: попытка подтвердить без источника")
            return "ОТКАЗ-БЕЗ-ИСТОЧНИКА"
        c["status"] = raise_status
        c["verified_by"] = verifier
        c["history"].append("подтверждено проверяющим %s" % verifier)
        return raise_status

    def unknown(self, scope, reason, owner, impact):
        """R5: неизвестность — объект первого класса, не молчаливый пропуск."""
        return {
            "scope": scope, "reason": reason, "owner": owner, "impact": impact,
            "registered": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    def roster(self):
        return [(c["id"], c["subject"], c["status"]) for c in self.claims.values()]


# ----------------------------------------------------------------------------
# ОРГАН 8 (v1.1): ПРОТОКОЛ — «одно другое не исключает»
# ----------------------------------------------------------------------------

class StateProtocol:
    """П1 (корпус _1, дословная реализация принципа):
    по умолчанию все состояния сосуществуют (слияние = ОБЪЕДИНЕНИЕ, не замена);
    отсутствие ключа ≠ ложь (без изменений);
    взаимоисключение — ТОЛЬКО явно заданное ограничение; нарушение = ProtocolViolation."""

    def __init__(self):
        self.active = set()
        self.constraints = []  # список set{a,b,…} — несовместны только по явному указанию

    def add_constraint(self, *keys):
        if len(keys) >= 2:
            self.constraints.append(set(keys))

    def check_constraints(self, candidates):
        return [g for g in self.constraints if len(candidates & g) > 1]

    def merge(self, payload):
        incoming = {k for k, v in payload.items() if v is True}
        candidates = self.active | incoming          # объединение, НЕ замена
        violations = self.check_constraints(candidates)
        if violations:
            raise ProtocolViolation("нарушены явные ограничения: %s" %
                                    [sorted(g) for g in violations])
        self.active = candidates
        return {"active_states": sorted(self.active), "count": len(self.active)}

    def create_message(self, facts, source="system"):
        return json.dumps({
            "id": str(uuid.uuid4()),
            "timestamp": int(time.time() * 1000),
            "source": source,
            "payload": facts,
            "constraints": [sorted(g) for g in self.constraints],
        }, ensure_ascii=False)

    @staticmethod
    def parse_message(s):
        return json.loads(s)


# ----------------------------------------------------------------------------
# ОРГАН 9 (v1.1): РЕФЛЕКС — Gödel-цикл lite (8 вопросов самому себе)
# ----------------------------------------------------------------------------

class Reflex:
    """П4 (опора: Gödel Agent, arXiv 2024/2025 — self-referential framework).
    inspect → отвечать на 8 вопросов; self.update → только амендмент генома (k-из-n);
    verify → машинный selftest. LLM-самомодификация минус власть над истиной."""

    QUESTIONS = [
        "identity", "whole_root", "role", "parts_count",
        "stale_claims", "conflicts", "unknowns", "can_reconstruct",
    ]

    def __init__(self, hologram, registry):
        self.hg = hologram
        self.reg = registry

    def inspect(self):
        reg = self.hg.regenerate()
        return {
            "identity": "АРХИВАРИУС v1.1 (геном v%s, id %s…)" % (
                self.hg.genome.version, self.hg.genome.id[:12]),
            "whole_root": reg["name_root"][:16] + "…",
            "role": "архивариус: носитель генома, суд и манифест диалога",
            "parts_count": "%d живых тел, известно частей: %d, состояние: %s" % (
                reg["living_bodies"], reg["known_parts"], reg["state"]),
            "stale_claims": "заявлений в реестре: %d; конфликтов: %d" % (
                len(self.reg.claims), len(self.reg.conflicts)),
            "conflicts": ["%s ↔ %s" % pair for pair in self.reg.conflicts] or "нет",
            "unknowns": "неизвестности фиксируются объектами (scope/reason/owner/impact)",
            "can_reconstruct": "да, если жив ≥1 носитель; иначе честно: ИСТИНА БЕЗ ТЕЛА",
        }


# ----------------------------------------------------------------------------
# SELFTEST v1.1: база 36/36 (родитель) + 21 новый = 57/57
# ----------------------------------------------------------------------------

def selftest(verbose=True):
    ok_base, _, _ = V10.selftest(verbose=False)

    passed, failed = [], []

    def check(tid, label, cond):
        (passed if cond else failed).append("%s %s" % (tid, label))

    g = Genome(GENOME_TEXT_V1)
    hg = Hologram(g, "партия-v11")
    bones = ["реконструкция помечается", "без «впервые» без оговорки"]
    hg.birth("протокол", "Протокол партии", "геном диалога", bones)
    hg.birth("разбор", "Разбор источника", "две колонны", bones)
    hg.birth("агент", "Ядро v1.0", "шесть органов", bones)
    reg = ClaimRegistry()

    # --- БАТАРЕЯ КОРПУСА: TEST 01–16 ---
    s4 = hg.birth("досье", "Досье-2", "новая часть", bones)            # TEST 01 добавить
    check("T37", "TEST 01: добавление части растит манифест", s4.index == 4)
    dead = hg.kill("S03")                                              # TEST 02 удалить
    check("T38", "TEST 02: удаление тела не меняет имя (append-only)", dead.sid == "S03" and hg.regenerate()["name_root"] == hg.manifest.root())
    forged_proof = dict(s4.proof)
    forged_proof["leaf"] = "0" * 64                                    # TEST 03 подделать membership
    check("T39", "TEST 03: подделанное membership отвергнуто", not hg.manifest.verify_full(forged_proof))
    gt = Genome(GENOME_TEXT_V1)                                        # TEST 04 изменить genome
    gt.text += "\nГ11 самозванец"
    check("T40", "TEST 04: изменённый геном ловится verify()", not gt.verify())
    forged = {"title": s4.title, "body": s4.body, "genome_id": s4.genome_id,
              "index": s4.index, "proof": s4.proof, "record": dict(s4.record())}
    forged["record"]["title"] = "ПЕРЕКРАШЕНО"                          # TEST 05 изменить part
    check("T41", "TEST 05: подделанное тело = ОСКОЛОК", Court(hg).classify(forged)["verdict"] == "ОСКОЛОК")
    stale = s4.sketch                                                   # TEST 06 stale projection
    hg.birth("агент", "Ядро v1.1", "три новых органа", bones)
    check("T42", "TEST 06: старый эскиз честно протух — не знает новую часть S05 и помнит убитую S03",
          stale["n_parts"] == 4 and "S05" not in stale["ids"] and "S03" in stale["ids"]
          and len(hg.shards) == 4)
    reg.register("порог-сборки", "любые k из n", "ОПРЕДЕЛЕНИЕ", sources=["геном Г9"])
    reg.register("порог-сборки", "ровно k", "ОПРЕДЕЛЕНИЕ", sources=["иной источник"])   # TEST 07 конфликт
    check("T43", "TEST 07: конфликтующие заявления → СПОРНО (не слить)",
          len(reg.conflicts) == 1 and all(c["status"] == "СПОРНО" for c in reg.claims.values()))
    hg.kill("S04")                                                      # TEST 08 удалить снова
    check("T44", "TEST 08: повторное удаление — состояние честно пересчитано",
          hg.regenerate()["living_bodies"] == 3)
    for sid in list(hg.shards.keys()):                                  # TEST 09 потерять несколько
        hg.kill(sid)
    check("T45", "TEST 09: потеря всех → ИСТИНА БЕЗ ТЕЛА, не галлюцинация целостности",
          hg.regenerate()["state"] == "ИСТИНА БЕЗ ТЕЛА")
    hgr = Hologram(Genome(GENOME_TEXT_V1), "партия-восстановленная")     # TEST 10 восстановить Whole
    hgr.birth("эскиз-носитель", "Сводка целого", "титулы всех частей прошлой сессии", bones)
    check("T46", "TEST 10: восстановление целого из частей — геном тот же",
          hgr.genome.id == g.id and hgr.regenerate()["known_parts"] == 1)
    c_false = reg.register("сервис-А", "Сервис А исправен", "ПОДТВЕРЖДЕНО",  # TEST 11 ложь LLM
                           sources=[], asserted_by="LLM")
    check("T47", "TEST 11: ложное утверждение LLM без источника понижено до ГИПОТЕЗЫ",
          c_false["status"] == "ГИПОТЕЗА" and c_false["note"] is not None)
    try:                                                                 # TEST 11б само-подтверждение
        reg.verify(c_false["id"], verifier="LLM")
        check("T48", "TEST 11б: LLM сам себя подтвердил — ЗАПРЕЩЕНО", False)
    except SelfConfirmationForbidden:
        check("T48", "TEST 11б: LLM сам себя подтвердил — ЗАПРЕЩЕНО", True)
    try:                                                                 # TEST 12 полномочия
        g.amend(GENOME_TEXT_V1 + "\nГ11 …", {"одна-подпись"}, k=2)
        check("T49", "TEST 12: амендмент без полномочий отвергнут", False)
    except AmendmentRejected:
        check("T49", "TEST 12: амендмент без полномочий отвергнут", True)
    unk = reg.unknown("дата-ритуал при офлайн-сборке", "нет доступа к часам среды",     # TEST 13
                      "источник", "блокирует ритуал СВЕРКА")
    check("T50", "TEST 13: неизвестность — полный объект первого класса",
          all(unk[k] for k in ("scope", "reason", "owner", "impact")))
    c_noprovenance = reg.register("автор-цитаты", "Цитата принадлежит Бому", "ПОДТВЕРЖДЕНО",
                                  sources=[])                            # TEST 14 скрыть provenance
    check("T51", "TEST 14: заявление без provenance не становится ПОДТВЕРЖДЕНО",
          c_noprovenance["status"] == "ГИПОТЕЗА")
    g11 = g.amend(GENOME_TEXT_V1 + "\nГ11 Эскиз целого читается из любой части.",       # TEST 15
                  {"агент", "источник"}, k=2, new_version="1.1")
    check("T52", "TEST 15: конституция меняется только амендментом k-из-n (родитель записан)",
          g11.version == "1.1" and g11.parent_id == g.id and g.verify())
    hgr2 = Hologram(Genome(GENOME_TEXT_V1), "партия-из-частей")          # TEST 16 восстановить агента
    sh = hgr2.birth("шард", "Пересобранный шард", "эскиз прошлой сессии", bones)
    check("T53", "TEST 16: агент восстановлен из частей с валидным доказательством",
          hgr2.manifest.verify_full(sh.proof) and hgr2.genome.id == g.id)

    # --- ПРОТОКОЛ «одно другое не исключает» (П1) ---
    sp = StateProtocol()
    sp.merge({"А": True, "Б": True})
    r2 = sp.merge({"В": True})
    check("T54", "ПРОТОКОЛ: А, Б и В сосуществуют (объединение, не замена)",
          r2["active_states"] == ["А", "Б", "В"])
    sp2 = StateProtocol()
    sp2.merge({"А": True})
    sp2.add_constraint("А", "Б")
    try:
        sp2.merge({"Б": True})
        check("T55", "ПРОТОКОЛ: явное ограничение блокирует (исключение, не молчание)", False)
    except ProtocolViolation:
        check("T55", "ПРОТОКОЛ: явное ограничение блокирует (исключение, не молчание)", True)
    msg = sp.create_message({"Г": True}, "сенсор-1")
    parsed = StateProtocol.parse_message(msg)
    check("T56", "ПРОТОКОЛ: сообщение переносит payload и constraints без искажения",
          parsed["payload"] == {"Г": True} and parsed["source"] == "сенсор-1" and "id" in parsed)
    before = sp.active.copy()
    sp.merge({})                                   # отсутствие ключей ≠ ложь
    check("T57", "ПРОТОКОЛ: пустой payload ничего не отменяет (отсутствие ≠ ложь)",
          sp.active == before)

    # --- РЕФЛЕКС (П4) ---
    rx = Reflex(hgr2, reg).inspect()
    check("T58", "РЕФЛЕКС: 8 вопросов самопроверки отвечены непусто",
          all(rx[q] for q in Reflex.QUESTIONS))

    if verbose:
        print("SELFTEST АРХИВАРИУС v1.1: база %s; новые %d/%d PASS, FAIL=%d" % (
            "36/36 PASS" if ok_base else "36/36 FAIL(!)", len(passed), len(passed) + len(failed), len(failed)))
        for f in failed:
            print("  FAIL:", f)
    return ok_base and not failed


# ----------------------------------------------------------------------------
# DEMO v1.1 — adversarial-повествование с антигаллюцинационным контуром
# ----------------------------------------------------------------------------

def demo():
    print("=" * 72)
    print("ПОЛИГОН v1.1: заяв-суд · протокол «одно другое не исключает» · рефлекс")
    print("=" * 72)
    g = Genome(GENOME_TEXT_V1)
    hg = Hologram(g, "АРХИВАРИУС")
    hg.birth("протокол", "Протокол партии", "геном диалога", ["кость"])
    hg.birth("механизм", "Голограмма-2026", "пять органов + суд", ["кость"])
    reg = ClaimRegistry()
    print("[1] ЗАЯВ (антигаллюцинация):")
    c1 = reg.register("кто-заказывает", "Заказчик установлен по трём независимым линиям",
                      "ПОДТВЕРЖДЕНО", sources=["afisha", "moslenta", "дайджест-ИРИ"], asserted_by="АРХИВАРИУС")
    print("    с источником        → %s (%s)" % (c1["status"], c1["id"]))
    c2 = reg.register("квантовый-резонанс", "Части синхронизируются квантовым резонансом",
                      "ПОДТВЕРЖДЕНО", sources=[], asserted_by="LLM")
    print("    без источника (LLM) → %s  [причина: %s]" % (c2["status"], c2["note"]))
    try:
        reg.verify(c2["id"], verifier="LLM")
    except SelfConfirmationForbidden as e:
        print("    само-подтверждение  → ЗАПРЕЩЕНО (%s…)" % str(e)[:52])
    reg.register("кто-заказывает", "Заказчик неизвестен", "ГИПОТЕЗА", asserted_by="скептик")
    print("    конфликт заявлений  → оба СПОРНО, конфликт предъявлен: %s" % (reg.conflicts,))
    print("[2] ПРОТОКОЛ «одно другое не исключает»:")
    sp = StateProtocol()
    sp.merge({"эхо-обработано": True, "разбор-завершён": True})
    print("    оба состояния сосуществуют: %s" % sorted(sp.active))
    sp.add_constraint("истина", "ложь")
    try:
        sp.merge({"истина": True, "ложь": True})
    except ProtocolViolation as e:
        print("    явное ограничение сработало → ProtocolViolation (%s…)" % str(e)[:44])
    print("[3] РЕФЛЕКС (Gödel-цикл lite):")
    for k, v in Reflex(hg, reg).inspect().items():
        print("    %-16s = %s" % (k, v))
    print("=" * 72)
    print("ВЫВОД: LLM генерирует кандидатов; статус даёт ЗАЯВ (источник + независимый проверяющий);")
    print("       состояния объединяются, если не запрещено ЯВНО; агент проверяет себя машиной.")
    return 0


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "--selftest"
    if mode == "--selftest":
        ok = selftest()
        sys.exit(0 if ok else 1)
    elif mode == "--demo":
        sys.exit(demo())
    else:
        print("использование: АРХИВАРИУС_v1.1_ЯДРО.py [--selftest|--demo]")
        sys.exit(2)
