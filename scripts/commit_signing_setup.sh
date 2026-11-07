#!/usr/bin/env bash
# commit_signing_setup.sh — сетап SSH-подписи коммитов (docs/COMMIT_SIGNING.md).
# Генерирует ключ ТОЛЬКО для подписей, печатает pubkey и git-команды.
# Приватный ключ остаётся локально и никуда не отправляется.
set -euo pipefail

KEY="${1:-$HOME/.ssh/id_ed25519_signing}"

if [ -f "$KEY" ]; then
  echo "Ключ уже существует: $KEY — переиспользую."
else
  ssh-keygen -t ed25519 -C "commit signing (polymath-os)" -f "$KEY" -N ""
  echo "Ключ создан: $KEY (приватный, не для auth)"
fi

echo
echo "══ 1. Добавь ПУБЛИЧНЫЙ ключ в GitHub: Settings → SSH and GPG keys → New SSH key → тип «Signing Key» ══"
echo
cat "${KEY}.pub"
echo
echo "══ 2. git config (выполни в репо или глобально) ══"
echo
echo "git config gpg.format ssh"
echo "git config user.signingkey ${KEY}.pub"
echo "git config commit.gpgsign true"
echo "git config tag.gpgsign true"
echo
echo "══ 3. Проверка ══"
echo
echo "git commit --allow-empty -S -m 'test: verify signing' && git log --show-signature -1"
