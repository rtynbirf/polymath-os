# POLIMAT_PIPELINE — канон механизма заливки в репо (v1.1)

Linux-воспроизведение Windows-пака владельца (`POLIMAT_AUTO_PUSH.bat` /
`POLIMAT_FINISH.bat` / `POLIMAT_MERGE.bat`, снапшот `123.7z`) — тот же
порядок шагов, та же идемпотентность, тот же verify-гейт, без Windows.
Выучен по интеграции PR#15 (merged `7e8c9254`) и оформлен как
многоразовый инструмент канона.

## Канон механизма (9 шагов)

1. Клон (идемпотентно: есть — `fetch --prune` + `pull --ff-only`; нет — лестница попыток)
2. Ремонт состояния: снос `.git/rebase-apply|merge` прерванных операций
3. Ветка `feat/<scope>-<kebab>` (жизнь ≤24ч по CONTRIBUTING)
4. Коммиты: Conventional Commits + DCO (`-s`); патчи — `git am` как готовые
   коммиты, повторно НЕ применяются, если контент уже в ветке
5. **Verify-гейт**: `make verify` ≠ 0 → пуша НЕТ («НЕ СЛОМАЙ verify»)
6. Пуш ×3 с ретраями; токен ТОЛЬКО в памяти процесса
7. PR по шаблону триажа (обновление существующего, если открыт)
8. merge-режим: squash-merge + удаление ветки; идемпотентно к «уже влито»
9. Пост-пуш audit: свежий клон + `make verify` + пересчёт пломб SHA256SUMS

## Команды

```
prepare  --repo OWNER/REPO --branch feat/xxx [--workdir DIR]
commit   --workdir DIR --message FILE --paths p1 ...   (или --patch FILE)
verify   --workdir DIR              # гейт; EXIT≠0 блокирует пуш
push     --workdir DIR --repo OWNER/REPO
pr       --workdir DIR --repo OWNER/REPO --body PR_BODY.md [--title T]
merge    --repo OWNER/REPO --branch feat/xxx [--pr N]
audit    --repo OWNER/REPO          # свежий клон + verify + пломбы
```

Секреты: только `POLIMAT_TOKEN` (env; не argv, не файл, не `.git/config`).
Идентичность: `POLIMAT_GIT_NAME` / `POLIMAT_GIT_EMAIL` (дефолт — DCO канона).

## Верификация

`python3 selftest.py` → `12/12 PASS` (офлайн: без сети, без токена,
без GitHub). Встроен в канон как **claim #29** (`make verify`).

## Журнал дефектов

- **D1 (v1.0, закрыт в v1.1)**: идемпотентность патчей детектировалась
  строкой `"already applied"`, которую `git am` не печатает — реальное
  сообщение для уже применённого патча: `patch does not apply`. Пойман
  машиной при построении T12; лечение — проверка по содержимому
  `git apply --reverse --check` (обратное применение валидно ⇔ контент
  уже в ветке). Доказано T12: повторный `commit --patch` по влитому
  патчу — без дубля коммита и без падения.

## Пломба

`SHA256SUMS.txt` — sha256 трёх файлов модуля; пересчёт:
`sha256sum -c SHA256SUMS.txt` из этого каталога.
