/* ============================================================
   SVET.JS v2.1 — optional helper (no dependencies, ~1.5 KB)
   - data-theme="auto": resolves day/evening/night by local clock
     (Law V warm continuum) and follows the time silently.
   - data-theme="day|evening|night": manual, respected, no timer.
   - Without JS at all: prefers-color-scheme handles it (Law I).
   ============================================================ */
(() => {
  'use strict';
  const root = document.documentElement;
  const attr = root.getAttribute('data-theme');

  if (attr === 'auto' || attr === null) {
    const resolve = () => {
      const h = new Date().getHours();
      return h >= 8 && h < 17 ? 'day' : (h >= 17 && h < 21 ? 'evening' : 'night');
    };
    const apply = () => { root.setAttribute('data-theme', resolve()); };
    apply();
    setInterval(apply, 60_000);        // follow the continuum, minute precision
  }

  /* Public toggles (bind to any control via data-svet-* attributes) */
  document.addEventListener('click', (e) => {
    const t = e.target.closest('[data-svet-toggle]');
    if (!t) return;
    const key = t.dataset.svetToggle;             // motion | grayscale | spotlight
    if (key === 'motion')
      root.dataset.motion = root.dataset.motion === 'off' ? 'on' : 'off';
    if (key === 'grayscale')
      root.toggleAttribute('data-grayscale');
    if (key === 'spotlight')
      document.body.toggleAttribute('data-spotlight');
  });
})();
