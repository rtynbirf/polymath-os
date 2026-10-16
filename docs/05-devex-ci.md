# DevEx / CI / IaC / Dotfiles — Layer 4

> Best-in-class практики для DevEx, CI/CD, security, observability, IaC, dotfiles (2024-2026).

---

## Принципы

1. **Everything in repo.** Конфигурация CI, IaC, линтеров, dotfiles, devcontainer — всё в git. Машина = функция от `git clone`.
2. **Least privilege & short-lived secrets.** OIDC trust, динамические секреты. Секрет, не меняющийся за 90 дней, = скомпрометирован.
3. **Fail fast, fail local.** `act` / `dagger` / `tilt up` воспроизводят 90% CI.
4. **Immutable artifacts + cryptographic provenance.** Контейнер с digest, SBOM, SLSA, cosign. Не верифицируется → не деплоится.
5. **Trunk-based + feature flags.** `main` всегда зелёный и деплоится. Незавершённое — за флагом, не за long-lived branch.
6. **Observability-first.** OTel SDK в сервисе до того, как написан бизнес-код.
7. **Reversibility.** IaC-apply = `destroy`-able. Deploy = `rollback`-able ≤60 сек. Dotfiles = `chezmoi forget`-able.

## Стек (Polymath OS defaults)

| Категория | Tool | Зачем |
|---|---|---|
| CI/CD | **GitHub Actions** + reusable workflows + composite actions | Default для OSS, 90% нужд закрывают через DRY |
| Local CI runner | **act** (nektos/act) | Локальная отладка GHA в Docker |
| CI alt (self-host) | **Woodpecker CI** + Forgejo | Self-host forges, GHA-совместимый синтаксис |
| Pipeline-as-code | **Dagger** | CI-agnostic, на Go/Python/TS вместо YAML |
| Secrets (git-ops) | **SOPS + age** | Зашифрованные секреты в репо |
| Secrets (CI injection) | **Doppler** / 1Password CI/CD | Zero-ops sync в CI |
| Secrets (dynamic) | **HashiCorp Vault** / Infisical | Enterprise, динамические |
| SAST | **Semgrep** + CodeQL | Быстрый + глубокий dataflow |
| Container scan | **Trivy** | Образы + IaC + fs |
| Secret scan | **gitleaks** + Trufflehog | Pre-commit + CI |
| Python lint | **Ruff** | Дефолт-замена flake8+isort+black, на порядки быстрее |
| JS/TS lint | **Biome** | Drop-in для ESLint+Prettier |
| Structural lint | **ast-grep** | Custom rules, codemods |
| IaC | **OpenTofu** (Terraform fork) | Drop-in совместим, OSS, без BSL lock-in |
| IaC alt | **Pulumi** | Если команде комфортнее real languages |
| Dev shell | **Nix Flakes** + direnv | Reproducible на macOS/Linux/WSL2 |
| Dotfiles | **chezmoi** + age + 1Password CLI | `chezmoi init --apply` на новой машине |
| Dev env spec | **devcontainer.json** | Codespaces + DevPod + Cursor + VS Code |
| Dev env platform | **DevPod** (OSS) + Codespaces (cloud) | Multi-backend, identity-окружение |
| Local K8s dev | **Tilt** | Hot-reload в kind/k3s/minikube |
| Multi-container | **Docker Compose v2** | Non-K8s локальная разработка |
| Integration tests | **Testcontainers** | Real Postgres/Redis/Kafka в CI |
| Feature flags | **Unleash** (self-hosted) | Trunk-based dev без long-lived branches |
| Observability | **OpenTelemetry** SDK | Vendor-neutral instrumentation |
| Self-host obs stack | **Grafana LGTM** (Loki+Tempo+Mimir) | Unified self-hosted |
| Error tracking | **Sentry** / Glitchtip | Exception tracking |
| Uptime | **BetterStack** | Solo/indie мониторинг |
| Artifact signing | **cosign** + Sigstore | Keyless OIDC signing |
| SBOM | **CycloneDX** + `@cyclonedx/cyclonedx-npm` | App security focus |
| Supply chain | **SLSA framework** | Provenance levels 1-4 |

## Паттерны

### Reusable workflow + composite action (GitHub Actions)

`.github-templates` репо на уровне org: reusable workflows (целые pipelines) + composite actions (задачи). Версии фиксируются тегами `v1`, `v2`.

```yaml
# .github/actions/setup-node-pnpm/action.yml
inputs:
  node-version: { required: false, default: '20' }
runs:
  using: composite
  steps:
    - uses: pnpm/action-setup@v4
      with: { version: 9 }
    - uses: actions/setup-node@v4
      with: { node-version: ${{ inputs.node-version }}, cache: pnpm }
    - shell: bash
      run: pnpm install --frozen-lockfile
```

### OIDC trust (zero long-lived secrets)

GitHub Actions → AWS через OIDC. Никаких `AWS_ACCESS_KEY_ID` в репо.

```yaml
permissions:
  id-token: write
  contents: read
jobs:
  deploy:
    steps:
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/gha-deploy
          aws-region: us-east-1
```

### Cosign keyless + SBOM + SLSA

```yaml
- uses: sigstore/cosign-installer@v3
- uses: anchore/sbom-action@v0
  with: { image: ghcr.io/my-org/app:${{ github.sha }}, format: cyclonedx-json, output-file: sbom.json }
- run: cosign sign --yes ghcr.io/my-org/app:${{ github.sha }}
- run: cosign attest --predicate sbom.json --type cyclonedx ghcr.io/my-org/app:${{ github.sha }}
```

### SOPS + age (git-ops secrets)

```bash
age-keygen -o ~/.config/sops/age/keys.txt   # НЕ коммитить
cat > .sops.yaml <<'YAML'
creation_rules:
  - path_regex: secrets/.*\.yaml$
    age: age1qz...your-public-key
YAML
sops secrets/prod.yaml    # editor → зашифрует на сохранение
sops -d secrets/prod.yaml  # decrypt на лету
```

### Nix flake как reproducible dev shell

```nix
{
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.05";
  inputs.flake-utils.url = "github:numtide/flake-utils";
  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let pkgs = import nixpkgs { inherit system; }; in {
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [ go_1_22 golangci-lint air k3s tilt cosign trivy semgrep ];
        };
      });
}
```

Запуск: `nix develop` или через `direnv` + `nix-direnv` автоматически при `cd`.

### chezmoi + age + 1Password CLI

```bash
chezmoi init --ssh git@github.com:myuser/dotfiles
chezmoi init --apply git@github.com:myuser/dotfiles  # на новой машине
```

`run_once-install-packages.sh.tmpl` ставит brew/apt пакеты по OS detection. Секреты через `chezmoi secret op item get`.

### devcontainer.json

```jsonc
{
  "name": "Polymath OS Dev",
  "image": "mcr.microsoft.com/devcontainers/go:1.22",
  "features": {
    "ghcr.io/devcontainers/features/docker-outside-of-docker:1": {},
    "ghcr.io/devcontainers-contrib/features/tilt:1": {}
  },
  "postCreateCommand": "make bootstrap",
  "forwardPorts": [8080, 5432],
  "customizations": { "vscode": { "extensions": ["golang.go"] } }
}
```

Работает в Codespaces, DevPod, VS Code, Cursor — identity-окружение.

### Tiltfile (inner dev loop)

```python
docker_build('app', '.', live_update=[
  sync('./cmd', '/app/cmd'),
  sync('./internal', '/app/internal'),
  run('go build -o /app/bin/app ./cmd/app')
])
k8s_yaml('deploy/k8s')
k8s_resource('app-deployment', port_forwards='8080:8080')
local_resource('postgres', 'docker run -p 5432:5432 -e POSTGRES_PASSWORD=dev postgres:16')
```

## Anti-patterns

1. Monolithic pipeline (500-строчный `build-deploy.yml` без DRY)
2. Long-lived branches + manual release
3. Секреты в YAML / env-files в репо
4. No caching = 18-минутные пайплайны
5. Gold-image gaps (self-hosted runner со старыми пакетами)
6. Manual deploys по кнопке
7. Earthly (deprecated Jul 16, 2025)
8. `fmt.Println` как observability
9. Snowflake laptops (неделя настройки новой машины)
10. Long-lived access tokens

## LFS-рекомендации

См. `ROADMAP.md` Фаза 1 (дни 8-21) + Фаза 2 (дни 43-50, 51-60). Резюме:

1. 3 репо источника правды: `dotfiles`, `.github-templates`, `infra`
2. Dotfiles rebuild через `chezmoi init --apply` (одна команда)
3. Dev-shell rebuild через Nix flake + direnv
4. CI rebuild через standardized `.github-templates` (reusable + composite)
5. Security rebuild: SOPS+age + cosign + SBOM в CI
6. IaC rebuild: OpenTofu (drop-in замена Terraform)
7. Observability rebuild: self-host LGTM stack + OTel SDK в каждом сервисе
8. Local dev loop rebuild: Tilt + Docker Compose v2 + Testcontainers
9. Remote dev: DevPod + devcontainer.json (identity-окружение)
10. Single-command bootstrap: `~/.local/bin/new-machine-bootstrap.sh`

## Референсы

- GitHub Actions reusing workflows: https://docs.github.com/en/actions/concepts/workflows-and-actions/reusing-workflow-configurations
- Woodpecker CI: https://woodpecker-ci.org
- Act: https://github.com/nektos/act
- Dagger: https://dagger.io
- SOPS: https://github.com/getsops/sops
- Doppler: https://www.doppler.com
- Infisical: https://infisical.com
- HashiCorp Vault: https://www.vaultproject.io
- Semgrep: https://semgrep.dev
- Trivy: https://github.com/aquasecurity/trivy
- Ruff: https://github.com/astral-sh/ruff
- Biome: https://biomejs.dev
- OpenTofu: https://opentofu.org
- Pulumi: https://www.pulumi.com
- Nix Flakes: https://nixos.wiki/wiki/Flakes
- chezmoi: https://chezmoi.io
- devcontainer.json: https://containers.dev/implementors/json_reference/
- DevPod: https://github.com/loft-sh/devpod
- Tilt: https://tilt.dev
- Testcontainers: https://testcontainers.com
- Unleash: https://www.getunleash.io
- OpenTelemetry: https://opentelemetry.io
- Grafana LGTM: https://grafana.com
- cosign: https://github.com/sigstore/cosign
- SLSA: https://slsa.dev
- CycloneDX: https://cyclonedx.org
