# OSPS Baseline — матрица соответствия

Стандарт: Open Source Project Security (OSPS) Baseline, версия **v2026.08.28** —
текущая на момент самооценки ([сайт](https://baseline.openssf.org/versions/2026-08-28.html),
[исходники контролей](https://github.com/ossf/security-baseline)). Это жёсткий
MUST-чеклист OpenSSF по трём уровням зрелости проекта.

- **Дата самооценки:** 2026-11-10 (волна ×14), состояние main: `3bfdf07`.
- **Метод:** каждый вердикт подкреплён доказательством — файлом репозитория,
  живым API-ответом или зелёным прогоном CI. Никаких украшений: что не
  соответствует — то не соответствует.
- **Уровни зрелости:** L1 — база (24 контроля), L2 — от 2 мейнтейнеров (19),
  L3 — большая база пользователей (21). Соло-проект: цель = **L1 на 100% +
  L2 по максимуму**; контроли L3, которые проект уже перекрывает, отмечены.
- **Вердикты:** ✅ соответствует · ⚠️ соответствует с оговоркой · ❌ не
  соответствует · n/a не применим.
- Соседние канонические документы: `security-insights.yml` (машиночитаемый),
  `SECURITY.md`, `GOVERNANCE.md`, `CONTRIBUTING.md`; живой Scorecard-бейдж —
  в `README.md`. Официальный кроссворк OSPS ↔ Scorecard ведётся самим стандартом
  (в карточках контролей на сайте), здесь приводим только своё состояние.

## Итог (2026-11-10)

| Уровень | ✅  | ⚠️  | ❌  | n/a | Всего |
| ------- | --- | --- | --- | --- | ----- |
| L1      | 22  | 2   | 0   | 0   | 24    |
| L2      | 19  | 0   | 0   | 0   | 19    |
| L3      | 9   | 9   | 1   | 2   | 21    |

- **Закрыто этой волной (×14):** OSPS-DO-06.01 (политика зависимостей — секция
  ниже), OSPS-DO-03.01 и OSPS-DO-03.02 (инструкция верификации релиза — секция
  ниже).
- **Единственный ❌ — OSPS-QA-07.01** (апрув не-автора человеком): соло-потолок,
  тот же корень, что Scorecard Code-Review 0 и Maintained 0. Решается вторым
  человеком, не кодом; PR-механика (2 approvals, CODEOWNERS, линейная история)
  стоит и ждёт.
- **OSPS-AC-01.01 (MFA)** — вне API-периметра репозитория: гарантия на стороне
  аккаунта Хозяина, из git/API не верифицируется — потому честный ⚠️, а не ✅.
- Самооценка самодекларативная (с доказательствами), не сертификация.

## Level 1 — 24 контроля

| ID            | Требование (суть)                                | Вердикт | Доказательство                                                                                                                                |
| ------------- | ------------------------------------------------ | ------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| OSPS-AC-01.01 | MFA на чувствительных действиях                  | ⚠️      | 2FA аккаунта GitHub — вне API-периметра репо; остальной стек верифицируем                                                                     |
| OSPS-AC-02.01 | минимальные права соавторов по умолчанию         | ✅      | соавторов нет; дефолт GitHub = минимальные права; роли — GOVERNANCE.md                                                                        |
| OSPS-AC-03.01 | прямой коммит в primary ветку блокируется        | ⚠️      | 2 approvals + strict checks + подписи + linear history (API-факт), но enforce_admins=false — легальный admin-bypass канон роя (GOVERNANCE.md) |
| OSPS-AC-03.02 | удаление primary ветки запрещено                 | ✅      | allow_deletions=false (живой API-ответ 2026-11-10) + ruleset polimat-guard                                                                    |
| OSPS-BR-01.01 | санитизация недоверенных метаданных в CI         | ✅      | все экшены пинованы по SHA; persist-credentials=false; входы диспатчей — choice-enum                                                          |
| OSPS-BR-01.03 | изоляция недоверенных снапшотов от секретов      | ✅      | read-all на верхнем уровне всех 14 воркфлоу; job-level по необходимости (волна ×11)                                                           |
| OSPS-BR-03.01 | официальные каналы только по шифрованным каналам | ✅      | github.com по HTTPS/SSH; плейн-HTTP URI в документации отсутствуют                                                                            |
| OSPS-BR-03.02 | канал дистрибуции против MitM                    | ✅      | GitHub Releases (HTTPS) + подписи cosign (keyless OIDC) + аттестации                                                                          |
| OSPS-BR-07.01 | запрет секретов в VCS                            | ✅      | gitleaks (шаг 13 CI) + check_token_hygiene.py (claim #23 make verify); env-only канон; canary-ловушка в vault                                 |
| OSPS-DO-01.01 | пользовательская документация                    | ✅      | README Quick start + docs/01–05 + INSTALL_NIX.md                                                                                              |
| OSPS-DO-02.01 | гайд по репорту дефектов                         | ✅      | SUPPORT.md (волна ×13) + SECURITY.md для уязвимостей                                                                                          |
| OSPS-GV-02.01 | публичные обсуждения                             | ✅      | Issues открыты; issue #10 = живой канал роя                                                                                                   |
| OSPS-GV-03.01 | процесс вклада описан                            | ✅      | CONTRIBUTING.md                                                                                                                               |
| OSPS-LE-02.01 | лицензия исходников OSI/FSF                      | ✅      | MIT (LICENSE, claim #08 make verify)                                                                                                          |
| OSPS-LE-02.02 | лицензия релизных ассетов OSI/FSF                | ✅      | MIT на всё дерево релиза                                                                                                                      |
| OSPS-LE-03.01 | LICENSE в корне репозитория                      | ✅      | LICENSE в корне                                                                                                                               |
| OSPS-LE-03.02 | лицензия вместе с релизными ассетами             | ✅      | релизные архивы исходника содержат LICENSE                                                                                                    |
| OSPS-QA-01.01 | публичный статический URL репозитория            | ✅      | github.com/rtynbirf/polymath-os                                                                                                               |
| OSPS-QA-01.02 | публичная история изменений                      | ✅      | git-история + подписанные коммиты (required_signatures)                                                                                       |
| OSPS-QA-02.01 | список прямых зависимостей                       | ✅      | package.json + pnpm-lock.yaml + requirements/\*.txt с мультихешами                                                                            |
| OSPS-QA-04.01 | список репозиториев проекта                      | ✅      | docs/ECOSYSTEM.md + swarm.json                                                                                                                |
| OSPS-QA-05.01 | нет сгенерированных исполняемых артефактов       | ✅      | claim #11 make verify проверяет отсутствие \_\_pycache\_\_/\*.pyc                                                                             |
| OSPS-QA-05.02 | нет непросматриваемых бинарников                 | ✅      | единственные бинарники — PNG-баннеры (иллюстрации, не исполняемое)                                                                            |
| OSPS-VM-02.01 | контакты безопасности в документации             | ✅      | SECURITY.md Contacts → GitHub Security Advisories                                                                                             |

## Level 2 — 19 контролей

| ID            | Требование (суть)                              | Вердикт | Доказательство                                                                        |
| ------------- | ---------------------------------------------- | ------- | ------------------------------------------------------------------------------------- |
| OSPS-AC-04.01 | дефолт прав CI = минимум                       | ✅      | permissions: read-all на верхнем уровне всех воркфлоу (живой канон)                   |
| OSPS-BR-02.01 | уникальный идентификатор версии релиза         | ✅      | SemVer теги v\*.\*.\* (release.yml)                                                   |
| OSPS-BR-04.01 | changelog с релизом                            | ✅      | CHANGELOG.md (Keep a Changelog) → release notes автодостаются release.yml             |
| OSPS-BR-05.01 | стандартизированный тулинг зависимостей        | ✅      | pnpm --frozen-lockfile + pip --require-hashes (мультихеши)                            |
| OSPS-BR-06.01 | релиз подписан / манифест с хешами             | ✅      | SBOM + .sha256 + cosign bundle (keyless) + GH-аттестации ×2 (живой прогон ×13)        |
| OSPS-DO-06.01 | как выбираются и отслеживаются зависимости     | ✅      | секция «Политика зависимостей» ниже — закрыто волной ×14                              |
| OSPS-DO-07.01 | инструкции сборки                              | ✅      | README Quick start + Makefile + INSTALL_NIX.md + flake.nix                            |
| OSPS-GV-01.01 | список держателей доступа                      | ✅      | GOVERNANCE.md «Роли»: владелец, рой, вкладчики                                        |
| OSPS-GV-01.02 | роли и ответственность                         | ✅      | GOVERNANCE.md: полномочия по каждой роли                                              |
| OSPS-GV-03.02 | требования к вкладу                            | ✅      | CONTRIBUTING.md: ADR, статус-чеки, squash, линейная история                           |
| OSPS-LE-01.01 | правовая легитимность вклада на каждом коммите | ✅      | DCO Signed-off-by канон + required_signatures (SSH)                                   |
| OSPS-QA-03.01 | статус-чеки обязательны на primary             | ✅      | 2 required checks strict (API-факт): make verify + lint/typecheck/test/build/security |
| OSPS-QA-06.01 | автоматический тест-сьют в CI                  | ✅      | make verify 33/33 + 295 тестов рантайма (зелёный CI)                                  |
| OSPS-SA-01.01 | дизайн-документация акторов и действий         | ✅      | ARCHITECTURE.md + 35 ADR                                                              |
| OSPS-SA-02.01 | описание внешних интерфейсов                   | ✅      | runtime/docs/TECHNICAL_SPEC.md + ADR-0027 (HTTP JSON-RPC декрет-сервер)               |
| OSPS-SA-03.01 | оценка безопасности (security assessment)      | ✅      | runtime/docs/THREAT_MODEL.md + security-insights.yml                                  |
| OSPS-VM-01.01 | политика CVD с чёткими сроками                 | ✅      | SECURITY.md: ≤72 ч подтверждение, ≤7 дней оценка                                      |
| OSPS-VM-03.01 | приватный канал репорта уязвимостей            | ✅      | PVR enabled=true (живой API-ответ 2026-11-10) + SECURITY.md                           |
| OSPS-VM-04.01 | публикация данных о найденных уязвимостях      | ✅      | канал GHSA+CVE готов; опубликованных уязвимостей нет — публиковать нечего             |

## Level 3 — 21 контроль

Формально Level 3 адресован проектам с большой пользовательской базой; для
соло-проекта часть контролей n/a, но уже перекрытые отмечены честно.

| ID            | Требование (суть)                              | Вердикт | Доказательство                                                                                                                             |
| ------------- | ---------------------------------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| OSPS-AC-04.02 | job-права = только необходимые                 | ✅      | release.yml: contents+id-token+attestations; packages:write убран (волна ×11)                                                              |
| OSPS-BR-01.04 | санитизация входов от доверенных collaborators | ⚠️      | choice-enum в release.yml; полный аудит всех workflow_dispatch входов — дорожная карта                                                     |
| OSPS-BR-02.02 | каждый ассет связан с идентификатором версии   | ⚠️      | ассеты прикреплены к странице релиза-версии; имена файлов без суффикса версии                                                              |
| OSPS-BR-07.02 | политика управления секретами                  | ⚠️      | канон env-only + ротация на мандат + sealed box — в runbook (token-registry, П-74); выделенной страницы в репо нет, ссылка в секции ниже   |
| OSPS-DO-03.01 | инструкция верификации целостности релиза      | ✅      | секция «Верификация релиза» ниже — закрыто волной ×14                                                                                      |
| OSPS-DO-03.02 | инструкция верификации личности издателя       | ✅      | секция «Верификация релиза» ниже — закрыто волной ×14                                                                                      |
| OSPS-DO-04.01 | scope и срок поддержки релизов                 | ✅      | SECURITY.md: latest main + тегированные релизы                                                                                             |
| OSPS-DO-05.01 | объявление конца поддержки версий              | ✅      | та же таблица: «anything older ❌»                                                                                                         |
| OSPS-GV-04.01 | пересмотр прав перед эскалацией                | ⚠️      | соавторов нет (n/a по сути); правило выдачи прав — GOVERNANCE.md «Вкладчики», до второго человека — частично                               |
| OSPS-QA-02.02 | SBOM у всех скомпилированных релизных ассетов  | ✅      | SBOM npm+Python (CycloneDX 1.6) на каждый релиз (живой прогон ×13)                                                                         |
| OSPS-QA-04.02 | субпроекты — требования не слабее основного    | n/a     | субпроекты роя ведут hive-scorecard v1; формальное требование — в прицеле                                                                  |
| OSPS-QA-06.02 | когда и как гоняются тесты — документировано   | ✅      | docs/05-devex-ci.md + CONTRIBUTING.md (каждый push/PR; make ci-local)                                                                      |
| OSPS-QA-06.03 | политика «мажорные изменения добавляют тесты»  | ✅      | CONTRIBUTING.md «Tests»: unit обязательны для packages/\*, integration для apps/\*, eval для агентов                                       |
| OSPS-QA-07.01 | апрув не-автора человеком на primary           | ❌      | соло-мандат: голосов второго человека нет; PR-механика (2 approvals, CODEOWNERS) стоит и ждёт — тот же корень, что Scorecard Code-Review 0 |
| OSPS-SA-03.02 | threat model и анализ поверхности атаки        | ✅      | runtime/docs/THREAT_MODEL.md: критические пути декрет-гейта                                                                                |
| OSPS-VM-04.02 | VEX по неэксплуатируемым уязвимостям           | n/a     | таких уязвимостей не обнаружено — публиковать нечего                                                                                       |
| OSPS-VM-05.01 | порог ремедиации SCA-фактов                    | ⚠️      | Dependabot-алерты живы; числовой порог не формализован в репо                                                                              |
| OSPS-VM-05.02 | SCA-барьер до релиза                           | ⚠️      | алерты до релиза видны; формализованный барьер — дорожная карта                                                                            |
| OSPS-VM-05.03 | авто-оценка зависимостей с блокировкой         | ⚠️      | require-hashes + Dependabot живы; авто-блок по CVE зависимостей — частично                                                                 |
| OSPS-VM-06.01 | порог ремедиации SAST-фактов                   | ⚠️      | CodeQL security-extended жив; числовой порог не формализован                                                                               |
| OSPS-VM-06.02 | авто-оценка кода с блокировкой                 | ⚠️      | CodeQL + красные required checks блокируют merge; формализованная политика — частично                                                      |

## Политика зависимостей (закрывает OSPS-DO-06.01)

1. **Выбор:** новая прямая зависимость — только через ADR (изменение поведения
   без ADR запрещено) + запись в Sovereignty Registry (claim #06 make verify
   проверяет полноту покрытия).
2. **Фиксация:** JS/TS — `pnpm-lock.yaml` (устанавливается только с
   `--frozen-lockfile`); Python — `scripts/requirements/*.txt` с
   мультихешами всех платформенных вариантов из PyPI JSON API
   (`--require-hashes`; вскрытие волны ×13 — «hash mismatch» без мультихешей).
3. **Обновление:** Dependabot (pip-граф виден в живых прогонах «Graph Update»);
   ручной подъём — через conventional-commit `chore(deps):`.
4. **Контроль:** CodeQL (security-extended) + gitleaks +
   `check_token_hygiene.py` в `make verify`; айсберг зависимостей —
   `runtime/` и MCP-адаптеры — нулевые внешние зависимости по построению.

## Политика секретов и токенов (OSPS-BR-07.02 — сводка с ссылкой)

- Байты секретов в VCS = ноль (gitleaks + token-hygiene канон); секреты —
  только env/secrets.
- Ключи выдаются Хозяином вручную на мандат; реестр мандатов —
  `rtynbirf/github-runbook` → `token-registry.json`; часовой —
  `tools/token_expiry_watch.py` (🔴 классика запрещена целевой схемой П-74,
  ротация каждый мандат, переход на fine-grained/OIDC — после перевыпуска
  FG с Contents:write, живая проба волны ×14: write-гранты у FG пока отсутствуют).
- Ротация workflow-секретов роя — libsodium sealed box; пульс-коммиты —
  `[skip ci]`, использование admin-bypass видно в истории коммитов.

## Верификация релиза — целостность и личность издателя

Закрывает OSPS-DO-03.01 и OSPS-DO-03.02. Каждому релизу сопутствуют:
`sbom.cyclonedx.json`, `sbom.cyclonedx.json.sha256`, `sbom.python.cyclonedx.json`,
`sbom.pem`/`sbom.sig`/`sbom.bundle` (cosign keyless), `sbom.attestation.bundle`,
`sbom.slsa-provenance.intoto.jsonl`. Проверка локально:

```bash
TAG=v3.25.0  # версия релиза

# 1. Хеши ассетов (целостность)
curl -sLO "https://github.com/rtynbirf/polymath-os/releases/download/$TAG/sbom.cyclonedx.json"
curl -sLO "https://github.com/rtynbirf/polymath-os/releases/download/$TAG/sbom.cyclonedx.json.sha256"
sha256sum -c sbom.cyclonedx.json.sha256

# 2. Подпись Sigstore (личность издателя: OIDC-личность воркфлоу release.yml)
cosign verify-blob sbom.cyclonedx.json \
  --bundle sbom.bundle \
  --certificate-identity-regexp '^https://github.com/rtynbirf/polymath-os/' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com

# 3. GitHub Artifact Attestation (SLSA Build L3 — аттестацию хранит сервис GitHub,
#    билд не может её подделать; identity = воркфлоу release.yml@main)
gh attestation verify sbom.cyclonedx.json -R rtynbirf/polymath-os
gh attestation verify sbom.python.cyclonedx.json -R rtynbirf/polymath-os

# 4. Иммутабельность: после публикации тег и ассеты залочены GitHub
gh release view "$TAG" -R rtynbirf/polymath-os --json isDraft,latest
```

Шаг 2 подтверждает, что подпись выпущена OIDC-личностью конкретного воркфлоу
этого репозитория (не человеком, не сторонним билдером); шаг 3 — что артефакт
собран именно этим прогоном release.yml на GitHub Actions (SLSA Build L3).
