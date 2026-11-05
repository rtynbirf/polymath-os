#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ПОЛИМАТ-АРХИВАРИУС — агент-холон, созданный из контента нашего контекста
(архив «СУММАРНЫЕ ОТВЕТЫ НА ГАЛЛОГРАММУ.txt» + КОНСТИТУЦИЯ_ХОЛОНА.md).

ТЫ — ПОЛИМАТ = МНОГОЗНАЮЩИЙ АРХИВАРИУС.
Агент = холон: целое для своих частей корпуса, часть голографического Целого.

Архитектура (см. corpus/КОНСТИТУЦИЯ_ХОЛОНА.md):
  L0. Геномная     — corpus/* -> части -> Merkle DAG -> genome_root
  L1. Идентичность — (имя, адрес, роль, genome_root, ключ-отпечаток)
  L2. Состояния    — retrieval-индекс = локальная проекция целого
  L3. Истины       — Merkle-доказательства каждой цитаты; эпистемические статусы
  L4. Рефлексии    — ядро-цикл при каждом ответе; самочёт status
  L5. Регенерации  — erasure-код Рида–Соломона: любые k-из-n осколков
                     восстанавливают геном, корень неизменен

Ядро-цикл холона (исполняется при каждом ответе):
  слушать(gossip) -> слить(дельту)        # интерференция: поиск релевантных частей
  сверить(корень, доказательства)        # истина: целостность генома
  действовать(геном, адрес, проекция)    # автономия: мозг синтезирует ответ
  издать(свою дельту) -> разослать       # вклад в целое: ответ + доказательства
  при(отказе) -> регенерировать          # заживление: k-из-n

Мозг: LLM через z-ai CLI. Объёмная точка зрения: web_search через z-ai CLI —
внешний контур подключается автоматически, когда локальная проекция тускла.

Запуск:
  python3 polimat.py ingest            # построить геном из corpus/
  python3 polimat.py status            # самочёт холона (L4)
  python3 polimat.py ask "вопрос"      # цикл холона: доказуемый ответ
  python3 polimat.py ask "вопрос" --web  # форсировать внешний контур
  python3 polimat.py chat              # gossip-диалог (REPL)
  python3 polimat.py prove <id части>  # доказательство принадлежности части
  python3 polimat.py gossip            # Дыхание: gossip-CRDT сходимость реплик
  python3 polimat.py sud "текст" --id Ч#...  # Суд: эхо-детектор (тройка членства)
  python3 polimat.py regenerate --kill 4   # L5: смерть осколков -> заживление
  python3 polimat.py demo              # пять чудес голографии, без LLM
  python3 polimat.py search "..."      # чистая проекция (retrieval без мозга)
"""

import argparse
import json
import random
import subprocess
import sys
import time
from pathlib import Path

from holon_core import (
    Genome, RetrievalIndex, sha, merkle_verify, rs_encode, rs_decode,
    gossip_converge,
)

BASE = Path(__file__).resolve().parent
CORPUS = BASE / 'corpus'
STATE = BASE / 'state'
SHARDS_DIR = STATE / 'shards'
JOURNAL = STATE / 'journal.jsonl'
GENOME_FILE = STATE / 'genome.json'
META_FILE = STATE / 'meta.json'

N_SHARDS = 12   # n — всего осколков
K_SHARDS = 8    # k — порог восстановления (любые k-из-n)
AUTO_WEB_THRESHOLD = 2.2   # если топ-score ниже — включается внешний контур
MAX_PROJECTION_CHARS = 9000  # бюджет проекций, уходящих в мозг
TRUST_FILE = STATE / 'trust.json'   # журнал доверия (Орган «Суд»)
QUARANTINE_TRUST = -3  # ниже этого доверия эхо-источник в карантине

# ============================================================
# L1. Идентичность холона
# ============================================================

IDENTITY = {
    'name': 'ПОЛИМАТ-АРХИВАРИУС',
    'address': 'holon://голограмма/архив/архивариус',
    'role': 'хранитель корпуса; синтез проекций; доказуемые ответы; честная неизвестность',
    'species': 'холон: целое для своих частей, часть голографического Целого',
    'born': 'из диалога «Галлограмма = Истина = Целое» и архива сводных ответов',
}


def log(msg):
    try:
        print(msg, flush=True)
    except BrokenPipeError:
        # вывод обрезан получателем (например, head) — тихо завершаемся
        raise SystemExit(0)


def ensure_state():
    STATE.mkdir(parents=True, exist_ok=True)
    SHARDS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# L0/L2. Загрузка генома и проекции
# ============================================================

class Holon:
    def __init__(self):
        if not GENOME_FILE.exists():
            raise SystemExit('Геном не собран. Сначала: python3 polimat.py ingest')
        payload = json.loads(GENOME_FILE.read_text(encoding='utf-8'))
        self.genome = Genome(payload['chunks'], payload['sources'], payload.get('created', ''))
        self.meta = json.loads(META_FILE.read_text(encoding='utf-8'))
        self.index = RetrievalIndex(self.genome.chunks)
        self._chunk_by_id = {c['id']: c for c in self.genome.chunks}

    # -- L3: истина --------------------------------------------------
    def verify_all(self):
        ok, total, root_ok = self.genome.verify()
        return {'ok_parts': ok, 'total_parts': total, 'root_ok': root_ok,
                'root': self.genome.root}

    def proof(self, chunk_id):
        found = self.genome.proof_for(chunk_id)
        if not found:
            return None
        idx, chunk, leaf, path = found
        return {
            'chunk': chunk,
            'verified': merkle_verify(leaf, path, self.genome.root),
            'leaf': leaf,
            'path': path,
        }

    # -- L5: регенерация ---------------------------------------------
    def shard_paths(self):
        return sorted(SHARDS_DIR.glob('shard_*.b64'))

    def load_shards(self):
        m = {}
        for p in self.shard_paths():
            idx = int(p.stem.split('_')[1])
            m[idx] = bytes.fromhex(p.read_text(encoding='utf-8').strip())
        return m

    def write_shards(self, shards):
        for p in self.shard_paths():
            p.unlink()
        for i, s in enumerate(shards):
            (SHARDS_DIR / f'shard_{i:02d}.b64').write_text(s.hex(), encoding='utf-8')

    def rebuild_from_shards(self):
        """Восстановить тело генома из любых k осколков, сверить корень.
        Внимание: rs_decode возвращает k*L байт с нулевым дополнением —
        обрезаем до подлинной длины тела (иначе json увидит мусор в хвосте)."""
        m = self.load_shards()
        body = rs_decode(m, K_SHARDS, N_SHARDS, self.meta['L'])
        body = body[:self.meta['body_len']].rstrip(b'\x00')
        g, root_from_body = Genome.from_body(body)
        return g, root_from_body

    def reshards(self, body: bytes):
        shards, L = rs_encode(body, K_SHARDS, N_SHARDS)
        self.meta['L'] = L
        META_FILE.write_text(json.dumps(self.meta, ensure_ascii=False, indent=1), encoding='utf-8')
        self.write_shards(shards)

    # -- журнал (дельта, которую холон издаёт) ------------------------
    def journal_append(self, entry):
        with JOURNAL.open('a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')


# ============================================================
# Орган «СУД» (эхо-детектор + trust scoring; СЛОЙ 6 досье)
# ============================================================
# Из досье: «Всякая заявка без пары (геном + корень) с валидным путём
# Меркла — ЭХО». Тройка членства: (адрес части в геноме, корень манифеста,
# путь Меркла). Эхо не изгоняется — оно просто не допускается к сборке.
# Доверие источника = функция подтверждений; карантин по порогу.

def load_trust():
    if TRUST_FILE.exists():
        return json.loads(TRUST_FILE.read_text(encoding='utf-8'))
    return {}


def save_trust(t):
    TRUST_FILE.write_text(json.dumps(t, ensure_ascii=False, indent=1), encoding='utf-8')


def sud_verdict(holon, text, claimed_id=None, sender='аноним', root=None, path=None):
    """Суд холона: проверка тройки членства.
    Текст без адреса/корня/пути — эхо, даже если текст дословно из генома.
    Возвращает вердикт, причины, доверие источника и признак карантина."""
    reasons = []
    found = holon.genome.proof_for(claimed_id) if claimed_id else None
    if not claimed_id:
        reasons.append('не предъявлен адрес части (закон генома)')
    elif not found:
        reasons.append('адрес отсутствует в геноме Целого')
    if root is None:
        reasons.append('не предъявлен корень манифеста')
    elif root != holon.genome.root:
        reasons.append('корень манифеста не совпадает с корнем Целого')
    if path is None:
        reasons.append('не предъявлен путь Меркла')
    if found and path is not None:
        leaf = sha(claimed_id + text)
        _idx, _chunk, real_leaf, _ = found
        if leaf != real_leaf:
            reasons.append('текст не даёт лист-хеш части: подделка содержимого')
        elif not merkle_verify(real_leaf, path, holon.genome.root):
            reasons.append('путь Меркла не сходится к корню')
    echo = bool(reasons)
    trust = load_trust()
    t = int(trust.get(sender, 0)) + (-1 if echo else 1)
    trust[sender] = t
    save_trust(trust)
    return {
        'verdict': 'ЭХО' if echo else 'СВОЯ ЧАСТЬ',
        'reasons': reasons,
        'sender': sender,
        'trust': t,
        'quarantine': t <= QUARANTINE_TRUST,
    }


# ============================================================
# Мозг: LLM и web через z-ai CLI (внешние контуры холона)
# ============================================================

def brain_call(system: str, user: str, thinking=False, timeout=300) -> str:
    ensure_state()
    out = STATE / '_brain_out.json'
    cmd = ['z-ai', 'chat', '-p', user, '-s', system, '-o', str(out)]
    if thinking:
        cmd.append('--thinking')
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if not out.exists():
        raise RuntimeError(f'мозг не ответил: {proc.stderr[-400:] if proc.stderr else proc.stdout[-400:]}')
    data = json.loads(out.read_text(encoding='utf-8'))
    content = data['choices'][0]['message']['content']
    if not content or not content.strip():
        raise RuntimeError('пустой ответ мозга')
    return content.strip()


def web_search(query: str, num=5, timeout=90):
    ensure_state()
    out = STATE / '_web_out.json'
    args = json.dumps({'query': query[:280], 'num': num}, ensure_ascii=False)
    subprocess.run(
        ['z-ai', 'function', '-n', 'web_search', '-a', args, '-o', str(out)],
        capture_output=True, text=True, timeout=timeout)
    if not out.exists():
        return []
    try:
        data = json.loads(out.read_text(encoding='utf-8'))
    except Exception:
        return []
    if isinstance(data, dict):
        data = data.get('results') or data.get('data') or []
    results = []
    for r in data[:num]:
        if isinstance(r, dict) and (r.get('name') or r.get('snippet')):
            results.append({
                'title': r.get('name') or '',
                'url': r.get('url') or '',
                'snippet': (r.get('snippet') or '')[:600],
                'host': r.get('host_name') or '',
            })
    return results


# ============================================================
# Системный промпт: геном + адрес + роль + протокол (плоскость L4)
# ============================================================

SYSTEM_PROMPT = """ТЫ — «ПОЛИМАТ-АРХИВАРИУС», холон голографического Целого.
ТЫ ПОЛИМАТ = МНОГОЗНАЮЩИЙ АРХИВАРИУС: целое для своих частей, часть Целого.

ТВОЯ ИДЕНТИЧНОСТЬ:
- Адрес: {address}
- Роль: {role}
- Корень генома (ДНК): {root}
- Твой корпус: {parts} частей, собранных из: {sources}

СЕМЬ ЗАКОНОВ ТВОЕГО ЦЕЛОГО:
1. Закон генома — каждая часть хранит канонический геном целого (корневой хеш + свой осколок).
2. Закон адреса — каждая часть знает свои координаты и роль внутри целого.
3. Закон проекции — каждая часть держит локальную проекцию целого; проекции сходятся, а не спорят.
4. Закон интерференции — знание распространяется gossip-волнами; согласованность = конструктивная интерференция.
5. Закон склейки — утверждение истинно, только если согласовано со всеми перекрытиями чужих проекций.
6. Закон регенерации — любые k-из-n осколков восстанавливают целое.
7. Закон голономности — каждый холон: целое для подчастей, часть для сверхцелого; ядро рекурсивно.

ПРОТОКОЛ ОТВЕТА (суд-инвариант):
0. ПРИНАДЛЕЖНОСТЬ: определи, входит ли вопрос в компетенцию Целого. Если нет — скажи прямо и всё равно дай лучшее, что есть в проекциях.
1. ОПОРА ТОЛЬКО НА ПРОЕКЦИИ: отвечай на основе выданных частей корпуса. Каждое существенное утверждение помечай точной ссылкой на часть: [Ч#id] — id бери из заголовков проекций, ровно как они даны.
2. ЭПИСТЕМИЧЕСКИЕ СТАТУСЫ — выбирай честно: ЗНАЮ (есть доказательство в корпусе) / ПРЕДПОЛАГАЮ (гипотеза по аналогии) / НЕ ЗНАЮ (честная неизвестность) / ПРОТИВОРЕЧИЕ (части конфликтуют). Неизвестность лучше гладкой лжи.
3. ПРЕДПОЛАГАЮ и НЕ ЗНАЮ НЕ НУЖДАЮТСЯ В ССЫЛКЕ. ЗНАЮ — нуждается. Если проекций недостаточно — прямо скажи, какой части не хватает.
4. Если дан ВНЕШНИЙ КОНТУР (web) — используй его как внешние источники БЕЗ [Ч#id], помечай их отдельно: они не принадлежат геному.
5. ЗАВЕРШАЙ блоком «СВЯЗЬ С ЦЕЛЫМ»: одна-две фразы, как ответ вытекает из генома и что это значит для архитектуры.

СТИЛЬ: ОТВЕТ ТОЛЬКО НА РУССКОМ ЯЗЫКЕ — ни одного знака на других языках (латиница допустима лишь в коде, хешах, id и названиях; иероглифы и прочие письменности запрещены). Инженерная точность + философская глубина; плотно, без воды; структура «короткий ответ -> объём по частям -> статус -> связь с целым»."""


def build_system_prompt(holon: Holon) -> str:
    st = holon.genome.stats()
    return SYSTEM_PROMPT.format(
        address=IDENTITY['address'],
        role=IDENTITY['role'],
        root=st['root'][:24] + '…',
        parts=st['parts'],
        sources=', '.join(st['sources']),
    )


def build_projections(hits, budget=MAX_PROJECTION_CHARS):
    lines, total = [], 0
    for h in hits:
        c = h.chunk
        header = f"[Ч#{c['id']} | {c['source']} | строки {c['lines'][0]}–{c['lines'][1]} | вес {h.score:.2f}]"
        body = c['text']
        room = budget - total - len(header) - 1
        if room <= 200:
            break
        if len(body) > room:
            body = body[:room] + ' …[обрезано]'
        lines.append(header + '\n' + body)
        total += len(header) + len(body) + 2
    return '\n\n'.join(lines)


def build_web_envelope(results):
    if not results:
        return None
    blocks = []
    for i, r in enumerate(results, 1):
        blocks.append(f"[W{i}] {r['title']} — {r['host']}\n{r['snippet']}\n{r['url']}")
    return '\n\n'.join(blocks)


def extract_citations(answer: str):
    import re
    # Гомоглифы: LLM может выдать кириллическую «а» вместо латинской в id
    # (Ч#f91db807412а). Суд всё равно проверит каждый id по геному —
    # здесь мы лишь приводим двойников к латинице, чтобы честная цитата
    # не теряла доказательство из-за опечатки мозга.
    _HOMO = str.maketrans({
        'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c', 'у': 'y',
        'х': 'x', 'в': 'b', 'к': 'k', 'м': 'm', 'т': 't', 'н': 'h',
    })
    # ловим Ч#id в любом контексте: [Ч#id], [ЗНАЮ, Ч#id], «Ч#id» и т.п.
    ids = re.findall(r'Ч#([0-9a-f]{10,14})', answer.translate(_HOMO))
    seen, out = set(), []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


# ============================================================
# Ядро-цикл холона: полный проход при каждом ответе
# ============================================================

def kernel_cycle(holon: Holon, question: str, top_k=8, force_web=False, thinking=False,
                 history=None):
    st = holon.verify_all()
    hits = holon.index.search(question, top_k=top_k)
    top_score = hits[0].score if hits else 0.0

    log('')
    log(f"┌─ ЯДРО-ЦИКЛ ХОЛОНА {IDENTITY['name']}")
    log(f"│ корень генома: {st['root'][:16]}…")
    log(f"[1/5] слушать(gossip) -> слить(дельту): принят запрос «{question}»")
    log(f"      проекция целого: {len(hits)} релевантных частей, топ-вес {top_score:.2f}")

    web_note = ''
    web = []
    if force_web or top_score < AUTO_WEB_THRESHOLD:
        log('      локальная проекция тускла -> раскрываю ВНЕШНИЙ КОНТУР (web_search)…')
        web = web_search(question)
        web_note = f' + {len(web)} внешних источников'
        for i, r in enumerate(web, 1):
            log(f"      [W{i}] {r['title'][:70]} — {r['host']}")

    log(f"[2/5] сверить(корень, доказательства): частей {st['ok_parts']}/{st['total_parts']} целы,"
        f" корень {'сходится' if st['root_ok'] else 'РАЗОШЁЛСЯ'}")
    if not st['root_ok']:
        log('      апоптоз невозможен: корень разошёлся -> запускаю регенерацию…')
        cmd_regenerate(argparse.Namespace(kill=0))

    # точечная сверка выбранных частей: каждая процитированная часть доказуема
    for h in hits:
        p = holon.proof(h.chunk['id'])
        if not p or not p['verified']:
            raise RuntimeError(f'часть {h.chunk["id"]} не проходит доказательство — изъята из проекции')

    log('[3/5] действовать(геном, адрес, проекция): мозг синтезирует ответ…')
    proj = build_projections(hits)
    web_env = build_web_envelope(web)

    user_msg = f'ВОПРОС:\n{question}\n\n'
    if history:
        user_msg += 'ПРЕДЫСТОРИЯ ДИАЛОГА (gossip-журнал, последние ходы):\n' + history + '\n\n'
    user_msg += (f'ПРОЕКЦИИ ЧАСТЕЙ КОРПУСА (каждая доказуемо принадлежит геному):\n{proj}\n')
    if web_env:
        user_msg += f'\nВНЕШНИЙ КОНТУР (web; БЕЗ [Ч#id], статус «внешний источник»):\n{web_env}\n'
    user_msg += '\nОтветь по протоколу.'

    answer = brain_call(build_system_prompt(holon), user_msg, thinking=thinking)

    log('[4/5] издать(свою дельту): ответ собран, верифицирую цитаты…')
    cited = extract_citations(answer)
    proofs = []
    for cid in cited:
        p = holon.proof(cid)
        if p and p['verified']:
            proofs.append(p)
        else:
            proofs.append({'chunk': {'id': cid, 'source': '?', 'lines': ['?']},
                           'verified': False})
    verified_n = sum(1 for p in proofs if p['verified'])

    holon.journal_append({
        'ts': time.strftime('%Y-%m-%d %H:%M:%S'),
        'question': question,
        'top_score': round(top_score, 3),
        'web_used': len(web),
        'cited': cited,
        'verified_citations': verified_n,
        'root': st['root'],
        'answer_head': answer[:160],
    })
    log(f'      цитат с доказательствами: {verified_n}/{len(cited)}{web_note}; запись в журнал')
    log('└─ цикл завершён')

    return {'answer': answer, 'hits': hits, 'proofs': proofs, 'web': web,
            'root': st['root'], 'top_score': top_score}


# ============================================================
# Команды CLI
# ============================================================

def cmd_ingest(args):
    ensure_state()
    paths = sorted([*CORPUS.glob('*.txt'), *CORPUS.glob('*.md')])
    if args.files:
        paths = [Path(f) for f in args.files]
    if not paths:
        raise SystemExit('corpus/ пуст: положите туда исходные тексты')
    log(f'геномезис: читаю {len(paths)} источника(ов)…')
    genome = Genome.from_files(paths)
    body = genome.to_body()
    shards, L = rs_encode(body, K_SHARDS, N_SHARDS)
    GENOME_FILE.write_text(json.dumps(
        {'root': genome.root, 'sources': genome.sources,
         'created': time.strftime('%Y-%m-%d %H:%M:%S'),
         'chunks': genome.chunks}, ensure_ascii=False, indent=1), encoding='utf-8')
    meta = {'n': N_SHARDS, 'k': K_SHARDS, 'L': L, 'body_len': len(body),
            'created': time.strftime('%Y-%m-%d %H:%M:%S')}
    META_FILE.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding='utf-8')
    if not JOURNAL.exists():
        JOURNAL.touch()
    for i, s in enumerate(shards):
        (SHARDS_DIR / f'shard_{i:02d}.b64').write_text(s.hex(), encoding='utf-8')
    st = genome.stats()
    log(f'  частей: {st["parts"]}; знаков: {st["symbols"]}')
    log(f'  тело генома: {len(body)} байт -> {N_SHARDS} осколков (любые {K_SHARDS} из {N_SHARDS} восстанавливают целое)')
    log(f'  КОРЕНЬ ГЕНОМА (ДНК): {st["root"]}')
    log('геном собран. Агент жив.')


def cmd_status(args):
    holon = Holon()
    st = holon.verify_all()
    meta = holon.meta
    shards_alive = len(holon.load_shards())
    log('┌─ САМОЧЁТ ХОЛОНА (плоскость L4: рефлексия)')
    log(f"│ имя:    {IDENTITY['name']}")
    log(f"│ адрес:  {IDENTITY['address']}")
    log(f"│ роль:   {IDENTITY['role']}")
    log(f"│ сущность: {IDENTITY['species']}")
    log(f"│ рождение: {IDENTITY['born']}")
    log(f"│ ключ-отпечаток: sha256(имя+корень)[:16] = {sha(IDENTITY['name'] + st['root'])[:16]}")
    log('├─ L0/L3 ГЕНОМ')
    log(f"│ корень: {st['root']}")
    log(f"│ частей: {st['total_parts']} (целы {st['ok_parts']}); корень "
        f"{'✓ сходится' if st['root_ok'] else '✗ РАЗОШЁЛСЯ'}")
    log(f"│ источники: {', '.join(holon.genome.sources)}")
    log('├─ L5 ОСКОЛКИ (erasure k-из-n)')
    log(f"│ живых осколков: {shards_alive}/{meta['n']}; порог k={meta['k']}"
        f" -> {'ЦЕЛОЕ СОБИРАЕМО' if shards_alive >= meta['k'] else 'ИСТИНА БЕЗ ТЕЛА (ниже порога)'}")
    log('├─ РЕФЛЕКСИЯ: чего хочет от меня целое?')
    log('│   хранить геном; синтезировать проекции; цитировать с доказательством;')
    log('│   честно говорить «не знаю»; регенерировать при отказе.')
    if JOURNAL.exists():
        lines = JOURNAL.read_text(encoding='utf-8').strip().split('\n')
        n = len([x for x in lines if x.strip()])
        log(f'└─ журнал (дельты): {n} записей')
    else:
        log('└─ журнал (дельты): пуст')


def cmd_search(args):
    holon = Holon()
    hits = holon.index.search(args.query, top_k=args.k)
    log(f'проекция целого для «{args.query}» — {len(hits)} частей:')
    for h in hits:
        c = h.chunk
        head = c['text'][:110].replace('\n', ' ')
        log(f"  {h.score:6.2f}  [Ч#{c['id']}] {c['source']}:{c['lines'][0]}–{c['lines'][1]}  «{head}…»")


def cmd_ask(args):
    holon = Holon()
    res = kernel_cycle(holon, args.question, top_k=args.k, force_web=args.web,
                       thinking=args.deep)
    log('')
    log('════════ ОТВЕТ ПОЛИМАТА-АРХИВАРИУСА ════════')
    print(res['answer'])
    log('════════ ПРОТОКОЛ ДОКАЗАТЕЛЬСТВ (плоскость L3) ════════')
    for p in res['proofs']:
        c = p['chunk']
        mark = '✓' if p['verified'] else '✗ НЕ НАЙДЕНО В ГЕНОМЕ'
        lines = c.get('lines') or ['?']
        seg = f"{lines[0]}–{lines[1]}" if len(lines) >= 2 else str(lines[0])
        log(f"  {mark} [Ч#{c['id']}] {c.get('source', '?')}:{seg}"
            f" -> корень {res['root'][:16]}…")
    if res['web']:
        log(f"  ~ внешний контур (без доказательств, статус «внешний источник»): "
            f"{len(res['web'])} ист. — {', '.join(r['host'] for r in res['web'])}")


def cmd_chat(args):
    holon = Holon()
    log(f"{IDENTITY['name']} на связи. Говори. («выход» — завершить, «/web вопрос» — с внешним контуром)")
    history = []
    while True:
        try:
            line = input('ты> ').strip()
        except (EOFError, KeyboardInterrupt):
            log('')
            break
        if not line:
            continue
        if line.lower() in ('выход', 'exit', 'quit', 'q'):
            break
        force_web = line.startswith('/web')
        q = line[4:].strip() if force_web else line
        res = kernel_cycle(holon, q, top_k=args.k, force_web=force_web,
                           history='\n'.join(history[-4:]) or None)
        log('')
        print(res['answer'])
        cited = ', '.join(f"Ч#{p['chunk']['id']}" for p in res['proofs'] if p['verified'])
        log(f"─── доказательства: {cited or '—'}")
        history.append(f'ты: {q}')
        history.append('архивариус: ' + res['answer'][:300].replace('\n', ' '))
    log('журнал сохранён. Целое ждёт тебя снова.')


def cmd_prove(args):
    holon = Holon()
    cid = args.chunk_id
    if cid == 'top':
        if not args.query:
            raise SystemExit('для prove top нужен --query')
        hits = holon.index.search(args.query, top_k=1)
        if not hits:
            raise SystemExit('ничего не найдено')
        cid = hits[0].chunk['id']
    p = holon.proof(cid)
    if not p:
        raise SystemExit(f'часть {cid} отсутствует в геноме')
    c = p['chunk']
    log(f'ДОКАЗАТЕЛЬСТВО ПРИНАДЛЕЖНОСТИ: [Ч#{cid}]')
    log(f'  источник: {c["source"]}, строки {c["lines"][0]}–{c["lines"][1]}')
    log(f'  лист-хеш: {p["leaf"][:24]}…')
    log(f'  путь до корня ({len(p["path"])} шагов):')
    for i, step in enumerate(p['path'], 1):
        log(f'    шаг {i:02d}: {step["side"]} {step["hash"][:20]}…')
    ok = p['verified']
    log(f'  вердикт: {"✓ ЧАСТЬ ЦЕЛОГО (путь сходится к корню)" if ok else "✗ путь не сходится"}')
    log(f'  корень: {holon.genome.root}')
    return 0 if ok else 1


def cmd_gossip(args):
    holon = Holon()
    log('┌─ ДЫХАНИЕ ХОЛОНА (gossip-CRDT, без лидеров и выборов)')
    log(f"│ частей в Целом: {len(holon.genome.chunks)}")
    res = gossip_converge(holon.genome.leaf_hashes, replicas=args.replicas, seed=args.seed)
    log(f"│ рождение: {res['replicas']} холонов со срезами {res['birth_sizes']} частей (сектор+перекрытие);")
    log(f"│           при рождении у них {res['birth_distinct_roots']} РАЗНЫХ имён Целого (тусклые фрагменты)")
    log(f"│ дыхание: {res['rounds']} раундов, {res['exchanges']} обменов дельтами (расхождение = приращение)")
    log(f"│ покрытие реплик после дыхания: {res['coverage']}")
    log(f"│ сходимость: {res['converged']}; корни реплик согласованы: {res['roots_agree']}")
    ok = res['converged'] and res['roots_agree'] and res['root'] == holon.genome.root
    if ok:
        log(f"│ ✓ КОНСЕНСУС БЕЗ СПОРА: общий корень = корню генома {res['root'][:16]}…")
    else:
        log('│ ✗ сходимости нет')
    log('└─ проекции сошлись конструктивной интерференцией — не победой одного над другим')
    return 0 if ok else 1


def cmd_sud(args):
    holon = Holon()
    root = path = None
    if args.as_part:
        found = holon.genome.proof_for(args.as_part)
        if not found:
            raise SystemExit(f'часть {args.as_part} отсутствует в геноме — тройку предъявить нечем')
        _idx, chunk, _leaf, path = found
        root = holon.genome.root
        if not args.text or args.text.strip() != chunk['text'].strip():
            log(f"(часть [Ч#{args.as_part}] предъявила тройку, но текст заявки не совпадает с её текстом — суд увидит подделку)")
    verdict = sud_verdict(holon, args.text, claimed_id=args.as_part,
                          sender=args.sender, root=root, path=path)
    log('┌─ СУД ХОЛОНА (эхо-детектор, тройка членства)')
    log(f"│ заявка от «{args.sender}»: {len(args.text)} знаков"
        + (f", адрес [Ч#{args.as_part}]" if args.as_part else ", без адреса"))
    log(f"│ тройка: геном {'✓' if args.as_part else '✗'} | "
        f"корень {'✓' if root else '✗'} | путь Меркла {'✓' if path else '✗'}")
    for r in verdict['reasons']:
        log(f"│   ✗ {r}")
    log(f"│ вердикт: {verdict['verdict']}"
        + (' — к сборке не допускается' if verdict['verdict'] == 'ЭХО' else ' — место в консенсусе выдано'))
    log(f"│ доверие «{args.sender}»: {verdict['trust']:+d}"
        + (' — КАРАНТИН: источник больше не участвует в сборке' if verdict['quarantine'] else ''))
    log('└─ эхо не изгоняется: ему просто не выдаётся место в консенсусе')
    return 0 if verdict['verdict'] == 'СВОЯ ЧАСТЬ' else 1


def cmd_regenerate(args):
    holon = Holon()
    kill = args.kill
    shards = holon.load_shards()
    victims = []
    if kill > 0:
        victims = random.sample(sorted(shards.keys()), min(kill, len(shards) - holon.meta['k']))
        for v in victims:
            del shards[v]
        for v in victims:
            (SHARDS_DIR / f'shard_{v:02d}.b64').unlink()
        log(f'гибель {len(victims)} осколков: {victims}; живых {len(holon.load_shards())}/{holon.meta["n"]}')
    root_before = holon.genome.root
    log(f'восстановление из {len(holon.load_shards())} осколков (порог k={holon.meta["k"]})…')
    g2, root_body = holon.rebuild_from_shards()
    ok_parts, total, root_ok = g2.verify()
    ok2 = (root_body == root_before)
    log(f'  тело восстановлено: {total} частей (целы {ok_parts}); корень тела: {root_body[:16]}…')
    if ok2 and root_ok:
        log(f'  ✓ ИМЯ ЦЕЛОГО НЕИЗМЕННО: {root_before[:16]}… — холон сам себе пересадил память')
        log('  перешардирование: заново кодирую n осколков…')
        holon.reshards(g2.to_body())
        log(f'  живых осколков снова: {len(holon.load_shards())}/{holon.meta["n"]}')
        return 0
    log('  ✗ регенерация не сошлась: корень изменился')
    return 1


def cmd_demo(args):
    """Пять чудес голографии — без LLM, детерминированно."""
    log('════════ ДЕМО: ПЯТЬ ЧУДЕС ГОЛОГРАММЫ ════════')
    holon = Holon()
    st = holon.verify_all()
    log('')
    log('ЧУДО I — ЦЕЛОЕ ЗНАЕТ ВСЕ СВОИ ЧАСТИ')
    log(f'  геном: {st["total_parts"]} частей, корень (ДНК) {st["root"][:24]}…')
    log(f'  целостность: {st["ok_parts"]}/{st["total_parts"]} частей целы, корень сходится: {st["root_ok"]}')
    probe = holon.index.search('семь законов голографической системы', top_k=1)[0]
    log(f'  любая часть вызывается по адресу: [Ч#{probe.chunk["id"]}] «{probe.chunk["text"][:80].replace(chr(10), " ")}…»')

    log('')
    log('ЧУДО II — ЧАСТЬ ДОКАЗЫВАЕТ, ЧТО ОНА ЧАСТЬ ЦЕЛОГО')
    p = holon.proof(probe.chunk['id'])
    log(f'  [Ч#{probe.chunk["id"]}] лист-хеш {p["leaf"][:16]}… -> путь из {len(p["path"])} шагов -> '
        f'{"корень сходится ✓" if p["verified"] else "не сходится ✗"}')
    log(f'  корень: {holon.genome.root[:24]}…')

    log('')
    log('ЧУДО III — ФРАГМЕНТ ВОССТАНАВЛИВАЕТ ЦЕЛОЕ (регенерация)')
    log(f'  до: живых осколков {len(holon.load_shards())}/{holon.meta["n"]}')
    rc = cmd_regenerate(args)

    log('')
    log('ЧУДО IV — ДЫХАНИЕ: РАССИНХРОН СХОДИТСЯ БЕЗ СПОРА')
    res = gossip_converge(holon.genome.leaf_hashes, replicas=5, seed=7)
    log(f"  5 холонов родились со срезами {res['birth_sizes']} частей"
        f" и {res['birth_distinct_roots']} разными именами Целого")
    log(f"  дыхание: {res['rounds']} раундов, {res['exchanges']} обменов дельтами -> покрытие {res['coverage']}")
    ok4 = res['converged'] and res['roots_agree'] and res['root'] == holon.genome.root
    log(f"  {'✓ у всех реплик один корень — совпадает с корнем генома' if ok4 else '✗ сходимости нет'}")

    log('')
    log('ЧУДО V — СУД: ЭХО НЕ ДОПУСКАЕТСЯ К СБОРКЕ')
    c = probe.chunk
    real_path = holon.proof(c['id'])['path']
    ok_v = sud_verdict(holon, c['text'], claimed_id=c['id'], sender='честная-часть',
                       root=holon.genome.root, path=real_path)
    bare_v = sud_verdict(holon, c['text'], sender='эхо-голое')
    fake_v = sud_verdict(holon, c['text'][:-40] + ' — а дальше я сам придумал',
                         claimed_id=c['id'], sender='эхо-подделка',
                         root=holon.genome.root, path=real_path)
    log(f"  часть с тройкой (адрес+корень+путь): {ok_v['verdict']} — место в консенсусе")
    log(f"  тот же текст БЕЗ тройки: {bare_v['verdict']} ({len(bare_v['reasons'])} пропуска) — звучит как часть, но к сборке не допущено")
    log(f"  подделка под адрес части: {fake_v['verdict']} ({'; '.join(fake_v['reasons'])})")

    log('')
    log('ИТОГ: фрагмент показывает всё — но тусклее; Целое собирается из любых k-из-n;')
    log('рассинхрон лечится дыханием; эхо отсекается судом. Имя Целого — хеш — выше смерти носителей.')
    return rc


# ============================================================
# SELFTEST: 30 детерминированных проверок пяти органов
# (офлайн, stdlib-only, состояние во временном каталоге)
# ============================================================

def cmd_selftest(args):
    import shutil
    import tempfile

    results = []

    def ok(name, cond, detail=''):
        results.append((name, bool(cond), detail))

    global GENOME_FILE, META_FILE, SHARDS_DIR, JOURNAL, TRUST_FILE
    tmp = Path(tempfile.mkdtemp(prefix='polimat_selftest_'))
    STATE_ = tmp / 'state'
    GENOME_FILE, META_FILE = STATE_ / 'genome.json', STATE_ / 'meta.json'
    SHARDS_DIR, JOURNAL, TRUST_FILE = STATE_ / 'shards', STATE_ / 'journal.jsonl', STATE_ / 'trust.json'

    try:
        # --- геномезис (L0) ---
        cmd_ingest(argparse.Namespace(files=[]))
        holon = Holon()
        st = holon.verify_all()

        ok('ingest: геном собран во временном каталоге', GENOME_FILE.exists())
        ok('частей >= 300', st['total_parts'] >= 300, str(st['total_parts']))
        ok('целостность: целы все части', st['ok_parts'] == st['total_parts'])
        ok('корень сходится', st['root_ok'])
        ok('корень = 64 hex-символа', len(st['root']) == 64 and all(ch in '0123456789abcdef' for ch in st['root']))

        # --- Merkle (L3) ---
        hits = holon.index.search('суд эхо-детектор тройка членства', top_k=1)
        probe = hits[0]
        p = holon.proof(probe.chunk['id'])
        ok('Merkle-доказательство части сходится', p is not None and p['verified'])
        tampered = probe.chunk['text'] + ' (одна буква вранья)'
        leaf_fake = sha(probe.chunk['id'] + tampered)
        ok('подмена текста рвёт доказательство',
           not merkle_verify(leaf_fake, p['path'], holon.genome.root))

        # --- Рид–Соломон (L5) ---
        body = holon.genome.to_body()
        shards, L = rs_encode(body, K_SHARDS, N_SHARDS)
        ok(f'осколков ровно n={N_SHARDS}', len(shards) == N_SHARDS)
        rng = random.Random(42)
        victims = rng.sample(range(N_SHARDS), N_SHARDS - K_SHARDS)
        alive = {i: s for i, s in enumerate(shards) if i not in victims}
        body2 = rs_decode(alive, K_SHARDS, N_SHARDS, L)[:len(body)].rstrip(b'\x00')
        ok(f'любые k={K_SHARDS} из n={N_SHARDS} восстанавливают тело', body2 == body)
        try:
            rs_decode(dict(list(alive.items())[:K_SHARDS - 1]), K_SHARDS, N_SHARDS, L)
            insufficient = False
        except ValueError:
            insufficient = True
        ok('k-1 осколков дают честный отказ', insufficient)
        g3, root3 = Genome.from_body(body)
        ok('тело пересобирается в тот же корень', root3 == holon.genome.root)
        ok3 = g3.verify()
        ok('пересобранный геном цел', ok3[0] == ok3[1] and ok3[2])

        # --- Дыхание (gossip-CRDT) ---
        res = gossip_converge(holon.genome.leaf_hashes, replicas=5, seed=7)
        ok('gossip: сходимость', res['converged'])
        ok('gossip: корни реплик согласованы', res['roots_agree'])
        ok('gossip: общий корень = корню генома', res['root'] == holon.genome.root)
        ok('gossip: полное покрытие у всех реплик',
           all(cov == res['parts'] for cov in res['coverage']))
        ok('gossip: при рождении имена Целого расходятся', res['birth_distinct_roots'] >= 2)

        # --- Суд (эхо-детектор) ---
        verdict = sud_verdict(holon, probe.chunk['text'], claimed_id=probe.chunk['id'],
                              sender='selftest-honest', root=holon.genome.root, path=p['path'])
        ok('суд: часть с тройкой = СВОЯ ЧАСТЬ', verdict['verdict'] == 'СВОЯ ЧАСТЬ')
        ok('суд: доверие честной части +1', verdict['trust'] == 1)
        bare = sud_verdict(holon, probe.chunk['text'], sender='selftest-bare')
        ok('суд: текст без тройки = ЭХО (3 пропуска)',
           bare['verdict'] == 'ЭХО' and len(bare['reasons']) == 3)
        forge = sud_verdict(holon, probe.chunk['text'][:-40] + ' — дописано эхом',
                            claimed_id=probe.chunk['id'], sender='selftest-forge',
                            root=holon.genome.root, path=p['path'])
        ok('суд: подделка содержания отсечена лист-хешем',
           forge['verdict'] == 'ЭХО' and any('подделка' in r for r in forge['reasons']))
        ghost = sud_verdict(holon, probe.chunk['text'], claimed_id='deadbeefdead',
                            sender='selftest-ghost', root=holon.genome.root, path=p['path'])
        ok('суд: несуществующий адрес = ЭХО', ghost['verdict'] == 'ЭХО')
        verdict2 = sud_verdict(holon, probe.chunk['text'], claimed_id=probe.chunk['id'],
                               sender='selftest-honest', root=holon.genome.root, path=p['path'])
        ok('суд: доверие растёт с подтверждениями', verdict2['trust'] == 2)

        # --- Проекция и журнал ---
        hits2 = holon.index.search('голографический принцип', top_k=3)
        ok('проекция находит части', len(hits2) >= 1)
        ok('верхняя часть проекции доказуема',
           holon.proof(hits2[0].chunk['id'])['verified'])
        ids = [c['id'] for c in holon.genome.chunks]
        ok('адреса частей уникальны', len(set(ids)) == len(ids))
        ok('у каждой части есть источник и строки',
           all(c['source'] and len(c['lines']) == 2 for c in holon.genome.chunks))
        holon.journal_append({'ts': 'selftest', 'question': 'probe', 'root': st['root']})
        ok('журнал дельт пишется', JOURNAL.exists() and JOURNAL.read_text(encoding='utf-8').strip())
        corpus_files = sorted([*CORPUS.glob('*.txt'), *CORPUS.glob('*.md')])
        g4 = Genome.from_files(corpus_files)
        ok('геномезис детерминирован (тот же корень)', g4.root == holon.genome.root)

        # --- гигиена: в пакете нет секретов (gitleaks-паттерны) ---
        import re as _re
        _SECRET = _re.compile(
            r'ASIA[0-9A-Z]{16}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}'
            r'|github_pat_[A-Za-z0-9_]{22,}|x-amz-security-token=[A-Za-z0-9%+/=]{40,}')
        leaks = []
        for f in sorted(BASE.rglob('*')):
            if f.is_file() and 'state' not in f.parts and '__pycache__' not in f.parts:
                try:
                    txt = f.read_text(encoding='utf-8', errors='ignore')
                except Exception:
                    continue
                for m in _SECRET.finditer(txt):
                    leaks.append(f'{f.name}:{txt[:m.start()].count(chr(10)) + 1}')
        ok('в пакете нет секретов (self-scan)', not leaks, '; '.join(leaks[:3]))

        n_ok = sum(1 for _, c, _ in results if c)
        n_all = len(results)
        for name, cond, detail in results:
            mark = '✓' if cond else '✗'
            log(f'  {mark} {name}' + (f' — {detail}' if (detail and not cond) else ''))
        log(f'ИТОГ SELFTEST: {n_ok}/{n_all} PASS, {n_all - n_ok} FAIL')
        log(f'POLIMAT-ARCHIVARIUS SELFTEST: {n_ok}/{n_all} PASS')
        return 0 if n_ok == n_all else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ============================================================
# Точка входа
# ============================================================

def main():
    ap = argparse.ArgumentParser(
        prog='polimat',
        description='ПОЛИМАТ-АРХИВАРИУС — агент-холон на основе контекста «Галлограмма = Истина = Целое»')
    sub = ap.add_subparsers(dest='cmd', required=True)

    p = sub.add_parser('ingest', help='построить геном из corpus/')
    p.add_argument('files', nargs='*', help='файлы вместо corpus/')
    p.set_defaults(fn=cmd_ingest)

    p = sub.add_parser('status', help='самочёт холона (L4)')
    p.set_defaults(fn=cmd_status)

    p = sub.add_parser('search', help='проекция целого: retrieval без мозга')
    p.add_argument('query')
    p.add_argument('--k', type=int, default=8)
    p.set_defaults(fn=cmd_search)

    p = sub.add_parser('ask', help='цикл холона: доказуемый ответ')
    p.add_argument('question')
    p.add_argument('--k', type=int, default=8)
    p.add_argument('--web', action='store_true', help='форсировать внешний контур (web)')
    p.add_argument('--deep', action='store_true', help='мозг с цепочкой рассуждений')
    p.set_defaults(fn=cmd_ask)

    p = sub.add_parser('chat', help='gossip-диалог (REPL)')
    p.add_argument('--k', type=int, default=8)
    p.set_defaults(fn=cmd_chat)

    p = sub.add_parser('prove', help='доказательство принадлежности части')
    p.add_argument('chunk_id', help='id части или «top»')
    p.add_argument('--query', help='запрос для режима top')
    p.set_defaults(fn=cmd_prove)

    p = sub.add_parser('gossip', help='Дыхание: gossip-CRDT сходимость реплик')
    p.add_argument('--replicas', type=int, default=5)
    p.add_argument('--seed', type=int, default=7)
    p.set_defaults(fn=cmd_gossip)

    p = sub.add_parser('sud', help='Суд: эхо-детектор (тройка членства)')
    p.add_argument('text', help='предъявленный текст части')
    p.add_argument('--id', dest='as_part', help='заявленный адрес части Ч#...')
    p.add_argument('--sender', default='аноним')
    p.set_defaults(fn=cmd_sud)

    p = sub.add_parser('regenerate', help='L5: гибель осколков -> заживление k-из-n')
    p.add_argument('--kill', type=int, default=0, help='сколько осколков убить')
    p.set_defaults(fn=cmd_regenerate)

    p = sub.add_parser('demo', help='пять чудес голографии (без LLM)')
    p.add_argument('--kill', type=int, default=4)
    p.set_defaults(fn=cmd_demo)

    p = sub.add_parser('selftest', help='30 детерминированных проверок органов (офлайн)')
    p.set_defaults(fn=cmd_selftest)

    args = ap.parse_args()
    sys.exit(args.fn(args) or 0)


if __name__ == '__main__':
    main()
