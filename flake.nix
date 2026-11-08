# SPDX-License-Identifier: MIT
# flake.nix — Polymath OS
#
# Reproducible dev-shell для всей системы. Один `nix develop` (или `direnv allow`)
# ставит все инструменты из Sovereignty Registry (ADR-0002):
#   - Tier 1 (суверенное ядро): git, markdown, SQLite, age, Nix, cosign (keyless),
#     CycloneDX SBOM, Python (stdlib).
#   - Tier 2 (арендуемые сервисы + их offline-fallbacks): act, sops, gitleaks,
#     semgrep, trivy, chezmoi, 1Password CLI (`op`) — каждый с заменой.
#
# Этот flake — материальная проекция Принципа 1 (Repo-as-Everything):
# чистая машина + `git clone` + `nix develop` = готовая среда.
# См. `docs/05-devex-ci.md` §Nix flake, `docs/adr/0002-sovereignty-registry.md`,
# `docs/adr/0011-container-runtime.md`.

{
  description = "Polymath OS — reproducible dev shell (Tier 1 + Tier 2 tools)";

  inputs = {
    # nixos-24.05 — стабильный канал. Версия зафиксирована (Принцип 6: automation
    # over discipline; ADR-0008: version pin). Обновление — через PR с миграцией.
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.05";

    # flake-utils — eachDefaultSystem helper. Замена: manual per-system outputs.
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };

        # Платформа нужна для выбора container runtime (ADR-0011):
        #   macOS  → colima + docker CLI
        #   Linux  → podman (rootless) + docker-compat
        isDarwin = pkgs.stdenv.hostPlatform.isDarwin;
        isLinux = pkgs.stdenv.hostPlatform.isLinux;

        # ──────────────────────────────────────────────────────────────────
        # Базовый набор инструментов — Tier 1 суверенного ядра + Tier 2
        # арендуемых сервисов с offline-fallback. Каждый пакет снабжён
        # комментарием, ЗАЧЕМ он здесь (соответствие Sovereignty Registry).
        # ──────────────────────────────────────────────────────────────────
        baseTools = with pkgs; [
          # ── Tier 1: Суверенное ядро (works offline, no accounts) ──────────
          # git — само ядро. Format: git objects. Замена: невозможно (база).
          git

          # age — X25519 + ChaCha20-Poly1305. Format: encrypted blobs.
          # Замена: minisign / GPG. SOPS backend (см. ниже).
          age

          # gnupg — fallback для age, если требуется PGP-совместимость.
          # Tier 1 fallback (см. ADR-0002 Tier 1 table).
          gnupg

          # cosign (keyless OIDC) — Sigstore bundle (open format).
          # Подпись контейнеров, attestation SBOM, SLSA provenance (ADR-0004).
          # Замена: minisign (offline fallback).
          cosign

          # cycloneDX SBOM — JSON формат. CI генерирует через @cyclonedx/cyclonedx-npm,
          # но `trivy` тоже умеет его эмитить (см. ниже). Утилита здесь для локальной
          # генерации SBOM вне pnpm.
          # (cyclonedx-cli не в base nixpkgs; используем trivy --format cyclonedx)

          # python311 — Tier 1 (standard library only). SINGULYAR EIR runtime/
          # работает на чистой стандартной библиотеке без pip-зависимостей.
          python311

          # ── Tier 2: Арендуемые сервисы + их offline-fallback ─────────────

          # GitHub Actions CI → Woodpecker/Forgejo. Локальный fallback: `act`.
          # Запускает .github/workflows/*.yml локально в Docker-совместимом runtime.
          act

          # 1Password (secrets vault) → Bitwarden/Vaultwarden. CLI `op` для
          # chezmoi template-secret extraction. Замена: age-encrypted files in git.
          _1password-cli

          # sops — SOPS+age git-ops secrets. Шифрует YAML/JSON in-place.
          # Замена: age напрямую для single-file.
          sops

          # ── Static analysis / supply chain (Tier 2 security tooling) ─────

          # semgrep — SAST. Быстрый ruleset-based сканер. CI использует `auto`.
          semgrep

          # trivy — Container/FS/IaC scanner. Эмитит CycloneDX SBOM через
          # `--format cyclonedx`. Замена: grype (не включён для минимализма).
          trivy

          # gitleaks — secret scanner (pre-commit + CI). Замена: trufflehog.
          # ADR-0009: negative test на __CANARY__secret__ перед публикацией vault.
          gitleaks

          # ── Container runtime per ADR-0011 ───────────────────────────────
          # colima (macOS) и podman (Linux) добавлены ниже отдельно по платформе.
          # docker-client — CLI совместимость (нужен act, devcontainer, Testcontainers).
          docker-client

          # dive — inspect container image layers. Dev-tool, не критичен.
          dive

          # ── Local K8s dev loop (Tilt) ────────────────────────────────────
          # k3s — lightweight K8s. Замена: kind, minikube. ADR-0011 упоминает.
          k3s

          # tilt — hot-reload в k8s. `tilt up` запускает dev loop (Makefile: `make dev`).
          tilt

          # ── Dev languages / build tools (Layer 1: monorepo) ──────────────
          # go_1_22 — Tier 2 language. Используется в adapter-layer (ADR-0008)
          # и потенциально в tooling/agents/. golangci-lint — default линтер.
          go_1_22
          golangci-lint

          # air — Go live-reload. `air` перезапускает go-процесс при изменении файлов.
          air

          # node_20 — Tier 2 (Layer 1 monorepo: pnpm + turbo + changesets).
          # Движок для apps/ и packages/. Версия зафиксирована ≥20 (package.json engines).
          node_20

          # pnpm — PM для monorepo (Принцип 2 repo-structure).
          # Версия ≥9 (package.json packageManager: pnpm@9.12.0).
          pnpm

          # turbo — build system монорепо. Vercel Turbo. Замена: nx/bazel.
          # Включён и здесь (flake), и как devDependency (npm) — для полной оффлайн-сборки.
          turbo

          # ── Dotfiles / dev shell ─────────────────────────────────────────
          # chezmoi — dotfiles manager. `chezmoi init --apply` на новой машине
          # (Принцип 1, ADR-0006 self-bootstrap). Замена: yadm, stow.
          chezmoi

          # direnv — auto-load env on `cd`. Парный с `nix-direnv` (см. ниже)
          # для кэширования `nix develop`. См. .envrc.
          direnv

          # nix-direnv — extension для direnv, кэширует nix-shell build.
          # Без него каждый `cd` пересобирает dev-shell (30+ секунд).
          nix-direnv

          # ── CLI utilities (Quality-of-life, search, JSON/YAML processing) ─
          # jq — JSON processor. Стандарт для парсинга CI outputs, SBOM, etc.
          jq

          # yq — YAML processor (Go version, mikefarah/yq). Парсинг k8s manifests,
          # CI configs, .sops.yaml. В nixpkgs `yq` — python version (kislyuk/yq);
          # берём `yq-go` для совместимости с k8s-ecosystem.
          yq-go

          # gh — GitHub CLI. Замена: hub, raw `curl` against API.
          # Tier 2 fallback: git over SSH.
          gh

          # ripgrep — fast search (rg). Замена: grep.
          ripgrep

          # fd — fast find. Замена: find.
          fd

          # fzf — fuzzy finder. UX-layer над ripgrep/fd/git.
          fzf
        ];

        # ────────────────────────────────────────────────────────────────────
        # Container runtime per ADR-0011: colima (macOS) / podman (Linux).
        # На других платформах (например, aarch64-darwin на ARM) тоже colima.
        # ────────────────────────────────────────────────────────────────────
        containerRuntime =
          pkgs.lib.optionals isDarwin [ pkgs.colima ] ++
          pkgs.lib.optionals isLinux  [ pkgs.podman pkgs.podman-compose ];
      in
      {
        # ── devShells.default: один shell, который ставит всё ───────────────
        # Запуск: `nix develop` или автоматически через `direnv allow` (см. .envrc).
        # Смежный flake: `infra/flake.nix` — узкий dev-shell только для IaC
        # (OpenTofu, terragrunt, helm, kubectl, k9s). Запуск: `nix develop ./infra`.
        devShells.default = pkgs.mkShell {
          name = "polymath-os-dev";
          meta.description = "Polymath OS — full dev shell (Tier 1 sovereign core + Tier 2 fallbacks)";

          # buildInputs — пакеты, которые попадут в PATH внутри dev-shell.
          # (mkShell поддерживает и `packages` как современный alias, но
          # task spec требует именно `buildInputs` для back-compat с legacy nix.)
          buildInputs = baseTools ++ containerRuntime;

          # shellHook — bash-скрипт, выполняется при входе в shell.
          # Ставит env vars, печатает banner, подсказывает про container runtime.
          # НЕ должен падать (Makefile bootstrap вызывает `nix develop --command true`).
          shellHook = ''
            # ─── Polymath OS — dev shell ────────────────────────────────────
            # Repo-as-Everything (Принцип 1): чистая машина + git clone + nix develop
            # = готовая среда. См. docs/05-devex-ci.md, ADR-0002 Sovereignty Registry.

            # Корень репо (для путей к .local-state, .env.local, etc.)
            export POLYMATH_OS_ROOT="$PWD"

            # ── Env vars (override через .env.local, см. .envrc) ───────────
            # DATABASE_URL — turbo.json globalEnv. По умолчанию — локальная SQLite
            # (runtime/src/sqlite_ledger.py, Tier 1 sovereign core).
            export DATABASE_URL="sqlite:''${POLYMATH_OS_ROOT}/.local-state/polymath.db"

            # OTEL_EXPORTER_OTLP_ENDPOINT — turbo.json globalEnv.
            # OTel collector (Grafana LGTM, ADR-0012 cross-cutting observability).
            # Default: localhost gRPC. Override в .env.local для remote collector.
            export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"

            # Tracing: every span carries intent_id / capability_id / evidence_verdict
            # (ADR-0008 — наш собственный атрибут-набор, не OTel GenAI semconv).
            export OTEL_SERVICE_NAME="polymath-os-dev"

            # Локальная state-директория (gitignored, см. .gitignore).
            mkdir -p "''${POLYMATH_OS_ROOT}/.local-state"

            # ── Container runtime per ADR-0011 ──────────────────────────────
            # macOS: colima (start manually: `colima start --cpu 4 --memory 8`)
            # Linux:  podman (rootless, socket auto-created by systemd user unit)
            if command -v podman >/dev/null 2>&1; then
              export DOCKER_HOST="unix://''${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/podman/podman.sock"
            fi
            # colima на macOS экспортирует DOCKER_HOST автоматически через
            # `colima start`, поэтому тут ничего не делаем — пользователь запускает сам.

            # ── Banner (минимальный, чтобы не засорять `nix develop --command true`) ─
            if [ -n "''${POLYMATH_BANNER_SHOWN:-}" ]; then
              :
            else
              export POLYMATH_BANNER_SHOWN=1
              echo ""
              echo "  Polymath OS — dev shell (nixos-24.05)"
              echo "  Tier 1+2 tools ready. Container runtime per ADR-0011."
              echo "  Verify everything:   make verify"
              echo "  Local CI replica:    make ci-local"
              echo "  Dev loop (Tilt):    make dev"
              echo ""
            fi
          '';
        };

        # ── formatter: nixpkgs-fmt для самой flake и *.nix файлов ──────────
        # Запуск: `nix fmt`. Принцип 6 (automation over discipline).
        formatter = pkgs.nixpkgs-fmt;
      });
}
