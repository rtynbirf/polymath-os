# infra/flake.nix — Polymath OS Layer 4 (Infra)
#
# Отдельный flake для инфраструктурного dev-shell.
# Отделяет рантайм инфра-инструментов от рантайма приложений:
#   - nix develop ./infra#      -> only infra tooling
#   - nix develop                -> root dev shell (apps)
#
# Sovereignty Registry tier:
#   - OpenTofu, terragrunt, helm, kubectl, k9s, jq — OSS (Tier 1 / OSS dev tooling)
#   - aws-cli, cloudflare/wrangler — vendor CLIs, но open-source, без аккаунта работают только против local stack
#   - Все эти инструменты — fork-exec от человека (ADR-0002 §Tier 2 — rented services для backend, но CLI сам по себе OSS).
{
  description = "Polymath OS — Infra dev shell (OpenTofu, terragrunt, k8s, DNS)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.05";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
      in
      {
        devShells.default = pkgs.mkShell {
          name = "polymath-infra";
          meta.description = "OpenTofu + terragrunt + k8s + DNS tooling for Polymath OS infra/";

          packages = with pkgs; [
            # IaC core (OSS, drop-in совместим с Terraform 1.6+)
            opentofu          # OpenTofu — fork of Terraform, BSL-safe
            terragrunt        # DRY layer over OpenTofu, keep state DRY across envs

            # Cloud CLIs (OSS, vendor-bound; per ADR-0002 Tier 2)
            awscli             # S3 backend + DynamoDB lock table
            wrangler           # Cloudflare Workers / Pages / DNS

            # Kubernetes
            kubernetes-helm   # Helm 3 — deploy Vault, Unleash via charts
            kubectl            # k3s / k8s control
            k9s                # TUI for k8s — quick triage

            # Secrets (SOPS + age — Tier 1 sovereign core)
            sops               # Encrypt secrets at rest in git
            age                # X25519 + ChaCha20-Poly1305 — sovereign crypto

            # Data plumbing
            jq                 # JSON parsing for tfstate / k8s / sops outputs
            yq-go              # YAML parsing for compose / k8s / helm

            # Linting / formatting for HCL
            terraform-docs     # Generate module docs
            tflint             # Static analysis for HCL (OpenTofu-compatible)
          ];

          shellHook = ''
            echo ""
            echo "  ╭─ Polymath OS — infra dev shell"
            echo "  │  tofu  $(tofu version 2>/dev/null | head -1 | awk '{print $2}')"
            echo "  │  tg    $(terragrunt --version 2>/dev/null | head -1 | awk '{print $2}')"
            echo "  │  helm  $(helm version 2>/dev/null | sed -E 's/.*v([0-9]+\.[0-9]+\.[0-9]+).*/\1/' | head -1)"
            echo "  │  kubectl $(kubectl version --client --short 2>/dev/null | awk '{print $3}' | tr -d 'v' || echo 'pending')"
            echo "  │"
            echo "  ╰─ cd infra/tofu/environments/personal && tofu init"
            echo ""
          '';
        };

        # Convenience app: format check
        apps.default = {
          type = "app";
          program = toString (pkgs.writeShellScript "infra-fmt-check" ''
            set -euo pipefail
            cd "$(git rev-parse --show-toplevel)/infra/tofu"
            echo "→ tofu fmt -check -recursive"
            tofu fmt -check -recursive
            echo "→ tflint --recursive"
            tflint --recursive
          '');
        };
      });
}
