#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ЖИВОЙ ЩИТ — README самоверифицируется живьём (волна ×17, polymath-os).

Мир вешает статичные бейджи; polymath-os пересчитывает свой щит при каждом
прогоне workflow «ЖИВОЙ ЩИТ» из четырёх независимых источников:

  1. OpenSSF Scorecard — живой замер api.scorecard.dev;
  2. последний релиз — тег, дата, число артефактов, аттестационная цепь;
  3. SBOM — CycloneDX-артефакт СКАЧИВАЕТСЯ из релиза и парсится живьём
     (число компонентов), а не переписывается руками;
  4. OSPS Baseline — итоговая таблица самооценки из OSPS-BASELINE-MATRIX.md;
  5. TTL мандатов — минимальный срок жизни ключей из приватного реестра П-74
     (token-registry.json, github-runbook) через необязательный
     LIVING_SHIELD_TOKEN; без доступа — честное «реестр приватен».

Блок между маркерами LIVING-SHIELD:START/END в README.md заменяется целиком.
Только стандартная библиотека. Любой источник может упасть — щит ставит
«n/a» и остаётся честным; exit 1 — только если не собрался ни один источник.
"""

import base64
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone, date

README = "README.md"
START = "<!-- LIVING-SHIELD:START -->"
END = "<!-- LIVING-SHIELD:END -->"

UA = {"User-Agent": "polymath-os-living-shield"}


def http_get(url, token=None, timeout=30):
    """GET с таймаутом; возвращает (status, bytes). Токен не логируется."""
    req = urllib.request.Request(url, headers=UA)
    if token:
        req.add_header("Authorization", "Bearer %s" % token)
        req.add_header("Accept", "application/vnd.github+json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.getcode(), resp.read()
    except Exception as exc:  # noqa: BLE001 — щит честно ловит любой сбой источника
        print("  · источник недоступен (%s): %s" % (url.split("/")[-1][:60], exc))
        return 0, b""


def fetch_scorecard(repo):
    """Живой замер Scorecard из публичного API scorecard.dev."""
    slug = repo if repo.startswith("github.com/") else "github.com/%s" % repo
    code, body = http_get("https://api.scorecard.dev/projects/%s" % slug)
    if code != 200 or not body:
        return None
    try:
        data = json.loads(body)
        score = round(float(data["score"]), 1)
        return {
            "score": ("%g" % score),
            "viewer": "https://scorecard.dev/viewer/?uri=%s" % slug,
        }
    except (ValueError, KeyError):
        return None


def fetch_release(repo, token):
    """Последний релиз: тег, дата, артефакты, SBOM-компоненты живым парсингом."""
    code, body = http_get(
        "https://api.github.com/repos/%s/releases/latest" % repo, token=token
    )
    if code != 200 or not body:
        return None
    try:
        rel = json.loads(body)
        tag = rel.get("tag_name", "?")
        pub = (rel.get("published_at") or "?")[:10]
        assets = rel.get("assets", []) or []
        att = sum(
            1
            for a in assets
            if any(k in a.get("name", "") for k in ("attestation", "provenance", "sig"))
        )
        out = {
            "tag": tag,
            "date": pub,
            "assets": str(len(assets)),
            "att": str(att),
            "sbom": None,
            "spec": None,
        }
        for a in assets:
            if a.get("name") == "sbom.python.cyclonedx.json":
                c, raw = http_get(a.get("browser_download_url", ""), timeout=60)
                if c == 200 and raw:
                    try:
                        sbom = json.loads(raw)
                        out["sbom"] = str(len(sbom.get("components", [])))
                        out["spec"] = str(sbom.get("specVersion", "?"))
                    except ValueError:
                        pass
                break
        return out
    except (ValueError, KeyError):
        return None


def fetch_osps(root):
    """Итоговая таблица самооценки OSPS из репо-матрицы (парсинг «## Итог»)."""
    path = os.path.join(root, "OSPS-BASELINE-MATRIX.md")
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return None
    mver = re.search(r"версия \*\*([^*]+)\*\*", text)
    rows = {}
    for line in text.splitlines():
        m = re.match(
            r"^\|\s*L([123])\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|",
            line,
        )
        if m:
            rows[m.group(1)] = tuple(int(m.group(i)) for i in range(2, 7))
    if not rows:
        return None
    return {
        "ver": mver.group(1) if mver else "?",
        "rows": rows,
    }


def fetch_ttl(token):
    """Минимальный TTL живых мандатов из приватного реестра П-74.

    Токен реестра — необязательный секрет LIVING_SHIELD_TOKEN (read-only
    fine-grained по П-74). Без доступа щит честно пишет «реестр приватен».
    """
    if not token:
        return None
    code, body = http_get(
        "https://api.github.com/repos/rtynbirf/github-runbook/contents/token-registry.json",
        token=token,
    )
    if code != 200 or not body:
        return None
    try:
        content = json.loads(body).get("content", "")
        registry = json.loads(base64.b64decode(content))
        entries = registry.get("entries", registry if isinstance(registry, list) else [])
        dates = [
            date.fromisoformat(e["expires_at"])
            for e in entries
            if isinstance(e, dict) and e.get("expires_at")
        ]
        if not dates:
            return None
        soonest = min(dates)
        days = (soonest - date.today()).days
        mark = "🔴" if days <= 7 else ("🟡" if days <= 30 else "🟢")
        return {"days": days, "until": soonest.isoformat(), "mark": mark}
    except (ValueError, KeyError):
        return None


def render(repo, shield, rel, osps, ttl, workflow_url, run_url, ts):
    """Собирает блок щита; недоступные источники = честное n/a.

    Шапка — СТАТИЧНАЯ (ссылка на workflow, не на прогон), ссылка на
    конкретный прогон живёт в подвале-замере — иначе каждый прогон рождает
    холостую ревизию (косяк ×17 первого включения, починен в ту же волну).
    """
    lines = [START, "", "## 🛡 Living Shield — живой щит самоверификации", ""]
    lines.append(
        "Этот блок пересчитывается workflow [ЖИВОЙ ЩИТ](%s) — не статичный бейдж." % workflow_url
    )
    lines.append("")
    lines.append("| Источник | Живое значение |")
    lines.append("| --- | --- |")
    if shield:
        lines.append(
            "| OpenSSF Scorecard | **%s** / 10 — [живой замер](%s) |"
            % (shield["score"], shield["viewer"])
        )
    else:
        lines.append("| OpenSSF Scorecard | n/a (источник недоступен) |")
    if rel:
        lines.append(
            "| Последний релиз | **%s** (%s) · %s артефактов · цепь аттестаций ×%s (cosign + SLSA) |"
            % (rel["tag"], rel["date"], rel["assets"], rel["att"])
        )
        if rel.get("sbom"):
            lines.append(
                "| SBOM CycloneDX %s | **%s компонентов** — артефакт релиза скачан и распарсен живьём |"
                % (rel.get("spec", "?"), rel["sbom"])
            )
        else:
            lines.append("| SBOM CycloneDX | n/a (артефакт недоступен) |")
    else:
        lines.append("| Последний релиз | n/a (источник недоступен) |")
    if osps:
        r1, r2, r3 = osps["rows"].get("1"), osps["rows"].get("2"), osps["rows"].get("3")

        def cell(r):
            return "%s✅/%s⚠️/%s❌" % (r[0], r[1], r[2]) if r else "n/a"

        lines.append(
            "| OSPS Baseline %s (self-assessed) | L1 %s · L2 %s · L3 %s — [матрица](./OSPS-BASELINE-MATRIX.md) |"
            % (osps["ver"], cell(r1), cell(r2), cell(r3))
        )
    else:
        lines.append("| OSPS Baseline | n/a (матрица не найдена) |")
    if ttl:
        lines.append(
            "| TTL мандатов (П-74) | %s %s дн. до %s — реестр П-74 (приватный) |"
            % (ttl["mark"], ttl["days"], ttl["until"])
        )
    else:
        lines.append("| TTL мандатов (П-74) | реестр приватен · n/a |")
    lines.append("")
    lines.append(
        "_Замер: %s · [прогон](%s) · ручная правка между маркерами перезаписывается._"
        % (ts, run_url)
    )
    lines.append(END)
    return "\n".join(lines)


def block_core(block_text):
    """Блок без метки замера, маркеров и пустых строк — сравнение по существу.

    Ритм без шума (канон пульса): если показания не изменились, метка времени
    не обновляется и коммита нет — щит не течёт холостыми ревизиями.
    """
    lines = [
        ln
        for ln in block_text.splitlines()
        if not ln.startswith("_Замер:") and ln not in (START, END, "")
    ]
    return "\n".join(lines)


def main():
    repo = os.environ.get("GITHUB_REPOSITORY", "rtynbirf/polymath-os")
    gh_token = os.environ.get("GITHUB_TOKEN") or None
    shield_token = os.environ.get("LIVING_SHIELD_TOKEN") or None
    # Корень репо: POLYMATH_ROOT (локальные прогоны) или родитель scripts/ (в CI)
    root = os.environ.get("POLYMATH_ROOT") or os.path.abspath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    )

    workflow_url = "%s/%s/actions/workflows/living-shield.yml" % (
        os.environ.get("GITHUB_SERVER_URL", "https://github.com"),
        repo,
    )
    run_url = workflow_url
    if os.environ.get("GITHUB_RUN_ID"):
        run_url = "%s/%s/actions/runs/%s" % (
            os.environ.get("GITHUB_SERVER_URL", "https://github.com"),
            repo,
            os.environ["GITHUB_RUN_ID"],
        )
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    print("ЖИВОЙ ЩИТ: пересчёт из независимых источников (%s)" % repo)
    shield = fetch_scorecard(repo)
    print("  · Scorecard: %s" % (shield["score"] if shield else "n/a"))
    rel = fetch_release(repo, gh_token)
    print(
        "  · Релиз: %s (%s артефактов, SBOM %s)"
        % (rel["tag"] if rel else "n/a", rel["assets"] if rel else "-", rel.get("sbom") if rel else "-")
    )
    osps = fetch_osps(root)
    print("  · OSPS: %s" % (osps["ver"] if osps else "n/a"))
    ttl = fetch_ttl(shield_token)
    print("  · TTL мандатов: %s" % ("%s дн." % ttl["days"] if ttl else "реестр приватен"))

    if not any([shield, rel, osps]):
        print("!! Ни один источник не ответил — щит не выдаёт ложь, падает честно")
        return 1

    block = render(repo, shield, rel, osps, ttl, workflow_url, run_url, ts)

    readme_path = os.path.join(root, "README.md")
    with open(readme_path, encoding="utf-8") as fh:
        text = fh.read()

    action = "вставлен"
    if START in text and END in text:
        old_block = text[text.index(START): text.index(END) + len(END)]
        if block_core(old_block) == block_core(block):
            print("Показания щита без изменений — метка замера не течёт, README не тронут")
            return 0
        pre = text[: text.index(START)]
        post = text[text.index(END) + len(END):]
        new_text = pre + block + post
        action = "заменён"
    else:
        anchor = re.search(r"^(\*\*Current version:.*\S.*)$", text, re.M)
        if not anchor:
            print("!! Якорь «Current version» в README не найден — вставка отменена")
            return 2
        cut = anchor.end()
        new_text = text[:cut] + "\n\n" + block + text[cut:]
        action = "вставлен"

    if new_text == text:
        print("Щит без изменений — README не тронут")
        return 0

    with open(readme_path, "w", encoding="utf-8") as fh:
        fh.write(new_text)
    print("Живой щит %s в README.md (замер %s)" % (action, ts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
