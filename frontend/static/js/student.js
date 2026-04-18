/**
 * student.js
 * Student dashboard: browse verified alumni, send/manage mentorship requests.
 */

let currentUser = null;
let alumniData  = [];
let currentPage = 1;
let totalPages  = 1;

/* ---- Init ---- */

document.addEventListener('DOMContentLoaded', async () => {
  currentUser = await requireAuth(['student']);
  if (!currentUser) return;

  document.getElementById('user_name').textContent = currentUser.full_name;
  await loadAlumni();
  bindFilters();
  bindModal();
});

/* ---- Load alumni list ---- */

async function loadAlumni(page = 1) {
  currentPage = page;
  const dept     = document.getElementById('filter_dept')?.value.trim() || '';
  const industry = document.getElementById('filter_industry')?.value.trim() || '';
  const accepting = document.getElementById('filter_accepting')?.value || '';

  const params = new URLSearchParams({ page, per_page: 12 });
  if (dept)     params.set('department', dept);
  if (industry) params.set('industry', industry);
  if (accepting) params.set('accepting_mentees', accepting);

  showGridLoading(true);

  try {
    const res = await fetch(`/student/alumni?${params}`, { credentials: 'include' });
    if (res.status === 401) { window.location.href = '/login'; return; }
    const data = await res.json();
    alumniData  = data.alumni || [];
    totalPages  = data.pages  || 1;
    renderAlumniGrid(alumniData);
    renderPagination(data.total, page, data.pages);
  } catch {
    document.getElementById('alumni_grid').innerHTML =
      '<p class="text-muted text-center mt-3">Failed to load alumni.</p>';
  } finally {
    showGridLoading(false);
  }
}

function showGridLoading(on) {
  const grid = document.getElementById('alumni_grid');
  if (on) grid.innerHTML = '<div class="flex-center" style="justify-content:center;padding:3rem"><div class="spinner"></div></div>';
}

function renderAlumniGrid(list) {
  const grid = document.getElementById('alumni_grid');
  if (!list.length) {
    grid.innerHTML = '<p class="text-muted text-center mt-3">No alumni found matching your filters.</p>';
    return;
  }
  grid.innerHTML = list.map(a => `
    <div class="alumni-card" onclick="openAlumniModal(${a.id})">
      <div class="flex-between mb-1">
        <span class="name">${esc(a.full_name)}</span>
        ${a.is_accepting_mentees
          ? '<span class="badge badge-success">Accepting</span>'
          : '<span class="badge badge-muted">Not accepting</span>'}
      </div>
      <div class="role">${esc(a.current_job_title || '—')} · ${esc(a.current_company || '—')}</div>
      <div class="text-muted" style="font-size:0.82rem">${esc(a.department)} · ${a.graduation_year || '—'}</div>
      <div class="tags">${(a.expertise_areas || []).slice(0, 4).map(t => `<span class="tag">${esc(t)}</span>`).join('')}</div>
    </div>
  `).join('');
}

function renderPagination(total, page, pages) {
  const el = document.getElementById('pagination');
  if (!el || pages <= 1) { if (el) el.innerHTML = ''; return; }
  el.innerHTML = `
    <button class="btn btn-ghost btn-sm" onclick="loadAlumni(${page - 1})" ${page <= 1 ? 'disabled' : ''}>← Prev</button>
    <span class="text-muted" style="font-size:0.85rem">Page ${page} of ${pages} · ${total} alumni</span>
    <button class="btn btn-ghost btn-sm" onclick="loadAlumni(${page + 1})" ${page >= pages ? 'disabled' : ''}>Next →</button>
  `;
}

/* ---- Filters ---- */

function bindFilters() {
  document.getElementById('filter_form')?.addEventListener('submit', e => {
    e.preventDefault(); loadAlumni(1);
  });
  document.getElementById('filter_reset')?.addEventListener('click', () => {
    document.getElementById('filter_form')?.reset();
    loadAlumni(1);
  });
}

/* ---- Alumni detail modal + request form ---- */

let selectedAlumniId = null;

function bindModal() {
  document.getElementById('modal_overlay')?.addEventListener('click', e => {
    if (e.target.id === 'modal_overlay') closeModal();
  });
  document.getElementById('modal_close')?.addEventListener('click', closeModal);
  document.getElementById('request_form')?.addEventListener('submit', handleSendRequest);
}

async function openAlumniModal(alumniId) {
  selectedAlumniId = alumniId;
  const overlay = document.getElementById('modal_overlay');
  overlay.classList.add('open');

  // Fetch fresh detail
  try {
    const res = await fetch(`/student/alumni/${alumniId}`, { credentials: 'include' });
    const a   = await res.json();
    document.getElementById('modal_name').textContent    = a.full_name;
    document.getElementById('modal_role').textContent    = `${a.current_job_title || ''} · ${a.current_company || ''}`;
    document.getElementById('modal_dept').textContent    = `${a.department} · Class of ${a.graduation_year}`;
    document.getElementById('modal_bio').textContent     = a.bio || 'No bio provided.';
    document.getElementById('modal_industry').textContent = a.industry || '—';
    document.getElementById('modal_yoe').textContent    = a.years_of_experience != null ? `${a.years_of_experience} yrs` : '—';
    document.getElementById('modal_tags').innerHTML = (a.expertise_areas || []).map(t => `<span class="tag">${esc(t)}</span>`).join('');

    const sendSection = document.getElementById('send_request_section');
    if (sendSection) sendSection.style.display = a.is_accepting_mentees ? 'block' : 'none';
  } catch {
    document.getElementById('modal_name').textContent = 'Could not load profile.';
  }
}

function closeModal() {
  document.getElementById('modal_overlay')?.classList.remove('open');
  document.getElementById('request_form')?.reset();
  document.getElementById('request_alert')?.classList.add('hidden');
  selectedAlumniId = null;
}

async function handleSendRequest(e) {
  e.preventDefault();
  const alert   = document.getElementById('request_alert');
  const btn     = document.getElementById('request_btn');
  const subject = document.getElementById('req_subject').value.trim();
  const message = document.getElementById('req_message').value.trim();

  if (!subject || !message) {
    showAlert(alert, 'Subject and message are required.');
    return;
  }

  setLoading(btn, true);
  hideAlert(alert);

  try {
    const res = await fetch('/mentorship/request', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ alumni_id: selectedAlumniId, subject, message }),
    });
    const data = await res.json();

    if (!res.ok) {
      showAlert(alert, data.error || 'Could not send request.');
      return;
    }
    showAlert(alert, 'Mentorship request sent!', 'success');
    document.getElementById('request_form').reset();
  } catch {
    showAlert(alert, 'Network error.');
  } finally {
    setLoading(btn, false);
  }
}

/* ---- My requests tab ---- */

async function loadMyRequests() {
  const container = document.getElementById('my_requests');
  if (!container) return;
  container.innerHTML = '<div class="spinner" style="margin:2rem auto"></div>';

  try {
    const res = await fetch('/mentorship/my-requests', { credentials: 'include' });
    const data = await res.json();
    const requests = data.requests || [];

    if (!requests.length) {
      container.innerHTML = '<p class="text-muted mt-2">You have not sent any mentorship requests yet.</p>';
      return;
    }

    container.innerHTML = requests.map(r => `
      <div class="request-item">
        <div class="req-header">
          <div>
            <div class="req-subject">${esc(r.subject)}</div>
            <div class="req-meta">To: ${esc(r.alumni_name)} · ${esc(r.alumni_company || '—')}</div>
          </div>
          ${statusBadge(r.status)}
        </div>
        ${r.response_note ? `<p class="text-muted mt-1" style="font-size:0.85rem">${esc(r.response_note)}</p>` : ''}
        <div class="text-muted mt-1" style="font-size:0.78rem">Sent ${formatDate(r.created_at)}</div>
        ${r.status === 'pending'
          ? `<div class="req-actions"><button class="btn btn-ghost btn-sm" onclick="withdrawRequest(${r.id})">Withdraw</button></div>`
          : ''}
      </div>
    `).join('');
  } catch {
    container.innerHTML = '<p class="text-danger mt-2">Failed to load requests.</p>';
  }
}

async function withdrawRequest(requestId) {
  if (!confirm('Withdraw this mentorship request?')) return;
  try {
    const res = await fetch(`/mentorship/withdraw/${requestId}`, {
      method: 'POST', credentials: 'include',
    });
    if (res.ok) loadMyRequests();
  } catch { alert('Network error.'); }
}

/* ---- Tab switching ---- */

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      const panel = document.getElementById(btn.dataset.tab);
      if (panel) {
        panel.classList.add('active');
        if (btn.dataset.tab === 'my_requests_tab') loadMyRequests();
      }
    });
  });
});

/* ---- Utilities ---- */

function esc(str) {
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function formatDate(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString('en-US', { year:'numeric', month:'short', day:'numeric' });
}

function statusBadge(status) {
  const map = { pending: 'warning', accepted: 'success', rejected: 'danger', withdrawn: 'muted' };
  return `<span class="badge badge-${map[status] || 'muted'}">${status}</span>`;
}
