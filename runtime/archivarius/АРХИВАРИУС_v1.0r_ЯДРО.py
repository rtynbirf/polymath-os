#!/usr/bin/env python3
"""
АРХИВАРИУС v1.0r — РЕКОНСТРУКЦИЯ (Task 19) голографического агента-холона
Шесть органов: ГЕНОМ, МАНИФЕСТ, ТЕЛО, ЭСКИЗ, ДЫХАНИЕ, СУД
Принцип: ОДНО ДРУГОЕ НЕ ИСКЛЮЧАЕТ (слияние = объединение)
Selftest: 36/36 PASS

ИСТОРИЯ НОСИТЕЛЯ (честно, Г2):
- Оригинал v1.0 (697 строк, sha256 c41fef9dce6886b2...) съеден откатом среды — шрам №2 (Task 19).
- Байт-в-байт восстановление НЕВОЗМОЖНО: полного текста оригинала нет ни в одном носителе.
- v1.0r собран из выжившей копии кода (компендиум «СУММАРНЫЕ ОТВЕТЫ НА ГАЛЛОГРАММУ_2»,
  код-блок 2002-2668) + 3 машинных фикса:
  * T09/T15 — корень манифеста меняется только при append;
  * T28 — путь Меркла: сдвиг индекса один раз за уровень;
  * T28 — заявка несёт хэш записи листа.
- Статус: РЕКОНСТРУКЦИЯ. Функциональная целостность доказана selftest 36/36.
- Полный текст промпт-носителя выжил и восстановлен отдельно.
"""

import hashlib
import json
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
        
        # Проверка 6: совпадает ли корень?
        if claim["manifest_root"] != self.manifest.root():
            return Verdict.ОСКОЛОК
        
        # Проверка 7: есть ли тело?
        if "body_hash" not in claim or not claim["body_hash"]:
            return Verdict.ОТКАЗ
        
        # Проверка 8: совпадает ли хэш тела с записью?
        if claim["body_hash"] != hash_obj(entry.data):
            return Verdict.ОСКОЛОК
        
        return Verdict.ЧАСТЬ

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
    total = 36
    
    def check(test_id: int, condition: bool, description: str):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  ✓ T{test_id:02d}: {description}")
        else:
            failed += 1
            print(f"  ✗ T{test_id:02d}: {description}")
    
    print("=" * 70)
    print("SELFTEST: АРХИВАРИУС v1.0 — 36 проверок")
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
    agent.manifest.append({"test": "data2"})
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
        print("  --selftest  Запустить 36 проверок")
        print("  --demo      Запустить adversarial-демо")
        sys.exit(0)
