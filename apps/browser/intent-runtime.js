/* SINGULYAR Intent Runtime — deterministic reference implementation, v0.2.0.
 * No network, no model call, no implicit side effects. CommonJS + browser global.
 */
((root, factory) => {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.SingulyarIntentRuntime = api;
})(typeof globalThis !== "undefined" ? globalThis : this, () => {
  const VERSION = "0.2.0";
  const CAPABILITIES = Object.freeze({
    "note.create.local": {
      id: "note.create.local",
      title: "Создать локальную заметку",
      risk: "low",
      effects: ["local-write"],
      requiresApproval: true,
      adapter: "local-note-v1",
      verifies: "Запись доступна при повторном чтении из localStorage",
    },
    "web.search.prepare": {
      id: "web.search.prepare",
      title: "Подготовить веб-поиск",
      risk: "medium",
      effects: ["external-data-transfer"],
      requiresApproval: true,
      adapter: "external-search-link-v1",
      verifies: "Показан URL; отправка не происходит до отдельного клика пользователя",
    },
    "system.status.read": {
      id: "system.status.read",
      title: "Показать статус прототипа",
      risk: "low",
      effects: ["local-read"],
      requiresApproval: false,
      adapter: "local-status-v1",
      verifies: "Сформирован отчёт о возможностях этой демонстрации",
    },
  });
  function base(intent, capabilityId, params, why) {
    const capability = CAPABILITIES[capabilityId];
    return {
      schema: "singulyar.intent.v1",
      runtimeVersion: VERSION,
      intent: {
        id: `intent-${simpleHash(`${intent}|${capabilityId}`)}`,
        raw: intent,
        goal: capability ? capability.title : "Неизвестное намерение",
      },
      capability: capability ? { ...capability } : null,
      params: params || {},
      policy: {
        decision: capability
          ? capability.requiresApproval
            ? "approval-required"
            : "allow-readonly"
          : "deny",
        reason: why,
      },
      execution: { status: "not-started", sideEffectsStarted: false },
      observation: null,
      evidence: null,
      boundary:
        "Демонстрационный runtime: не вызывает LLM, не управляет браузерными вкладками и не выполняет сетевые запросы.",
    };
  }
  function simpleHash(s) {
    let h = 2166136261;
    for (let i = 0; i < s.length; i++) {
      h ^= s.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return (h >>> 0).toString(16);
  }
  function planIntent(input) {
    const raw = String(input || "").trim();
    if (!raw) return base(raw, null, {}, "Пустой запрос: нужно уточнение.");
    let m = raw.match(/^(?:создай|сделай|запиши)\s+заметк(?:у|а)\s*[:—-]\s*([\s\S]+)$/i);
    if (m) {
      const content = m[1].trim();
      if (!content) return base(raw, null, {}, "Не указано содержание заметки.");
      const parts = content.split(/\s*\|\s*/);
      return base(
        raw,
        "note.create.local",
        {
          title: parts.length > 1 ? parts[0].slice(0, 180) : "Заметка из намерения",
          body: (parts.length > 1 ? parts.slice(1).join(" | ") : parts[0]).slice(0, 10000),
        },
        "Локальная запись изменяет данные; требуется явное подтверждение.",
      );
    }
    m = raw.match(/^(?:подготовь|найди|поиск)\s+(?:веб[- ]?)?поиск\s*[:—-]\s*([\s\S]+)$/i);
    if (m?.[1].trim()) {
      const query = m[1].trim().slice(0, 500);
      return base(
        raw,
        "web.search.prepare",
        { query, url: `https://www.google.com/search?q=${encodeURIComponent(query)}` },
        "Поисковый запрос передаётся внешнему поставщику только после отдельного клика.",
      );
    }
    if (/^(?:покажи|проверить|проверь)\s+(?:мне\s+)?статус\s*\??$/i.test(raw))
      return base(raw, "system.status.read", {}, "Только чтение сведений о текущей демонстрации.");
    return base(
      raw,
      null,
      {},
      "Намерение не распознано однозначно. Ничего не выполняется; уточните цель.",
    );
  }
  function authorize(plan, approved) {
    if (!plan || !plan.capability)
      return { allowed: false, status: "DENIED", reason: "Нет зарегистрированной возможности." };
    if (plan.policy.decision === "deny")
      return { allowed: false, status: "DENIED", reason: plan.policy.reason };
    if (plan.capability.requiresApproval && approved !== true)
      return {
        allowed: false,
        status: "AWAITING_APPROVAL",
        reason: "Нужно отдельное явное подтверждение человека.",
      };
    return {
      allowed: true,
      status: "AUTHORIZED",
      reason: "Разрешено только действие в заявленной области.",
    };
  }
  function evidence(status, observation, details) {
    return {
      kind: "singulyar.evidence.v1",
      status,
      observedAt: new Date().toISOString(),
      observation,
      details: details || {},
      verifier: "demo-postcondition-check",
    };
  }
  return Object.freeze({ VERSION, CAPABILITIES, planIntent, authorize, evidence });
});
