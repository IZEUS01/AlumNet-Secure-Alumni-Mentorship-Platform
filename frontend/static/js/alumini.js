/**
 * alumni.js
 * Alumni dashboard: profile management, mentorship inbox, document status.
 */

let currentUser = null;

document.addEventListener('DOMContentLoaded', async () => {
  currentUser = await requireAuth(['verified_alumni', 'unverified_alumni']);
  if (!currentUser) return;

  document.getElementById('user_name').textContent = currentUser.full_name;

  // Show pending banner for unverified alumni
  if (currentUser.role === 'unverified_alumni') {
    document.getElementById('pending_banner')?.classList.remove('hidden');
    document.getElementById('mentorship_tab_btn')?.setAttribute('disabled', true);
  }

  await loadProfile();
  bindProfileForm();
  bindTabs();

  if (currentUser.role === 'verified_alumni') {
    await loadMentorshipRequests();
  }
  await loadDocumentStatus();
});

/* ---- Profile ---- */

async function loadProfile() {
  try {
    const res  = await fetch('/alumni/profile', { credentials: 'include' });
    const data = await res.json();
    populateProfileForm(data);
  } catch { /* non-critical */ }
}

function populateProfileForm(p) {
  const set = (id, val) => { const el = document.getElementById(id); if (el) el.value = val || ''; };
  set('prof_company',   p.current_company);
  set('prof_title',     p.current_job_title);
  set('prof_industry',  p.industry);
  set('prof_yoe',       p.years_of_experience);
  set('prof_linkedin',  p.linkedin_url);
  set('prof_bio',       p.bio);
  set('prof_expertise', (p.expertise_areas || []).join(', '));
  const acceptEl = document.getElementById('prof_accepting');
  if (acceptEl) acceptEl.checked = !!p.is_accepting_mentees;
}

function bindProfileForm() {
  document.getElementById('profile_form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const alert = document.getElementById('profile_alert');
    const btn   = document.getElementById('profile_btn');

    const expertiseRaw = document.getElementById('prof_expertise')?.value || '';
    const expertise = expertiseRaw.split(',').map(s => s.trim()).filter(Boolean);

    const payload = {
      current_company:    document.getElementById('prof_company')?.value.trim(),
      current_job_title:  document.getElementById('prof_title')?.value.trim(),
      industry:           document.getElementById('prof_industry')?.value.trim(),
      years_of_experience: parseInt(document.getElementById('prof_yoe')?.value) || undefined,
      linkedin_url:       document.getElementById('prof_linkedin')?.value.trim(),
      bio:                document.getElementById('prof_bio')?.value.trim(),
      expertise_areas:    expertise,
      is_accepting_mentees: document.getElementById('prof_accepting')?.checked || false,
    };

    setLoading(btn, true);
    hideAlert(alert);

    try {
      const res = await fetch('/alumni/profile', {
        method: 'PUT',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        showAlert(alert, Object.values(data.errors || {}).join(' ') || data.error || 'Update failed.');
      } else {
        showAlert(alert, 'Profile updated successfully.', 'success');
      }
    } catch {
      showAlert(alert, 'Network error.');
    } finally {
      setLoading(btn, false);
    }
  });
}

/* ---- Mentorship inbox ---- */

async function loadMentorshipRequests(status = 'pending') {
  const container = document.getElementById('requests_list');
  if (!container) return;
  container.innerHTML = '<div class="spinner" style="margin:2rem auto"></div>';

  try {
    const res  = await fetch(`/alumni/mentorship/requests?status=${status}`, { credentials: 'include' });
    const data = await res.json();
    const reqs = data.requests || [];

    if (!reqs.length) {
      container.innerHTML = `<p class="text-muted mt-2">No ${status} requests.</p>`;
      return;
    }

    container.innerHTML = reqs.map(r => `
      <div class="request-item" id="req_${r.id}">
        <div class="req-header">
          <div>
            <div class="req-subject">${esc(r.subject)}</div>
            <div class="req-meta">From: ${esc(r.student_name)} · ${esc(r.student_dept)} · ${esc(r.student_program)}</div>
          </div>
          ${statusBadge(r.status)}
        </div>
        <p class="text-muted mt-1" style="font-size:0.88rem">${esc(r.message)}</p>
        <div class="text-muted mt-1" style="font-size:0.78rem">Received ${formatDate(r.created_at)}</div>
        ${r.status === 'pending' ? `
          <div class="req-actions">
            <button class="btn btn-success btn-sm" onclick="respondRequest(${r.id}, 'accept')">Accept</button>
            <button class="btn btn-danger btn-sm"  onclick="respondRequest(${r.id}, 'reject')">Reject</button>
          </div>
          <div id="respond_alert_${r.id}" class="alert hidden mt-1"></div>
        ` : ''}
      </div>
    `).join('');
  } catch {
    container.innerHTML = '<p class="text-danger mt-2">Failed to load requests.</p>';
  }
}

async function respondRequest(requestId, action) {
  const note  = action === 'reject'
    ? (prompt('Optional: reason for rejection') || '')
    : '';
  const alert = document.getElementById(`respond_alert_${requestId}`);

  try {
    const res = await fetch(`/alumni/mentorship/requests/${requestId}/respond`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, response_note: note }),
    });
    const data = await res.json();
    if (!res.ok) {
      showAlert(alert, data.error || 'Action failed.');
      return;
    }
    // Reload the inbox
    loadMentorshipRequests();
  } catch {
    showAlert(alert, 'Network error.');
  }
}

/* ---- Document / verification status ---- */

async function loadDocumentStatus() {
  const container = document.getElementById('doc_status');
  if (!container) return;

  try {
    const res  = await fetch('/alumni/verification/status', { credentials: 'include' });
    const data = await res.json();

    const statusHtml = data.is_verified
      ? '<span class="badge badge-success">Verified ✓</span>'
      : data.rejection_reason
        ? `<span class="badge badge-danger">Rejected</span> <span class="text-muted" style="font-size:0.82rem">— ${esc(data.rejection_reason)}</span>`
        : '<span class="badge badge-warning">Pending Review</span>';

    const docsHtml = data.documents.length
      ? data.documents.map(d => `
          <div class="flex-between" style="padding:0.6rem 0; border-bottom:1px solid var(--border)">
            <div>
              <span style="font-size:0.88rem">${esc(d.original_filename)}</span>
              <span class="text-muted" style="font-size:0.78rem; margin-left:0.5rem">${esc(d.document_type)}</span>
            </div>
            ${statusBadge(d.review_status)}
          </div>
        `).join('')
      : '<p class="text-muted mt-1" style="font-size:0.88rem">No documents uploaded yet.</p>';

    container.innerHTML = `
      <div class="flex-center mb-2">
        <span class="text-muted" style="font-size:0.85rem">Verification status:</span>
        ${statusHtml}
      </div>
      ${docsHtml}
    `;
  } catch {
    container.innerHTML = '<p class="text-danger">Could not load verification status.</p>';
  }
}

/* ---- Tab switching ---- */

function bindTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      if (btn.hasAttribute('disabled')) return;
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      const panel = document.getElementById(btn.dataset.tab);
      if (panel) panel.classList.add('active');

      if (btn.dataset.tab === 'inbox_tab') {
        const filter = document.getElementById('req_status_filter')?.value || 'pending';
        loadMentorshipRequests(filter);
      }
    });
  });

  document.getElementById('req_status_filter')?.addEventListener('change', e => {
    loadMentorshipRequests(e.target.value);
  });
}

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
  const map = { pending: 'warning', accepted: 'success', approved: 'success', rejected: 'danger', withdrawn: 'muted' };
  return `<span class="badge badge-${map[status] || 'muted'}">${status}</span>`;
}

function showAlert(el, msg, type = 'danger') {
  if (!el) return;
  el.className = `alert alert-${type}`;
  el.textContent = msg;
  el.classList.remove('hidden');
}

function hideAlert(el) { if (el) el.classList.add('hidden'); }

function setLoading(btn, loading) {
  if (!btn) return;
  btn.disabled = loading;
  btn.dataset.orig = btn.dataset.orig || btn.textContent;
  btn.textContent = loading ? 'Saving…' : btn.dataset.orig;
}
