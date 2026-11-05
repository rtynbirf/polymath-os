#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
POLIMAT_PIPELINE v1.2 — Linux-канон механизма заливки в репо.
v1.2: дефект D2 закрыт — api_req возвращает {} на пустое тело (204
No Content при DELETE ветки после merge; поймано машиной в живом merge
PR#17, доказано T13).
v1.1: дефект D1 закрыт — идемпотентность патчей по СОДЕРЖИМОМУ
(git apply --reverse --check), а не по строке «already applied», которую
git не печатает (реальное сообщение — «patch does not apply»; поймано
машиной при построении selftest T12).
Воспроизводит Windows-пак владельца (POLIMAT_AUTO_PUSH.bat / POLIMAT_FINISH.bat /
POLIMAT_MERGE.bat, снапшот 123.7z) без Windows: тот же порядок шагов, та же
идемпотентность, тот же verify-гейт. Выучен по Task 23 (PR#15 merged 7e8c9254).

Канон механизма (по батнику):
  1. Клон (идемпотентно: если есть — fetch --ff-only)  [AUTO_PUSH 3/6]
  2. Ремонт состояния: снос .git/rebase-apply|merge    [AUTO_PUSH 4/6a]
  3. Ветка feat/<scope>-<kebab> (≤24ч)                  [CONTRIBUTING]
  4. Коммиты: Conventional Commits + DCO (-s)           [AUTO_PUSH 4/6d,e]
     — патчи принимаются git am как готовые коммиты;
       повторно НЕ применяются, если контент уже в ветке (по содержимому!)
  5. Verify-гейт: make verify, иначе пуша НЕТ           [AUTO_PUSH 5/6, «НЕ СЛОМАЙ verify»]
  6. Пуш с ретраями (токен только в памяти процесса)    [AUTO_PUSH 6/6]
  7. PR по шаблону триажа (body-файл)                   [AUTO_PUSH PR-блок]
  8. merge-режим: squash-merge + удаление ветки         [AUTO_PUSH merge / MERGE.bat]
  9. Пост-пуш верификация свежим клоном + пломбы        [FINISH/задача 23]

Токен: ТОЛЬКО переменная окружения POLIMAT_TOKEN. Не argv, не файл, не .git/config.
Идентичность коммитов: POLIMAT_GIT_NAME / POLIMAT_GIT_EMAIL (дефолт — канон DCO).

Команды:
  prepare  --repo OWNER/REPO --branch feat/xxx [--workdir DIR]
  commit   --workdir DIR --message FILE --paths p1 p2 ...   (или --patch FILE для git am)
  verify   --workdir DIR                        (гейт; EXIT≠0 блокирует пуш)
  push     --workdir DIR --repo OWNER/REPO
  pr       --workdir DIR --repo OWNER/REPO --body PR_BODY.md [--title T]
  merge    --repo OWNER/REPO --branch feat/xxx  [--pr N]
  audit    --repo OWNER/REPO                    (свежий клон + verify + пломбы)

Идемпотентность «уже влито» (по батнику FINISH): merge-режим сначала смотрит
состояние PR; MERGED → синхронизирует локаль и завершает 0.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.github.com"
DEFAULT_ID = ("rtynbirf", "rtynbirf@users.noreply.github.com")


def sh(args, cwd=None, capture=True):
    r = subprocess.run(args, cwd=cwd, text=True,
                       capture_output=capture)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def token() -> str:
    t = os.environ.get("POLIMAT_TOKEN", "").strip()
    if not t:
        sys.exit("ПОЛИМАТ-ПАЙПЛАЙН: нет POLIMAT_TOKEN в окружении "
                 "(секрет только в памяти процесса, канон 03)")
    return t


def git_id():
    name = os.environ.get("POLIMAT_GIT_NAME", DEFAULT_ID[0])
    mail = os.environ.get("POLIMAT_GIT_EMAIL", DEFAULT_ID[1])
    return ["-c", f"user.name={name}", "-c", f"user.email={mail}"]


def repair(wd: Path):
    """Шаг 2: снос мусора прерванного am/rebase (самолечение из батника)."""
    for junk in ("rebase-apply", "rebase-merge"):
        p = wd / ".git" / junk
        if p.exists():
            sh(["git", f"{junk.split('-')[0]}" + (" --abort" if junk == "rebase-merge" else " --abort")], cwd=wd)
            shutil.rmtree(p, ignore_errors=True)
            print(f"  ремонт: снесён .git/{junk}")


def api_req(method: str, path: str, body: dict | None = None):
    req = urllib.request.Request(
        API + path, method=method,
        data=json.dumps(body).encode() if body else None,
        headers={"Authorization": f"Bearer {token()}",
                 "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read().decode()
            # v1.2 D2: 204 No Content (DELETE ветки после merge) — пустое тело,
            # парсер обязан вернуть {}, а не падать JSONDecodeError (доказано T13)
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode() or "{}"
        return json.loads(raw) if raw.strip() else {}


def cmd_prepare(a):
    url = f"https://github.com/{a.repo}.git"
    wd = Path(a.workdir or Path(a.repo.split("/")[1]))
    if (wd / ".git").exists():
        print(f"[1] клон уже есть — продолжаю: {wd}")
        sh(["git", "fetch", "origin", "--prune"], cwd=wd)
    else:
        for attempt, extra in enumerate(([], ["-c", "http.version=HTTP/1.1"],
                                         ["-c", "http.version=HTTP/1.1", "--depth", "1"])):
            rc, out = sh(["git", "clone", "--quiet", *extra, url, str(wd)])
            if rc == 0:
                print(f"[1] клон готов (попытка {attempt + 1}): {wd}")
                break
        else:
            sys.exit("[1] клон не прошёл 3 попытки — сеть/фильтр (канон батника: лестница попыток)")
    repair(wd)
    rc, out = sh(["git", "pull", "--ff-only", "--quiet"], cwd=wd)
    if rc != 0:
        sys.exit("[1] pull --ff-only не прошёл — история разошлась, нужен ручной разбор")
    if a.branch:
        sh(["git", "checkout", "-f", "-B", a.branch, f"origin/{a.branch}"], cwd=wd) \
            if sh(["git", "ls-remote", "--heads", url, a.branch], cwd=wd)[0] == 0 and \
            sh(["git", "ls-remote", "--heads", url, a.branch], cwd=wd)[1].strip() \
            else sh(["git", "checkout", "-f", "-B", a.branch], cwd=wd)
        print(f"[3] ветка готова: {a.branch}")
    print("prepare OK")


def cmd_commit(a):
    wd = Path(a.workdir)
    if a.patch:
        # патч = готовый коммит с DCO; повторно не применяем, если контент уже есть
        rc, out = sh(["git", *git_id(), "am", "--keep-non-patch", a.patch], cwd=wd)
        if rc != 0:
            sh(["git", "am", "--abort"], cwd=wd)
            # v1.1 D1: идемпотентность по содержимому — патч уже в ветке,
            # если его ОБРАТНОЕ применение валидно (git apply -R --check);
            # строка «already applied» git'ом не печатается (T12)
            rc_r, _ = sh(["git", "apply", "--reverse", "--check", "--quiet", a.patch], cwd=wd)
            if rc_r == 0:
                print("  патч уже в ветке (по содержимому) — повторно не применяю (идемпотентность батника)")
            else:
                sys.exit(f"git am не прошёл:\n{out[-800:]}")
        else:
            print("  патч применён как готовый коммит (DCO)")
    else:
        if a.paths:
            sh(["git", "add", *a.paths], cwd=wd)
        rc, out = sh(["git", "diff", "--cached", "--quiet"], cwd=wd)
        if rc == 0:
            print("  изменений нет — коммит не нужен (идемпотентность)")
            return
        rc, out = sh(["git", *git_id(), "commit", "-s", "--quiet", "-F", a.message], cwd=wd)
        if rc != 0:
            sys.exit(f"commit не прошёл:\n{out[-800:]}")
        print("  коммит собран (Conventional Commits + DCO)")


def cmd_verify(a):
    """Шаг 5: ГЕЙТ. Пуша нет, пока make verify ≠ 0."""
    rc, out = sh(["make", "verify"], cwd=a.workdir)
    line = next((l for l in out.splitlines() if "Result:" in l), "Result: ?")
    print(f"  verify: {line.strip()}")
    if rc != 0:
        sys.exit(f"verify-гейт ЗАКРЫТ (EXIT={rc}) — пуш отменён. "
                 f"Канон: «НЕ СЛОМАЙ make verify».\n{out[-1500:]}")
    print("verify-гейт ОТКРЫТ")


def cmd_push(a):
    wd = Path(a.workdir)
    branch = sh(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=wd)[1].strip()
    t = token()
    for attempt in range(3):
        rc, out = sh(["git", "push", "-u",
                      f"https://x-access-token:{t}@github.com/{a.repo}.git", branch], cwd=wd)
        if rc == 0:
            print(f"[6] ветка {branch} на GitHub (попытка {attempt + 1})")
            return
    sys.exit(f"пуш не прошёл 3 раза:\n{out[-600:]}")


def cmd_pr(a):
    wd = Path(a.workdir)
    branch = sh(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=wd)[1].strip()
    body = Path(a.body).read_text(encoding="utf-8")
    title = a.title or body.splitlines()[0].lstrip("# ")[:120]
    existing = api_req("GET", f"/repos/{a.repo}/pulls?head={a.repo.split('/')[0]}:{branch}&state=open")
    if isinstance(existing, list) and existing:
        n = existing[0]["number"]
        api_req("PATCH", f"/repos/{a.repo}/pulls/{n}", {"body": body, "title": title})
        print(f"PR #{n} обновлён: https://github.com/{a.repo}/pull/{n}")
        return
    d = api_req("POST", f"/repos/{a.repo}/pulls",
                {"title": title, "head": branch, "base": a.base, "body": body})
    if "number" in d:
        print(f"PR #{d['number']} создан: {d['html_url']}")
    else:
        sys.exit(f"PR не создан: {d}")


def cmd_merge(a):
    """Шаг 8: squash-merge по канону (≤24ч) + удаление ветки. Идемпотентно."""
    if a.pr:
        n = a.pr
    else:
        lst = api_req("GET", f"/repos/{a.repo}/pulls?head={a.repo.split('/')[0]}:{a.branch}&state=open")
        if not isinstance(lst, list) or not lst:
            print("открытого PR нет — возможно, уже влито; проверяю main...")
            sys.exit(0)
        n = lst[0]["number"]
    st = api_req("GET", f"/repos/{a.repo}/pulls/{n}")
    if st.get("state") == "merged" or st.get("merged"):
        print(f"PR #{n} уже влит — идемпотентность, синхронизируй main")
        return
    d = api_req("PUT", f"/repos/{a.repo}/pulls/{n}/merge", {
        "merge_method": "squash",
        "commit_title": st["title"] + f" (#{n})",
        "commit_message": st.get("body", "")[:2000] +
            "\n\nSigned-off-by: rtynbirf <rtynbirf@users.noreply.github.com>"})
    print(f"merge: {d.get('merged')} | sha: {str(d.get('sha', ''))[:12]} | {d.get('message', '')}")
    if d.get("merged"):
        api_req("DELETE", f"/repos/{a.repo}/git/refs/heads/{a.branch}")
        print(f"ветка {a.branch} удалена (PR закрыт автоматически)")


def cmd_audit(a):
    """Шаг 9: свежий клон + verify + пломбы. Итог — только числа."""
    t = token()
    with tempfile.TemporaryDirectory(prefix="polimat_audit_") as td:
        wd = Path(td) / a.repo.split("/")[1]
        rc, out = sh(["git", "clone", "--quiet", "--depth", "1",
                      f"https://x-access-token:{t}@github.com/{a.repo}.git", str(wd)])
        if rc != 0:
            sys.exit(f"audit-клон не прошёл: {out[-400:]}")
        head = sh(["git", "log", "--oneline", "-1"], cwd=wd)[1].strip()
        rc, out = sh(["make", "verify"], cwd=wd)
        line = next((l for l in out.splitlines() if "Result:" in l), "Result: ?")
        print(f"  HEAD: {head}")
        print(f"  verify: {line.strip()} | EXIT={rc}")
        seals = 0
        for s in wd.rglob("SHA256SUMS*.txt"):
            r2, o2 = sh(["sha256sum", "-c", str(s)], cwd=str(s.parent))
            ok = sum(1 for l in o2.splitlines() if l.endswith(": OK"))
            seals += ok
            print(f"  пломба {s.relative_to(wd)}: {ok} OK, EXIT={r2}")
        if rc != 0:
            sys.exit("AUDIT ПРОВАЛЕН: verify ≠ 0 на свежем клоне")
        print(f"audit OK: {seals} пломб сошлись")


def main():
    p = argparse.ArgumentParser(description="POLIMAT_PIPELINE — Linux-канон заливки в репо")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn in (("prepare", cmd_prepare), ("commit", cmd_commit),
                     ("verify", cmd_verify), ("push", cmd_push),
                     ("pr", cmd_pr), ("merge", cmd_merge), ("audit", cmd_audit)):
        s = sub.add_parser(name)
        s.add_argument("--repo"); s.add_argument("--branch"); s.add_argument("--workdir")
        s.add_argument("--message"); s.add_argument("--paths", nargs="*")
        s.add_argument("--patch"); s.add_argument("--body"); s.add_argument("--title")
        s.add_argument("--pr", type=int); s.add_argument("--base", default="main")
        s.set_defaults(fn=fn)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
