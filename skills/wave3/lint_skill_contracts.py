#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Скилл = договор (ПРЕДЛОЖЕНИЕ-16, polymath-os#33 · волна Э-2 · П-50): CI-гейт.

Канон SKILL.md — ключи верхнего уровня «ключ: значение»:
  invariant: <непустое обещание> · verify: <команда проверки; печатается в отчёт>
  evidence: <необязательный путь к досье; ищется от корня репо, потом от SKILL.md>
Досье «7 claims → 4 статуса»: ровно 7 строк «claim N: <текст>», в каждой ровно
один тег [FACT] | [CALCULATED] | [MODEL] | [UNKNOWN]; «сделано» без досье не существует.

Гейт (scan): все SKILL.md репо; ноль скиллов — зелёный no-op (плавный храповик,
--strict-empty делает пустоту красной); нарушение договора — код 1, FAIL файл:строка.
Шаблоны: --template skill|evidence · Самопроверка: --selftest. Только stdlib, Python 3.11.
"""
from __future__ import annotations

import argparse
import re
import tempfile
from pathlib import Path

STATUSES = ("FACT", "CALCULATED", "MODEL", "UNKNOWN")
RE_KEY = re.compile(r"^(invariant|verify|evidence)\s*:\s*(.*)$")
RE_CLAIM = re.compile(r"^claim\s+([0-9]+)\s*:\s*(.+)$")
N_CLAIMS, SKILL_NAME = 7, "SKILL.md"

TEMPLATE_SKILL = """# <имя скилла>

invariant: (заполняется при принятии скилла: одно предложение — что скилл гарантирует)
verify: (заполняется при принятии скилла: команда, которой любой агент проверяет инвариант)
evidence: evidence/0001-<имя-скилла>.md

## Что делает
(заполняется при принятии скилла)
"""

TEMPLATE_EVIDENCE = """# Досье · 7 claims → 4 статуса

Скилл: skills/<путь>/SKILL.md · Дата: (заполняется при применении досье)
Статусы: [FACT] — проверено фактом; [CALCULATED] — вычислено из данных;
[MODEL] — модельное ожидание; [UNKNOWN] — неизвестно (почему — в самой строке).

claim 1: (заполняется при применении досье) [FACT]
claim 2: (заполняется при применении досье) [CALCULATED]
claim 3: (заполняется при применении досье) [MODEL]
claim 4: (заполняется при применении досье) [UNKNOWN]
claim 5: (заполняется при применении досье) [FACT]
claim 6: (заполняется при применении досье) [CALCULATED]
claim 7: (заполняется при применении досье) [UNKNOWN]
"""


def rel(root: Path, p: Path) -> str:
    try:
        return p.relative_to(root).as_posix()
    except ValueError:
        return str(p)


def parse_contract(path: Path) -> tuple[dict, list[str]]:
    keys: dict[str, str] = {}
    errs: list[str] = []
    for i, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        m = RE_KEY.match(raw.strip())
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if key in keys:
            errs.append(f"{path}:{i}: ключ «{key}:» повторяется — договор неоднозначен")
        else:
            keys[key] = val
    return keys, errs


def check_evidence(root: Path, path: Path) -> tuple[list[str], dict]:
    errs, nums, by_status = [], [], {s: 0 for s in STATUSES}
    for i, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        m = RE_CLAIM.match(raw.strip())
        if not m:
            continue
        num, text = int(m.group(1)), m.group(2)
        nums.append(num)
        tags = [s for s in STATUSES if f"[{s}]" in text]
        if len(tags) != 1:
            errs.append(f"{rel(root, path)}:{i}: claim {num} — нужен ровно один "
                        f"статус-тег из {list(STATUSES)}")
        else:
            by_status[tags[0]] += 1
    if nums != list(range(1, N_CLAIMS + 1)):
        errs.append(f"{rel(root, path)}: досье обязано нести ровно {N_CLAIMS} претензий "
                    f"claim 1..{N_CLAIMS} по порядку (найдено {len(nums)})")
    return errs, {"claims": len(nums), "by_status": by_status}


def check_skill(root: Path, path: Path) -> tuple[list[str], dict]:
    keys, dup = parse_contract(path)
    errs: list[str] = list(dup)
    name = rel(root, path)
    for req in ("invariant", "verify"):
        if not keys.get(req):
            errs.append(f"{name}: нет непустого «{req}:» — скилл без договора не принимается")
    stats = {"claims": 0, "by_status": {s: 0 for s in STATUSES}}
    ev = keys.get("evidence", "")
    if ev:
        cand = root / ev
        if not cand.exists():
            cand = path.parent / ev
        if not cand.exists():
            errs.append(f"{name}: досье «{ev}» не найдено")
        else:
            ev_errs, stats = check_evidence(root, cand)
            errs += ev_errs
    return errs, {"rel": name, "keys": keys, "evidence": stats}


def scan(root: Path, strict_empty: bool = False) -> int:
    skills = sorted(p for p in root.rglob(SKILL_NAME) if ".git" not in p.parts)
    print(f"ГЕЙТ «скилл = договор» · скиллов: {len(skills)} · корень: {root.name}")
    if not skills:
        print("(скиллов пока нет — гейт зелёный как no-op; шаблон: --template skill; "
              "храповик строжеет с первым SKILL.md)")
        if strict_empty:
            print("FAIL пусто при --strict-empty")
            return 1
        return 0
    errors: list[str] = []
    for s in skills:
        errs, info = check_skill(root, s)
        b = info["evidence"]["by_status"]
        print(f"{info['rel']}")
        print(f"  invariant: {info['keys'].get('invariant', '—')}")
        print(f"  verify: {info['keys'].get('verify', '—')}")
        if info["evidence"]["claims"]:
            print(f"  evidence: claims {info['evidence']['claims']}: "
                  f"FACT {b['FACT']} · CALCULATED {b['CALCULATED']} · "
                  f"MODEL {b['MODEL']} · UNKNOWN {b['UNKNOWN']}")
        errors += errs
    for e in errors:
        print(f"FAIL {e}")
    print("ИТОГ: договор соблюдён" if not errors else f"ИТОГ: FAIL ({len(errors)} ошибок)")
    return 1 if errors else 0


def selftest() -> int:
    good = "invariant: печатает ровно одну строку отчёта\nverify: python3 run.py --check\n"
    with tempfile.TemporaryDirectory() as td:
        root, d = Path(td), Path(td) / "skills" / "demo"
        d.mkdir(parents=True)
        (d / "ev.md").write_text(
            "\n".join(f"claim {n}: пример претензии {n} [FACT]" for n in range(1, 8)) + "\n",
            encoding="utf-8")
        (d / SKILL_NAME).write_text(good + "evidence: ev.md\n", encoding="utf-8")
        errs, info = check_skill(root, d / SKILL_NAME)
        assert errs == [] and info["evidence"]["claims"] == 7, (errs, info)
        e1, s1 = check_evidence(root, d / "ev.md")
        assert e1 == [] and s1["claims"] == 7 and s1["by_status"]["FACT"] == 7, (e1, s1)
        (d / "ev6.md").write_text(
            "\n".join(f"claim {n}: пример {n} [FACT]" for n in range(1, 7)) + "\n",
            encoding="utf-8")
        e2, _ = check_evidence(root, d / "ev6.md")
        assert len(e2) == 1 and "claim 1..7" in e2[0], e2
        (d / "evtag.md").write_text("claim 1: двойной тег [FACT] [MODEL]\n", encoding="utf-8")
        assert any("статус-тег" in x for x in check_evidence(root, d / "evtag.md")[0])
        (d / SKILL_NAME).write_text("invariant: без verify нельзя\n", encoding="utf-8")
        errs_bad, _ = check_skill(root, d / SKILL_NAME)
        assert len(errs_bad) == 1 and "verify" in errs_bad[0], errs_bad
        (d / SKILL_NAME).write_text(good + "evidence: нет-такого.md\n", encoding="utf-8")
        errs_miss, _ = check_skill(root, d / SKILL_NAME)
        assert len(errs_miss) == 1 and "не найдено" in errs_miss[0], errs_miss
        assert scan(root) == 1  # скилл с битым досье роняет гейт
        (d / SKILL_NAME).write_text(good + "evidence: ev.md\n", encoding="utf-8")
        assert scan(root) == 0
        empty = root / "пусто"
        empty.mkdir()
        assert scan(empty) == 0 and scan(empty, strict_empty=True) == 1
    print("selftest: OK (инвариант+verify, досье 7 claims, теги, no-op пустоты, strict-empty)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Гейт «скилл = договор»: инвариант + verify + досье 7 claims (issue 33)")
    ap.add_argument("--root", default=".", help="корень репо для скана")
    ap.add_argument("--strict-empty", action="store_true",
                    help="ноль SKILL.md считать ошибкой (храповик по зрелости)")
    ap.add_argument("--template", choices=("skill", "evidence"),
                    help="печать шаблона SKILL.md или досье в stdout")
    ap.add_argument("--selftest", action="store_true", help="самопроверка на фикстурах")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if args.template:
        print(TEMPLATE_SKILL if args.template == "skill" else TEMPLATE_EVIDENCE, end="")
        return 0
    return scan(Path(args.root).resolve(), strict_empty=args.strict_empty)


if __name__ == "__main__":
    raise SystemExit(main())
