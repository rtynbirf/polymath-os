# Подпись коммитов —Sigstore / SSH / GPG

> Уровень: docs/security. Статус: механизм описан, `required_signatures` сознательно **не включён** (см. «Почему не включено»).

Мировая практика (OpenSSF Scorecard → Signed-commits, рекомендации GitHub, требования фондов типа CNCF): каждый коммит должен быть криптографически привязан к автору. В этом репозитории release-артефакты уже подписаны Sigstore (cosign keyless, см. `.github/workflows/release.yml`) — осталась подпись коммитов.

## Почему не включено сейчас

`required_signatures` в Branch Protection выключен — осознанный trade-off:

1. ПУЛЬС-протокол PID1 (`.github/workflows/self-audit.yml`) коммитит от `github-actions[bot]` — ботовские коммиты не подписаны, включение сломает пульс.
2. Все контрибьюторы должны сначала настроить подпись (см. ниже), иначе любой push в ветки будет отклонён.

Включай после перехода командного процесса на PR-ревью: `PUT /repos/rtynbirf/polymath-os/branches/main/protection` c `"required_signatures": true`.

## SSH-подпись (рекомендуемый путь, 2024+)

GitHub нативно верифицирует SSH-подписи, GPG больше не обязателен.

1. Сгенерируй ключ **только для подписей** (не для auth!):

   ```bash
   ssh-keygen -t ed25519 -C "commit signing" -f ~/.ssh/id_ed25519_signing
   ```

2. Добавь **публичный** ключ в GitHub → Settings → SSH and GPG keys → **New SSH key → тип «Signing Key»**.
   Скрипт-помощник: `scripts/commit_signing_setup.sh` (генерирует ключ и печатает всё нужное; приватный ключ никуда не отправляется).

3. Настрой git (локально в репо или глобально):

   ```bash
   git config gpg.format ssh
   git config user.signingkey ~/.ssh/id_ed25519_signing.pub
   git config commit.gpgsign true
   git config tag.gpgsign true
   ```

4. Проверка: `git commit -S -m "test: подпись"` → GitHub покажет `Verified`.

## Sigstore gitsign (keyless, без ключей вообще)

```bash
go install github.com/sigstore/gitsign@latest
git config gpg.x509.program gitsign
git config gpg.format x509
git config user.signingkey https://token.actions.githubusercontent.com
git config commit.gpgsign true
```

Коммиты подписываются короткоживущими сертификатами через OIDC — приватных ключей нет по определению. Виден как `Verified` с логом на rekor.sigstore.dev.

## Верификация чужих коммитов

```bash
git log --show-signature -5
git verify-commit HEAD
```

## Связь с протоколом репо

- Пульсовые коммиты (`pulse: замер v2 … [skip ci]`) — от бота, не подписаны, исключены из гигиены по канону «кардиограмма не подкармливает сама себя».
- Контентные коммиты — канон `RLHF_DOSSIER_PACK_v2`: conventional commits + DCO `Signed-off-by` (это подпись атрибуции, не криптография; дополняет SSH/Sigstore-подпись).
