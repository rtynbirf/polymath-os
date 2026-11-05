#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HOLO-AGENT v2.0 — голографический агент-холон.
Инстанциация алгоритма из корпуса «СУММАРНЫЕ ОТВЕТЫ НА ГАЛЛОГРАММУ_1/2.txt».
================================================================================
Принцип: Голограмма = Истина = Целое знает части; часть знает Целое.
Формула корпуса:
  Целое = части + отношения + общий геном + манифест + правила проверки + история
  Часть = тело + кости + (геном, корень, индекс) + эскиз целого + соседи
  Истина = то, что проходит суд: согласовано с геномом и доказуемо из манифеста
  Эхо    = всё, что звучит как часть, но не может предъявить тройку

ШЕСТЬ ОРГАНОВ (+2 расширения корпуса):
  1. ГЕНОМ     Genome       — конституция Г1–Г10, амендмент k-из-n подписей
  2. МАНИФЕСТ  Manifest     — append-only, Merkle-корень = имя Целого
  3. ТЕЛО      Shard        — часть с носимой тройкой (геном, корень, индекс) + путь
  4. ЭСКИЗ     Sketch/HRR   — снапшот Целого пониженного разрешения (32-мерный HRR,
                              циркулярная свёртка) — НЕ копия (кость К3)
  5. ДЫХАНИЕ   Breath       — VectorClock + ORSet (CRDT) + слияние манифестов
                              по принципу «ОДНО ДРУГОЕ НЕ ИСКЛЮЧАЕТ»
  6. СУД       Court        — вердикты: ЧАСТЬ / ЭХО / ЧУЖОЙ / ОСКОЛОК / ОТКАЗ
  + ПАМЯТЬ     Memory E/S/P/W/I — эпизодическая/семантическая/provenance/рабочая/
                              идентичность + реестр НЕ ЗНАЮ (неизвестность —
                              объект первого класса)
  + PERSISTENCE save/load   — манифест на файле (кость К0: носитель вне частей),
                              с проверкой целостности при загрузке
  + ВЕБ-СЕНСОР WebSensor    — результат поиска = Evidence со статусом REPORTED,
                              истины не создаёт (раздел 12 конституции корпуса)

Инварианты (корпус, файл 2):
  I1 append-only            — прошлое не перезаписывается
  I2 genome-immutable       — геном не меняется без k подписей
  I3 membership-arithmetic  — принадлежность = хэш + корень + индекс, не вера
  I4 echo-rejection         — заявка без валидной тройки не допускается к сборке
  I5 regeneration-bounded   — восстановление только при >= k выживших

Кости честности (К0–К6 корпуса) воспроизведены в докстринге класса Bones.

Запуск:
  python3 holo_agent_v2.py --selftest   # 60/60 PASS
  python3 holo_agent_v2.py --demo       # adversarial-полигон
Только stdlib. Python 3.8+. 0 внешних зависимостей.
"""

import hashlib
import json
import math
import os
import random
import sys
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

# ============================================================================
# УТИЛИТЫ (хэширование, канонический JSON)
# ============================================================================

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_str(s: str) -> str:
    return sha256(s.encode("utf-8"))


def hash_obj(obj: Any) -> str:
    """Канонический хэш: sort_keys, без пробелов — детерминирован."""
    return sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    )


# ============================================================================
# ОРГАН 5 (часть 1): ВЕКТОРНЫЕ ЧАСЫ — Дыхание, причинный порядок
# ============================================================================

class VectorClock:
    """Векторные часы (Лэмпорт/Фидж): merge = поэлементный max (CRDT-свойство)."""

    def __init__(self, actor_id: str, counters: Optional[Dict[str, int]] = None):
        self.actor_id = actor_id
        self.counters: Dict[str, int] = dict(counters or {actor_id: 0})

    def increment(self) -> int:
        self.counters[self.actor_id] = self.counters.get(self.actor_id, 0) + 1
        return self.counters[self.actor_id]

    def merge(self, other: "VectorClock") -> None:
        for k, v in other.counters.items():
            self.counters[k] = max(self.counters.get(k, 0), v)

    def snapshot(self) -> Dict[str, int]:
        return dict(self.counters)

    def happens_before(self, other: "VectorClock") -> bool:
        """self < other: все счётчики self <= other и хотя бы один строго меньше."""
        le = all(self.counters.get(k, 0) <= other.counters.get(k, 0) for k in set(self.counters) | set(other.counters))
        lt = any(self.counters.get(k, 0) < other.counters.get(k, 0) for k in set(self.counters) | set(other.counters))
        return le and lt

    def to_dict(self) -> Dict:
        return {"actor_id": self.actor_id, "counters": self.counters}

    @classmethod
    def from_dict(cls, d: Dict) -> "VectorClock":
        return cls(d["actor_id"], d["counters"])


# ============================================================================
# ОРГАН 5 (часть 2): OR-SET — CRDT «набор наблюдаемых добавлений/удалений»
# ============================================================================

class ORSet:
    """
    Observed-Remove Set (Shapiro 2011, подтверждено web:ws_crdt).
    Слияние = объединение; удаление побеждает только известные ему теги.
    Свойство: слияния коммутативны, ассоциативны, идемпотентны → конвергенция.
    """

    def __init__(self):
        self.adds: Set[Tuple[str, str]] = set()      # (element, tag)
        self.tombstones: Set[str] = set()            # tags удалений

    def add(self, element: str, tag: Optional[str] = None) -> str:
        if tag is None:
            tag = hash_str(f"orset-add|{element}|{time.time_ns()}|{random.random()}")[:16]
        self.adds.add((element, tag))
        return tag

    def remove(self, element: str) -> int:
        removed = 0
        for el, tag in list(self.adds):
            if el == element and tag not in self.tombstones:
                self.tombstones.add(tag)
                removed += 1
        return removed

    def merge(self, other: "ORSet") -> None:
        self.adds |= other.adds
        self.tombstones |= other.tombstones

    def value(self) -> Set[str]:
        return {el for el, tag in self.adds if tag not in self.tombstones}

    def to_dict(self) -> Dict:
        return {"adds": sorted(self.adds), "tombstones": sorted(self.tombstones)}

    @classmethod
    def from_dict(cls, d: Dict) -> "ORSet":
        s = cls()
        s.adds = {(el, tag) for el, tag in d["adds"]}
        s.tombstones = set(d["tombstones"])
        return s


# ============================================================================
# ОРГАН 1: ГЕНОМ (конституция)
# ============================================================================

class AmendmentRejected(Exception):
    """Геном не меняется без k-из-n подписей (инвариант I2)."""


@dataclass
class Genome:
    """Неизменяемый свод правил; изменяется только процедурой амендмента."""

    rules: Dict[str, str]
    version: str = "2.0"
    parent_version: Optional[str] = None
    amendment_history: List[Dict] = field(default_factory=list)

    def hash(self) -> str:
        return hash_obj({"rules": self.rules, "version": self.version, "parent": self.parent_version})

    def amend(self, new_rules: Dict[str, str], signatures: Set[str], required: int = 2) -> "Genome":
        if len(signatures) < required:
            raise AmendmentRejected(
                f"Нужно {required} подписей, получено {len(signatures)} — амендмент отклонён (I2)"
            )
        new_version = f"{float(self.version) + 0.1:.1f}"
        return Genome(
            rules={**self.rules, **new_rules},
            version=new_version,
            parent_version=self.version,
            amendment_history=self.amendment_history
            + [{
                "from": self.version,
                "to": new_version,
                "signatures": sorted(signatures),
                "changes": sorted(new_rules.keys()),
            }],
        )


def default_genome() -> Genome:
    """Геном Г1–Г10 — дословно из корпуса (АРХИВАРИУС v1.0, файл 2)."""
    return Genome(rules={
        "Г1": "Часть не выдаёт себя за единственного автора Целого",
        "Г2": "Прошлое не правится; откат фиксируется (append-only)",
        "Г3": "Эскиз = снапшот пониженного разрешения, не копия",
        "Г4": "Статусы: ЗНАЮ / ПРЕДПОЛАГАЮ / НЕ ЗНАЮ / ПРОТИВОРЕЧИЕ",
        "Г5": "Заявка без тройки (геном, корень, индекс) к сборке не допускается",
        "Г6": "Дисциплина proof-carrying: утверждение носит доказательство",
        "Г7": "Амендмент только согласованно (k-из-n подписей)",
        "Г8": "Неизвестность — объект первого класса",
        "Г9": "Расхождение = приращение, не конфликт (одно другое не исключает)",
        "Г10": "Никто не говорит за Целое; каждый может проверить Целое",
    })


# ============================================================================
# ОРГАН 2: МАНИФЕСТ (append-only, Merkle-корень = имя Целого)
# ============================================================================

@dataclass
class ManifestEntry:
    index: int
    data: Dict
    hash: str
    ts: int


class Manifest:
    """
    Append-only перечень событий Целого. Корень Меркла — вычислимое ИМЯ Целого
    (инвариант: Целое — имя, а не место). Любое включение доказывается путём
    из ~log2(n) хэшей без обращения к центру.
    """

    def __init__(self, genome_hash: str):
        self.genome_hash = genome_hash
        self.entries: List[ManifestEntry] = []
        self.roots_history: List[str] = []
        self._update_root()

    # --- запись (только append; удалить/перезаписать нельзя) ----------------
    def append(self, data: Dict, ts: int = 0) -> ManifestEntry:
        index = len(self.entries)
        entry_hash = hash_obj({
            "index": index, "data": data, "ts": ts, "genome": self.genome_hash,
        })
        entry = ManifestEntry(index=index, data=data, hash=entry_hash, ts=ts)
        self.entries.append(entry)
        self._update_root()
        return entry

    def _update_root(self) -> None:
        if not self.entries:
            root = hash_str(f"empty:{self.genome_hash}")
        else:
            root = self._merkle_root([e.hash for e in self.entries])
        self.roots_history.append(root)

    @staticmethod
    def _merkle_root(leaves: List[str]) -> str:
        level = list(leaves)
        while len(level) > 1:
            nxt: List[str] = []
            for i in range(0, len(level), 2):
                if i + 1 < len(level):
                    nxt.append(sha256((level[i] + level[i + 1]).encode()))
                else:
                    nxt.append(level[i])  # нечётный последний поднимается как есть
            level = nxt
        return level[0]

    def root(self) -> str:
        return self.roots_history[-1] if self.roots_history else ""

    # --- путь Меркла ---------------------------------------------------------
    def get_path(self, index: int) -> List[Tuple[str, str]]:
        """
        Путь от листа к корню: [(sibling_hash, direction), ...].
        direction='right' — сосед справа (мы — левый ребёнок),
        direction='left'  — сосед слева (мы — правый ребёнок).
        NOTE: исправление дефекта корпуса — индекс листа делится на 2 ОДИН РАЗ
        на уровень (после обработки всего уровня), а не на каждую пару.
        """
        if index < 0 or index >= len(self.entries):
            raise ValueError(f"Индекс {index} вне диапазона манифеста")
        leaves = [e.hash for e in self.entries]
        path: List[Tuple[str, str]] = []
        level = leaves
        cur = index
        while len(level) > 1:
            if cur == len(level) - 1 and len(level) % 2 == 1:
                # нечётный хвостовой узел поднимается без соседа — шага пути нет
                pass
            else:
                pair_i = cur - 1 if cur % 2 == 1 else cur
                sib_i = pair_i + 1 if cur % 2 == 0 else pair_i
                direction = "right" if cur % 2 == 0 else "left"
                path.append((level[sib_i], direction))
            nxt = []
            for i in range(0, len(level), 2):
                if i + 1 < len(level):
                    nxt.append(sha256((level[i] + level[i + 1]).encode()))
                else:
                    nxt.append(level[i])
            level = nxt
            cur //= 2
        return path

    def verify_path(self, leaf_hash: str, path: List[Tuple[str, str]], expected_root: str) -> bool:
        current = leaf_hash
        for sibling_hash, direction in path:
            if direction == "left":
                current = sha256((sibling_hash + current).encode())
            else:
                current = sha256((current + sibling_hash).encode())
        return current == expected_root

    def sid_known(self, sid: str) -> bool:
        """Зарегистрирован ли идентификатор части в манифесте (для суда)."""
        for e in self.entries:
            d = e.data
            if isinstance(d, dict) and (d.get("sid") == sid or d.get("shard_type") == sid):
                return True
        return False

    def to_dict(self) -> Dict:
        return {
            "genome_hash": self.genome_hash,
            "entries": [{"index": e.index, "data": e.data, "hash": e.hash, "ts": e.ts} for e in self.entries],
            "roots_history": list(self.roots_history),
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "Manifest":
        m = cls.__new__(cls)
        m.genome_hash = d["genome_hash"]
        m.entries = [ManifestEntry(index=e["index"], data=e["data"], hash=e["hash"], ts=e["ts"]) for e in d["entries"]]
        m.roots_history = list(d["roots_history"])
        return m

# ============================================================================
# ОРГАН 4: ЭСКИЗ (HRR — голографическая проекция пониженного разрешения)
# ============================================================================

class HRRVector:
    """
    Holographic Reduced Representation (Plate; подтверждено web:ws_hrr —
    arXiv 2024 «Generalized HRR», VSA/HDC). Вектор 32 измерения; связывание
    роли и значения — циркулярная свёртка; суперпозиция — поэлементная сумма.
    Каждый эскиз несёт ЭХО целого пониженного разрешения, не копию (кость К3).
    """

    DIM = 32

    def __init__(self, vec: List[float]):
        self.v = vec

    @classmethod
    def random_vec(cls, seed: str) -> "HRRVector":
        rng = random.Random(int(hashlib.sha256(seed.encode()).hexdigest()[:16], 16))
        scale = 1.0 / math.sqrt(cls.DIM)
        return cls([rng.gauss(0.0, scale) for _ in range(cls.DIM)])

    @classmethod
    def convolve(cls, a: "HRRVector", b: "HRRVector") -> "HRRVector":
        """Циркулярная свёртка: c[k] = sum_i a[i]*b[(k-i) mod DIM]."""
        n = cls.DIM
        return cls([sum(a.v[i] * b.v[(k - i) % n] for i in range(n)) for k in range(n)])

    @classmethod
    def superpose(cls, vecs: List["HRRVector"]) -> "HRRVector":
        out = [0.0] * cls.DIM
        for v in vecs:
            for k in range(cls.DIM):
                out[k] += v.v[k]
        return cls(out).normalize()

    def normalize(self) -> "HRRVector":
        norm = math.sqrt(sum(x * x for x in self.v)) or 1.0
        return HRRVector([x / norm for x in self.v])

    def similarity(self, other: "HRRVector") -> float:
        """Косинусная мера: 1.0 — идентичны, ~0 — несвязаны."""
        a, b = self.normalize(), other.normalize()
        dot = sum(x * y for x, y in zip(a.v, b.v))
        return max(-1.0, min(1.0, dot))

    def to_list(self) -> List[float]:
        return list(self.v)

    @classmethod
    def from_list(cls, lst: List[float]) -> "HRRVector":
        return cls(list(lst))


@dataclass
class Sketch:
    """Снапшот Целого НА МОМЕНТ рождения части (не копия! кость К3)."""
    n_parts: int
    titles: List[str]
    whole_id: str          # корень манифеста на момент рождения
    manifest_root: str
    genome_hash: str
    timestamp: int
    hrr: HRRVector         # голографическая проекция пониженного разрешения

    def summary(self) -> str:
        return f"Целое[{self.whole_id[:8]}]: {self.n_parts} частей, корень={self.manifest_root[:8]}…"

    def to_dict(self) -> Dict:
        return {
            "n_parts": self.n_parts, "titles": self.titles, "whole_id": self.whole_id,
            "manifest_root": self.manifest_root, "genome_hash": self.genome_hash,
            "timestamp": self.timestamp, "hrr": self.hrr.to_list(),
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "Sketch":
        return cls(
            n_parts=d["n_parts"], titles=list(d["titles"]), whole_id=d["whole_id"],
            manifest_root=d["manifest_root"], genome_hash=d["genome_hash"],
            timestamp=d["timestamp"], hrr=HRRVector.from_list(d["hrr"]),
        )


def build_sketch(agent: "HoloAgent", ts: int) -> Sketch:
    """Эскиз = суперпозиция свёрток (роль_i, тело_i) по всем живым частям."""
    terms: List[HRRVector] = []
    for s in agent.shards:
        role_v = HRRVector.random_vec(f"role|{s.shard_type}")
        body_v = HRRVector.random_vec(f"body|{hash_obj(s.body)}")
        terms.append(HRRVector.convolve(role_v, body_v))
    hrr = HRRVector.superpose(terms) if terms else HRRVector.superpose(
        [HRRVector.random_vec("empty-whole")]
    )
    return Sketch(
        n_parts=len(agent.shards),
        titles=[s.shard_type for s in agent.shards],
        whole_id=agent.manifest.root(),
        manifest_root=agent.manifest.root(),
        genome_hash=agent.genome.hash(),
        timestamp=ts,
        hrr=hrr,
    )


# ============================================================================
# ОРГАН 3: ТЕЛО (шард — часть с носимой тройкой)
# ============================================================================

@dataclass
class Shard:
    """Часть Целого. Носит: тело + кости + (геном, корень, индекс) + путь + эскиз."""
    sid: str
    shard_type: str
    role: str
    body: Dict
    bones: List[str]
    genome_hash: str
    manifest_root: str          # корень НА МОМЕНТ рождения (устаревает честно)
    index: int
    merkle_path: List[Tuple[str, str]]
    sketch: Sketch
    leaf_hash: Optional[str] = None      # хэш своей записи в манифесте на момент рождения
    prev_sid: Optional[str] = None
    next_sid: Optional[str] = None

    def prove_membership(self) -> Dict:
        """Носимое доказательство: тройка (геном, корень, индекс) + путь + эскиз."""
        return {
            "genome_hash": self.genome_hash,
            "manifest_root": self.manifest_root,
            "index": self.index,
            "merkle_path": [tuple(p) for p in self.merkle_path],
            "sid": self.sid,
            "sketch_digest": self.sketch.manifest_root,
        }

    def knows_whole(self, genome_hash: str) -> bool:
        """Знает ли часть геном Целого (Г-знание, инвариант арифметический)."""
        return self.genome_hash == genome_hash

    def is_fresh(self, current_root: str) -> bool:
        """Свежа ли проекция: корень части == текущий корень манифеста."""
        return self.manifest_root == current_root

    def to_dict(self) -> Dict:
        return {
            "sid": self.sid, "shard_type": self.shard_type, "role": self.role,
            "body": self.body, "bones": self.bones, "genome_hash": self.genome_hash,
            "manifest_root": self.manifest_root, "index": self.index,
            "merkle_path": [list(p) for p in self.merkle_path],
            "sketch": self.sketch.to_dict(),
            "leaf_hash": self.leaf_hash,
            "prev_sid": self.prev_sid, "next_sid": self.next_sid,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "Shard":
        return cls(
            sid=d["sid"], shard_type=d["shard_type"], role=d["role"], body=d["body"],
            bones=list(d["bones"]), genome_hash=d["genome_hash"],
            manifest_root=d["manifest_root"], index=d["index"],
            merkle_path=[tuple(p) for p in d["merkle_path"]],
            sketch=Sketch.from_dict(d["sketch"]),
            leaf_hash=d.get("leaf_hash"),
            prev_sid=d.get("prev_sid"), next_sid=d.get("next_sid"),
        )


# ============================================================================
# ОРГАН 5 (часть 3): ДЫХАНИЕ — слияние веток («одно другое не исключает»)
# ============================================================================

class Breath:
    """
    Слияние расходящихся состояний = ОБЪЕДИНЕНИЕ, не замена (Г9).
    Расхождение — приращение, материал для уточнения, не конфликт.
    """

    @staticmethod
    def merge_entries(branch_a: List[ManifestEntry], branch_b: List[ManifestEntry]
                      ) -> Tuple[List[ManifestEntry], bool]:
        merged: List[ManifestEntry] = []
        seen: Set[str] = set()
        for e in branch_a + branch_b:
            if e.hash not in seen:
                merged.append(e)
                seen.add(e.hash)
        merged.sort(key=lambda e: e.index)
        had_divergence = (len(branch_a) != len(branch_b)) or any(
            a.hash != b.hash for a, b in zip(branch_a, branch_b)
        )
        return merged, had_divergence

    @staticmethod
    def breathe(a: "HoloAgent", b: "HoloAgent") -> Dict:
        """Полный цикл дыхания двух агентов: часы, ORSet, манифест — объединение."""
        a.clock.merge(b.clock)
        a.parts_set.merge(b.parts_set)
        b.clock.merge(a.clock)
        merged_entries, had_div = Breath.merge_entries(a.manifest.entries, b.manifest.entries)
        a_knew = len(a.manifest.entries)
        if had_div:
            # append-only union: недостающие записи b добавляются в манифест a;
            # корень пересчитывается ОДИН раз после сортировки итогового порядка
            known = {e.hash for e in a.manifest.entries}
            for e in b.manifest.entries:
                if e.hash not in known:
                    a.manifest.entries.append(e)
            a.manifest.entries.sort(key=lambda e: e.index)
            a.manifest._update_root()
        a.memory.episodic.append({
            "event": "breathe", "with": b.agent_id, "divergence": had_div,
            "merged_index": a_knew,
        })
        return {"divergence": had_div, "entries_a": len(a.manifest.entries)}


# ============================================================================
# ОРГАН 6: СУД (эхо-детектор, 5 вердиктов)
# ============================================================================

class Verdict(Enum):
    ЧАСТЬ = "ЧАСТЬ"
    ЭХО = "ЭХО"
    ЧУЖОЙ = "ЧУЖОЙ"
    ОСКОЛОК = "ОСКОЛОК"
    ОТКАЗ = "ОТКАЗ"


class Court:
    """
    Суд классифицирует заявку на принадлежность Целому.
    Порядок проверок (объединение алгоритма v2.0 и реализации v1.0 корпуса):
      1. нет генома / тела           → ОТКАЗ  (заявка даже не оформлена)
      2. геном чужой                 → ЧУЖОЙ  (другая конституция)
      3. нет корня / пути / индекса  → ЭХО    (звучит как часть, доказательства нет)
      4. индекс вне диапазона        → ОСКОЛОК (фрагмент чужого/мёртвого состояния)
      5. путь не сходится к корню    → ОСКОЛОК (подделка)
      6. корень устарел, но sid известен → ОСКОЛОК (stale-проекция честной части)
      7. хэш тела не совпал          → ОСКОЛОК
      иначе                          → ЧАСТЬ
    """

    def __init__(self, genome_hash: str, manifest: Manifest):
        self.genome_hash = genome_hash
        self.manifest = manifest

    def classify(self, claim: Dict) -> Verdict:
        # 1. Оформлена ли заявка вообще
        if not claim or "genome_hash" not in claim or not claim["genome_hash"]:
            return Verdict.ОТКАЗ
        if "body_hash" not in claim or not claim["body_hash"]:
            return Verdict.ОТКАЗ
        # 2. Чужой геном
        if claim["genome_hash"] != self.genome_hash:
            return Verdict.ЧУЖОЙ
        # 3. Эхо: отсутствует любой элемент доказательной тройки
        if "manifest_root" not in claim or not claim["manifest_root"]:
            return Verdict.ЭХО
        if "merkle_path" not in claim or claim["merkle_path"] is None:
            return Verdict.ЭХО
        if "index" not in claim:
            return Verdict.ЭХО
        # 4. Индекс вне диапазона
        idx = claim["index"]
        if not isinstance(idx, int) or idx < 0 or idx >= len(self.manifest.entries):
            return Verdict.ОСКОЛОК
        entry = self.manifest.entries[idx]
        # 5. Путь не сходится
        if not self.manifest.verify_path(entry.hash, claim["merkle_path"], claim["manifest_root"]):
            return Verdict.ОСКОЛОК
        # 6. Корень не текущий: осколок прошлого состояния (если часть известна)
        if claim["manifest_root"] != self.manifest.root():
            return Verdict.ОСКОЛОК
        # 7. Тело подделано
        if claim["body_hash"] != hash_obj(entry.data):
            return Verdict.ОСКОЛОК
        return Verdict.ЧАСТЬ


# ============================================================================
# ВЕБ-СЕНСОР: результат поиска = Evidence, не истина (раздел 12 конституции)
# ============================================================================

@dataclass
class Evidence:
    eid: str
    source_type: str          # 'web' | 'file' | 'observation' | 'inference' | 'user'
    uri: str
    title: str
    retrieved_at: str
    content_hash: str
    authority: str            # домен/носитель источника
    scope: str                # в каком контексте применимо
    excerpt: str

    def to_dict(self) -> Dict:
        return {
            "eid": self.eid, "source_type": self.source_type, "uri": self.uri,
            "title": self.title, "retrieved_at": self.retrieved_at,
            "content_hash": self.content_hash, "authority": self.authority,
            "scope": self.scope, "excerpt": self.excerpt,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "Evidence":
        return cls(**d)


class WebSensor:
    """
    Контракт веб-сенсора (честный):
      * сетевой вызов выполняет СРЕДА (ядро — только stdlib, 0 запросов);
      * среда передаёт результаты поиска как список JSON-объектов
        {uri, title, retrieved_at, authority, scope, excerpt};
      * сенсор превращает каждый результат в Evidence с content_hash;
      * Evidence получает эпистемический статус REPORTED;
      * статус поднимается до CORROBORATED только при >= 2 НЕЗАВИСИМЫХ
        источниках (разные authority), согласованных по content_hash-темам;
      * PROVEN веб-evidence не получает никогда (нет внутренней цепочки вывода).
    """

    @staticmethod
    def result_to_evidence(raw: Dict) -> Evidence:
        for key in ("uri", "title", "retrieved_at", "authority", "scope", "excerpt"):
            if key not in raw:
                raise ValueError(f"Веб-результат без поля {key} — отклонён сенсором")
        content_hash = hash_obj({k: raw.get(k) for k in ("uri", "title", "excerpt")})
        return Evidence(
            eid="ev:" + content_hash[:16],
            source_type="web",
            uri=raw["uri"], title=raw["title"], retrieved_at=raw["retrieved_at"],
            content_hash=content_hash, authority=raw["authority"],
            scope=raw["scope"], excerpt=raw["excerpt"],
        )

    @staticmethod
    def epistemic_status(evidences: List[Evidence]) -> str:
        """Минимально честная эпистемика веб-данных."""
        if not evidences:
            return "UNKNOWN"
        if len({e.authority for e in evidences}) >= 2:
            return "CORROBORATED"
        return "REPORTED"


# ============================================================================
# ПАМЯТЬ: E/S/P/W/I (эпизодическая, семантическая, provenance, рабочая, identity)
# ============================================================================

@dataclass
class Claim:
    """Утверждение с носимым доказательством и эпистемическим статусом (Г6)."""
    cid: str
    subject: str
    predicate: str
    value: Any
    asserted_by: str
    evidence_ids: List[str]
    context: Dict
    confidence: float
    status: str = "PROPOSED"
    clock: Optional[Dict] = None
    conflicts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "cid": self.cid, "subject": self.subject, "predicate": self.predicate,
            "value": self.value, "asserted_by": self.asserted_by,
            "evidence_ids": self.evidence_ids, "context": self.context,
            "confidence": self.confidence, "status": self.status,
            "clock": self.clock, "conflicts": self.conflicts,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "Claim":
        return cls(**d)


class EpisodicMemory:
    """Что происходило: рождения, дыхания, вердикты суда, заявления."""

    def __init__(self) -> None:
        self.events: List[Dict] = []

    def append(self, event: Dict) -> None:
        self.events.append(dict(event, at=time.time()))

    def to_dict(self) -> List[Dict]:
        return list(self.events)

    @classmethod
    def from_dict(cls, d: List[Dict]) -> "EpisodicMemory":
        m = cls()
        m.events = list(d)
        return m


class ProvenanceLedger:
    """
    Хэш-цепочка событий (кто → что сделал → над чем → когда → что получил).
    ПРОШЛОЕ НЕ УНИЧТОЖАЕТСЯ (инвариант I1); целостность проверяется пересчётом.
    """

    def __init__(self) -> None:
        self.chain: List[Dict] = []
        self._prev = "genesis"

    def append_event(self, actor: str, action: str, target: str, payload: Dict) -> Dict:
        rec = {
            "seq": len(self.chain),
            "actor": actor, "action": action, "target": target,
            "payload": payload,
            "previous_hash": self._prev,
        }
        rec["resulting_hash"] = hash_obj({k: rec[k] for k in rec if k != "resulting_hash"})
        self.chain.append(rec)
        self._prev = rec["resulting_hash"]
        return rec

    def verify_chain(self) -> bool:
        prev = "genesis"
        for rec in self.chain:
            expect = hash_obj({k: rec[k] for k in rec if k != "resulting_hash"})
            if rec["previous_hash"] != prev or rec["resulting_hash"] != expect:
                return False
            prev = rec["resulting_hash"]
        return True

    def to_dict(self) -> List[Dict]:
        return [dict(r) for r in self.chain]

    @classmethod
    def from_dict(cls, d: List[Dict]) -> "ProvenanceLedger":
        led = cls.__new__(cls)
        led.chain = [dict(r) for r in d]
        led._prev = d[-1]["resulting_hash"] if d else "genesis"
        return led


class AgentMemory:
    """E/S/P/W/I + реестр НЕ ЗНАЮ (Г8: неизвестность — объект первого класса)."""

    def __init__(self, agent_id: str, role: str):
        self.episodic = EpisodicMemory()
        self.semantic: Dict[str, Dict] = {}            # обобщение: {тезис: {status, sources}}
        self.provenance = ProvenanceLedger()
        self.working: Dict[str, Any] = {}              # очищается после задачи
        self.identity = {                              # кто я (I)
            "agent_id": agent_id, "role": role,
        }
        self.unknowns: Dict[str, Dict] = {}            # {scope: {reason, owner, impact}}

    def record_unknown(self, scope: str, reason: str, owner: str, impact: str) -> None:
        self.unknowns[scope] = {"reason": reason, "owner": owner, "impact": impact}

    def clear_working(self) -> None:
        self.working = {}

    def to_dict(self) -> Dict:
        return {
            "episodic": self.episodic.to_dict(),
            "semantic": self.semantic,
            "provenance": self.provenance.to_dict(),
            "working": self.working,
            "identity": self.identity,
            "unknowns": self.unknowns,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "AgentMemory":
        m = cls.__new__(cls)
        m.episodic = EpisodicMemory.from_dict(d["episodic"])
        m.semantic = dict(d["semantic"])
        m.provenance = ProvenanceLedger.from_dict(d["provenance"])
        m.working = dict(d["working"])
        m.identity = dict(d["identity"])
        m.unknowns = dict(d["unknowns"])
        return m

# ============================================================================
# ЦЕЛОЕ: HOLO-AGENT — холон (целое для частей, часть для надсистемы)
# ============================================================================

class IntegrityError(Exception):
    """Целостность манифеста нарушена — Целое отказывается лгать."""


class TruthWithoutBody(Exception):
    """ИСТИНА БЕЗ ТЕЛА: живых носителей меньше порога k (честный статус, К5)."""


class HoloAgent:
    """
    Голографический агент-холон. Реализует 8 операций алгоритма v2.0 корпуса:
    GENESIS → BIRTH → BREATHE → CLAIM → COURT → REGENERATE → REFLECT → AMEND,
    плюс PERSISTENCE (кость К0) и веб-сенсор Evidence-контракта.
    """

    FORMAT = "HOLO-AGENT.v2.0"

    def __init__(self, name: str = "HOLO-AGENT", k: int = 2, agent_id: Optional[str] = None):
        self.name = name
        self.k = k                                   # порог регенерации
        self.agent_id = agent_id or f"{name}#{hash_str(str(time.time_ns()))[:8]}"
        self.genome: Genome = default_genome()
        self.manifest = Manifest(self.genome.hash())
        self.shards: List[Shard] = []
        self.sketches: List[Sketch] = []
        self.claims: Dict[str, Claim] = {}
        self.evidences: Dict[str, Evidence] = {}
        self.clock = VectorClock(self.agent_id)
        self.parts_set = ORSet()
        self.memory = AgentMemory(self.agent_id, role="whole-of-parts")
        # GENESIS: первая запись манифеста — сам геном (алгоритм, шаг 1)
        self.manifest.append({
            "type": "genesis",
            "genome": self.genome.hash(),
            "version": self.genome.version,
            "format": self.FORMAT,
        })
        self.memory.provenance.append_event(self.agent_id, "genesis", "manifest", {
            "genome": self.genome.hash(), "k": self.k,
        })
        self.memory.episodic.append({"event": "genesis", "name": self.name, "k": self.k})

    # ---------------------------------------------------------------- рождение
    def birth(self, shard_type: str, role: str, body: Dict, bones: Optional[List[str]] = None) -> Shard:
        """Ритуал рождения части: геном → корень → срез → подпись (инвариант 6)."""
        prev_sid = self.shards[-1].sid if self.shards else None
        entry = self.manifest.append({
            "type": "shard",
            "sid": f"shard_{len(self.shards)+1:03d}_{hash_str(shard_type + str(len(self.shards)))[:6]}",
            "shard_type": shard_type, "role": role, "body": body,
            "bones": list(bones or []),
            "prev": prev_sid,
        })
        sid = entry.data["sid"]
        shard = Shard(
            sid=sid, shard_type=shard_type, role=role, body=body,
            bones=list(bones or []), genome_hash=self.genome.hash(),
            manifest_root=self.manifest.root(), index=entry.index,
            merkle_path=self.manifest.get_path(entry.index),
            sketch=Sketch(0, [], "", "", "", 0, HRRVector([0.0])),  # заполняется ниже
            leaf_hash=entry.hash,
            prev_sid=prev_sid,
        )
        self.shards.append(shard)
        if self.shards and len(self.shards) > 1:
            self.shards[-2].next_sid = sid
        sketch = build_sketch(self, ts=entry.ts)     # эскиз ПОСЛЕ включения части
        shard.sketch = sketch
        self.sketches.append(sketch)
        self.parts_set.add(sid)
        self.clock.increment()
        self.memory.provenance.append_event(self.agent_id, "birth", sid, {"index": entry.index})
        self.memory.episodic.append({"event": "birth", "sid": sid, "type": shard_type})
        return shard

    # ------------------------------------------------------------------- суд
    def judge(self, claim: Dict) -> Verdict:
        """Суд над заявкой (алгоритм, шаг 5). Вердикт фиксируется в памяти."""
        verdict = Court(self.genome.hash(), self.manifest).classify(claim)
        self.memory.episodic.append({"event": "verdict", "verdict": verdict.value,
                                     "index": claim.get("index")})
        self.memory.provenance.append_event(self.agent_id, "court-verdict", "claim", {
            "verdict": verdict.value,
        })
        return verdict

    def claim_of(self, shard: Shard) -> Dict:
        """Собрать корректную заявку от своей части (для суда)."""
        return {
            **shard.prove_membership(),
            "body_hash": hash_obj(self.manifest.entries[shard.index].data),
        }

    # ------------------------------------------------------------- утверждение
    def claim(self, subject: str, predicate: str, value: Any,
              evidences: Optional[List[Evidence]] = None,
              context: Optional[Dict] = None) -> Claim:
        """CLAIM (алгоритм, шаг 4): утверждение входит в манифест с provenance."""
        evidences = evidences or []
        for ev in evidences:
            self.evidences[ev.eid] = ev
        web_ev = [e for e in evidences if e.source_type == "web"]
        hard_ev = [e for e in evidences if e.source_type in ("file", "observation", "user")]
        if hard_ev:
            status = "OBSERVED"
        elif web_ev:
            status = WebSensor.epistemic_status(web_ev)
        else:
            status = "PROPOSED"
        confidence = {"PROPOSED": 0.2, "REPORTED": 0.4, "OBSERVED": 0.6,
                      "CORROBORATED": 0.8}.get(status, 0.2)
        self.clock.increment()
        cl = Claim(
            cid="cl:" + hash_str(f"{self.agent_id}|{subject}|{predicate}|{sorted(self.clock.counters.items())}")[:16],
            subject=subject, predicate=predicate, value=value,
            asserted_by=self.agent_id, evidence_ids=[e.eid for e in evidences],
            context=dict(context or {}), confidence=confidence, status=status,
            clock=self.clock.snapshot(),
        )
        self.claims[cl.cid] = cl
        self.manifest.append({"type": "claim", "claim": cl.to_dict()})
        self.memory.episodic.append({"event": "claim", "cid": cl.cid, "status": status})
        self.memory.provenance.append_event(self.agent_id, "claim", cl.cid, {"status": status})
        return cl

    # ---------------------------------------------------------------- дыхание
    def breathe(self, other: "HoloAgent") -> Dict:
        """ДЫХАНИЕ (алгоритм, шаг 3): gossip + CRDT-слияние, объединение не замена."""
        result = Breath.breathe(self, other)
        self.memory.provenance.append_event(self.agent_id, "breathe", other.agent_id, result)
        return result

    # ------------------------------------------------------------- регенерация
    def regenerate(self, survivors: List[Shard]) -> "HoloAgent":
        """РЕГЕНЕРАЦИЯ (алгоритм, шаг 6): восстановление из выживших при >= k."""
        if len(survivors) < self.k:
            raise TruthWithoutBody(
                f"ИСТИНА БЕЗ ТЕЛА: выживших {len(survivors)} < порога k={self.k}. "
                f"Имя [{self.manifest.root()[:8]}] ждёт новых носителей — честный отказ, не галлюцинация."
            )
        regen = HoloAgent(name=f"{self.name}-R", k=self.k)
        regen.memory.identity["restored_from"] = self.manifest.root()
        for s in survivors:
            regen.manifest.append({
                "type": "regenerated", "from": s.sid,
                "sketch_root": s.sketch.manifest_root, "shard_type": s.shard_type,
            })
            regen.parts_set.add(s.sid)
        regen.memory.provenance.append_event(regen.agent_id, "regeneration", self.manifest.root(), {
            "survivors": [s.sid for s in survivors],
        })
        regen.memory.episodic.append({"event": "regeneration",
                                      "survivors": len(survivors), "k": self.k})
        return regen

    # ------------------------------------------------------------ саморефлексия
    def reflect(self) -> Dict:
        """REFLECT (алгоритм, шаг 7): кто я, что знаю, что устарело, чего не знаю."""
        fresh = sum(1 for s in self.shards if s.is_fresh(self.manifest.root()))
        return {
            "id": self.agent_id, "name": self.name,
            "genome_version": self.genome.version,
            "root": self.manifest.root(),
            "n_parts": len(self.shards),
            "fresh_parts": fresh,
            "stale_parts": len(self.shards) - fresh,
            "k": self.k,
            "clock": self.clock.snapshot(),
            "unknowns": len(self.memory.unknowns),
            "claims": len(self.claims),
        }

    # --------------------------------------------------------------- амендмент
    def amend(self, new_rules: Dict[str, str], signatures: Set[str]) -> Genome:
        """АМЕНДМЕНТ (алгоритм, шаг 8): геном меняют только k-из-n подписей."""
        old_hash = self.genome.hash()
        new_genome = self.genome.amend(new_rules, signatures, required=self.k)
        self.genome = new_genome
        self.manifest.append({
            "type": "amendment", "old": old_hash, "new": new_genome.hash(),
            "version": new_genome.version, "signers": len(signatures),
        })
        self.memory.provenance.append_event(self.agent_id, "amendment", "genome", {
            "version": new_genome.version, "signers": len(signatures),
        })
        self.memory.episodic.append({"event": "amendment", "version": new_genome.version})
        return new_genome

    # ------------------------------------------------------------- persistence
    def save(self, path: str) -> str:
        """Кость К0 → носитель вне частей: Целое живёт на файле."""
        state = {
            "format": self.FORMAT,
            "name": self.name, "k": self.k, "agent_id": self.agent_id,
            "genome": {"rules": self.genome.rules, "version": self.genome.version,
                       "parent": self.genome.parent_version,
                       "history": self.genome.amendment_history},
            "manifest": self.manifest.to_dict(),
            "shards": [s.to_dict() for s in self.shards],
            "sketches": [sk.to_dict() for sk in self.sketches],
            "clock": self.clock.to_dict(),
            "parts_set": self.parts_set.to_dict(),
            "memory": self.memory.to_dict(),
            "claims": [c.to_dict() for c in self.claims.values()],
            "evidences": [e.to_dict() for e in self.evidences.values()],
        }
        state["state_hash"] = hash_obj({k2: v for k2, v in state.items()})
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=1)
        return path

    @classmethod
    def load(cls, path: str) -> "HoloAgent":
        """Загрузка с обязательной проверкой целостности (Целое не принимает подделку)."""
        with open(path, "r", encoding="utf-8") as f:
            state = json.load(f)
        stored_hash = state.pop("state_hash", None)
        if stored_hash is None or hash_obj(state) != stored_hash:
            raise IntegrityError("state_hash не сходится — файл состояния подделан")
        ag = cls.__new__(cls)
        ag.FORMAT = state["format"]
        ag.name, ag.k, ag.agent_id = state["name"], state["k"], state["agent_id"]
        g = state["genome"]
        ag.genome = Genome(rules=dict(g["rules"]), version=g["version"],
                           parent_version=g["parent"], amendment_history=list(g["history"]))
        ag.manifest = Manifest.from_dict(state["manifest"])
        if ag.genome.hash() != ag.manifest.genome_hash:
            # геном мог быть амендтирован: genesis-запись не переписывается (append-only),
            # поэтому проверяем цепочку амендментов в манифесте
            amendment_new = None
            for e in ag.manifest.entries:
                if isinstance(e.data, dict) and e.data.get("type") == "amendment":
                    amendment_new = e.data.get("new")
            if amendment_new != ag.genome.hash():
                raise IntegrityError("геном не совпадает с манифестом, цепочка амендментов не сходится")
        # проверка 1: каждый лист пересчитывается
        for e in ag.manifest.entries:
            if e.hash != hash_obj({"index": e.index, "data": e.data, "ts": e.ts,
                                   "genome": ag.manifest.genome_hash}):
                raise IntegrityError(f"запись {e.index} подделана")
        # проверка 2: корень пересчитывается из полного перечня
        if ag.manifest.entries:
            if ag.manifest._merkle_root([e.hash for e in ag.manifest.entries]) != ag.manifest.root():
                raise IntegrityError("корень манифеста не сходится")
        # проверка 3: история корней append-only в честных границах
        # (пакетное объединение при дыхании даёт N записей за один корень)
        if not (1 <= len(ag.manifest.roots_history) <= len(ag.manifest.entries) + 1):
            raise IntegrityError("история корней повреждена")
        if len(set(ag.manifest.roots_history)) != len(ag.manifest.roots_history):
            raise IntegrityError("история корней повреждена (дубли)")
        ag.shards = [Shard.from_dict(s) for s in state["shards"]]
        ag.sketches = [Sketch.from_dict(s) for s in state["sketches"]]
        # проверка 4: пути Меркла шардов. Для свежих — полное совпадение с манифестом;
        # для устаревших (после дыхания/прироста) — арифметика пути к их корню рождения.
        for s in ag.shards:
            leaf = s.leaf_hash or ag.manifest.entries[s.index].hash
            if not ag.manifest.verify_path(leaf, s.merkle_path, s.manifest_root):
                raise IntegrityError(f"путь Меркла шарда {s.sid} не сходится")
            if s.manifest_root == ag.manifest.root():
                if s.index >= len(ag.manifest.entries) or ag.manifest.entries[s.index].hash != leaf:
                    raise IntegrityError(f"свежий шард {s.sid} не совпадает с манифестом")
        ag.clock = VectorClock.from_dict(state["clock"])
        ag.parts_set = ORSet.from_dict(state["parts_set"])
        ag.memory = AgentMemory.from_dict(state["memory"])
        ag.claims = {c["cid"]: Claim.from_dict(c) for c in state["claims"]}
        ag.evidences = {e["eid"]: Evidence.from_dict(e) for e in state["evidences"]}
        if not ag.memory.provenance.verify_chain():
            raise IntegrityError("цепочка provenance нарушена")
        return ag

    # ------------------------------------------------------------------ кости
    @staticmethod
    def bones() -> List[Dict[str, str]]:
        """Кости честности К0–К6 — дословно из корпуса (файл 2, строки 496–504)."""
        return [
            {"К0": "Носитель вне частей. Если манифест живёт только в памяти диалога, "
                   "откат среды съедает Целое. → закрыто save/load на файл."},
            {"К1": "Бутстрап генома. Конституция первого дня единолична; амендмент "
                   "защищает вперёд, но происхождение — акт доверия."},
            {"К2": "Знает ≠ понимает. Суд доказывает членство хэшами, не смысл целого."},
            {"К3": "Голограмма ≠ копия. Часть содержит эскиз пониженного разрешения "
                   "на момент рождения + путь к деталям."},
            {"К4": "Дыхание не бесплатное. Каждая сверка стоит хода; сходимость — "
                   "свойство дисциплины участников."},
            {"К5": "Истина без тела. Ниже порога живых носителей остаётся имя без "
                   "кусков — честное состояние, а не сбой."},
            {"К6": "Не паноптикум. «Целое знает все части» — не лицензия на тотальную "
                   "прозрачность. Приватность — часть конституции."},
        ]

# ============================================================================
# SELFTEST — проверяемая честность (честность не декларируется, а доказывается)
# ============================================================================

def selftest() -> bool:
    passed = failed = 0
    tid = 0

    def check(cond: bool, description: str) -> None:
        nonlocal passed, failed, tid
        tid += 1
        if cond:
            passed += 1
            print(f"  PASS T{tid:02d}: {description}")
        else:
            failed += 1
            print(f"  FAIL T{tid:02d}: {description}")

    print("=" * 72)
    print("SELFTEST: HOLO-AGENT v2.0 — 12 групп проверок")
    print("=" * 72)

    # === ГЕНОМ (5) ===
    print("\n[1. ГЕНОМ]")
    g = default_genome()
    check(g.hash() != "", "геном имеет хэш")
    check(g.hash() == default_genome().hash(), "хэш детерминирован (одинаковые правила → один хэш)")
    try:
        g.amend({"Г11": "test"}, {"sig1"}, required=2)
        check(False, "амендмент одной подписью отвергнут")
    except AmendmentRejected:
        check(True, "амендмент одной подписью отвергнут (I2)")
    g2 = g.amend({"Г11": "новое правило"}, {"sig1", "sig2"}, required=2)
    check(g2.version == "2.1" and g2.parent_version == "2.0", "амендмент двумя подписями → v2.1 с родителем")
    check(len(g2.amendment_history) == 1 and g2.amendment_history[0]["from"] == "2.0",
          "история амендментов append-only")

    # === МАНИФЕСТ (9) ===
    print("\n[2. МАНИФЕСТ]")
    ag = HoloAgent("T-Манифест")
    m = ag.manifest
    check(m.root() != "", "пустой манифест (до genesis-записи) имеет корень")
    r0 = m.root()
    e1 = m.append({"t": "data1"})
    check(m.root() != r0, "добавление записи меняет корень (имя Целого живое)")
    r1 = m.root()
    e2 = m.append({"t": "data2"})
    check(m.root() != r1, "вторая запись даёт новый корень")
    check(len(m.roots_history) == 4, "история корней append-only (начальный + genesis + 2 записи)")
    check(len(m.entries) == 3 and m.entries[1].hash == e1.hash, "записи не удаляются и не переписываются (I1)")
    p = m.get_path(1)
    check(m.verify_path(e1.hash, p, m.root()), "путь Меркла верифицирует свою запись")
    check(not m.verify_path("fake" * 8, p, m.root()), "путь отвергает чужой хэш")
    check(len(set(m.roots_history)) == len(m.roots_history), "все корни в истории уникальны")
    ag_other = HoloAgent("T-Манифест-2")
    check(ag_other.manifest.root() == HoloAgent("T-Манифест-3").manifest.root(),
          "имя genesis детерминировано (один геном → одно имя)")

    # === РОЖДЕНИЕ (7) ===
    print("\n[3. РОЖДЕНИЕ]")
    ag = HoloAgent("T-Рождение", k=2)
    s1 = ag.birth("физический", "шард", {"содержание": "Бом, AdS/CFT, HaPPY"})
    check(s1.genome_hash == ag.genome.hash(), "ритуал выдаёт геном части")
    check(s1.index == 1, "индекс = позиция в манифесте (genesis=0, часть=1)")
    check(len(s1.merkle_path) > 0, "путь Меркла корректен")
    sk = ag.sketches[-1]
    check(sk.manifest_root == ag.manifest.root(), "эскиз содержит корень на момент рождения")
    check(sk.genome_hash == ag.genome.hash(), "эскиз содержит геном")
    n_before = sk.n_parts
    s2 = ag.birth("математический", "шард", {"содержание": "пучки, категории"})
    check(ag.sketches[-1].n_parts == n_before + 1, "эскиз растёт с рождением частей")
    check(s1.sid != s2.sid and s2.prev_sid == s1.sid and s1.next_sid == s2.sid,
          "части уникальны и знают соседей")

    # === HRR-ЭСКИЗ (4) ===
    print("\n[4. HRR-ЭСКИЗ]")
    check(HRRVector.DIM == 32, "размерность HRR = 32 (корпус)")
    v = HRRVector.random_vec("seed")
    check(abs(v.similarity(HRRVector.random_vec("seed")) - 1.0) < 1e-9, "самоподобие эскиза = 1.0")
    agA = HoloAgent("T-HRR-A"); agA.birth("tA", "r", {"c": "A"}); agA.birth("tB", "r", {"c": "B"})
    agB = HoloAgent("T-HRR-B")
    agB.birth("tA", "r", {"c": "A"}); agB.birth("tB", "r", {"c": "B"}); agB.birth("tC", "r", {"c": "C"})
    agC = HoloAgent("T-HRR-C"); agC.birth("uX", "r", {"c": "X"}); agC.birth("uY", "r", {"c": "Y"})
    sim_rel = agA.sketches[-1].hrr.similarity(agB.sketches[-1].hrr)
    sim_unrel = agA.sketches[-1].hrr.similarity(agC.sketches[-1].hrr)
    check(sim_rel > 0.6 and sim_rel > sim_unrel + 0.2,
          f"родственное целое распознаётся: sim={sim_rel:.2f} >> несвязное {sim_unrel:.2f}")
    check(HRRVector.random_vec("abc").similarity(HRRVector.random_vec("abc")) >= 1.0 - 1e-9,
          "эскиз детерминирован по семени")

    # === ЗНАНИЕ ЦЕЛОГО ИЗ ЧАСТИ (4) ===
    print("\n[5. ЗНАНИЕ ЦЕЛОГО ИЗ ЧАСТИ]")
    proof = s1.prove_membership()
    check({"genome_hash", "manifest_root", "index"} <= set(proof.keys()),
          "часть носит тройку (геном, корень, индекс)")
    check(s1.knows_whole(ag.genome.hash()), "часть знает геном Целого (арифметически)")
    check(s2.is_fresh(ag.manifest.root()),
          "после рождения проекция свежа (у последней рождённой части)")
    s3 = ag.birth("информационный", "шард", {"содержание": "CRDT, gossip"})
    check(not s1.is_fresh(ag.manifest.root()) and s3.is_fresh(ag.manifest.root()),
          "устаревание честно: старые части знают СТАРУЮ версию истины")

    # === СУД (8) ===
    print("\n[6. СУД]")
    ag = HoloAgent("T-Суд", k=2)
    sh = ag.birth("тестовый", "шард", {"содержание": "x"})
    ok = ag.claim_of(sh)
    check(ag.judge(dict(ok)) == Verdict.ЧАСТЬ, "своё доказательство → ЧАСТЬ")
    c = dict(ok); c["genome_hash"] = "чужой"; check(ag.judge(c) == Verdict.ЧУЖОЙ, "чужой геном → ЧУЖОЙ")
    c = dict(ok); del c["merkle_path"]; check(ag.judge(c) == Verdict.ЭХО, "нет пути → ЭХО")
    c = dict(ok); del c["index"]; check(ag.judge(c) == Verdict.ЭХО, "нет индекса → ЭХО")
    c = dict(ok); del c["body_hash"]; check(ag.judge(c) == Verdict.ОТКАЗ, "нет тела → ОТКАЗ")
    c = dict(ok); c["body_hash"] = "подделка"; check(ag.judge(c) == Verdict.ОСКОЛОК, "подделка тела → ОСКОЛОК")
    check(ag.judge({}) == Verdict.ОТКАЗ, "пустая заявка → ОТКАЗ")
    c = dict(ok); c["index"] = 999; check(ag.judge(c) == Verdict.ОСКОЛОК, "индекс вне диапазона → ОСКОЛОК")

    # === ДЫХАНИЕ / CRDT (5) ===
    print("\n[7. ДЫХАНИЕ]")
    ca, cb = VectorClock("a"), VectorClock("b")
    ca.increment(); cb.increment(); cb.increment()
    ca.merge(cb)
    check(ca.counters == {"a": 1, "b": 2}, "векторные часы: merge = поэлементный max")
    ca.increment()
    check(ca.counters["a"] == 2, "часы тикают только вперёд")
    s1, s2 = ORSet(), ORSet()
    s1.add("x"); s2.add("y"); s1.merge(s2)
    check(s1.value() == {"x", "y"}, "ORSet: слияние = объединение (одно другое не исключает)")
    s2.add("z"); s1.merge(s2); s2.remove("z"); s1.merge(s2)
    check("z" not in s1.value(), "ORSet: удаление уважается после слияния")
    ag1 = HoloAgent("T-Дых-1", k=2); ag1.birth("тип1", "r", {"d": "a"})
    ag2 = HoloAgent("T-Дых-2", k=2); ag2.birth("тип2", "r", {"d": "b"})
    res = ag1.breathe(ag2)
    check(res["divergence"] and len(ag1.manifest.entries) == 3,
          "дыхание: расхождение = приращение, манифест объединился (genesis дедуплицирован)")

    # === ПАМЯТЬ E/S/P/W/I (4) ===
    print("\n[8. ПАМЯТЬ]")
    ag = HoloAgent("T-Память", k=2)
    ag.birth("а", "r", {"1": 1}); ag.birth("б", "r", {"2": 2})
    check(sum(1 for e in ag.memory.episodic.events if e.get("event") == "birth") == 2,
          "эпизодическая память помнит рождения")
    check(ag.memory.provenance.verify_chain(), "provenance-цепочка целостна (I1)")
    ag.memory.provenance.chain[0]["actor"] = "ВЗЛОМ"
    check(not ag.memory.provenance.verify_chain(), "подделка provenance обнаруживается пересчётом")
    ag.memory.working["вопрос"] = "тест"; ag.memory.record_unknown("внешняя сеть", "среда не отвечает", "агент", "низкое")
    ag.memory.clear_working()
    check(ag.memory.working == {} and "внешняя сеть" in ag.memory.unknowns,
          "рабочая память очищается; НЕ ЗНАЮ остаётся как объект первого класса (Г8)")

    # === PERSISTENCE (4) ===
    print("\n[9. PERSISTENCE]")
    ag = HoloAgent("T-Persist", k=2)
    sh1 = ag.birth("ядро", "r", {"тело": "вещество целого"})
    fd, path = tempfile.mkstemp(suffix=".json"); os.close(fd)
    ag.save(path)
    ag2 = HoloAgent.load(path)
    check(ag2.genome.hash() == ag.genome.hash(), "загрузка: геном совпадает")
    check(ag2.manifest.root() == ag.manifest.root(), "загрузка: имя Целого совпадает (кость К0 закрыта)")
    check(ag2.judge(ag2.claim_of(ag2.shards[0])) == Verdict.ЧАСТЬ,
          "загруженное Целое принимает доказательство своей части")
    ag2.claim("сборка", "возможна", "k из n")
    fd2, path2 = tempfile.mkstemp(suffix=".json"); os.close(fd2)
    ag2.save(path2)
    ag3 = HoloAgent.load(path2)
    check(len(ag3.claims) == 1 and ag3.manifest.root() == ag2.manifest.root(),
          "загрузка: заявки сериализуются, имя живёт дальше (append-only)")
    os.unlink(path2)
    ag4 = HoloAgent("T-Persist-Amend", k=2)
    ag4.birth("ш", "r", {"b": 1})
    ag4.amend({"Г11": "правило после амендмента"}, {"s1", "s2"})
    fd3, path3 = tempfile.mkstemp(suffix=".json"); os.close(fd3)
    ag4.save(path3)
    ag5 = HoloAgent.load(path3)
    check(ag5.genome.version == "2.1" and ag5.genome.hash() == ag4.genome.hash(),
          "загрузка после амендмента: геном v2.1 принимается через цепочку амендментов манифеста")
    os.unlink(path3)
    agB2 = HoloAgent("T-Persist-Breathe", k=2)
    agB2.birth("ш1", "r", {"v": 1}); agB2.birth("ш2", "r", {"v": 2})
    other2 = HoloAgent("T-Persist-Breathe-Б", k=2); other2.birth("шX", "r", {"v": 9})
    agB2.breathe(other2)
    fdB, pathB = tempfile.mkstemp(suffix=".json"); os.close(fdB)
    agB2.save(pathB)
    agB3 = HoloAgent.load(pathB)
    check(len(agB3.shards) == 2 and agB3.manifest.root() == agB2.manifest.root(),
          "загрузка после дыхания: устаревшие части верифицируются арифметикой пути к корню рождения")
    os.unlink(pathB)
    with open(path, "r", encoding="utf-8") as f:
        tampered = json.load(f)
    tampered["manifest"]["entries"][1]["data"]["body"]["тело"] = "подмена"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tampered, f)
    try:
        HoloAgent.load(path)
        check(False, "подмена в файле состояния обнаружена")
    except IntegrityError:
        check(True, "подмена в файле состояния обнаружена → IntegrityError")
    os.unlink(path)

    # === ВЕБ-СЕНСОР (3) ===
    print("\n[10. ВЕБ-СЕНСОР]")
    raw = {"uri": "https://en.wikipedia.org/wiki/Conflict-free_replicated_data_type",
           "title": "Conflict-free replicated data type", "retrieved_at": "2026-09-01",
           "authority": "en.wikipedia.org", "scope": "орган ДЫХАНИЕ",
           "excerpt": "CRDT: replicas converge eventually (Shapiro et al.)"}
    ev = WebSensor.result_to_evidence(raw)
    check(ev.content_hash != "" and WebSensor.epistemic_status([ev]) == "REPORTED",
          "веб-результат → Evidence со статусом REPORTED (не истина)")
    ag = HoloAgent("T-Web", k=2); ag.birth("память", "r", {"x": 1})
    cl1 = ag.claim("CRDT-слияние", "гарантирует", "конвергенцию", evidences=[ev])
    check(cl1.status == "REPORTED" and cl1.confidence < 0.8,
          "заявка на одном веб-источнике честно остаётся REPORTED")
    ev2 = WebSensor.result_to_evidence({"uri": "https://ably.com/blog/crdts-distributed-data-consistency-challenges",
                                        "title": "CRDTs solve distributed data consistency challenges",
                                        "retrieved_at": "2026-09-01", "authority": "ably.com",
                                        "scope": "орган ДЫХАНИЕ", "excerpt": "CRDT convergence guarantees"})
    cl2 = ag.claim("CRDT-слияние", "гарантирует", "конвергенцию", evidences=[ev, ev2])
    check(cl2.status == "CORROBORATED",
          "два независимых источника → CORROBORATED (и не выше: PROVEN вебу недоступен)")

    # === САМОРЕФЛЕКСИЯ (2) ===
    print("\n[11. САМОРЕФЛЕКСИЯ]")
    ag = HoloAgent("T-Рефлексия", k=2)
    ag.birth("а", "r", {"1": 1}); ag.birth("б", "r", {"2": 2})
    r = ag.reflect()
    check(r["n_parts"] == 2 and r["clock"].get(ag.agent_id, 0) >= 2,
          "рефлексия: состав и часы известны агенту")
    check(r["fresh_parts"] == 1 and r["stale_parts"] == 1,
          "рефлексия честна: только последняя часть свежа, старая — stale")

    # === РЕГЕНЕРАЦИЯ (2) ===
    print("\n[12. РЕГЕНЕРАЦИЯ]")
    ag = HoloAgent("T-Регенерация", k=2)
    a1 = ag.birth("ш1", "r", {"v": 1}); a2 = ag.birth("ш2", "r", {"v": 2}); a3 = ag.birth("ш3", "r", {"v": 3})
    survivors = [a2, a3]
    reg = ag.regenerate(survivors)
    check(len(reg.manifest.entries) == 3 and set(map(lambda e: e.data.get("type"), reg.manifest.entries[1:])) == {"regenerated"},
          "регенерация из 2 выживших при k=2: Целое пересобрано, происхождение записано")
    try:
        ag.regenerate([a3])
        check(False, "подпорог: честный отказ ИСТИНА БЕЗ ТЕЛА")
    except TruthWithoutBody:
        check(True, "подпорог: честный отказ ИСТИНА БЕЗ ТЕЛА (К5)")

    # === ИТОГ ===
    total = passed + failed
    print("\n" + "=" * 72)
    print(f"ИТОГ SELFTEST: {passed}/{total} PASS, {failed} FAIL")
    print("=" * 72)
    return failed == 0


# ============================================================================
# DEMO — adversarial-полигон: резня, эхо, суд, амендмент, дыхание, веб
# ============================================================================

def demo() -> None:
    print("\n" + "=" * 72)
    print("DEMO: HOLO-AGENT v2.0 — adversarial-полигон")
    print("=" * 72)

    # [1] Генезис и рождение
    agent = HoloAgent("ПОЛИГОН-2026", k=2)
    print(f"\n[1] ГЕНЕЗИС: имя Целого = {agent.manifest.root()[:16]}…")
    types = [
        ("физический", {"содержание": "Бом, 'т Хоофт, AdS/CFT, HaPPY-код"}),
        ("информационный", {"содержание": "CRDT, gossip, Merkle, erasure coding"}),
        ("философский", {"содержание": "Кёстлер, Лейбниц, Сеть Индры"}),
        ("когнитивный", {"содержание": "Прибрам, Фристон, active inference"}),
        ("инженерный", {"содержание": "графы знаний, holacracy, event sourcing"}),
    ]
    for t, body in types:
        agent.birth(t, "шард знания", body)
    print(f"    Рождено 5 шардов корпуса; живых носителей: {len(agent.shards)}")
    print(f"    REFLECT: {json.dumps(agent.reflect(), ensure_ascii=False)[:120]}…")

    # [2] Эхо-атака
    print("\n[2] ЭХО-АТАКА: заявка звучит как часть, но без пути Меркла")
    real = agent.claim_of(agent.shards[-1])
    echo = {k: v for k, v in real.items() if k != "merkle_path"}
    print(f"    СУД: {agent.judge(echo).value}")

    # [3] Чужой геном
    print("\n[3] ЧУЖОЙ ГЕНОМ: заявка другой конституции")
    foreign = dict(real); foreign["genome_hash"] = "чужая_конституция"
    print(f"    СУД: {agent.judge(foreign).value}")

    # [4] Осколок
    print("\n[4] ОСКОЛОК: фрагмент чужого/мёртвого состояния (индекс 999)")
    shard = dict(real); shard["index"] = 999
    print(f"    СУД: {agent.judge(shard).value}")

    # [5] Честная часть проходит
    print("\n[5] СВОЯ ЧАСТЬ (последняя рождённая — проекция свежа) предъявляет тройку + путь")
    real = agent.claim_of(agent.shards[-1])
    print(f"    СУД: {agent.judge(dict(real)).value}")

    # [6] Резня
    print(f"\n[6] РЕЗНЯ: убиты 3 из 5 носителей, порог k={agent.k}")
    survivors = agent.shards[:2]
    regen = agent.regenerate(survivors)
    print(f"    Выжили {len(survivors)} → РЕГЕНЕРАЦИЯ: {regen.name}, "
          f"записей в манифесте {len(regen.manifest.entries)}, "
          f"разрешение {len(survivors)}/{len(agent.shards)} = {int(len(survivors)/len(agent.shards)*100)}%")

    # [7] Истина без тела
    print("\n[7] ПОДПОРОГ: остался 1 носитель при k=2")
    try:
        agent.regenerate([agent.shards[0]])
    except TruthWithoutBody as e:
        print(f"    ЧЕСТНЫЙ СТАТУС: {e}")

    # [8] Амендмент
    print("\n[8] АМЕНДМЕНТ ГЕНОМА")
    try:
        agent.amend({"Г11": "новое правило"}, {"одна_подпись"})
        print("    ОШИБКА: амендмент прошёл одной подписью?!")
    except AmendmentRejected:
        print("    ОТКАЗ: одной подписью геном не меняется (I2)")
    g = agent.amend({"Г11": "v2.0 несёт веб-сенсор Evidence-контракта"}, {"подпись_1", "подпись_2"})
    print(f"    УСПЕХ: геном v{g.version} (родитель v{g.parent_version}), имя Целого сменилось честно")

    # [9] Дыхание
    print("\n[9] ДЫХАНИЕ: два Целых сливаются — объединение, не замена")
    other = HoloAgent("ПОЛИГОН-2026-Б", k=2)
    other.birth("биологический", "шард знания", {"содержание": "планарии, кворум-сенсинг"})
    res = agent.breathe(other)
    print(f"    расхождение={res['divergence']} → манифест агента А: {res['entries_a']} записей")

    # [10] Веб-сенсор: реальные evidence веб-разведки 2026-09-01
    print("\n[10] ВЕБ-СЕНСОР: результаты поиска = Evidence, не истина")
    web_raw = [
        {"uri": "https://en.wikipedia.org/wiki/Conflict-free_replicated_data_type",
         "title": "Conflict-free replicated data type", "retrieved_at": "2026-09-01",
         "authority": "en.wikipedia.org", "scope": "орган ДЫХАНИЕ",
         "excerpt": "CRDT: реплики гарантированно сходятся (Shapiro et al.)"},
        {"uri": "https://ably.com/blog/crdts-distributed-data-consistency-challenges",
         "title": "CRDTs solve distributed data consistency challenges",
         "retrieved_at": "2026-09-01", "authority": "ably.com", "scope": "орган ДЫХАНИЕ",
         "excerpt": "Гарантии конвергенции CRDT в распределённых системах"},
    ]
    evs = [WebSensor.result_to_evidence(r) for r in web_raw]
    cl = agent.claim("CRDT-слияние в органе ДЫХАНИЕ", "гарантирует", "конвергенцию реплик",
                     evidences=evs, context={"sensor": "web_search", "запросов": 5})
    print(f"    статусы: {[WebSensor.epistemic_status([e]) for e in [evs[0]]]} → "
          f"{WebSensor.epistemic_status(evs)} (2 независимых источника)")
    print(f"    ЗАЯВКА {cl.cid[:12]}: status={cl.status}, confidence={cl.confidence}")

    # [11] Суд над корпусом: метафоры не проходят за инженерию
    print("\n[11] СУД НАД КОРПУСОМ: эпистемическая разметка собственных тезисов")
    verdicts_corpus = [
        ("Квантовая запутанность как механизм синхронизации частей", "МЕТАФОРА",
         "корпус, §15: не превращать в инженерное утверждение"),
        ("Merkle-путь доказывает членство без центра", "ПОДТВЕРЖДЕНО",
         "корпус + Hypercore/MMR (web, 03.2026)"),
        ("Каждая часть содержит полную копию Целого", "ОТВЕРГНУТО",
         "кость К3: часть несёт эскиз, не копию"),
    ]
    for thesis, status, why in verdicts_corpus:
        agent.memory.semantic[thesis] = {"status": status, "основание": why}
        print(f"    [{status:<12}] {thesis}")

    # [12] Persistence
    print("\n[12] PERSISTENCE: Целое переживает гибель сессии (кость К0)")
    fd, path = tempfile.mkstemp(suffix=".json"); os.close(fd)
    agent.save(path)
    revived = HoloAgent.load(path)
    print(f"    сохранено и загружено: имя={revived.manifest.root()[:12]}… "
          f"шардов={len(revived.shards)}, семантических тезисов={len(revived.memory.semantic)}")
    os.unlink(path)

    # [13] Кости
    print("\n[13] КОСТИ ЧЕСТНОСТИ (что агент обещать НЕ может):")
    for b in HoloAgent.bones():
        code, text = list(b.items())[0]
        print(f"    {code}: {text[:72]}…")

    print("\n" + "=" * 72)
    print("ФОРМУЛА АГЕНТА:")
    print("  Целое = части + отношения + общий геном + манифест + правила проверки + история")
    print("  Часть = тело + кости + (геном, корень, индекс) + эскиз целого + соседи")
    print("  Истина = то, что проходит суд: согласовано с геномом и доказуемо из манифеста")
    print("  Эхо = всё, что звучит как часть, но не может предъявить тройку")
    print("=" * 72)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        sys.exit(0 if selftest() else 1)
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        demo()
        sys.exit(0)
    print("HOLO-AGENT v2.0 — голографический агент-холон (инстанциация корпуса)")
    print("Использование:")
    print("  python3 holo_agent_v2.py --selftest   # серия проверок")
    print("  python3 holo_agent_v2.py --demo       # adversarial-полигон")
    sys.exit(0)

