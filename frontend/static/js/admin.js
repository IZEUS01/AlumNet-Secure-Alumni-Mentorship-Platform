/**
 * admin.js — AlumNet Admin Dashboard
 * IDs match admin_panel.html exactly.
 */

const ADMIN = '/admin';

/* ── helpers ─────────────────────────────────────────────────────── */

async function apiFetch(url, opts = {}) {
  const res  = await fetch(url, { credentials: 'include', ...opts });
  const text = await res.text();
  let data = {};
  try { data = JSON.parse(text); } catch { data = { error: text }; }
  return { ok: res.ok, status: res.status, data };
}

async function apiPost(url, body = {}) {
  return apiFetch(url, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(body),
  });
}

function showToast(msg, type = 'success') {
  let box = document.getElementById('toast-container');
  if (!box) {
    box = document.createElement('div');
    box.id = 'toast-container';
    box.style.cssText = 'position:fixed;bottom:1.5rem;right:1.5rem;z-index:9999;display:flex;flex-direction:column;gap:.5rem;pointer-events:none;';
    document.body.appendChild(box);
  }
  const bg   = type === 'success' ? 'rgba(52,211,153,.15)' : 'rgba(251,113,133,.15)';
  const bdr  = type === 'success' ? 'rgba(52,211,153,.35)' : 'rgba(251,113,133,.35)';
  const t    = document.createElement('div');
  t.style.cssText = `padding:.75rem 1.1rem;border-radius:8px;font-size:.85rem;font-weight:500;
    color:#e2e8f4;background:${bg};border:1px solid ${bdr};
    box-shadow:0 8px 24px rgba(0,0,0,.4);max-width:320px;pointer-events:auto;
    transform:translateX(120%);transition:transform .3s cubic-bezier(.16,1,.3,1);`;
  t.textContent = msg;
  box.appendChild(t);
  requestAnimationFrame(() => t.style.transform = 'translateX(0)');
  setTimeout(() => { t.style.transform = 'translateX(120%)'; setTimeout(() => t.remove(), 350); }, 4500);
}

function roleBadge(role) {
  const map = {
    student:           ['Student',         '#4fc4f7'],
    unverified_alumni: ['Alumni (Pending)', '#fbbf24'],
    verified_alumni:   ['Alumni ✓',        '#34d399'],
    admin:             ['Admin',           '#a78bfa'],
  };
  const [label, color] = map[role] || [role, '#94a3b8'];
  return `<span style="background:${color}22;color:${color};padding:.2rem .55rem;border-radius:99px;font-size:.7rem;font-weight:700;border:1px solid ${color}44;white-space:nowrap;">${label}</span>`;
}

function statusBadge(status) {
  const map = {
    pending:  ['Pending',  '#fbbf24'],
    approved: ['Approved', '#34d399'],
    rejected: ['Rejected', '#fb7185'],
  };
  const [label, color] = map[status] || [status, '#94a3b8'];
  return `<span style="background:${color}22;color:${color};padding:.2rem .55rem;border-radius:99px;font-size:.7rem;font-weight:700;border:1px solid ${color}44;">${label}</span>`;
}

function timeAgo(iso) {
  if (!iso) return '—';
  const s = Math.floor((Date.now() - new Date(iso)) / 1000);
  if (s < 60)    return 'just now';
  if (s < 3600)  return `${Math.floor(s/60)}m ago`;
  if (s < 86400) return `${Math.floor(s/3600)}h ago`;
  return `${Math.floor(s/86400)}d ago`;
}

/* ── Stats ───────────────────────────────────────────────────────── */

async function loadStats() {
  const { ok, data } = await apiFetch(`${ADMIN}/stats`);
  if (!ok) return;

  const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val ?? 0; };
  set('stat_total',    data.total_users);
  set('stat_students', data.total_students);
  set('stat_verified', data.total_verified_alumni);
  set('stat_pending',  data.pending_approval);

  // Also update sidebar pending badge
  const badge = document.getElementById('sidebar_pending_count');
  if (badge) {
    badge.textContent = data.pending_approval;
    badge.style.display = data.pending_approval > 0 ? 'inline-flex' : 'none';
  }
}

/* ── Recent Activity ─────────────────────────────────────────────── */

async function loadRecentActivity() {
  const container = document.getElementById('recent_activity');
  if (!container) return;

  const { ok, data } = await apiFetch(`${ADMIN}/users?per_page=8`);
  if (!ok) {
    container.innerHTML = `<p style="color:var(--text-muted);text-align:center;padding:1.5rem;">Could not load activity.</p>`;
    return;
  }

  const users = data.users || [];
  if (users.length === 0) {
    container.innerHTML = `<p style="color:var(--text-muted);text-align:center;padding:1.5rem;">No users yet.</p>`;
    return;
  }

  container.innerHTML = users.map(u => `
    <div style="display:flex;align-items:center;gap:.9rem;padding:.7rem 0;border-bottom:1px solid rgba(255,255,255,.05);">
      <div style="width:36px;height:36px;border-radius:50%;background:var(--bg-input);
           display:flex;align-items:center;justify-content:center;
           font-size:.85rem;font-weight:700;color:var(--cyan);flex-shrink:0;">
        ${(u.full_name?.[0] || '?').toUpperCase()}
      </div>
      <div style="flex:1;min-width:0;">
        <div style="font-size:.875rem;font-weight:600;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${u.full_name}</div>
        <div style="font-size:.74rem;color:var(--text-muted);">${u.email}</div>
      </div>
      <div style="display:flex;align-items:center;gap:.4rem;flex-shrink:0;">
        ${roleBadge(u.role)} ${statusBadge(u.account_status)}
        <span style="font-size:.7rem;color:var(--text-muted);min-width:60px;text-align:right;">${timeAgo(u.created_at)}</span>
      </div>
    </div>
  `).join('');
}

/* ── Pending approvals ───────────────────────────────────────────── */

let pendingPage = 1;

async function loadPending(page = 1) {
  pendingPage = page;
  const tbody = document.getElementById('pending_body');
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:2.5rem;"><div class="spinner" style="margin:0 auto;"></div></td></tr>`;

  const { ok, data } = await apiFetch(`${ADMIN}/pending?page=${page}&per_page=20`);
  if (!ok) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:2rem;color:var(--text-muted);">Failed to load pending users.</td></tr>`;
    return;
  }

  if (!data.users || data.users.length === 0) {
    tbody.innerHTML = `
      <tr><td colspan="7" style="text-align:center;padding:3rem;">
        <div style="font-size:2rem;margin-bottom:.5rem;">✅</div>
        <div style="font-weight:600;color:var(--text);">All caught up!</div>
        <div style="font-size:.85rem;color:var(--text-muted);">No pending registrations.</div>
      </td></tr>`;
    return;
  }

  tbody.innerHTML = data.users.map(u => `
    <tr id="pending_row_${u.id}">
      <td style="padding:.75rem;">
        <div style="font-weight:600;color:var(--text);">${u.full_name}</div>
        <div style="font-size:.74rem;color:var(--text-muted);">@${u.username} · ${timeAgo(u.created_at)}</div>
        <div style="margin-top:.3rem;">${roleBadge(u.role)}</div>
      </td>
      <td style="padding:.75rem;font-size:.83rem;color:var(--text-muted);">${u.email}</td>
      <td style="padding:.75rem;font-size:.83rem;">${u.department || '—'}</td>
      <td style="padding:.75rem;font-size:.83rem;">${u.graduation_year || '—'}</td>
      <td style="padding:.75rem;font-size:.83rem;">${u.gik_roll_number || '—'}</td>
      <td style="padding:.75rem;font-size:.75rem;color:var(--text-muted);">—</td>
      <td style="padding:.75rem;">
        <div style="display:flex;gap:.4rem;">
          <button onclick="approveUser(${u.id}, this)"
            style="padding:.4rem .9rem;background:rgba(52,211,153,.12);color:#34d399;
                   border:1px solid rgba(52,211,153,.3);border-radius:7px;
                   font-size:.78rem;font-weight:700;cursor:pointer;">
            ✓ Approve
          </button>
          <button onclick="openRejectModal(${u.id})"
            style="padding:.4rem .9rem;background:rgba(251,113,133,.1);color:#fb7185;
                   border:1px solid rgba(251,113,133,.25);border-radius:7px;
                   font-size:.78rem;font-weight:700;cursor:pointer;">
            ✕ Reject
          </button>
        </div>
      </td>
    </tr>
  `).join('');

  // Pagination
  const pag = document.getElementById('pending_pagination');
  if (pag && data.pages > 1) {
    pag.innerHTML = Array.from({ length: data.pages }, (_, i) => i + 1).map(p => `
      <button onclick="loadPending(${p})"
        style="width:30px;height:30px;border-radius:7px;border:1px solid var(--border);
               background:${p===page?'var(--cyan)':'var(--bg-input)'};
               color:${p===page?'#080c14':'var(--text)'};
               font-size:.78rem;font-weight:600;cursor:pointer;margin:0 2px;">${p}</button>
    `).join('');
  } else if (pag) { pag.innerHTML = ''; }
}

/* ── Approve ─────────────────────────────────────────────────────── */

async function approveUser(userId, btn) {
  if (btn) { btn.disabled = true; btn.textContent = '…'; }
  const { ok, data } = await apiPost(`${ADMIN}/users/${userId}/approve`);
  if (ok) {
    showToast(data.message || 'User approved ✓', 'success');
    const row = document.getElementById(`pending_row_${userId}`);
    if (row) { row.style.opacity='0'; row.style.transition='opacity .3s'; setTimeout(()=>row.remove(),300); }
    loadStats();
  } else {
    showToast(data.error || 'Approval failed.', 'error');
    if (btn) { btn.disabled = false; btn.textContent = '✓ Approve'; }
  }
}

/* ── Reject ──────────────────────────────────────────────────────── */

async function rejectAlumni(userId, reason) {
  const { ok, data } = await apiPost(`${ADMIN}/users/${userId}/reject`, { reason });
  if (ok) {
    showToast(data.message || 'User rejected.', 'error');
    const row = document.getElementById(`pending_row_${userId}`);
    if (row) { row.style.opacity='0'; row.style.transition='opacity .3s'; setTimeout(()=>row.remove(),300); }
    loadStats();
  } else {
    showToast(data.error || 'Rejection failed.', 'error');
  }
}

/* ── All Users table ─────────────────────────────────────────────── */

let usersPage = 1;
let searchTimer;

function debounceSearch() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => loadUsers(1), 350);
}

async function loadUsers(page = 1) {
  usersPage = page;
  const tbody = document.getElementById('users_body');
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:2.5rem;"><div class="spinner" style="margin:0 auto;"></div></td></tr>`;

  const search = (document.getElementById('user_search')?.value || '').trim();
  const role   = document.getElementById('users_role_filter')?.value || '';
  let url = `${ADMIN}/users?page=${page}&per_page=20`;
  if (role) url += `&role=${encodeURIComponent(role)}`;

  const { ok, data } = await apiFetch(url);
  if (!ok) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:2rem;color:var(--text-muted);">Failed to load users.</td></tr>`;
    return;
  }

  let users = data.users || [];
  if (search) {
    const q = search.toLowerCase();
    users = users.filter(u => (u.full_name+u.email+u.username).toLowerCase().includes(q));
  }

  const countEl = document.getElementById('users_count');
  if (countEl) countEl.textContent = `${data.total} user${data.total !== 1 ? 's' : ''} total`;

  if (users.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:2rem;color:var(--text-muted);">No users found.</td></tr>`;
    return;
  }

  tbody.innerHTML = users.map(u => `
    <tr id="user_row_${u.id}">
      <td style="padding:.7rem;">
        <div style="font-weight:600;color:var(--text);">${u.full_name}</div>
        <div style="font-size:.74rem;color:var(--text-muted);">@${u.username}</div>
      </td>
      <td style="padding:.7rem;font-size:.83rem;color:var(--text-muted);">${u.email}</td>
      <td style="padding:.7rem;">${roleBadge(u.role)}</td>
      <td style="padding:.7rem;font-size:.78rem;color:var(--text-muted);">${timeAgo(u.created_at)}</td>
      <td style="padding:.7rem;">${statusBadge(u.account_status)}</td>
      <td style="padding:.7rem;">
        ${u.account_status === 'pending' ? `
          <button onclick="approveUser(${u.id}, this)"
            style="padding:.35rem .75rem;background:rgba(52,211,153,.12);color:#34d399;
                   border:1px solid rgba(52,211,153,.28);border-radius:6px;
                   font-size:.74rem;font-weight:700;cursor:pointer;margin-right:.3rem;">Approve</button>
          <button onclick="openRejectModal(${u.id})"
            style="padding:.35rem .75rem;background:rgba(251,113,133,.1);color:#fb7185;
                   border:1px solid rgba(251,113,133,.25);border-radius:6px;
                   font-size:.74rem;font-weight:700;cursor:pointer;">Reject</button>
        ` : u.role !== 'admin' && u.is_active ? `
          <button onclick="deactivateUser(${u.id})"
            style="padding:.35rem .75rem;background:rgba(148,163,184,.08);color:var(--text-muted);
                   border:1px solid var(--border);border-radius:6px;font-size:.74rem;cursor:pointer;">Deactivate</button>
        ` : `<span style="font-size:.74rem;color:var(--text-muted);">${u.is_active ? '—' : 'Inactive'}</span>`}
      </td>
    </tr>
  `).join('');

  // Pagination
  const pag = document.getElementById('users_pagination');
  if (pag && data.pages > 1) {
    pag.innerHTML = Array.from({ length: data.pages }, (_, i) => i + 1).map(p => `
      <button onclick="loadUsers(${p})"
        style="width:30px;height:30px;border-radius:7px;border:1px solid var(--border);
               background:${p===page?'var(--cyan)':'var(--bg-input)'};
               color:${p===page?'#080c14':'var(--text)'};
               font-size:.78rem;font-weight:600;cursor:pointer;margin:0 2px;">${p}</button>
    `).join('');
  } else if (pag) { pag.innerHTML = ''; }
}

/* ── Deactivate ──────────────────────────────────────────────────── */

async function deactivateUser(userId) {
  if (!confirm('Deactivate this user? They will not be able to log in.')) return;
  const { ok, data } = await apiPost(`${ADMIN}/users/${userId}/deactivate`);
  if (ok) { showToast('User deactivated.', 'success'); loadUsers(usersPage); loadStats(); }
  else     showToast(data.error || 'Failed.', 'error');
}

/* ── Audit log ───────────────────────────────────────────────────── */

async function loadAuditLog() {
  const tbody = document.getElementById('audit_body');
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;padding:2rem;"><div class="spinner" style="margin:0 auto;"></div></td></tr>`;

  const { ok, data } = await apiFetch(`${ADMIN}/users?per_page=50`);
  if (!ok) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;padding:2rem;color:var(--text-muted);">Failed to load.</td></tr>`;
    return;
  }

  const users = data.users || [];
  if (!users.length) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;padding:2rem;color:var(--text-muted);">No activity yet.</td></tr>`;
    return;
  }

  tbody.innerHTML = users.map(u => `
    <tr>
      <td style="padding:.65rem;font-size:.78rem;color:var(--text-muted);">${timeAgo(u.created_at)}</td>
      <td style="padding:.65rem;">${roleBadge(u.role)}</td>
      <td style="padding:.65rem;font-size:.83rem;color:var(--text);">${u.full_name}</td>
      <td style="padding:.65rem;font-size:.78rem;color:var(--text-muted);">${u.email}</td>
      <td style="padding:.65rem;">${statusBadge(u.account_status)}</td>
    </tr>
  `).join('');
}

/* ── Boot ────────────────────────────────────────────────────────── */

document.addEventListener('DOMContentLoaded', async () => {
  // Verify admin session
  try {
    const res = await fetch('/auth/me', { credentials: 'include' });
    if (!res.ok) { window.location.href = '/login'; return; }
    const me = await res.json();
    if (me.role !== 'admin') { window.location.href = '/login'; return; }
    if (me.account_status !== 'approved') { window.location.href = '/login?status=' + me.account_status; return; }
  } catch {
    window.location.href = '/login'; return;
  }

  // Load overview
  await loadStats();
  await loadRecentActivity();
});
