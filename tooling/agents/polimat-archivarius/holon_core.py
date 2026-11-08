# -*- coding: utf-8 -*-
"""
holon_core.py — геномное ядро агента «ПОЛИМАТ-АРХИВАРИУС».

Здесь живут плоскости голографической архитектуры (см. КОНСТИТУЦИЯ_ХОЛОНА.md):
  L0. Геномная    — корпус -> части (чанки) -> Merkle DAG -> genome_root.
                    Корневой хеш = «ДНК» Целого.
  L2. Состояния   — retrieval-индекс: локальная проекция целого,
                    по которой агент находит нужные части.
  L3. Истины      — Merkle-доказательства: путь от любой части до корня.
                    Часть может доказать кому угодно, что она часть Целого.
  L5. Регенерации — erasure-код Рида–Соломона (k-из-n): любые k осколков
                    восстанавливают геном; корень при этом не меняется.

Законы, воплощённые в коде:
  1. Закон генома       — каждая часть хранит ссылку на корень целого.
  2. Закон адреса       — каждая часть знает источник и строки (своё место).
  5. Закон склейки      — истина = согласованность части с корнем.
  6. Закон регенерации  — k-из-n осколков восстанавливают целое.
  7. Закон голономности — ядро рекурсивно: сам polimat.py устроен как холон.

Только стандартная библиотека. Без магии — композиция известных механизмов.
"""

import hashlib
import json
import math
import random
import re
from collections import Counter
from pathlib import Path

# ============================================================
# Хеширование (content-addressed мир)
# ============================================================

def sha(data) -> str:
    if isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()


# ============================================================
# GF(2^8) — поле Галуа для erasure-кода Рида–Соломона
# ============================================================

GF_POLY = 0x11D
_EXP = [0] * 512
_LOG = [0] * 256


def _init_gf():
    x = 1
    for i in range(255):
        _EXP[i] = x
        _LOG[x] = i
        x <<= 1
        if x & 0x100:
            x ^= GF_POLY
    for i in range(255, 512):
        _EXP[i] = _EXP[i - 255]


_init_gf()


def gf_mul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return _EXP[_LOG[a] + _LOG[b]]


def gf_inv(a: int) -> int:
    if a == 0:
        raise ZeroDivisionError('gf_inv(0)')
    return _EXP[255 - _LOG[a]]


def gf_div(a: int, b: int) -> int:
    if a == 0:
        return 0
    return gf_mul(a, gf_inv(b))


def cauchy_coef(j: int, i: int, m: int) -> int:
    """Коэффициент матрицы Коши V[j][i] = 1/(x_j ^ y_i),
    x_j = j (0..m-1), y_i = m+i. Матрица Коши гарантирует MDS:
    любые k строк кодирующей матрицы обратимы -> k-из-n."""
    x = j
    y = m + i
    if x ^ y == 0:
        raise ValueError('Cauchy: x ^ y == 0')
    return gf_div(1, x ^ y)


# ============================================================
# Erasure-кодирование: n осколков, любые k восстанавливают целое
# ============================================================

def rs_encode(data: bytes, k: int, n: int):
    """Систематический Рид–Соломон: возвращает n осколков.
    Первые k — сами данные (с дополнением), остальные m = n-k — парити."""
    m = n - k
    total = len(data)
    L = (total + k - 1) // k  # длина каждого блока
    blocks = []
    for i in range(k):
        b = data[i * L:(i + 1) * L]
        blocks.append(b + b'\x00' * (L - len(b)))
    shards = list(blocks)
    for j in range(m):
        coefs = [cauchy_coef(j, i, m) for i in range(k)]
        tables = [[gf_mul(c, v) for v in range(256)] for c in coefs]
        pj = bytearray(L)
        for i in range(k):
            tbl = tables[i]
            bi = blocks[i]
            for x in range(L):
                pj[x] ^= tbl[bi[x]]
        shards.append(bytes(pj))
    return shards, L


def rs_decode(shards_map: dict, k: int, n: int, L: int) -> bytes:
    """Восстановить данные из любых k осколков.
    shards_map: {индекс_осколка: bytes}. Гауссово исключение над GF(2^8)."""
    m = n - k
    avail = [i for i in range(n) if shards_map.get(i) is not None][:k]
    if len(avail) < k:
        raise ValueError(f'недостаточно осколков: {len(avail)} < k={k}')

    A, B = [], []
    for r in avail:
        if r < k:
            A.append([1 if c == r else 0 for c in range(k)])
        else:
            j = r - k
            A.append([cauchy_coef(j, i, m) for i in range(k)])
        B.append(shards_map[r])

    for col in range(k):
        piv = None
        for r in range(col, k):
            if A[r][col]:
                piv = r
                break
        if piv is None:
            raise ValueError('вырожденная система: матрица не MDS')
        A[col], A[piv] = A[piv], A[col]
        B[col], B[piv] = B[piv], B[col]
        inv = gf_inv(A[col][col])
        A[col] = [gf_mul(v, inv) for v in A[col]]
        B[col] = bytes(gf_mul(b, inv) for b in B[col])
        for r in range(k):
            if r != col and A[r][col]:
                f = A[r][col]
                A[r] = [a ^ gf_mul(f, ac) for a, ac in zip(A[r], A[col])]
                B[r] = bytes(b ^ gf_mul(f, bc) for b, bc in zip(B[r], B[col]))

    data = b''.join(B)
    return data


# ============================================================
# Merkle DAG: корень = «ДНК», доказательства = путь до корня
# ============================================================

def merkle_root(leaf_hashes):
    level = list(leaf_hashes)
    if not level:
        return sha('пустое-целое')
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [sha(level[i] + level[i + 1]) for i in range(0, len(level), 2)]
    return level[0]


def merkle_proof(leaf_hashes, idx):
    """Путь от листа idx до корня: список {'hash', 'side'}.
    side = 'L' — сосед слева (хеш идёт первым), 'R' — сосед справа."""
    level = list(leaf_hashes)
    proof = []
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        sib = idx ^ 1
        side = 'L' if sib < idx else 'R'
        proof.append({'hash': level[sib], 'side': side})
        level = [sha(level[i] + level[i + 1]) for i in range(0, len(level), 2)]
        idx //= 2
    return proof


def merkle_verify(leaf_hash: str, proof, root: str) -> bool:
    h = leaf_hash
    for step in proof:
        h = sha(h + step['hash']) if step['side'] == 'R' else sha(step['hash'] + h)
    return h == root


# ============================================================
# Чанкинг: корпус -> части (закон адреса: источник + строки)
# ============================================================

_SENT_SPLIT = re.compile(r'(?<=[.!?…»])\s+')


def _paragraphs(lines):
    """Абзацы с номерами строк: [(начало, конец, текст)] (1-based)."""
    paras, cur, start = [], [], None
    for idx, line in enumerate(lines, 1):
        if line.strip():
            if not cur:
                start = idx
            cur.append(line)
        else:
            if cur:
                paras.append((start, idx - 1, '\n'.join(cur)))
                cur = []
    if cur:
        paras.append((start, len(lines), '\n'.join(cur)))
    return paras


def _split_big(text, max_len):
    if len(text) <= max_len:
        return [text]
    out, buf = [], ''
    for s in _SENT_SPLIT.split(text):
        if buf and len(buf) + len(s) + 1 > max_len:
            out.append(buf)
            buf = s
        else:
            buf = (buf + ' ' + s) if buf else s
    if buf:
        out.append(buf)
    return out


def chunk_text(text: str, source: str, target=1000, max_len=1800, seen=None):
    """Разрезать корпус на части: абзацы склеиваются до ~target,
    слишком длинные абзацы режутся по предложениям.
    Каждая часть получает id = хеш содержимого (content-addressed).
    seen — общий реестр адресов на ВЕСЬ корпус: одинаковые абзацы в разных
    файлах получают разные адреса (закон адреса: адрес уникален)."""
    if seen is None:
        seen = {}
    pieces = []
    for a, b, t in _paragraphs(text.split('\n')):
        for piece in _split_big(t, max_len):
            pieces.append([a, b, piece])

    raw = []
    buf_txt, buf_a, buf_b = '', None, None
    for a, b, t in pieces:
        if buf_txt and len(buf_txt) + len(t) + 1 > target:
            raw.append({'text': buf_txt, 'lines': [buf_a, buf_b]})
            buf_txt, buf_a, buf_b = '', None, None
        if not buf_txt:
            buf_a = a
        buf_txt = (buf_txt + '\n' + t) if buf_txt else t
        buf_b = b
    if buf_txt:
        raw.append({'text': buf_txt, 'lines': [buf_a, buf_b]})

    chunks = []
    for c in raw:
        cid = sha(c['text'])[:12]
        if cid in seen:
            seen[cid] += 1
            cid = cid[:10] + f'{seen[cid]:02x}'
        else:
            seen[cid] = 0
        chunks.append({
            'id': cid,
            'text': c['text'],
            'source': source,
            'lines': c['lines'],
        })
    return chunks


# ============================================================
# Токены и лёгкий стеммер (проекция текста в термы)
# ============================================================

_RU_SUFFIXES = [
    'ирования', 'ированию', 'ированием', 'ироваться', 'ированиями',
    'остями', 'ственности', 'ательств', 'ическому', 'ическими',
    'ующими', 'ющими', 'шему', 'овому', 'ейшей', 'айший',
    'ование', 'ирование', 'ования', 'ениями', 'иями',
    'ствами', 'ах', 'ях', 'ями', 'ами',
    'ой', 'ей', 'ый', 'ий', 'ая', 'яя', 'ое', 'ее', 'ые', 'ие',
    'ому', 'ему', 'ым', 'им', 'ом', 'ем', 'ую', 'юю',
    'ов', 'ев', 'уть', 'ать', 'ять', 'еть',
    'ешь', 'ишь', 'ует', 'ают', 'яют', 'или', 'ена', 'ено', 'ены',
    'ть', 'ся', 'сь', 'ы', 'и', 'а', 'я', 'о', 'е', 'у', 'ю', 'ь',
]


def stem_ru(w: str) -> str:
    for suf in _RU_SUFFIXES:
        if suf and w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[: len(w) - len(suf)]
    return w


def tokens(text: str):
    words = re.findall(r'[а-яёa-z0-9_]+', text.lower())
    out = []
    for w in words:
        if len(w) <= 2 or w.isdigit():
            out.append(w)
        elif w[0] in 'abcdefghijklmnopqrstuvwxyz':
            out.append(w[:-1] if w.endswith('s') and len(w) > 3 else w)
        else:
            out.append(stem_ru(w))
    return out


# ============================================================
# Retrieval-индекс: локальная проекция целого (плоскость L2)
# ============================================================

class Hit:
    __slots__ = ('chunk', 'score')

    def __init__(self, chunk, score):
        self.chunk = chunk
        self.score = score


class RetrievalIndex:
    """TF-IDF поверх частей корпуса. Это «локальная проекция целого»:
    агент не хранит всё в голове, но по любому запросу восстанавливает
    нужные сечения — фрагмент показывает всё, но тусклее."""

    def __init__(self, chunks):
        self.chunks = chunks
        self.N = len(chunks)
        self.tfs = []
        df = Counter()
        for c in chunks:
            tf = Counter(tokens(c['text']))
            self.tfs.append(tf)
            for t in set(tf):
                df[t] += 1
        self.idf = {t: math.log((self.N + 1) / (d + 1)) + 1.0 for t, d in df.items()}

    def search(self, query: str, top_k=8):
        qt = Counter(tokens(query))
        if not qt:
            return []
        scored = []
        for i, tf in enumerate(self.tfs):
            s = 0.0
            for t, qn in qt.items():
                cnt = tf.get(t)
                if cnt:
                    s += self.idf.get(t, 1.0) * min(cnt, 4) * (1 + 0.15 * (qn - 1))
            if s > 0:
                scored.append((s, i))
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [Hit(self.chunks[i], s) for s, i in scored[:top_k]]


# ============================================================
# Геном: сборка, сохранение, целостность, регенерация
# ============================================================

class Genome:
    """Целое = части + связи + корень. Геном коммитит ростер частей:
    корневой хеш меняется при любом изменении состава частей."""

    def __init__(self, chunks, sources, created):
        self.chunks = chunks
        self.sources = sources
        self.created = created
        self.leaf_hashes = [sha(c['id'] + c['text']) for c in chunks]
        self.root = merkle_root(self.leaf_hashes)

    @classmethod
    def from_files(cls, paths, target=1000, max_len=1800):
        chunks, sources = [], []
        seen = {}  # общий реестр адресов: дедупликация сквозь все файлы
        for p in paths:
            text = Path(p).read_text(encoding='utf-8', errors='replace')
            src = Path(p).name
            chunks.extend(chunk_text(text, src, target, max_len, seen=seen))
            sources.append(src)
        return cls(chunks, sources, '')

    def to_body(self) -> bytes:
        payload = {
            'root': self.root,
            'sources': self.sources,
            'chunks': self.chunks,
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True,
                          separators=(',', ':')).encode('utf-8')

    @classmethod
    def from_body(cls, body: bytes):
        payload = json.loads(body.decode('utf-8'))
        g = cls(payload['chunks'], payload['sources'], '')
        return g, payload['root']

    def verify(self):
        """Полная сверка: каждая часть хешируется, корень пересобирается.
        Возвращает (число целых частей, всего частей, корень сходится)."""
        ok = 0
        for c, lh in zip(self.chunks, self.leaf_hashes):
            if sha(c['id'] + c['text']) == lh:
                ok += 1
        return ok, len(self.chunks), merkle_root([sha(c['id'] + c['text']) for c in self.chunks]) == self.root

    def proof_for(self, chunk_id: str):
        for i, c in enumerate(self.chunks):
            if c['id'] == chunk_id:
                return i, self.chunks[i], self.leaf_hashes[i], merkle_proof(self.leaf_hashes, i)
        return None

    def stats(self):
        total = sum(len(c['text']) for c in self.chunks)
        return {
            'root': self.root,
            'parts': len(self.chunks),
            'symbols': total,
            'sources': self.sources,
        }


# ============================================================
# Орган «ДЫХАНИЕ» (gossip о gossip): расхождение = приращение
# ============================================================
# Из досье (Орган 4; 4.1 Дыхание; СЛОЙ 5): холоны обмениваются дельтами,
# слияние = объединение (G-set CRDT, рост только вширь), без лидеров
# и выборов. До сходимости части видят слегка разные целые («честная
# цена» из досье); после — один общий корень.

def gossip_converge(leaf_hashes, replicas=5, frac0=0.25, seed=7, rounds_cap=2000):
    """Симуляция Дыхания: R реплик-холонов. Каждая рождается со случайным
    срезом частей (ритуал рождения, шаг 3: «получить срез данных»).
    Раунд: случайная пара обменивается дельтами — только тем, чего у
    другого нет. Возвращает статистику сходимости и сверку корней:
    каждая реплика пересобирает корень из СВОИХ листьев в порядке индексов."""
    rng = random.Random(seed)
    n = len(leaf_hashes)
    if replicas < 2:
        raise ValueError('реплик должно быть >= 2')
    # Ритуал рождения (из досье, шаг 3: «получить срез данных»).
    # Срез = СЕКТОР («французский флаг» Уолперта: часть знает своё место
    # в Целом) + случайное перекрытие (интерференция с чужими областями).
    # Секторы всех реплик в сумме покрывают весь геном — иначе G-set CRDT
    # не смог бы собрать части, которых нет ни у одной реплики.
    sector = math.ceil(n / replicas)
    k0 = max(1, int(n * frac0))
    views = []
    for r in range(replicas):
        ids = set(range(r * sector, min(n, (r + 1) * sector)))
        ids |= set(rng.sample(range(n), k0))
        views.append({i: leaf_hashes[i] for i in ids})

    def roots_now():
        return [merkle_root([v[i] for i in sorted(v)]) for v in views]

    roots_birth = roots_now()
    distinct_birth = len(set(roots_birth))
    birth_sizes = [len(v) for v in views]

    rounds, exchanges = 0, 0
    while rounds < rounds_cap:
        rounds += 1
        a, b = rng.sample(range(replicas), 2)
        da = {i: h for i, h in views[b].items() if i not in views[a]}  # дельта a<-b
        db = {i: h for i, h in views[a].items() if i not in views[b]}  # дельта b<-a
        if da or db:
            exchanges += 1
        views[a].update(da)   # слияние = объединение, ничто не перезаписывается
        views[b].update(db)
        if all(len(v) == n for v in views):
            break

    converged = all(len(v) == n for v in views)
    roots = roots_now()
    return {
        'replicas': replicas,
        'parts': n,
        'birth_slice': k0,
        'birth_sizes': birth_sizes,
        'birth_distinct_roots': distinct_birth,
        'rounds': rounds,
        'exchanges': exchanges,
        'converged': converged,
        'roots_agree': len(set(roots)) == 1,
        'root': roots[0],
        'coverage': [len(v) for v in views],
    }
