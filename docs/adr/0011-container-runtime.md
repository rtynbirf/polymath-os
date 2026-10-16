# ADR-0011: Container runtime — colima / podman / containerd+nerdctl

**Date:** 2026-10-16
**Status:** Accepted
**Deciders:** @USER
**Audit:** A11 (Docker Desktop vs act/devcontainer/Testcontainers)

## Context

Polymath OS отчёт заявлял «Не ставим Docker Desktop (используем colima / podman / Linux native)», но при этом требует:
- `act` (nektos/act) для локальной отладки GitHub Actions
- devcontainer.json (Codespaces / DevPod / VS Code / Cursor)
- Testcontainers для integration tests

Все эти инструменты **требуют container runtime**. Без явного указания, какой именно:
- На macOS по умолчанию — Docker Desktop (что противоречит A11)
- На Linux — varies (Docker daemon, Podman, containerd)
- В CI — GitHub-runner defaults

Это **непроизводительный стандарт**: каждый разработчик/CI может оказаться на разном runtime, что ломает reproducibility.

## Decision

### Container runtime — зафиксирован по платформе

| Платформа | Runtime | Зачем |
|---|---|---|
| **macOS** (dev) | **colima** + Docker CLI | Open-source, не требует лицензии Docker Desktop, работает с `act`, devcontainer, Testcontainers через `DOCKER_HOST` |
| **Linux** (dev, CI runners) | **podman** + `podman-docker` compat | Rootless по умолчанию, OSS, drop-in совместим с docker CLI |
| **Linux alt** (servers, k3s nodes) | **containerd** + `nerdctl` | Минимум overhead, production-grade, native в k8s |
| **CI (GitHub Actions)** | default runner image (Docker) | Оставляем, но **тестируем** совместимость с colima/podman локально |

### Фиксация в `flake.nix`

```nix
# flake.nix
devShell = pkgs.mkShell {
  buildInputs = with pkgs; [
    colima            # macOS
    podman            # Linux
    docker-client     # CLI compatibility
    act               # GHA local runner
    dive              # image inspector
  ];
};
```

### Фиксация в `chezmoi` (dotfiles)

`run_once-install-container-runtime.sh.tmpl`:
```bash
{{ if eq .chezmoi.os "darwin" -}}
brew install colima docker docker-compose
colima start --cpu 4 --memory 8 --disk 60
{{ else if eq .chezmoi.os "linux" -}}
sudo apt install -y podman podman-docker uidmap
{{ end -}}
```

### devcontainer.json — явно указывает runtime

```jsonc
{
  "name": "Polymath OS Dev",
  "image": "...",
  "features": {
    "ghcr.io/devcontainers/features/docker-outside-of-docker:1": {
      "version": "latest"
    }
  }
}
```

DevPod указывает провайдера явно: `devpod up . --provider docker` (colima/podman).

## Consequences

- **Positive:**
  - Reproducibility: каждый dev/CI на одном и том же runtime (или совместимом)
  - colima и podman — OSS, без лицензионных рисков Docker Desktop
  - podman rootless — меньше attack surface
- **Negative:**
  - colima на macOS медленнее Docker Desktop при некоторых операциях (например, volume mounts)
  - podman не 100% drop-in для Docker (some edge cases, особенно с compose v2)
  - Containerd+nerdctl — минимальный, но требует больше ручной настройки
- **Neutral:**
  - CI на GitHub Actions runner — default Docker. Это fine, потому что **локально** мы на colima/podman, а CI-Docker совместим с обоими.

## Alternatives Considered

### Docker Desktop (macOS) + Docker daemon (Linux)
Отвергнуто: лицензионные ограничения Docker Desktop (2022+ для enterprise), не OSS.

### Только podman (везде)
Отвергнуто: на macOS podman менее стабильный, чем colima.

### Без container runtime (только Nix)
Отвергнуто: act, devcontainer, Testcontainers — реально нужны. Nix — для dev shell, не для container orchestration.

## References

- Audit: `runtime/docs/AUDIT_POLYMATH.md` §A11
- colima: https://github.com/abiosoft/colima
- podman: https://podman.io/
- nerdctl: https://github.com/containerd/nerdctl
- act: https://github.com/nektos/act
- DevPod: https://github.com/loft-sh/devpod
- Testcontainers: https://testcontainers.com
