# Установка Nix для bootstrap

> Учитель OpenSSF Scorecard (Pinned-Dependencies): репозиторий не выполняет
> `curl | sh` и не скачивает исполняемые файлы «на лету» — это фиксируется
> проверкой и это правильная практика. Nix ставится один раз вручную, с пином
> релиза `nix-installer` и проверкой официального sha256-дайджеста.

## Вариант 1 (рекомендуемый): nix-installer с sha256-пином

Релиз: **v3.24.2** (Determinate Systems, опубликован 2026-11-05). Дайджесты
взяты из GitHub Releases API (поле `digest` ассета), а не переписаны вручную:

| Платформа | Артефакт | sha256 |
| --- | --- | --- |
| x86_64-linux | `nix-installer-x86_64-linux` | `22ed14ee1b24d100d388f1fc245e3062bd5982433d159cffa6dec34c0eb15dab` |
| aarch64-linux | `nix-installer-aarch64-linux` | `bc18d8d8ca12f95d219b5978201e15d0049b2e9d8b7c49593f26503c87172145` |
| aarch64-darwin (Apple Silicon) | `nix-installer-aarch64-darwin` | `0163fb800be1749880fb51cd529a88fd4dace474601a144d0db9929006eba775` |

```bash
VERSION="v3.24.2"
case "$(uname -s)-$(uname -m)" in
  Linux-x86_64)   PKG="nix-installer-x86_64-linux";   SHA="22ed14ee1b24d100d388f1fc245e3062bd5982433d159cffa6dec34c0eb15dab" ;;
  Linux-aarch64)  PKG="nix-installer-aarch64-linux";  SHA="bc18d8d8ca12f95d219b5978201e15d0049b2e9d8b7c49593f26503c87172145" ;;
  Darwin-arm64)   PKG="nix-installer-aarch64-darwin"; SHA="0163fb800be1749880fb51cd529a88fd4dace474601a144d0db9929006eba775" ;;
  *) echo "unsupported platform"; exit 1 ;;
esac
curl -fsSL -o "/tmp/$PKG" \
  "https://github.com/DeterminateSystems/nix-installer/releases/download/${VERSION}/${PKG}"

# sha256sum (GNU/Linux) или shasum -a 256 (macOS)
if command -v sha256sum >/dev/null 2>&1; then
  echo "$SHA  /tmp/$PKG" | sha256sum -c - || { echo "sha256 MISMATCH"; exit 1; }
else
  echo "$SHA  /tmp/$PKG" | shasum -a 256 -c - || { echo "sha256 MISMATCH"; exit 1; }
fi

chmod +x "/tmp/$PKG" && "/tmp/$PKG" install --no-confirm
```

При выходе новых версий `nix-installer` обновляйте и версию, и дайджесты —
источник: <https://github.com/DeterminateSystems/nix-installer/releases>
(у каждого ассета есть поле digest в API Releases).

## Вариант 2: официальные установщики NixOS

Следуйте инструкции для вашей платформы: <https://nixos.org/download>.

## Дальше

```bash
./scripts/bootstrap.sh
```

Bootstrap поставит `direnv` + `nix-direnv` + `chezmoi` из фиксированной
ревизии nixpkgs (`NIXPKGS_REV` в `scripts/bootstrap.sh`, ветка `nixos-24.05` —
та же, что вход `flake.nix`), соберёт dev-shell и прогонит `make verify`.
