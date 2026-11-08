# KNOWN ISSUES · polymath-os

## Волна ×5 · 2026-11-09

| Воркфлоу | Run id (sha) | Диагноз | Статус после патча |
|---|---|---|---|
| CI | 42515608485 (2d215dc, 19:33) | Biome check: 3 format-ошибки — wave3-dora.yml (пробелы перед комментом), wave3-skill-contract.yml (одинарные кавычки в paths), wave3/DORA-дайджест.md (выравнивание таблицы) | 🟢 ×4 исправил в 6b296af: 42516126529 🟢 (19:39); 42516492826 🟢 на fef57b3 (19:43) |
| CI | 42516035353 (312e199, 19:38) | тот же корень (Lint-step в job «lint + typecheck + test + build + security») | 🟢 то же; диспатч ×5 42527907783 на 5a6de65 (дверь workflow_dispatch добавлена) |

### Квирки

- Job make verify (open-source contract) зелёный всегда отдельно от lint-джобы — краснота ×5-дня была только в Lint.
- OpenSSF Scorecard и CodeQL ходят на каждый push и зелёные с 19:42–19:43.
- actions/checkout запинен по полному SHA (3d3c42e5… v7.0.1) с persist-credentials: false — SLSA-канон ×4; не откатывать на тэг.
