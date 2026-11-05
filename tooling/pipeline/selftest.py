#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SELFTEST инструмента POLIMAT_PIPELINE (claim #29 канона polymath-os).
12 машинных проверок офлайн-семантики механизма заливки: БЕЗ сети,
БЕЗ токена, БЕЗ GitHub. Печатает «12/12 PASS» и EXIT=0; первый провал —
подробности и EXIT=1. Все временные репо — в tempfile и стираются.

Покрытие (T01–T12): синтаксис; целостность канона 9 шагов; ремонт
rebase-мусора; секрет только в памяти процесса; идентичность коммитов
(дефолт DCO + переопределение env); CLI 7 подкоманд; гигиена (0 ghp_);
verify-гейт ОТКРЫТ; verify-гейт ЗАКРЫТ (пуш блокирован); коммит с DCO
и идемпотентность «изменений нет»; идемпотентность патча ПО СОДЕРЖИМОМУ
(git apply --reverse --check, дефект D1 v1.0 закрыт).
"""
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True  # гигиена: без __pycache__ рядом с каноном

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import polimat_pipeline as pp  # noqa: E402

PASSED = 0
TOTAL = 12


def ok(n, name):
    global PASSED
    PASSED += 1
    print(f"T{n:02d} PASS {name}")


def fail(n, name, detail):
    print(f"T{n:02d} FAIL {name}: {detail}")


class Namespace:
    """Минимальная заглушка argparse.Namespace для cmd_* функций."""
    def __init__(self, **kw):
        self.__dict__.update(kw)


def git_sh(args, cwd):
    return subprocess.run(args, cwd=str(cwd), capture_output=True, text=True)


# T01 — синтаксис инструмента (py_compile с cfile во временном каталоге,
# чтобы не рождать __pycache__ в каноне)
def t01():
    out = Path(tempfile.mkdtemp()) / "p.pyc"
    r = subprocess.run(
        [sys.executable, "-c",
         "import py_compile,sys; py_compile.compile(sys.argv[1], cfile=sys.argv[2], doraise=True)",
         str(HERE / "polimat_pipeline.py"), str(out)],
        capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-400:]


# T02 — целостность канона: все 9 шагов механизма присутствуют в docstring
def t02():
    doc = pp.__doc__
    marks = ["1. Клон", "2. Ремонт", "3. Ветка", "4. Коммиты", "5. Verify-гейт",
             "6. Пуш", "7. PR", "8. merge-режим", "9. Пост-пуш"]
    missing = [m for m in marks if m not in doc]
    assert not missing, f"канон повреждён, нет шагов: {missing}"


# T03 — ремонт: снос мусора прерванного am/rebase (самолечение из батника)
def t03():
    with tempfile.TemporaryDirectory() as td:
        wd = Path(td) / "wd"
        (wd / ".git" / "rebase-apply").mkdir(parents=True)
        (wd / ".git" / "rebase-merge").mkdir(parents=True)
        pp.repair(wd)
        assert not (wd / ".git" / "rebase-apply").exists()
        assert not (wd / ".git" / "rebase-merge").exists()


# T04 — секрет: без POLIMAT_TOKEN в окружении → честный SystemExit
def t04():
    saved = {k: v for k, v in __import__("os").environ.items()
             if k.startswith("POLIMAT")}
    for k in list(saved):
        del __import__("os").environ[k]
    try:
        try:
            pp.token()
            raise AssertionError("token() не отказался без POLIMAT_TOKEN")
        except SystemExit as e:
            assert "POLIMAT_TOKEN" in str(e), f"не то сообщение: {e}"
    finally:
        __import__("os").environ.update(saved)


# T05 — секрет: токен читается ТОЛЬКО из памяти процесса (env)
def t05():
    import os
    os.environ["POLIMAT_TOKEN"] = "smoke-value-T05"
    try:
        assert pp.token() == "smoke-value-T05"
    finally:
        os.environ.pop("POLIMAT_TOKEN", None)


# T06 — идентичность коммитов: дефолт DCO канона + переопределение env
def t06():
    import os
    a = pp.git_id()
    assert "user.name=rtynbirf" in a and "rtynbirf@users.noreply.github.com" in " ".join(a)
    os.environ["POLIMAT_GIT_NAME"] = "Владелец"
    os.environ["POLIMAT_GIT_EMAIL"] = "owner@example.com"
    try:
        a = pp.git_id()
        assert "user.name=Владелец" in a and "user.email=owner@example.com" in a
    finally:
        os.environ.pop("POLIMAT_GIT_NAME", None)
        os.environ.pop("POLIMAT_GIT_EMAIL", None)


# T07 — CLI: все 7 подкоманд имеют рабочую справку (EXIT=0)
def t07():
    for sub in ("prepare", "commit", "verify", "push", "pr", "merge", "audit"):
        r = subprocess.run([sys.executable, str(HERE / "polimat_pipeline.py"),
                            sub, "--help"], capture_output=True, text=True)
        assert r.returncode == 0, f"{sub} --help EXIT={r.returncode}"


# T08 — гигиена: в исходнике 0 литералов ghp_; секрет берётся только из env
def t08():
    src = (HERE / "polimat_pipeline.py").read_text(encoding="utf-8")
    assert "ghp_" not in src, "литерал токена в исходнике!"
    assert 'os.environ.get("POLIMAT_TOKEN"' in src, "токен читается не из env"


# T09 — verify-гейт ОТКРЫТ: make verify = 0 → команда проходит без SystemExit
def t09():
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "Makefile").write_text(
            "verify:\n\t@echo 'Result: 1 passed, 0 failed'\n", encoding="utf-8")
        pp.cmd_verify(Namespace(workdir=str(td)))  # SystemExit не поднят = гейт открыт


# T10 — verify-гейт ЗАКРЫТ: make verify != 0 → SystemExit, пуш блокирован
def t10():
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "Makefile").write_text(
            "verify:\n\t@echo 'Result: 0 passed, 1 failed'\n\t@exit 2\n",
            encoding="utf-8")
        try:
            pp.cmd_verify(Namespace(workdir=str(td)))
            raise AssertionError("гейт пропустил провал verify")
        except SystemExit as e:
            assert "ЗАКРЫТ" in str(e), f"не то сообщение: {e}"


# T11 — коммит: изменения → коммит с DCO-трейлером; пусто → «изменений нет»
def t11():
    with tempfile.TemporaryDirectory() as td:
        wd = Path(td) / "repo"
        git_sh(["git", "init", "-q", str(wd)], td)
        git_sh(["git", "config", "user.name", "t"], wd)
        git_sh(["git", "config", "user.email", "t@t"], wd)
        msg = Path(td) / "msg.txt"
        msg.write_text("test: T11 коммит пайплайна", encoding="utf-8")
        # (а) ничего не изменено → идемпотентность, коммита нет
        pp.cmd_commit(Namespace(workdir=str(wd), message=str(msg),
                                paths=["."], patch=None))
        assert git_sh(["git", "rev-list", "--count", "HEAD"], wd).returncode != 0
        # (б) изменение появилось → ровно один коммит с Signed-off-by
        (wd / "f.txt").write_text("T11", encoding="utf-8")
        pp.cmd_commit(Namespace(workdir=str(wd), message=str(msg),
                                paths=["f.txt"], patch=None))
        r = git_sh(["git", "log", "--format=%B", "-1"], wd)
        assert "Signed-off-by:" in r.stdout, "нет DCO-трейлера"
        assert git_sh(["git", "rev-list", "--count", "HEAD"], wd).stdout.strip() == "1"


# T12 — идемпотентность патча ПО СОДЕРЖИМОМУ (дефект D1 v1.0 закрыт):
# патч уже в ветке → git am падает («does not apply»), детектор v1.1
# распознаёт содержание через git apply -R --check и НЕ падает, НЕ дублирует
def t12():
    with tempfile.TemporaryDirectory() as td:
        wd = Path(td) / "repo"
        git_sh(["git", "init", "-q", str(wd)], td)
        git_sh(["git", "config", "user.name", "t"], wd)
        git_sh(["git", "config", "user.email", "t@t"], wd)
        (wd / "f.txt").write_text("line1\n", encoding="utf-8")
        git_sh(["git", "add", "f.txt"], wd)
        git_sh(["git", "commit", "-qm", "init"], wd)
        (wd / "f.txt").write_text("line1\nline2\n", encoding="utf-8")
        git_sh(["git", "commit", "-qam", "second"], wd)
        patch = Path(td) / "0001.patch"
        git_sh(["git", "format-patch", "-1", "--quiet", "-o", str(Path(td))], wd)
        patch = next(p for p in Path(td).glob("0001-*.patch"))
        # патч уже применён (HEAD == second); повторный cmd_commit --patch
        # обязан распознать «уже в ветке» и выйти штатно
        pp.cmd_commit(Namespace(workdir=str(wd), patch=str(patch),
                                message=None, paths=None))
        cnt = git_sh(["git", "rev-list", "--count", "HEAD"], wd).stdout.strip()
        assert cnt == "2", f"дубль коммита: HEAD count={cnt}"


TESTS = [(1, t01, "py_compile"), (2, t02, "канон 9 шагов"),
         (3, t03, "ремонт rebase-мусора"), (4, t04, "секрет: нет env → отказ"),
         (5, t05, "секрет: только env"), (6, t06, "идентичность DCO"),
         (7, t07, "CLI 7 подкоманд"), (8, t08, "гигиена 0 ghp_"),
         (9, t09, "гейт ОТКРЫТ"), (10, t10, "гейт ЗАКРЫТ"),
         (11, t11, "коммит DCO + идемпотентность"),
         (12, t12, "патч: идемпотентность по содержимому")]

for n, fn, name in TESTS:
    try:
        fn()
        ok(n, name)
    except Exception as e:  # noqa: BLE001 — самотест обязан печатать провал
        fail(n, name, repr(e)[:300])

print()
print(f"  Result: {PASSED}/{TOTAL} PASS" if PASSED == TOTAL
      else f"  Result: {PASSED}/{TOTAL} PASS — ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if PASSED == TOTAL else 1)
