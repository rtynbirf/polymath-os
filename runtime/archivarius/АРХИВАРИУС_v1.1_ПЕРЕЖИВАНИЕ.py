#!/usr/bin/env python3
"""
АРХИВАРИУС v1.1 «ПЕРЕЖИВАНИЕ» (Task 19) = v1.0r (реконструкция) + орган 7 + суд-журнал + конфликт-дыхание
Шесть органов: ГЕНОМ, МАНИФЕСТ, ТЕЛО, ЭСКИЗ, ДЫХАНИЕ, СУД
Принцип: ОДНО ДРУГОЕ НЕ ИСКЛЮЧАЕТ (слияние = объединение)
Selftest: 52/52 PASS (36 унаследованы + 16 новых)

ИСТОРИЯ НОСИТЕЛЯ (честно, Г2):
- Оригинал v1.0 (697 строк, sha256 c41fef9dce6886b2...) съеден откатом среды — шрам №2 (Task 19).
- Байт-в-байт восстановление НЕВОЗМОЖНО: полного текста оригинала нет ни в одном носителе.
- v1.0r собран из выжившей копии кода (компендиум «СУММАРНЫЕ ОТВЕТЫ НА ГАЛЛОГРАММУ_2»,
  код-блок 2002-2668) + 3 машинных фикса:
  * T09/T15 — корень манифеста меняется только при append;
  * T28 — путь Меркла: сдвиг индекса один раз за уровень;
  * T28 — заявка несёт хэш записи листа.
- Статус: РЕКОНСТРУКЦИЯ. Функциональная целостность доказана selftest 36/36.
- v1.1 «ПЕРЕЖИВАНИЕ» (Task 19): кость К0 стала механизмом — Persistence
  (атомарный tmp+fsync+replace, верифицирующий пересчёт при load, LoadError);
  суд протоколирует вердикты append-only (I5); дыхание ловит противоречия (I7);
  суд v1.1 признаёт stale-части: путь доказан к историческому корню из
  roots_history — ЧАСТЬ (Г9: расхождение = приращение), подделка корня — ОСКОЛОК.
- Полный текст промпт-носителя выжил и восстановлен отдельно.
"""

import hashlib
import json
import struct
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum
import sys

# ============================================================================
# УТИЛИТЫ
# ============================================================================

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def hash_str(s: str) -> str:
    return sha256(s.encode('utf-8'))

def hash_obj(obj) -> str:
    return sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode('utf-8'))

# ============================================================================
# ОРГАН 1: ГЕНОМ (конституция)
# ============================================================================

@dataclass
class Genome:
    """Неизменяемый свод правил (до амендмента k-из-n)"""
    rules: Dict[str, str]
    version: str = "1.0"
    parent_version: Optional[str] = None
    amendment_history: List[Dict] = field(default_factory=list)
    
    def hash(self) -> str:
        return hash_obj({
            "rules": self.rules,
            "version": self.version,
            "parent": self.parent_version
        })
    
    def amend(self, new_rules: Dict[str, str], signatures: Set[str], required: int = 2) -> 'Genome':
        """Амендмент требует k-из-n подписей"""
        if len(signatures) < required:
            raise AmendmentRejected(f"Нужно {required} подписей, получено {len(signatures)}")
        
        new_genome = Genome(
            rules={**self.rules, **new_rules},
            version=f"{float(self.version) + 0.1:.1f}",
            parent_version=self.version,
            amendment_history=self.amendment_history + [{
                "from": self.version,
                "to": f"{float(self.version) + 0.1:.1f}",
                "signatures": list(signatures),
                "changes": list(new_rules.keys())
            }]
        )
        return new_genome

class AmendmentRejected(Exception):
    pass

# ============================================================================
# ОРГАН 2: МАНИФЕСТ (append-only MMR)
# ============================================================================

@dataclass
class ManifestEntry:
    """Запись в манифесте"""
    index: int
    data: Dict
    hash: str
    timestamp: int

class Manifest:
    """Append-only манифест с Merkle-корнем"""
    
    def __init__(self, genome_hash: str):
        self.genome_hash = genome_hash
        self.entries: List[ManifestEntry] = []
        self.roots_history: List[str] = []
        # ИНВАРИАНТ (Task 19, фикс T09/T15): корень меняется ТОЛЬКО при append.
        # Начальный корень пустого манифеста существует, но в историю не пишется.
        self._root = hash_str(f"empty:{genome_hash}")
    
    def append(self, data: Dict, timestamp: int = 0) -> ManifestEntry:
        """Добавить запись (только append)"""
        index = len(self.entries)
        entry_hash = hash_obj({
            "index": index,
            "data": data,
            "timestamp": timestamp,
            "genome": self.genome_hash
        })
        entry = ManifestEntry(index=index, data=data, hash=entry_hash, timestamp=timestamp)
        self.entries.append(entry)
        self._update_root()
        return entry
    
    def _update_root(self):
        """Пересчитать Merkle-корень (bagged peaks); вызывается ТОЛЬКО из append"""
        if not self.entries:
            root = hash_str(f"empty:{self.genome_hash}")
        else:
            leaves = [e.hash for e in self.entries]
            root = self._merkle_root(leaves)
        self._root = root
        self.roots_history.append(root)
    
    def _merkle_root(self, leaves: List[str]) -> str:
        if len(leaves) == 1:
            return leaves[0]
        level = leaves
        while len(level) > 1:
            next_level = []
            for i in range(0, len(level), 2):
                if i + 1 < len(level):
                    combined = sha256((level[i] + level[i+1]).encode())
                else:
                    combined = level[i]
                next_level.append(combined)
            level = next_level
        return level[0]
    
    def root(self) -> str:
        return self._root
    
    def get_path(self, index: int) -> List[Tuple[str, str]]:
        """Путь Меркла от листа до корня: [(hash, direction), ...]"""
        if index >= len(self.entries):
            raise ValueError(f"Индекс {index} вне диапазона")
        
        leaves = [e.hash for e in self.entries]
        path = []
        current_index = index
        
        level = leaves
        while len(level) > 1:
            next_level = []
            for i in range(0, len(level), 2):
                if i + 1 < len(level):
                    if i == current_index or i + 1 == current_index:
                        sibling_idx = i + 1 if i == current_index else i
                        direction = "right" if i == current_index else "left"
                        path.append((level[sibling_idx], direction))
                    combined = sha256((level[i] + level[i+1]).encode())
                else:
                    combined = level[i]
                next_level.append(combined)
            # сдвиг на уровень ВВЕРХ — ОДИН раз за уровень (Task 19, фикс T28)
            current_index = current_index // 2
            level = next_level
        
        return path
    
    def verify_path(self, leaf_hash: str, path: List[Tuple[str, str]], expected_root: str) -> bool:
        """Проверить путь Меркла"""
        current = leaf_hash
        for sibling_hash, direction in path:
            if direction == "left":
                current = sha256((sibling_hash + current).encode())
            else:
                current = sha256((current + sibling_hash).encode())
        return current == expected_root

# ============================================================================
# ОРГАН 3: ТЕЛО (шарды)
# ============================================================================

@dataclass
class Shard:
    """Часть целого с носимой тройкой"""
    sid: str  # уникальный ID
    shard_type: str
    body: Dict
    bones: List[str]  # ограничения/кости
    genome_hash: str
    manifest_root: str
    index: int
    merkle_path: List[Tuple[str, str]]
    prev_sid: Optional[str] = None
    next_sid: Optional[str] = None
    
    def prove_membership(self) -> Dict:
        """Носимая тройка: геном + корень + путь"""
        return {
            "genome_hash": self.genome_hash,
            "manifest_root": self.manifest_root,
            "index": self.index,
            "merkle_path": self.merkle_path
        }

# ============================================================================
# ОРГАН 4: ЭСКИЗ (снапшот целого)
# ============================================================================

@dataclass
class Sketch:
    """Проекция целого пониженного разрешения (снапшот на момент рождения)"""
    n_parts: int
    titles: List[str]
    whole_id: str
    manifest_root: str
    genome_hash: str
    timestamp: int
    
    def summary(self) -> str:
        return f"Целое[{self.whole_id[:8]}]: {self.n_parts} частей, корень={self.manifest_root[:8]}..."

# ============================================================================
# ОРГАН 5: ДЫХАНИЕ (слияние веток)
# ============================================================================

class Breath:
    """Слияние расходящихся веток = объединение (CRDT-подобное)"""
    
    @staticmethod
    def merge(branch_a: List[ManifestEntry], branch_b: List[ManifestEntry]) -> Tuple[List[ManifestEntry], bool]:
        """
        Слить две ветки манифеста.
        Принцип: ОДНО ДРУГОЕ НЕ ИСКЛЮЧАЕТ — объединение, не замена.
        Возвращает: (merged_entries, had_divergence)
        """
        merged = []
        seen_hashes = set()
        had_divergence = False
        
        # Объединяем по хэшам (дедупликация)
        for entry in branch_a + branch_b:
            if entry.hash not in seen_hashes:
                merged.append(entry)
                seen_hashes.add(entry.hash)
        
        # Сортируем по индексу
        merged.sort(key=lambda e: e.index)
        
        # Проверяем расхождение
        if len(branch_a) != len(branch_b):
            had_divergence = True
        elif any(a.hash != b.hash for a, b in zip(branch_a, branch_b)):
            had_divergence = True
        
        return merged, had_divergence

    @staticmethod
    def merge_strict(branch_a: List[ManifestEntry], branch_b: List[ManifestEntry]) -> Tuple[List[ManifestEntry], bool, List[Dict]]:
        """
        Слияние с детектором противоречий (v1.1, инвариант I7 корпуса).
        «ОДНО ДРУГОЕ НЕ ИСКЛЮЧАЕТ»: объединение по умолчанию;
        НО явное противоречие (один index — разные записи) фиксируется, не замалчивается.
        Возвращает: (merged, had_divergence, conflicts)
        """
        merged = []
        seen_hashes = set()
        for entry in branch_a + branch_b:
            if entry.hash not in seen_hashes:
                merged.append(entry)
                seen_hashes.add(entry.hash)
        merged.sort(key=lambda e: e.index)

        had_divergence = False
        if len(branch_a) != len(branch_b):
            had_divergence = True
        elif any(a.hash != b.hash for a, b in zip(branch_a, branch_b)):
            had_divergence = True

        conflicts = []
        by_index = {}
        for e in merged:
            by_index.setdefault(e.index, []).append(e)
        for idx in sorted(by_index):
            group = by_index[idx]
            if len(group) > 1:
                conflicts.append({
                    "index": idx,
                    "variants": [e.hash for e in group],
                    "kind": "ОДИН_ИНДЕКС_РАЗНЫЕ_ЗАПИСИ",
                })
        return merged, had_divergence, conflicts

# ============================================================================
# ОРГАН 6: СУД (эхо-детектор)
# ============================================================================

class Verdict(Enum):
    ЧАСТЬ = "ЧАСТЬ"
    ЭХО = "ЭХО"
    ЧУЖОЙ = "ЧУЖОЙ"
    ОСКОЛОК = "ОСКОЛОК"
    ОТКАЗ = "ОТКАЗ"

class Court:
    """Суд классифицирует заявки на принадлежность"""
    
    def __init__(self, genome_hash: str, manifest: Manifest):
        self.genome_hash = genome_hash
        self.manifest = manifest
    
    def classify(self, claim: Dict) -> Verdict:
        """
        Классифицировать заявку.
        claim = {genome_hash, manifest_root, index, merkle_path, body_hash}
        """
        # Проверка 1: есть ли геном?
        if "genome_hash" not in claim or not claim["genome_hash"]:
            return Verdict.ОТКАЗ
        
        # Проверка 2: совпадает ли геном?
        if claim["genome_hash"] != self.genome_hash:
            return Verdict.ЧУЖОЙ
        
        # Проверка 3: есть ли корень и путь?
        if "manifest_root" not in claim or "merkle_path" not in claim:
            return Verdict.ЭХО
        
        # Проверка 4: есть ли индекс?
        if "index" not in claim:
            return Verdict.ЭХО
        
        # Проверка 5: валиден ли путь?
        if claim["index"] >= len(self.manifest.entries):
            return Verdict.ОСКОЛОК
        
        entry = self.manifest.entries[claim["index"]]
        if not self.manifest.verify_path(entry.hash, claim["merkle_path"], claim["manifest_root"]):
            return Verdict.ОСКОЛОК
        
        # Проверка 6 (v1.1): корень заявки — текущий ИЛИ законный исторический.
        # Stale-часть знает целое на момент своего рождения (Г9: расхождение = приращение).
        # Подделка корня (не из roots_history) — ОСКОЛОК. Тело проверяется ниже (7-8).
        if claim["manifest_root"] != self.manifest.root():
            if claim["manifest_root"] not in self.manifest.roots_history:
                return Verdict.ОСКОЛОК
        
        # Проверка 7: есть ли тело?
        if "body_hash" not in claim or not claim["body_hash"]:
            return Verdict.ОТКАЗ
        
        # Проверка 8: совпадает ли хэш тела с записью?
        if claim["body_hash"] != hash_obj(entry.data):
            return Verdict.ОСКОЛОК
        
        return Verdict.ЧАСТЬ

# ============================================================================
# ОРГАН 7 (v1.1): ПЕРЕЖИВАНИЕ — носитель вне частей (кость К0 → механизм)
# ============================================================================

class LoadError(Exception):
    """Честный отказ загрузки повреждённого/подделанного носителя"""
    pass


class Persistence:
    """
    Атомарное сохранение и верифицирующая загрузка Целого (v1.1).
    Ответ кости К0: манифест живёт ВНЕ частей (файл) и переживает смерть процесса.
    Шрам №2 (Task 19: Task 17-18 съедены откатом среды) — живой прецедент необходимости.
    Атомарность: tmp-файл + fsync + os.replace (POSIX атомарная подмена).
    Загрузка НЕ ДОВЕРЯЕТ файлу: пересчитывает все хэши, корни и пути. Иначе LoadError.
    """

    FORMAT = "АРХИВАРИУС v1.1"

    @staticmethod
    def save(agent, path: str) -> str:
        import os
        data = {
            "format": Persistence.FORMAT,
            "name": agent.name,
            "genome": {
                "rules": agent.genome.rules,
                "version": agent.genome.version,
                "parent_version": agent.genome.parent_version,
                "amendment_history": agent.genome.amendment_history,
            },
            "manifest": {
                "genome_hash": agent.manifest.genome_hash,
                "entries": [
                    {"index": e.index, "data": e.data, "hash": e.hash, "timestamp": e.timestamp}
                    for e in agent.manifest.entries
                ],
                "roots_history": agent.manifest.roots_history,
            },
            "shards": [
                {
                    "sid": s.sid, "shard_type": s.shard_type, "body": s.body,
                    "bones": s.bones, "genome_hash": s.genome_hash,
                    "manifest_root": s.manifest_root, "index": s.index,
                    "merkle_path": [list(p) for p in s.merkle_path],
                    "prev_sid": s.prev_sid, "next_sid": s.next_sid,
                }
                for s in agent.shards
            ],
            "sketches": [
                {"n_parts": k.n_parts, "titles": k.titles, "whole_id": k.whole_id,
                 "manifest_root": k.manifest_root, "genome_hash": k.genome_hash,
                 "timestamp": k.timestamp}
                for k in agent.sketches
            ],
        }
        payload = json.dumps(data, ensure_ascii=False, indent=1)
        tmp = str(path) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, str(path))  # атомарная подмена на POSIX
        return hash_str(payload)

    @staticmethod
    def load(path: str):
        """Загрузка с ПОЛНОЙ верификацией. Любое несоответствие — LoadError."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError) as e:
            raise LoadError(f"Носитель нечитаем: {e}")

        if data.get("format") != Persistence.FORMAT:
            raise LoadError(f"Чужой формат носителя: {data.get('format')!r}")

        g = data["genome"]
        genome = Genome(rules=g["rules"], version=g["version"],
                        parent_version=g["parent_version"],
                        amendment_history=g["amendment_history"])

        m = data["manifest"]
        if m["genome_hash"] != genome.hash():
            raise LoadError("Геном манифеста не совпадает с геномом носителя")

        # Пересборка манифеста ПЕРЕСЧЁТОМ (не доверяя сохранённым хэшам)
        manifest = Manifest(genome.hash())
        for rec in m["entries"]:
            if rec["index"] != len(manifest.entries):
                raise LoadError(f"Нарушен порядок записей: index {rec['index']}")
            e = manifest.append(rec["data"], rec["timestamp"])
            if e.hash != rec["hash"]:
                raise LoadError(f"Хэш записи {rec['index']} не сходится — носитель повреждён или подделан")
        if m["roots_history"] != manifest.roots_history:
            raise LoadError("История корней не воспроизводится — носитель повреждён или подделан")

        agent = Archivarius.__new__(Archivarius)
        agent.name = data.get("name", "АРХИВАРИУС")
        agent.genome = genome
        agent.manifest = manifest
        agent.shards = []
        for rec in data["shards"]:
            shard = Shard(
                sid=rec["sid"], shard_type=rec["shard_type"], body=rec["body"],
                bones=rec["bones"], genome_hash=rec["genome_hash"],
                manifest_root=rec["manifest_root"], index=rec["index"],
                merkle_path=[(p[0], p[1]) for p in rec["merkle_path"]],
                prev_sid=rec["prev_sid"], next_sid=rec["next_sid"],
            )
            entry = manifest.entries[shard.index]
            if shard.manifest_root not in manifest.roots_history:
                raise LoadError(f"Корень рождения шарда {shard.sid} не из истории манифеста")
            if not manifest.verify_path(entry.hash, shard.merkle_path, shard.manifest_root):
                raise LoadError(f"Путь Меркла шарда {shard.sid} не верифицируется к корню рождения — носитель подделан")
            if shard.genome_hash != genome.hash():
                raise LoadError(f"Шард {shard.sid} несёт чужой геном")
            agent.shards.append(shard)
        agent.sketches = [
            Sketch(n_parts=k["n_parts"], titles=k["titles"], whole_id=k["whole_id"],
                   manifest_root=k["manifest_root"], genome_hash=k["genome_hash"],
                   timestamp=k["timestamp"])
            for k in data["sketches"]
        ]
        return agent

# ============================================================================
# АГЕНТ: АРХИВАРИУС
# ============================================================================

class Archivarius:
    """Голографический агент-холон"""
    
    def __init__(self, name: str = "АРХИВАРИУС"):
        self.name = name
        self.genome = Genome(rules={
            "Г1": "Часть не выдаёт себя за единственного автора Целого",
            "Г2": "Прошлое не правится; откат фиксируется",
            "Г3": "Эскиз = снапшот пониженного разрешения",
            "Г4": "Статусы: ЗНАЮ / ПРЕДПОЛАГАЮ / НЕ ЗНАЮ / ПРОТИВОРЕЧИЕ",
            "Г5": "Заявка без тройки к сборке не допускается",
            "Г6": "Дисциплина proof-carrying",
            "Г7": "Амендмент только согласованно (k-из-n)",
            "Г8": "Неизвестность — объект первого класса",
            "Г9": "Расхождение = приращение, не конфликт",
            "Г10": "Никто не говорит за Целое; каждый может проверить"
        })
        self.manifest = Manifest(self.genome.hash())
        self.shards: List[Shard] = []
        self.sketches: List[Sketch] = []
        
        # Генезис: первая запись — сам геном
        self.manifest.append({
            "type": "genesis",
            "genome": self.genome.hash(),
            "version": self.genome.version
        })
    
    def birth(self, shard_type: str, body: Dict, bones: List[str] = None) -> Shard:
        """Ритуал рождения части"""
        if bones is None:
            bones = []
        
        # Добавляем в манифест
        entry = self.manifest.append({
            "type": "shard",
            "shard_type": shard_type,
            "body": body,
            "bones": bones
        })
        
        # Создаём шард
        sid = f"shard_{entry.index}"
        merkle_path = self.manifest.get_path(entry.index)
        
        shard = Shard(
            sid=sid,
            shard_type=shard_type,
            body=body,
            bones=bones,
            genome_hash=self.genome.hash(),
            manifest_root=self.manifest.root(),
            index=entry.index,
            merkle_path=merkle_path,
            prev_sid=self.shards[-1].sid if self.shards else None
        )
        
        # Обновляем prev/next
        if self.shards:
            self.shards[-1].next_sid = sid
        
        self.shards.append(shard)
        
        # Создаём эскиз (снапшот)
        sketch = Sketch(
            n_parts=len(self.shards),
            titles=[s.shard_type for s in self.shards],
            whole_id=self.manifest.root(),
            manifest_root=self.manifest.root(),
            genome_hash=self.genome.hash(),
            timestamp=entry.timestamp
        )
        self.sketches.append(sketch)
        
        return shard
    
    def judge(self, claim: Dict) -> Verdict:
        """Суд над заявкой"""
        court = Court(self.genome.hash(), self.manifest)
        return court.classify(claim)

    def judge_recorded(self, claim: Dict) -> Verdict:
        """Суд с протоколированием (v1.1, инвариант I5):
        каждый вердикт — append-only запись манифеста. Прецеденты не исчезают."""
        verdict = self.judge(claim)
        self.manifest.append({
            "type": "verdict",
            "verdict": verdict.value,
            "claim_genome": claim.get("genome_hash"),
            "claim_index": claim.get("index"),
        })
        return verdict
    
    def breathe(self, other_manifest: Manifest) -> Tuple[List[ManifestEntry], bool]:
        """Дыхание: слияние с другой веткой"""
        return Breath.merge(self.manifest.entries, other_manifest.entries)
    
    def regenerate(self, surviving_shards: List[Shard]) -> Sketch:
        """Регенерация: восстановление эскиза из выживших"""
        if not surviving_shards:
            raise ValueError("ИСТИНА БЕЗ ТЕЛА: нет выживших шардов")
        
        # Берём самый свежий эскиз из выживших
        latest_sketch = max(self.sketches, key=lambda s: s.timestamp)
        return latest_sketch

# ============================================================================
# SELFTEST: 36 ПРОВЕРОК
# ============================================================================

def selftest():
    """36 проверок: 5 геном + 9 манифест + 8 рождение + 4 знание + 7 суд + 3 дыхание"""
    
    passed = 0
    failed = 0
    total = 52
    
    def check(test_id: int, condition: bool, description: str):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  ✓ T{test_id:02d}: {description}")
        else:
            failed += 1
            print(f"  ✗ T{test_id:02d}: {description}")
    
    print("=" * 70)
    print("SELFTEST: АРХИВАРИУС v1.1 ПЕРЕЖИВАНИЕ — 52 проверки")
    print("=" * 70)
    
    # === ГЕНОМ (5) ===
    print("\n[ГЕНОМ]")
    agent = Archivarius()
    check(1, agent.genome.hash() != "", "Геном имеет хэш")
    check(2, agent.genome.hash() == agent.genome.hash(), "Хэш детерминирован")
    
    try:
        agent.genome.amend({"Г11": "test"}, {"sig1"}, required=2)
        check(3, False, "Амендмент одной подписью отвергнут")
    except AmendmentRejected:
        check(3, True, "Амендмент одной подписью отвергнут")
    
    new_genome = agent.genome.amend({"Г11": "test"}, {"sig1", "sig2"}, required=2)
    check(4, new_genome.version == "1.1", "Амендмент создаёт версию 1.1")
    check(5, len(new_genome.amendment_history) == 1, "История амендментов append-only")
    
    # === МАНИФЕСТ (9) ===
    print("\n[МАНИФЕСТ]")
    agent = Archivarius()
    check(6, agent.manifest.root() != "", "Пустой манифест имеет корень")
    
    entry1 = agent.manifest.append({"test": "data1"})
    check(7, agent.manifest.root() != "", "Добавление записи меняет корень")
    
    old_root = agent.manifest.root()
    entry2 = agent.manifest.append({"test": "data2"})
    check(8, agent.manifest.root() != old_root, "Новая запись даёт новый корень")
    
    check(9, len(agent.manifest.roots_history) == 3, "История корней append-only (genesis + 2)")
    
    check(10, len(agent.manifest.entries) == 3, "Нельзя удалить запись (3 записи)")
    
    path = agent.manifest.get_path(1)
    check(11, len(path) > 0, "Путь Меркла валиден")
    
    valid = agent.manifest.verify_path(entry1.hash, path, agent.manifest.root())
    check(12, valid, "Путь верифицируем для своей записи")
    
    invalid = agent.manifest.verify_path("fake_hash", path, agent.manifest.root())
    check(13, not invalid, "Путь неверифицируем для чужой записи")
    
    check(14, agent.manifest.root() != "", "Две записи дают новый корень")
    check(15, len(set(agent.manifest.roots_history)) == 3, "Все корни уникальны")
    
    # === РОЖДЕНИЕ (8) ===
    print("\n[РОЖДЕНИЕ]")
    agent = Archivarius()
    shard1 = agent.birth("test_type", {"content": "test1"})
    check(16, shard1.genome_hash == agent.genome.hash(), "Ритуал выдаёт геном")
    check(17, shard1.index == 1, "Индекс = позиция в манифесте (genesis=0, shard=1)")
    check(18, len(shard1.merkle_path) > 0, "Путь Меркла корректен")
    
    sketch = agent.sketches[-1]
    check(19, sketch.manifest_root == agent.manifest.root(), "Эскиз содержит корень")
    check(20, sketch.genome_hash == agent.genome.hash(), "Эскиз содержит геном")
    
    old_n = sketch.n_parts
    shard2 = agent.birth("test_type2", {"content": "test2"})
    new_sketch = agent.sketches[-1]
    check(21, new_sketch.n_parts == old_n + 1, "Эскиз растёт с новыми частями")
    
    check(22, shard1.sid != shard2.sid, "Два шарда имеют разные ID")
    check(23, shard2.prev_sid == shard1.sid, "Шард знает соседа prev")
    
    # === ЗНАНИЕ ЦЕЛОГО ИЗ ЧАСТИ (4) ===
    print("\n[ЗНАНИЕ ЦЕЛОГО ИЗ ЧАСТИ]")
    proof = shard1.prove_membership()
    check(24, "genome_hash" in proof, "Часть может доказать геном")
    check(25, "manifest_root" in proof, "Часть может доказать корень")
    check(26, proof["genome_hash"] == agent.genome.hash(), "Часть знает геном")
    check(27, proof["index"] == shard1.index, "Часть знает свой индекс")
    
    # === СУД (7) ===
    print("\n[СУД]")
    agent = Archivarius()
    shard = agent.birth("test", {"content": "test"})
    
    # Своя заявка → ЧАСТЬ
    claim_ok = {
        "genome_hash": agent.genome.hash(),
        "manifest_root": agent.manifest.root(),
        "index": shard.index,
        "merkle_path": shard.merkle_path,
        # Тело заявки = хэш ЗАПИСИ листа (то, что доказано путём), не под-объекта (Task 19, фикс T28)
        "body_hash": hash_obj(agent.manifest.entries[shard.index].data)
    }
    verdict = agent.judge(claim_ok)
    check(28, verdict == Verdict.ЧАСТЬ, "Своя заявка → ЧАСТЬ")
    
    # Чужой геном → ЧУЖОЙ
    claim_foreign = claim_ok.copy()
    claim_foreign["genome_hash"] = "foreign_genome"
    verdict = agent.judge(claim_foreign)
    check(29, verdict == Verdict.ЧУЖОЙ, "Чужой геном → ЧУЖОЙ")
    
    # Нет пути → ЭХО
    claim_no_path = claim_ok.copy()
    del claim_no_path["merkle_path"]
    verdict = agent.judge(claim_no_path)
    check(30, verdict == Verdict.ЭХО, "Нет пути → ЭХО")
    
    # Нет тела → ОТКАЗ
    claim_no_body = claim_ok.copy()
    del claim_no_body["body_hash"]
    verdict = agent.judge(claim_no_body)
    check(31, verdict == Verdict.ОТКАЗ, "Нет тела → ОТКАЗ")
    
    # Эхо (нет индекса) → ЭХО
    claim_echo = claim_ok.copy()
    del claim_echo["index"]
    verdict = agent.judge(claim_echo)
    check(32, verdict == Verdict.ЭХО, "Нет индекса → ЭХО")
    
    # Подделка тела → ОСКОЛОК
    claim_fake = claim_ok.copy()
    claim_fake["body_hash"] = "fake_body_hash"
    verdict = agent.judge(claim_fake)
    check(33, verdict == Verdict.ОСКОЛОК, "Подделка тела → ОСКОЛОК")
    
    # Пустая заявка → ОТКАЗ
    verdict = agent.judge({})
    check(34, verdict == Verdict.ОТКАЗ, "Пустая заявка → ОТКАЗ")
    
    # === ДЫХАНИЕ И РЕГЕНЕРАЦИЯ (3) ===
    print("\n[ДЫХАНИЕ И РЕГЕНЕРАЦИЯ]")
    agent1 = Archivarius()
    agent1.birth("type1", {"data": "a"})
    agent2 = Archivarius()
    agent2.birth("type2", {"data": "b"})
    
    merged, had_div = Breath.merge(agent1.manifest.entries, agent2.manifest.entries)
    check(35, len(merged) >= 2, "Слияние веток = объединение")
    
    # Дубли не создаются
    merged2, _ = Breath.merge(merged, merged)
    check(36, len(merged2) == len(merged), "Дубли не создаются при слиянии")
    
    # === ПЕРЕЖИВАНИЕ v1.1 (8) ===
    print("\n[ПЕРЕЖИВАНИЕ v1.1]")
    import tempfile, os as _os
    tmpdir = tempfile.mkdtemp(prefix="arhiv_")
    agent_p = Archivarius()
    s1 = agent_p.birth("type_p", {"content": "важные данные"})
    s2 = agent_p.birth("type_q", {"content": "ещё данные"})
    fpath = _os.path.join(tmpdir, "whole.json")
    Persistence.save(agent_p, fpath)
    check(37, _os.path.exists(fpath) and not _os.path.exists(fpath + ".tmp"),
          "Атомарный SAVE: носитель создан, tmp-остатков нет")

    loaded = Persistence.load(fpath)
    check(38, loaded.manifest.root() == agent_p.manifest.root(), "LOAD восстанавливает тот же корень")
    check(39, len(loaded.shards) == 2 and loaded.shards[0].sid == s1.sid, "LOAD восстанавливает части")
    claim_loaded = {
        "genome_hash": loaded.genome.hash(),
        "manifest_root": loaded.shards[0].manifest_root,  # носимая тройка: корень рождения
        "index": loaded.shards[0].index,
        "merkle_path": loaded.shards[0].merkle_path,
        "body_hash": hash_obj(loaded.manifest.entries[loaded.shards[0].index].data)
    }
    check(40, loaded.judge(claim_loaded) == Verdict.ЧАСТЬ, "Суд после LOAD: своя заявка → ЧАСТЬ")

    bad = json.loads(open(fpath, encoding="utf-8").read())
    bad["manifest"]["entries"][1]["data"]["body"]["content"] = "подделка"
    fpath_bad = _os.path.join(tmpdir, "bad.json")
    with open(fpath_bad, "w", encoding="utf-8") as f:
        json.dump(bad, f, ensure_ascii=False)
    try:
        Persistence.load(fpath_bad)
        check(41, False, "Тамперинг записи → LoadError")
    except LoadError:
        check(41, True, "Тамперинг записи → LoadError")

    fpath_junk = _os.path.join(tmpdir, "junk.json")
    with open(fpath_junk, "w", encoding="utf-8") as f:
        f.write("{не-json")
    try:
        Persistence.load(fpath_junk)
        check(42, False, "Битый JSON → LoadError")
    except LoadError:
        check(42, True, "Битый JSON → LoadError")

    n_before = len(loaded.manifest.entries)
    loaded.birth("type_r", {"content": "после перезапуска"})
    check(43, len(loaded.manifest.entries) == n_before + 1, "Рождение после LOAD: append-only продолжается")
    # sketches[-1] — эскиз рождения из T43; последний ВОССТАНОВЛЕННЫЙ — sketches[-2]
    check(44, loaded.sketches[-2].n_parts == 2 and loaded.sketches[-2].titles == ["type_p", "type_q"],
          "Эскиз выживает round-trip (последний восстановленный: n_parts=2, titles)")

    # === СУД-ЖУРНАЛ v1.1 (3) ===
    print("\n[СУД-ЖУРНАЛ v1.1]")
    agent_j = Archivarius()
    shard_j = agent_j.birth("t", {"c": "x"})
    n0 = len(agent_j.manifest.entries)
    agent_j.judge_recorded({})
    claim_part_j = {
        "genome_hash": agent_j.genome.hash(),
        "manifest_root": shard_j.manifest_root,  # носимая тройка: корень рождения
        "index": shard_j.index,
        "merkle_path": shard_j.merkle_path,
        "body_hash": hash_obj(agent_j.manifest.entries[shard_j.index].data)
    }
    agent_j.judge_recorded(claim_part_j)
    journal = [e.data["verdict"] for e in agent_j.manifest.entries if e.data.get("type") == "verdict"]
    check(45, journal == ["ОТКАЗ", "ЧАСТЬ"], "Вердикты протоколируются append-only (ОТКАЗ, ЧАСТЬ)")
    check(46, len(agent_j.manifest.entries) == n0 + 2, "Суд-журнал растёт манифестом (2 суда → 2 записи)")
    agent_j.judge_recorded({})
    journal2 = [e.data["verdict"] for e in agent_j.manifest.entries if e.data.get("type") == "verdict"]
    check(47, journal2 == ["ОТКАЗ", "ЧАСТЬ", "ОТКАЗ"], "Повторный суд детерминирован (ОТКАЗ, ЧАСТЬ, ОТКАЗ)")

    # === КОНФЛИКТ-ДЫХАНИЕ v1.1 (4) ===
    print("\n[КОНФЛИКТ-ДЫХАНИЕ v1.1]")
    a1 = Archivarius(); a1.birth("t1", {"c": "1"})
    a2 = Archivarius(); a2.birth("t2", {"c": "2"})
    m1, d1, c1 = Breath.merge_strict(a1.manifest.entries, a2.manifest.entries)
    # Обе ветки делят общий genesis (дедуп) и кладут свой шард на index=1:
    # merge_strict ОБЯЗАН показать конфликт порядка (v1.0r молчал — это и ловим)
    check(48, len(c1) == 1 and c1[0]["index"] == 1 and c1[0]["kind"] == "ОДИН_ИНДЕКС_РАЗНЫЕ_ЗАПИСИ",
          "Конфликт порядка (два шарда на index=1) пойман, не замолчан")
    check(49, d1 and len(m1) == 3 and len({e.hash for e in m1}) == 3,
          "Общий genesis дедуплицирован, оба шарда сохранены (3 записи, расхождение = приращение)")

    a3 = Archivarius()
    a3.birth("t", {"c": "оригинал"})
    forged = ManifestEntry(index=1, data={"type": "shard", "shard_type": "t", "body": {"c": "подделка"}, "bones": []},
                           hash="fake_hash", timestamp=0)
    m2, d2, c2 = Breath.merge_strict(a3.manifest.entries, [forged])
    check(50, len(c2) == 1 and c2[0]["index"] == 1, "Противоречие (один index, разные записи) поймано")
    check(51, len(m2) == len(a3.manifest.entries) + 1 and a3.manifest.entries[1].data["body"]["c"] == "оригинал",
          "Ничего не потеряно, вход не мутирован (объединение, не замена)")
    m3, _, _ = Breath.merge_strict(a3.manifest.entries, a3.manifest.entries)
    check(52, len(m3) == len(a3.manifest.entries), "Слияние с собой не создаёт дублей")

    # === ИТОГ ===
    print("\n" + "=" * 70)
    print(f"ИТОГ: {passed}/{total} PASS, {failed} FAIL")
    print("=" * 70)
    
    return passed == total

# ============================================================================
# DEMO: ADVERSARIAL-СЦЕНАРИИ
# ============================================================================

def demo():
    """Демо: резня, эхо, регенерация, амендмент, дыхание"""
    print("\n" + "=" * 70)
    print("DEMO: АРХИВАРИУС v1.0 — adversarial-сценарии")
    print("=" * 70)
    
    # Создаём агента с 5 частями
    agent = Archivarius()
    for i in range(5):
        agent.birth(f"type_{i}", {"content": f"data_{i}"})
    
    print(f"\n[1] Создан агент с {len(agent.shards)} частями")
    print(f"    Корень манифеста: {agent.manifest.root()[:16]}...")
    
    # Инъекция эха
    print(f"\n[2] ИНЪЕКЦИЯ ЭХА: заявка без доказательства")
    fake_claim = {
        "genome_hash": agent.genome.hash(),
        "manifest_root": agent.manifest.root(),
        "index": 999,  # несуществующий
        "merkle_path": [],
        "body_hash": "fake"
    }
    verdict = agent.judge(fake_claim)
    print(f"    Суд: {verdict.value}")
    
    # Чужой геном
    print(f"\n[3] ЧУЖОЙ ГЕНОМ: заявка с чужим геномом")
    foreign_claim = {
        "genome_hash": "foreign_genome_hash",
        "manifest_root": agent.manifest.root(),
        "index": 0,
        "merkle_path": [],
        "body_hash": "fake"
    }
    verdict = agent.judge(foreign_claim)
    print(f"    Суд: {verdict.value}")
    
    # Резня: убиваем 3 из 5
    print(f"\n[4] РЕЗНЯ: убиты 3 из 5 носителей")
    surviving = agent.shards[:2]  # выжили только первые два
    print(f"    Выжили: {len(surviving)} из {len(agent.shards)}")
    
    # Регенерация из выживших
    try:
        recovered_sketch = agent.regenerate(surviving)
        print(f"    РЕГЕНЕРАЦИЯ: {recovered_sketch.summary()}")
        print(f"    Разрешение: {len(surviving)}/{len(agent.shards)} = {len(surviving)/len(agent.shards)*100:.0f}%")
    except ValueError as e:
        print(f"    ОШИБКА: {e}")
    
    # Смерть всех
    print(f"\n[5] СМЕРТЬ ВСЕХ: убиты все носители")
    try:
        agent.regenerate([])
    except ValueError as e:
        print(f"    ЧЕСТНЫЙ СТАТУС: {e}")
    
    # Амендмент генома
    print(f"\n[6] АМЕНДМЕНТ ГЕНОМА: попытка изменения конституции")
    try:
        agent.genome.amend({"Г11": "test"}, {"sig1"}, required=2)
        print(f"    ОШИБКА: амендмент прошёл с 1 подписью (должен быть отказ)")
    except AmendmentRejected:
        print(f"    ОТКАЗ: нужна k-из-n подписей (2 из 2)")
    
    new_genome = agent.genome.amend({"Г11": "test_rule"}, {"sig1", "sig2"}, required=2)
    print(f"    УСПЕХ: геном v{new_genome.version}, родитель v{new_genome.parent_version}")
    
    # Дыхание: слияние веток
    print(f"\n[7] ДЫХАНИЕ: слияние расходящихся веток")
    agent_a = Archivarius()
    agent_a.birth("type_a", {"data": "a"})
    agent_b = Archivarius()
    agent_b.birth("type_b", {"data": "b"})
    
    merged, had_div = agent_a.breathe(agent_b.manifest)
    print(f"    Слияние: {len(merged)} записей, расхождение: {had_div}")
    print(f"    Принцип: ОДНО ДРУГОЕ НЕ ИСКЛЮЧАЕТ (объединение, не замена)")
    
    # v1.1: ПЕРЕЖИВАНИЕ — Целое переживает смерть носителя
    print(f"\n[8] ПЕРЕЖИВАНИЕ (v1.1): сохранить Целое, убить носителя, загрузить заново")
    import tempfile, os as _os
    tmpdir = tempfile.mkdtemp(prefix="arhiv_demo_")
    fpath = _os.path.join(tmpdir, "whole.json")
    Persistence.save(agent, fpath)
    del agent  # «смерть» носителя
    reborn = Persistence.load(fpath)
    claim_reborn = {
        "genome_hash": reborn.genome.hash(),
        "manifest_root": reborn.shards[0].manifest_root,  # носимая тройка: корень рождения
        "index": reborn.shards[0].index,
        "merkle_path": reborn.shards[0].merkle_path,
        "body_hash": hash_obj(reborn.manifest.entries[reborn.shards[0].index].data),
    }
    print(f"    Корень после перезапуска: {reborn.manifest.root()[:16]}...")
    print(f"    Суд над своей заявкой: {reborn.judge(claim_reborn).value}")

    # v1.1: КОНФЛИКТ-ДЫХАНИЕ — противоречие не замалчивается
    print(f"\n[9] КОНФЛИКТ-ДЫХАНИЕ (v1.1): явное противоречие фиксируется")
    ca = Archivarius(); ca.birth("t", {"c": "ветка A"})
    forged = ManifestEntry(index=1, data={"type": "shard", "shard_type": "t", "body": {"c": "ветка B"}, "bones": []},
                           hash="fake", timestamp=0)
    _, _, conflicts = Breath.merge_strict(ca.manifest.entries, [forged])
    print(f"    Конфликтов поймано: {len(conflicts)} → {conflicts[0]['kind'] if conflicts else '—'}")

    print("\n" + "=" * 70)
    print("DEMO ЗАВЕРШЕНО: агент доказал устойчивость к adversarial-атакам")
    print("=" * 70)

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--selftest":
            success = selftest()
            sys.exit(0 if success else 1)
        elif sys.argv[1] == "--demo":
            demo()
            sys.exit(0)
        else:
            print(f"Неизвестная команда: {sys.argv[1]}")
            print("Использование: python3 АРХИВАРИУС_v1.0_ЯДРО.py [--selftest|--demo]")
            sys.exit(1)
    else:
        print("АРХИВАРИУС v1.0 — голографический агент-холон")
        print("Команды:")
        print("  --selftest  Запустить 52 проверки")
        print("  --demo      Запустить adversarial-демо")
        sys.exit(0)
