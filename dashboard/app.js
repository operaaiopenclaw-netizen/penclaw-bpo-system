// Shared Orkestra dashboard runtime — auth, nav, API helper.
// Loaded by every /ui/*.html page except login.html.

const API = window.location.origin;
const TOKEN = localStorage.getItem('orkestra.token');
const ME = (() => {
  try { return JSON.parse(localStorage.getItem('orkestra.user') || 'null'); }
  catch { return null; }
})();

function logout() {
  localStorage.removeItem('orkestra.token');
  localStorage.removeItem('orkestra.user');
  window.location.href = 'login.html';
}

if (!TOKEN || !ME) {
  window.location.href = 'login.html';
}

async function api(path, opts = {}) {
  const res = await fetch(`${API}${path}`, {
    ...opts,
    headers: {
      'content-type': 'application/json',
      authorization: `Bearer ${TOKEN}`,
      ...(opts.headers || {}),
    },
  });
  if (res.status === 401) { logout(); throw new Error('expired'); }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error?.message || body.error || body.message || `HTTP ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

// Attach to window only (not const) so pages that already declare their own
// fmtDate (e.g. operations.html) don't hit SyntaxError. Global name lookup
// falls through to window, so `fmtDate(...)` still works everywhere.
window.fmtDate = window.fmtDate || ((d) => !d ? '—' : new Date(d).toLocaleString('pt-BR'));
window.fmtDay  = window.fmtDay  || ((d) => !d ? '—' : new Date(d).toLocaleDateString('pt-BR'));
window.fmtMoney = window.fmtMoney || ((n) => n == null ? '—' : Number(n).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }));
window.fmtInt = window.fmtInt || ((n) => n == null ? '—' : Number(n).toLocaleString('pt-BR'));

// Role-based navigation. Each entry: { href, label, icon, roles: string[] | '*' }.
const NAV = [
  { href: 'index.html',             label: 'Financeiro',  icon: '📊', roles: ['admin', 'finance', 'manager'] },
  { href: 'crm.html',                label: 'CRM',         icon: '🤝', roles: ['admin', 'manager', 'finance'] },
  { href: 'events.html',             label: 'Eventos',     icon: '🎉', roles: ['admin', 'manager', 'finance', 'operator'] },
  { href: 'service-orders.html',     label: 'OS',          icon: '📋', roles: ['admin', 'manager', 'operator'] },
  { href: 'production-orders.html',  label: 'Produção',    icon: '🍳', roles: ['admin', 'manager', 'operator', 'kitchen'] },
  { href: 'kitchen.html',            label: 'Cozinha/CMV', icon: '🧂', roles: ['admin', 'manager', 'kitchen', 'finance'] },
  { href: 'execution.html',          label: 'Execução',    icon: '🎬', roles: ['admin', 'manager', 'operator'] },
  { href: 'commercial.html',         label: 'Comercial',   icon: '💸', roles: ['admin', 'finance', 'manager'] },
  { href: 'approvals.html',          label: 'Aprovações',  icon: '✅', roles: ['admin', 'manager', 'finance'] },
  { href: 'operations.html',         label: 'Operações',   icon: '⚙️', roles: ['admin', 'manager', 'operator'] },
  { href: 'users.html',              label: 'Usuários',    icon: '👤', roles: ['admin'] },
];

function canSee(item) {
  return item.roles === '*' || item.roles.includes(ME.role);
}

function renderNav(activeHref) {
  const visible = NAV.filter(canSee);
  const links = visible.map(n => `
    <a href="${n.href}" class="nav-item${n.href === activeHref ? ' active' : ''}">
      <span class="nav-icon">${n.icon}</span>${n.label}
    </a>
  `).join('');

  const nav = document.createElement('nav');
  nav.className = 'orkestra-nav';
  nav.innerHTML = `
    <div class="nav-brand">
      <a href="${visible[0]?.href ?? 'operations.html'}">🎛️ Orkestra</a>
    </div>
    <div class="nav-links">${links}</div>
    <div class="nav-user">
      <span class="nav-me">${ME.name} · <span class="nav-role role-${ME.role}">${ME.role}</span></span>
      <button class="nav-logout" onclick="logout()">Sair</button>
    </div>
  `;
  document.body.insertBefore(nav, document.body.firstChild);
}

function toast(msg, type = 'info') {
  const el = document.createElement('div');
  el.className = `ork-toast ork-${type}`;
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.classList.add('fade'), 2500);
  setTimeout(() => el.remove(), 3000);
}

async function tryAction(fn, successMsg) {
  try {
    await fn();
    if (successMsg) toast(successMsg, 'ok');
    return true;
  } catch (err) {
    toast(err.message || String(err), 'err');
    return false;
  }
}
