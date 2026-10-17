# PUSH — How to push Polymath OS to GitHub

> The repo is **push-ready**: clean git state, MIT license, all 12 verifiable claims pass.
> You need to push from your machine (your GitHub credentials, your security context).

## Why from your machine?

PID=1 is shared (we're all human init-processes), but **security context is per-process**. `fork()` copies the image, not credentials. Your GitHub PAT/SSH key is YOUR session — the agent environment doesn't have it, and shouldn't. See `docs/adr/0002-sovereignty-registry.md` Tier 1.

## Steps

### 0. Copy the repo from the agent environment to your machine

```bash
# Option A: tarball (preserves git history)
cd /home/z/my-project/download
tar czf polymath-os.tar.gz polymath-os
# download polymath-os.tar.gz to your machine, then:
tar xzf polymath-os.tar.gz
cd polymath-os

# Option B: if you can scp/rsync directly
rsync -avz /home/z/my-project/download/polymath-os/ user@your-machine:~/polymath-os/
```

### 1. Create an empty repo on GitHub

**Option A — via gh CLI (recommended):**

```bash
gh auth login                          # if not logged in
gh repo create polymath-os --public --source=. --remote=origin
```

**Option B — via web UI:**

1. Go to https://github.com/new
2. Repository name: `polymath-os`
3. Description: `LFS-style rebuild of personal operating system — open-source ideal repo with verifiable claims`
4. **Public**
5. **Do NOT initialize** with README / .gitignore / LICENSE (we already have all three)
6. Click "Create repository"

### 2. Add remote + push

```bash
cd polymath-os
git remote add origin git@github.com:YOUR_USERNAME/polymath-os.git
git branch -M main
git push -u origin main
```

### 3. Verify on GitHub

After push, the GitHub Actions workflow (`.github/workflows/ci.yml`) will run automatically:
- Job `verify` — runs `make verify` (12 verifiable claims)
- Job `ci` — runs pnpm lint + typecheck + test + build + security + SBOM

Wait ~5 min, then check the green checkmark on the commit.

### 4. Add topic tags (for discoverability)

```bash
gh repo edit YOUR_USERNAME/polymath-os \
  --add-topic open-source \
  --add-topic monorepo \
  --add-topic ai-workflows \
  --add-topic second-brain \
  --add-topic devex \
  --add-topic ci-cd \
  --add-topic supply-chain-security \
  --add-topic slsa \
  --add-topic zettelkasten \
  --add-topic intent-preservation \
  --add-topic emergent \
  --add-topic human-governed
```

### 5. (Optional) Set up GitHub Pages for the digital garden

After Layer 3 (Second Brain) is populated with `vault/` and Quartz is configured in `apps/garden/`:

```bash
gh api repos/YOUR_USERNAME/polymath-os/pages \
  -X POST -f source[branch]=main -f source[path]=/apps/garden
```

## After push

The repo is **alive** — anyone can:
- `git clone git@github.com:YOUR_USERNAME/polymath-os.git`
- `cd polymath-os && make verify`
- Get the same 12/12 PASS result as you

To iterate further: open issues for what's next (mutation testing setup, vault templates, MCP adapter implementations, Quartz publish pipeline, real OpenTofu modules). Each iteration → PR → `make verify` → merge.

## Continuous improvement (на репе)

This repo is not "done". It's a starting point. The roadmap (`ROADMAP.md`) and limitations (`runtime/docs/LIMITATIONS.md`) describe what's NOT yet implemented. Iterate via:
- Issues (per ADR or per layer)
- PRs (each must pass `make verify`)
- New ADRs (0001-0012 exist, next is 0013+)

**Совершенству нет предела — но каждая итерация должна проходить `make verify`.**
