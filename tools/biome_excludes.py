#!/usr/bin/env python3
"""biome_excludes.py — единый источник правды для files.includes в biome.json.

П-16 (polimat-hub#34): корневые файловые исключения biome ("!README.md",
"!PULSE.md", ...) выводятся из сечения ``generated`` в MANIFEST.json, а не
ведутся руками. Инфраструктурные исключения ("!**/node_modules" и т.п.)
остаются в biome.json как есть — инструмент их не трогает и не переставляет.

Целевой вид files.includes:
  ["**"] + инфраструктурные исключения (в исходном порядке, как есть)
         + ["!" + path] для каждого элемента generated (в порядке MANIFEST).

Корневые файловые исключения "!<имя>" (без "/"), которых нет в generated,
считаются ручными и удаляются.

Usage:
  python3 tools/biome_excludes.py --write   # перестроить biome.json
  python3 tools/biome_excludes.py --check   # rc=0 если biome.json == целевой, rc=2 если нет

Только stdlib. Запись атомарная (tmp + os.replace), json.dumps(indent=2,
ensure_ascii=False) + "\\n". Идемпотентно: повторный --write не меняет байты.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "MANIFEST.json"
BIOME_PATH = REPO_ROOT / "biome.json"

HEAD_INCLUDE = "**"


def _load_json(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    try:
        data = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise SystemExit(f"error: {path.name}: невалидный JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"error: {path.name}: ожидается JSON-объект верхнего уровня")
    return data, raw


def generated_paths(manifest: dict[str, Any]) -> list[str]:
    section = manifest.get("generated")
    if section is None:
        raise SystemExit(
            "error: MANIFEST.json: нет сечения 'generated' — целевой excludes не построить"
        )
    if not isinstance(section, list):
        raise SystemExit("error: MANIFEST.json: 'generated' должен быть массивом объектов")
    paths: list[str] = []
    for i, item in enumerate(section):
        if not isinstance(item, dict):
            raise SystemExit(f"error: MANIFEST.json: generated[{i}] — не объект")
        path = item.get("path")
        if not isinstance(path, str) or not path:
            raise SystemExit(f"error: MANIFEST.json: generated[{i}].path — не строка")
        if path not in paths:
            paths.append(path)
    return paths


def is_infra_exclude(pattern: str) -> bool:
    """Инфраструктурное исключение: '!'-паттерн с '/' внутри (каталог/glob)."""
    return pattern.startswith("!") and "/" in pattern[1:]


def target_includes(current: list[Any]) -> list[str]:
    manifest, _ = _load_json(MANIFEST_PATH)
    gen = generated_paths(manifest)

    head: list[str] = []
    infra: list[str] = []
    for entry in current:
        if not isinstance(entry, str):
            raise SystemExit("error: biome.json: files.includes содержит не-строку")
        if entry == HEAD_INCLUDE and not head:
            head.append(entry)
            continue
        if is_infra_exclude(entry):
            infra.append(entry)

    generated_excludes = ["!" + p for p in gen if "/" not in p]
    seen = set(infra) | set(generated_excludes)
    for p in gen:
        if "/" in p and ("!" + p) not in seen:
            generated_excludes.append("!" + p)

    return head + infra + generated_excludes


def canonical_bytes(doc: dict[str, Any], includes: list[str]) -> bytes:
    target = json.loads(json.dumps(doc))  # deep copy без внешних зависимостей
    target.setdefault("files", {})["includes"] = includes
    return (json.dumps(target, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def atomic_write(path: Path, payload: bytes) -> None:
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)  # атомарно на той же файловой системе
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def diff_description(current_raw: bytes, target_raw: bytes) -> str:
    cur = current_raw.decode("utf-8", errors="replace").splitlines()
    tgt = target_raw.decode("utf-8", errors="replace").splitlines()
    cur_set, tgt_set = set(cur), set(tgt)
    removed = [line for line in cur if line not in tgt_set and line.strip()]
    added = [line for line in tgt if line not in cur_set and line.strip()]
    lines = ["biome.json отличается от целевого:"]
    if removed:
        lines.append("  удалить:")
        lines += [f"    - {line}" for line in removed]
    if added:
        lines.append("  добавить:")
        lines += [f"    + {line}" for line in added]
    if not removed and not added:
        lines.append("  (содержимое то же, отличается форматирование/порядок байт)")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync biome.json files.includes from MANIFEST.json generated section"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--write", action="store_true", help="перестроить biome.json (атомарно, идемпотентно)"
    )
    group.add_argument(
        "--check", action="store_true", help="rc=0 если biome.json равен целевому, иначе rc=2"
    )
    args = parser.parse_args()

    doc, raw = _load_json(BIOME_PATH)
    files = doc.get("files")
    if not isinstance(files, dict) or not isinstance(files.get("includes"), list):
        raise SystemExit("error: biome.json: нет files.includes (массив)")
    includes = target_includes(files["includes"])
    target = canonical_bytes(doc, includes)

    if args.check:
        if raw == target:
            print("biome.json: OK — совпадает с целевым (по MANIFEST.json generated)")
            return 0
        print(diff_description(raw, target), file=sys.stderr)
        return 2

    atomic_write(BIOME_PATH, target)
    # Валидация после записи: файл читается, JSON валиден, includes == целевой
    verify_doc, verify_raw = _load_json(BIOME_PATH)
    if verify_raw != target:
        raise SystemExit("error: biome.json после записи не совпадает с целевыми байтами")
    if verify_doc.get("files", {}).get("includes") != includes:
        raise SystemExit("error: biome.json после записи: files.includes != целевой")
    print(f"biome.json: записан целевой files.includes ({len(includes)} entries: head+infra+generated)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
