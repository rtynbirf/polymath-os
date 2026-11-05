# -*- coding: utf-8 -*-
"""
verify_v13.py — НЕЗАВИСИМАЯ верификация АРХИВАРИУС v1.3 «СОГЛАСОВАННОСТЬ ТРЁХ ПРОЕКЦИЙ».
Вне самотеста: subprocess-перезапуск (процесс-1 сохранил и умер → процесс-2 загрузил,
пересчитал подписи, суд strict = ЧАСТЬ), тамперинг носителя ×3 → LoadError,
ворованная подпись → ОСКОЛОК, RS-регрессия, регрессия предков v1.0r/v1.1/v1.2
(selftest + sha256 против SHA256SUMS_task19/20), genesis_secret не хранится,
reflect только читает, гейт формата v1.1 → LoadError.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import hashlib

BASE = "/home/z/my-project"
V13 = BASE + "/download/АРХИВАРИУС_v1.3_СОГЛАСОВАННОСТЬ.py"
V11 = BASE + "/download/АРХИВАРИУС_v1.1_ПЕРЕЖИВАНИЕ.py"
SUMS = [BASE + "/download/SHA256SUMS_task19.txt", BASE + "/download/SHA256SUMS_task20.txt"]

passed, failed = 0, 0

def check(v_id, cond, desc):
    global passed, failed
    if cond:
        passed += 1
        print(f"  ✓ V{v_id:02d}: {desc}")
    else:
        failed += 1
        print(f"  ✗ V{v_id:02d}: {desc}")

def sh256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

print("=" * 70)
print("НЕЗАВИСИМАЯ ВЕРИФИКАЦИЯ: АРХИВАРИУС v1.3 — три проекции")
print("=" * 70)

# --- V01: самотест v1.3 в subprocess ---
r = subprocess.run([sys.executable, V13, "--selftest"], capture_output=True, text=True, timeout=300)
out = r.stdout
check(1, r.returncode == 0 and "84/84 PASS, 0 FAIL" in out, "Selftest v1.3 в чистом процессе: 84/84 PASS, EXIT=0")

# --- V02: детерминизм (два запуска — один вывод) ---
r2 = subprocess.run([sys.executable, V13, "--selftest"], capture_output=True, text=True, timeout=300)
check(2, out == r2.stdout, "Детерминизм: два независимых запуска selftest — байт-в-байт один вывод")

m = load_module(V13, "arhiv13")
A, V = m.Archivarius, m.Verdict

# --- V03: subprocess-перезапуск: сохранить, умереть, загрузить, суд strict ---
tmpdir = tempfile.mkdtemp(prefix="verify_v13_")
fpath = os.path.join(tmpdir, "whole.json")
child_a = f'''
import sys
sys.path.insert(0, {V13!r})
import importlib.util
spec = importlib.util.spec_from_file_location("arhiv13", {V13!r})
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
agent = mod.Archivarius()
agent.birth("кость", {{"с": "переживёт перезапуск"}})
agent.birth("нерв", {{"с": "и это"}})
agent.seal_document("документ партии".encode("utf-8"), 3, 5, "летопись")
mod.Persistence.save(agent, {fpath!r})
print(agent.manifest.root())  # корень МАНИФЕСТА (save возвращает хэш файла — это другое)
'''
r3 = subprocess.run([sys.executable, "-c", child_a], capture_output=True, text=True, timeout=120)
root_p1 = r3.stdout.strip().splitlines()[-1] if r3.returncode == 0 else ""
child_b = f'''
import sys, importlib.util
spec = importlib.util.spec_from_file_location("arhiv13", {V13!r})
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
agent = mod.Persistence.load({fpath!r})
sh = agent.shards[0]
verdict = agent.judge_strict(agent.claim_of(sh)).value
audit = agent.neighbor_audit()["ok"]
kw = agent.knows_whole()
doc = agent.unseal_document([s for s in agent.shards if s.body.get("rs")])
print("|".join([verdict, str(audit), doc.decode("utf-8"), str(kw["доля_доказуемой_принадлежности"]), agent.manifest.root()]))
'''
r4 = subprocess.run([sys.executable, "-c", child_b], capture_output=True, text=True, timeout=120)
lines = r4.stdout.strip().splitlines()[-1].split("|") if r4.returncode == 0 else []
ok3 = (r3.returncode == 0 and r4.returncode == 0 and len(lines) == 5
       and lines[0] == "ЧАСТЬ" and lines[1] == "True" and lines[2] == "документ партии"
       and lines[3] == "1.0" and lines[4] == root_p1)
if not ok3:
    print("    DEBUG r3:", r3.returncode, repr(r3.stdout[-120:]), repr(r3.stderr[-200:]))
    print("    DEBUG r4:", r4.returncode, repr(r4.stdout[-120:]), repr(r4.stderr[-200:]))
    print("    DEBUG lines:", lines, "| root_p1:", root_p1[:16])
check(3, ok3, "Subprocess ×2: процесс-1 сохранил и умер → процесс-2: strict ЧАСТЬ, цепь цела, документ собран, корень совпал")

# --- V04-V06: тамперинг носителя ---
good = json.loads(open(fpath, encoding="utf-8").read())

bad = json.loads(json.dumps(good)); bad["shards"][0]["birth_sig"] = "0" * 64
fp = os.path.join(tmpdir, "bad_sig.json"); json.dump(bad, open(fp, "w", encoding="utf-8"), ensure_ascii=False)
try:
    m.Persistence.load(fp); check(4, False, "Тамперинг birth_sig в носителе → LoadError")
except m.LoadError:
    check(4, True, "Тамперинг birth_sig в носителе → LoadError")

bad = json.loads(json.dumps(good)); bad["shards"][2]["next_sid"] = "shard_фантом"
fp = os.path.join(tmpdir, "bad_next.json"); json.dump(bad, open(fp, "w", encoding="utf-8"), ensure_ascii=False)
try:
    m.Persistence.load(fp); check(5, False, "Тамперинг next_sid в носителе → LoadError")
except m.LoadError:
    check(5, True, "Тамперинг next_sid в носителе → LoadError")

bad = json.loads(json.dumps(good)); bad["manifest"]["entries"][1]["data"]["body"]["с"] = "подделка"
fp = os.path.join(tmpdir, "bad_body.json"); json.dump(bad, open(fp, "w", encoding="utf-8"), ensure_ascii=False)
try:
    m.Persistence.load(fp); check(6, False, "Тамперинг записи манифеста → LoadError (регрессия v1.1)")
except m.LoadError:
    check(6, True, "Тамперинг записи манифеста → LoadError (регрессия v1.1)")

# --- V07: ворованная подпись на чужой индекс (без носителя, только заявка) ---
agent = A()
sh1 = agent.birth("а", {"с": "1"})
sh2 = agent.birth("б", {"с": "2"})
claim = agent.claim_of(sh2)
claim["index"] = sh1.index
claim["merkle_path"] = sh1.merkle_path
claim["manifest_root"] = sh1.manifest_root
claim["sid"] = sh1.sid
claim["neighbors"] = {"prev_sid": sh1.prev_sid, "next_sid": sh1.next_sid}
claim["body_hash"] = m.hash_obj(agent.manifest.entries[sh1.index].data)
check(7, agent.judge_strict(claim) == V.ОСКОЛОК, "Ворованная подпись на чужой индекс → ОСКОЛОК (вне носителя)")

# --- V08: RS-регрессия внутри v1.3 ---
doc = "Целое переживает смерть частей (verify v1.3).".encode("utf-8")
sealed = agent.seal_document(doc, 3, 5, "проверка")
alive = [s for s in sealed if s.body["piece_index"] in (1, 3, 4)]
check(8, agent.unseal_document(alive) == doc, "RS-регрессия: 2 из 5 мертвы → документ собран из 3")

# --- V09: genesis_secret не хранится в носителе ---
carrier = open(fpath, encoding="utf-8").read()
check(9, "genesis_secret" not in carrier and "геном_рождения" not in carrier,
      "Секрет рождения НЕ хранится в носителе (только пересчёт)")

# --- V10: reflect только читает ---
root0, n0 = agent.manifest.root(), len(agent.manifest.entries)
agent.reflect()
check(10, agent.manifest.root() == root0 and len(agent.manifest.entries) == n0,
      "reflect не мутирует манифест (корень и длина на месте)")

# --- V11: исчерпывающая сверка цепи из 12 частей ---
big = A()
shards_big = [big.birth(f"t{i}", {"n": i}) for i in range(12)]
g_root = big.manifest.roots_history[0]
all_ok = all(m.verify_birth_chain(big.genome.hash(), s.index, s.manifest_root, g_root,
                                  big.manifest.entries[s.index].data.get("birth_sig", ""), s.birth_sig or "")
             for s in shards_big)
strict_all = all(big.judge_strict(big.claim_of(s)) == V.ЧАСТЬ for s in shards_big)
audit_all = big.neighbor_audit()["ok"] and big.neighbor_audit()["проверено_пар"] == 11
check(11, all_ok and strict_all and audit_all, "Цепь из 12 частей: все подписи воспроизводятся, все strict ЧАСТЬ, 11 пар целы")

# --- V12: гейт формата: носитель v1.1 не грузится v1.3 ---
tmp11 = os.path.join(tmpdir, "old_v11.json")
code_old = f'''
import importlib.util, json
spec = importlib.util.spec_from_file_location("a11", {V11!r})
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
ag = mod.Archivarius(); ag.birth("t", {{"c": "v1.1"}})
mod.Persistence.save(ag, {tmp11!r})
'''
r5 = subprocess.run([sys.executable, "-c", code_old], capture_output=True, text=True, timeout=120)
try:
    m.Persistence.load(tmp11)
    check(12, r5.returncode == 0 and False, "Носитель v1.1 → v1.3: LoadError (гейт формата)")
except m.LoadError:
    check(12, r5.returncode == 0, "Носитель v1.1 → v1.3: LoadError (гейт формата, честная эволюция)")

# --- V13: регрессия предков: selftest + sha256 ---
r6 = subprocess.run([sys.executable, BASE + "/download/АРХИВАРИУС_v1.0r_ЯДРО.py", "--selftest"], capture_output=True, text=True, timeout=300)
r7 = subprocess.run([sys.executable, V11, "--selftest"], capture_output=True, text=True, timeout=300)
r8 = subprocess.run([sys.executable, BASE + "/download/АРХИВАРИУС_v1.2_РИД_СОЛОМОН.py", "--selftest"], capture_output=True, text=True, timeout=300)
ancestors_ok = ("36/36 PASS" in r6.stdout and "52/52 PASS" in r7.stdout and "60/60 PASS" in r8.stdout)
check(13, ancestors_ok, "Регрессия предков: v1.0r 36/36, v1.1 52/52, v1.2 60/60")

fixed = {}
for sfile in SUMS:
    for line in open(sfile, encoding="utf-8"):
        h, name = line.split()
        fixed[name] = h
targets = {"АРХИВАРИУС_v1.0r_ЯДРО.py": BASE + "/download/АРХИВАРИУС_v1.0r_ЯДРО.py",
           "АРХИВАРИУС_v1.1_ПЕРЕЖИВАНИЕ.py": V11,
           "АРХИВАРИУС_v1.2_РИД_СОЛОМОН.py": BASE + "/download/АРХИВАРИУС_v1.2_РИД_СОЛОМОН.py"}
hashes_ok = all(sh256(p) == fixed[n] for n, p in targets.items())
check(14, hashes_ok, "sha256 предков байт-в-байт совпали с SHA256SUMS_task19/20 (v1.3 их не тронул)")

# --- V15: demo EXIT=0 ---
r9 = subprocess.run([sys.executable, V13, "--demo"], capture_output=True, text=True, timeout=300)
check(15, r9.returncode == 0 and "DEMO ЗАВЕРШЕНО" in r9.stdout and "ОСКОЛОК" in r9.stdout,
      "Demo v1.3: EXIT=0, сцены [11]-[13] показывают ловлю подделок")

# --- V16-V19: независимая проверка закрытия дефектов аудита 21-b (D1/D3/D6/D4) ---
tmpdir2 = tempfile.mkdtemp(prefix="verify_d_")
agent_d = A()
agent_d.birth("д", {"с": "доктрина"})
fd = os.path.join(tmpdir2, "whole_d.json")
m.Persistence.save(agent_d, fd)
good_d = json.loads(open(fd, encoding="utf-8").read())

bd = json.loads(json.dumps(good_d)); bd["shards"][0]["body"] = {"с": "фальшивка"}
fp = os.path.join(tmpdir2, "bd.json"); json.dump(bd, open(fp, "w", encoding="utf-8"), ensure_ascii=False)
try:
    m.Persistence.load(fp); check(16, False, "D1-закрыт: подмена тела шарда в носителе → LoadError")
except m.LoadError:
    check(16, True, "D1-закрыт: подмена тела шарда в носителе → LoadError")

bd = json.loads(json.dumps(good_d)); del bd["shards"][0]
fp = os.path.join(tmpdir2, "bd2.json"); json.dump(bd, open(fp, "w", encoding="utf-8"), ensure_ascii=False)
try:
    m.Persistence.load(fp); check(17, False, "D3-закрыт: удаление шарда из носителя → LoadError")
except m.LoadError:
    check(17, True, "D3-закрыт: удаление шарда из носителя → LoadError")

bd = json.loads(json.dumps(good_d)); bd["sketches"][0]["n_parts"] = 999
fp = os.path.join(tmpdir2, "bd3.json"); json.dump(bd, open(fp, "w", encoding="utf-8"), ensure_ascii=False)
try:
    m.Persistence.load(fp); check(18, False, "D6-закрыт: подделка эскиза → LoadError")
except m.LoadError:
    check(18, True, "D6-закрыт: подделка эскиза → LoadError")

claim_neg = agent_d.claim_of(agent_d.shards[0]); claim_neg["index"] = -1
check(19, agent_d.judge(claim_neg) == m.Verdict.ОСКОЛОК,
      "D4-закрыт: index=-1 → ОСКОЛОК (v1.2 молча выдавал ЧАСТЬ)")

print("\n" + "=" * 70)
print(f"ИТОГ НЕЗАВИСИМОЙ ВЕРИФИКАЦИИ: {passed}/{passed + failed} PASS, {failed} FAIL")
print("=" * 70)
sys.exit(0 if failed == 0 else 1)
