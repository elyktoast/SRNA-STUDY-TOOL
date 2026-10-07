(() => {
  const CHECK_COOLDOWN = 120000;
  const CHECK_INTERVAL = 30000;
  const REQUEST_TIMEOUT = 8000;
  const BUILD_CACHE_KEY = 'mbu_build_manifest_v1';
  const script = document.currentScript;
  const manifestUrl = new URL('../build.json', script?.src || location.href);
  const runtimeBuild = script ? new URL(script.src).searchParams.get('b') : null;
  const cachedBaseline = sessionStorage.getItem(BUILD_CACHE_KEY);
  let baseline = runtimeBuild || (cachedBaseline && cachedBaseline.trim() ? cachedBaseline.trim() : null);
  if (runtimeBuild) sessionStorage.setItem(BUILD_CACHE_KEY, runtimeBuild);
  else if (!baseline && cachedBaseline !== null) sessionStorage.removeItem(BUILD_CACHE_KEY);
  let checking = false;
  let lastCheck = 0;
  let reloadPending = false;

  async function readBuild() {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);
    try {
      const response = await fetch(manifestUrl.href + '?t=' + Date.now(), {
        cache: 'no-store',
        credentials: 'same-origin',
        signal: controller.signal
      });
      if (!response.ok) throw new Error('Update check failed: ' + response.status);
      const data = await response.json();
      if (!data || typeof data.build !== 'string' || !data.build) throw new Error('Invalid build manifest');
      return data.build;
    } finally {
      clearTimeout(timer);
    }
  }

  async function establishBaseline() {
    if (baseline) return;
    try {
      baseline = await readBuild();
      lastCheck = Date.now();
      sessionStorage.setItem(BUILD_CACHE_KEY, baseline);
    } catch {}
  }

  async function check(force = false) {
    const now = Date.now();
    if (checking || document.hidden || (!force && now - lastCheck < CHECK_COOLDOWN)) return;
    checking = true;
    lastCheck = now;
    try {
      const latest = await readBuild();
      if (!baseline) {
        baseline = latest;
        sessionStorage.setItem(BUILD_CACHE_KEY, baseline);
      } else if (latest !== baseline && !reloadPending) {
        reloadPending = true;
        sessionStorage.setItem(BUILD_CACHE_KEY, latest);
        // A new published build is available. Reload once so build-bootstrap
        // fetches the new manifest and cache-busted assets.
        location.reload();
        return;
      }
    } catch {
      // Update checks are best-effort. Never reload a page underneath the learner.
    } finally {
      checking = false;
    }
  }

  const prime = () => {
    if ('requestIdleCallback' in window) requestIdleCallback(establishBaseline, { timeout: 1500 });
    else setTimeout(establishBaseline, 250);
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', prime, { once: true });
  else prime();

  window.addEventListener('pageshow', event => { if (event.persisted) check(true); });
  window.addEventListener('focus', () => check());
  document.addEventListener('visibilitychange', () => { if (!document.hidden) check(true); });
  window.addEventListener('online', () => check(true));
  setInterval(() => check(), CHECK_INTERVAL);
})();