#!/usr/bin/env python3
"""Два живых числа (ПРЕДЛОЖЕНИЕ-17, волна ×3 W3-D). Только stdlib, Python 3.11.

  dora    — DORA-дайджест роя: 16 чисел (4 метрики × 4 флагмана) из GitHub API:
            lead time (коммит -> успешный прогон), частота развёртываний (прокси:
            успешные прогоны CI в неделю на дефолтной ветке), MTTR (красный -> зелёный),
            доля красных прогонов. Окно: последние 100 прогонов дефолтной ветки.
            Числа пишутся в wave3/DORA-дайджест.md с построчными источниками.
  freedom — свобода-счёт: вывод check_freedom.py сверяется с колонкой freedom описи;
            расхождение краснит гейт. Отчёт: wave3/freedom-report.md.

Флагманы — сид по цепи ADR (cell-swarm -> runtime-protocol -> polymath-os) + agryp;
переопределяется живым ходом файлом wave3/flagships.json ({"flagships": [...]}).
Токен: env GITHUB_TOKEN (необязателен для публичных данных).
"""
import json
import os
import re
import statistics
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.github.com"
FLAGSHIPS_SEED = ["cell-swarm", "runtime-protocol", "polymath-os", "agryp"]


def api(path):
    req = urllib.request.Request(API + path,
                                 headers={"User-Agent": "polymath-os-wave3",
                                          "Authorization": "Bearer %s" % os.environ.get("GITHUB_TOKEN", "")})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def flagships():
    over = ROOT / "wave3" / "flagships.json"
    if over.exists():
        return json.loads(over.read_text(encoding="utf-8")).get("flagships", FLAGSHIPS_SEED)
    return FLAGSHIPS_SEED


def hours(iso_a, iso_b):
    a = datetime.fromisoformat(iso_a.replace("Z", "+00:00"))
    b = datetime.fromisoformat(iso_b.replace("Z", "+00:00"))
    return (a - b).total_seconds() / 3600.0


def med(xs):
    return round(statistics.median(xs), 1) if xs else None


def repo_numbers(name):
    meta = api("/repos/rtynbirf/%s" % name)
    db = meta.get("default_branch", "main")
    runs = api("/repos/rtynbirf/%s/actions/runs?per_page=100&branch=%s" % (name, db)).get("workflow_runs", [])
    runs = [r for r in runs if r.get("head_branch") == db]
    total = len(runs)
    failed = [r for r in runs if r.get("conclusion") == "failure"]
    ok = [r for r in runs if r.get("conclusion") == "success"]
    red_share = round(100.0 * len(failed) / total, 1) if total else None
    ordered = sorted(runs, key=lambda r: r.get("run_started_at") or "")
    gaps = []
    last_fail = None
    for r in ordered:
        if r.get("conclusion") == "failure":
            last_fail = r.get("run_started_at")
        elif r.get("conclusion") == "success" and last_fail:
            gaps.append(hours(r.get("run_started_at"), last_fail))
            last_fail = None
    commits = api("/repos/rtynbirf/%s/commits?sha=%s&per_page=30" % (name, db))
    first_ok = {}
    for r in ok:
        first_ok.setdefault(r.get("head_sha"), r.get("run_started_at"))
    leads = []
    for c in commits:
        sha = c.get("sha")
        when = (c.get("commit") or {}).get("committer", {}).get("date")
        if sha in first_ok and when:
            h = hours(first_ok[sha], when)
            if h >= 0:
                leads.append(h)
    freq = None
    if ordered:
        span_h = max(hours(ordered[-1].get("run_started_at"), ordered[0].get("run_started_at")), 1.0)
        freq = round(len(ok) / (span_h / 168.0), 1)  # успешных прогонов в неделю
    return {"lead": med(leads), "freq": freq, "mttr": med(gaps), "red": red_share,
            "прогонов": total}


def _pad_table(header, rows):
    """Markdown-таблица с выравниванием колонок по ширине (канон biome-формата)."""
    cols = len(header)
    grid = [header] + [[c for c in r] for r in rows]
    widths = [max(len(g[i]) for g in grid) for i in range(cols)]
    def line(cells, filler="-"):
        body = "| " + " | ".join(c.ljust(widths[i]) for i, c in enumerate(cells)) + " |"
        return body
    sep = "| " + " | ".join(widths[i] * "-" for i in range(cols)) + " |"
    return [line(header)] + [sep] + [line(r) for r in rows]


def dora():
    names = flagships()
    rows, nums = [], 0
    for name in names:
        try:
            n = repo_numbers(name)
        except Exception as e:
            rows.append([name, "нет данных", "нет данных", "нет данных", "нет данных", "(%s)" % type(e).__name__])
            continue
        nums += sum(1 for k in ("lead", "freq", "mttr", "red") if n[k] is not None)
        rows.append([
            name,
            "нет данных" if n["lead"] is None else "%s ч" % n["lead"],
            "нет данных" if n["freq"] is None else "%s/нед" % n["freq"],
            "нет данных" if n["mttr"] is None else "%s ч" % n["mttr"],
            "нет данных" if n["red"] is None else "%s%%" % n["red"],
            "%d прогонов в окне" % n["прогонов"]])
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    md = "\n".join([
        "# DORA-дайджест роя (волна ×3, ПРЕДЛОЖЕНИЕ-17)", "",
        "Дата: %s. Источник: GitHub API (действия репо, дефолтная ветка, окно 100 прогонов)." % now,
        "Флагманы — сид по цепи ADR; переопределяется wave3/flagships.json живым ходом.", "",
    ] + _pad_table(
        ["флагман", "lead time", "частота развёртываний (прокси)", "MTTR", "доля красных", "окно"],
        rows) + [
        "", "Метрики по канону DORA; «частота» — прокси (успешные прогоны CI в неделю),",
        "потому что деплой роя = зелёный конвейер. (заполняется скриптом wave3/two_numbers.py",
        "при каждом прогоне; источниковая база — api.github.com/repos/rtynbirf/<репо>/actions/runs)",
        "",
    ])
    out = ROOT / "wave3" / "DORA-дайджест.md"
    out.write_text(md, encoding="utf-8")
    print("дайджест: wave3/DORA-дайджест.md; живых чисел: %d из 16 (остальные — «нет данных»)" % nums)
    return 0


def freedom():
    lines = ["# Свобода-счёт (волна ×3, ПРЕДЛОЖЕНИЕ-17)", "",
             "Закон: колонка freedom (0-24) в описи == выводу check_freedom.py.", ""]
    script = next((p for p in ROOT.rglob("check_freedom.py") if ".git" not in p.parts), None)
    problems = []
    if script is None:
        lines.append("- check_freedom.py не найден в репо — свобода-счёт ждёт живого скрипта (каркас).")
        score = None
    else:
        p = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, timeout=120, cwd=str(ROOT))
        out = (p.stdout or "") + (p.stderr or "")
        m = re.search(r"(\d+)\s*/\s*24", out) or re.search(r"freedom[^0-9]{0,24}(\d+)", out, re.I)
        score = int(m.group(1)) if m and 0 <= int(m.group(1)) <= 24 else None
        lines.append("- check_freedom.py: %s (выход %d); счёт: %s" % (
            script.relative_to(ROOT), p.returncode, score if score is not None else "не распознан"))
        if score is None:
            problems.append("счёт свободы не распознан в выводе check_freedom.py")
    inv = [p for pat in ("*INVENTORY*", "*inventory*") for p in ROOT.rglob(pat)
           if ".git" not in p.parts and p.is_file() and p.stat().st_size < 2_000_000]
    cells = []
    for f in inv[:10]:
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            if "freedom" in line.lower():
                cells.append((f.name, line.strip()[:160]))
    if cells:
        lines.append("- опись: строки с колонкой freedom (%d шт.):" % len(cells))
        lines += ["  - %s: %s" % (n, s) for n, s in cells]
        vals = [int(x) for _, s in cells for x in re.findall(r"\b(\d{1,2})\b", s)
                if 0 <= int(x) <= 24]
        if score is not None and vals and score not in vals:
            problems.append("колонка freedom описи (%s) != выводу check_freedom.py (%d)" % (sorted(set(vals)), score))
    else:
        lines.append("- опись с колонкой freedom не найдена — сравнение отложено живым ходом.")
    out = ROOT / "wave3" / "freedom-report.md"
    out.write_text("\n".join(lines + ["", "(заполняется скриптом wave3/two_numbers.py при каждом прогоне)", ""]),
                   encoding="utf-8")
    if problems:
        out.write_text("\n".join(lines + ["", "ГАТ КРАСНЫЙ: " + "; ".join(problems), ""]), encoding="utf-8")
        print("свобода-счёт: КРАСНЫЙ —", "; ".join(problems))
        return 1
    print("свобода-счёт: отчёт wave3/freedom-report.md, расхождений нет")
    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    rc = 0
    if cmd in ("dora", "all"):
        rc |= dora()
    if cmd in ("freedom", "all"):
        rc |= freedom()
    return rc


if __name__ == "__main__":
    sys.exit(main())
