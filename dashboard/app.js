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
  { href: 'index.html',             label: 'Visão Geral', icon: '📊', roles: ['admin', 'finance', 'manager'] },
  { href: 'calendar.html',           label: 'Calendário',  icon: '📅', roles: '*' },
  { href: 'crm.html',                label: 'CRM',         icon: '🤝', roles: ['admin', 'manager', 'finance'] },
  { href: 'events.html',             label: 'Eventos',     icon: '🎉', roles: ['admin', 'manager', 'finance', 'operator'] },
  { href: 'service-orders.html',     label: 'OS',          icon: '📋', roles: ['admin', 'manager', 'operator'] },
  { href: 'production-orders.html',  label: 'Produção',    icon: '🍳', roles: ['admin', 'manager', 'operator', 'kitchen'] },
  { href: 'kitchen.html',            label: 'Cozinha/CMV', icon: '🧂', roles: ['admin', 'manager', 'kitchen', 'finance'] },
  { href: 'execution.html',          label: 'Execução',    icon: '🎬', roles: ['admin', 'manager', 'operator'] },
  { href: 'checklists.html',         label: 'Checklists',  icon: '✔️', roles: ['admin', 'manager', 'operator', 'kitchen'] },
  { href: 'commercial.html',         label: 'Comercial',   icon: '💼', roles: ['admin', 'finance', 'manager'] },
  { href: 'onboarding.html',         label: 'Onboarding',  icon: '🚀', roles: ['admin', 'finance', 'manager', 'operator'] },
  { href: 'finance.html',            label: 'Financeiro',  icon: '💸', roles: ['admin', 'finance'] },
  { href: 'insights.html',           label: 'Insights',    icon: '💡', roles: ['admin', 'finance', 'manager'] },
  { href: 'invoices.html',           label: 'Faturamento', icon: '🧾', roles: ['admin', 'finance', 'manager'] },
  { href: 'whatsapp.html',           label: 'WhatsApp',    icon: '💬', roles: ['admin', 'manager', 'operator'] },
  { href: 'marketing.html',          label: 'Marketing',   icon: '📣', roles: ['admin', 'manager', 'finance'] },
  { href: 'ai-chat.html',            label: 'AI Chat',     icon: '🤖', roles: '*' },
  { href: 'vault.html',              label: 'Documentos',  icon: '📁', roles: ['admin', 'manager'] },
  { href: 'hr.html',                 label: 'RH',          icon: '🧑‍💼', roles: ['admin', 'manager'] },
  { href: 'approvals.html',          label: 'Aprovações',  icon: '✅', roles: ['admin', 'manager', 'finance'] },
  { href: 'operations.html',         label: 'Operações',   icon: '⚙️', roles: ['admin', 'manager', 'operator'] },
  { href: 'integrations.html',       label: 'Integrações', icon: '🔌', roles: ['admin'] },
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
      <a href="${visible[0]?.href ?? 'operations.html'}" aria-label="Orkestra">
        <svg class="nav-mark" viewBox="-70 -70 140 140" width="22" height="22" aria-hidden="true">
          <g fill="currentColor">
            <path d="M -3 -20 C -10 -28 -13 -44 0 -54 C 13 -44 10 -28 3 -20 C 2 -18 -2 -18 -3 -20 Z" transform="rotate(0)"/>
            <path d="M -3 -20 C -10 -28 -13 -44 0 -54 C 13 -44 10 -28 3 -20 C 2 -18 -2 -18 -3 -20 Z" transform="rotate(22.5)"/>
            <path d="M -3 -20 C -10 -28 -13 -44 0 -54 C 13 -44 10 -28 3 -20 C 2 -18 -2 -18 -3 -20 Z" transform="rotate(45)"/>
            <path d="M -3 -20 C -10 -28 -13 -44 0 -54 C 13 -44 10 -28 3 -20 C 2 -18 -2 -18 -3 -20 Z" transform="rotate(67.5)"/>
            <path d="M -3 -20 C -10 -28 -13 -44 0 -54 C 13 -44 10 -28 3 -20 C 2 -18 -2 -18 -3 -20 Z" transform="rotate(90)"/>
            <path d="M -3 -20 C -10 -28 -13 -44 0 -54 C 13 -44 10 -28 3 -20 C 2 -18 -2 -18 -3 -20 Z" transform="rotate(112.5)"/>
            <path d="M -3 -20 C -10 -28 -13 -44 0 -54 C 13 -44 10 -28 3 -20 C 2 -18 -2 -18 -3 -20 Z" transform="rotate(135)"/>
            <path d="M -3 -20 C -10 -28 -13 -44 0 -54 C 13 -44 10 -28 3 -20 C 2 -18 -2 -18 -3 -20 Z" transform="rotate(157.5)"/>
            <path d="M -3 -20 C -10 -28 -13 -44 0 -54 C 13 -44 10 -28 3 -20 C 2 -18 -2 -18 -3 -20 Z" transform="rotate(180)"/>
            <path d="M -3 -20 C -10 -28 -13 -44 0 -54 C 13 -44 10 -28 3 -20 C 2 -18 -2 -18 -3 -20 Z" transform="rotate(202.5)"/>
            <path d="M -3 -20 C -10 -28 -13 -44 0 -54 C 13 -44 10 -28 3 -20 C 2 -18 -2 -18 -3 -20 Z" transform="rotate(225)"/>
            <path d="M -3 -20 C -10 -28 -13 -44 0 -54 C 13 -44 10 -28 3 -20 C 2 -18 -2 -18 -3 -20 Z" transform="rotate(247.5)"/>
            <path d="M -3 -20 C -10 -28 -13 -44 0 -54 C 13 -44 10 -28 3 -20 C 2 -18 -2 -18 -3 -20 Z" transform="rotate(270)"/>
            <path d="M -3 -20 C -10 -28 -13 -44 0 -54 C 13 -44 10 -28 3 -20 C 2 -18 -2 -18 -3 -20 Z" transform="rotate(292.5)"/>
            <path d="M -3 -20 C -10 -28 -13 -44 0 -54 C 13 -44 10 -28 3 -20 C 2 -18 -2 -18 -3 -20 Z" transform="rotate(315)"/>
            <path d="M -3 -20 C -10 -28 -13 -44 0 -54 C 13 -44 10 -28 3 -20 C 2 -18 -2 -18 -3 -20 Z" transform="rotate(337.5)"/>
            <circle r="20"/>
          </g>
          <circle r="14" fill="#0B0B0C"/>
          <circle r="8" fill="currentColor"/>
        </svg>
        <span>Orkestra</span>
      </a>
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

// ─── LGPD cookie banner ──────────────────────────────────────────
// Runs once after DOM is ready. Opt-in: user must explicitly accept.
(function mountCookieBanner() {
  const KEY = 'orkestra.lgpd.consent';
  if (localStorage.getItem(KEY)) return;

  window.addEventListener('DOMContentLoaded', () => {
    const bar = document.createElement('div');
    bar.className = 'ork-cookie-bar';
    bar.innerHTML = `
      <div class="ork-cookie-text">
        Usamos cookies e dados pessoais conforme a LGPD (Lei 13.709/18).
        Ao continuar, você concorda com nossa
        <a href="privacy.html">Política de Privacidade</a>.
      </div>
      <div class="ork-cookie-actions">
        <button class="ork-btn-ghost" id="ork-cookie-reject">Essenciais</button>
        <button class="ork-btn-primary" id="ork-cookie-accept">Aceitar todos</button>
      </div>`;
    document.body.appendChild(bar);

    const record = async (accepted) => {
      localStorage.setItem(KEY, JSON.stringify({ accepted, at: new Date().toISOString() }));
      bar.remove();
      try {
        await api('/lgpd/consent', {
          method: 'POST',
          body: JSON.stringify({ email: ME?.email, accepted, userAgent: navigator.userAgent }),
        });
      } catch { /* best effort */ }
    };
    bar.querySelector('#ork-cookie-accept').onclick = () => record(['essential', 'analytics']);
    bar.querySelector('#ork-cookie-reject').onclick = () => record(['essential']);
  });
})();
