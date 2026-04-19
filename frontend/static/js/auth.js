/**
 * auth.js — AlumNet
 * Auth routes are CSRF-exempt (JSON API + SameSite=Strict cookie).
 */

const API = '/auth';

/* ── POST helper ── */
async function postJSON(url, body) {
  const res = await fetch(url, {
    method:      'POST',
    credentials: 'include',
    headers:     { 'Content-Type': 'application/json' },
    body:        JSON.stringify(body),
  });
  // Always parse as text first — avoids JSON parse crash on unexpected HTML responses
  const text = await res.text();
  let data = {};
  try { data = JSON.parse(text); } catch { data = { error: text || 'Unexpected server response.' }; }
  return { res, data };
}

/* ── UI helpers ── */
function showAlert(el, msg, type = 'danger') {
  if (!el) return;
  el.className = `alert alert-${type}`;
  el.innerHTML = msg;
  el.classList.remove('hidden');
  el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}
function hideAlert(el) { if (el) el.classList.add('hidden'); }

function setLoading(btn, on, text = 'Please wait…') {
  if (!btn) return;
  btn.disabled = on;
  if (!btn.dataset.orig) btn.dataset.orig = btn.innerHTML;
  btn.innerHTML = on ? `<span class="btn-spinner"></span>${text}` : btn.dataset.orig;
}

function fieldError(id, msg) {
  const err = document.getElementById(id + '_error');
  const inp = document.getElementById(id);
  if (err) { err.textContent = msg || ''; err.classList.toggle('visible', !!msg); }
  if (inp)  inp.classList.toggle('input-error', !!msg);
}

function clearErrors() {
  document.querySelectorAll('.form-error').forEach(e => { e.textContent = ''; e.classList.remove('visible'); });
  document.querySelectorAll('.input-error').forEach(e => e.classList.remove('input-error'));
}

function showToast(msg, type = 'success') {
  const c = document.getElementById('toast-container');
  if (!c) return;
  const t = document.createElement('div');
  t.className = `toast toast-${type}`;
  t.innerHTML = `<span class="toast-icon">${type === 'success' ? '✓' : '✕'}</span>${msg}`;
  c.appendChild(t);
  requestAnimationFrame(() => t.classList.add('visible'));
  setTimeout(() => { t.classList.remove('visible'); setTimeout(() => t.remove(), 400); }, 4000);
}

/* ── Password strength ── */
function pwStrength(pw) {
  const checks = [
    { ok: pw.length >= 8,          hint: 'At least 8 characters.' },
    { ok: /[A-Z]/.test(pw),        hint: 'One uppercase letter.' },
    { ok: /[0-9]/.test(pw),        hint: 'One digit.' },
    { ok: /[^A-Za-z0-9]/.test(pw), hint: 'One special character.' },
  ];
  return { score: checks.filter(c => c.ok).length, missing: checks.filter(c => !c.ok).map(c => c.hint) };
}

function renderStrength(pw) {
  const wrap = document.getElementById('pw_strength_wrap');
  const bar  = document.getElementById('pw_strength_bar');
  const lbl  = document.getElementById('pw_strength_label');
  if (!wrap) return;
  wrap.style.display = pw ? 'flex' : 'none';
  if (!pw) return;
  const { score } = pwStrength(pw);
  const cfg = [
    null,
    { w:'25%',  c:'#fb7185', t:'Weak'   },
    { w:'50%',  c:'#fbbf24', t:'Fair'   },
    { w:'75%',  c:'#34d399', t:'Good'   },
    { w:'100%', c:'#4fc4f7', t:'Strong' },
  ][score] || { w:'0%', c:'', t:'' };
  if (bar) { bar.style.width = cfg.w; bar.style.background = cfg.c; }
  if (lbl) { lbl.textContent = cfg.t; lbl.style.color = cfg.c; }
}

/* ================================================================
   LOGIN
   ================================================================ */
async function handleLogin(e) {
  e.preventDefault();
  clearErrors();

  const alertEl = document.getElementById('login_alert');
  const btn     = document.getElementById('login_btn');
  const email   = document.getElementById('email').value.trim();
  const pass    = document.getElementById('password').value;

  if (!email) { fieldError('email',    'Email is required.');    return; }
  if (!pass)  { fieldError('password', 'Password is required.'); return; }

  setLoading(btn, true, 'Signing in…');
  hideAlert(alertEl);

  let res, data;
  try {
    ({ res, data } = await postJSON(`${API}/login`, { email, password: pass }));
  } catch (err) {
    showAlert(alertEl, `Server error: ${err.message}. Is Flask running?`);
    setLoading(btn, false);
    return;
  }

  setLoading(btn, false);

  if (!res.ok) {
    showAlert(alertEl, data.error || 'Login failed. Please try again.');
    return;
  }

  showToast('Welcome back, ' + (data.user?.full_name || 'there') + '!');
  const role = data.user?.role || '';
  setTimeout(() => {
    if      (role === 'admin')        window.location.href = '/admin/dashboard';
    else if (role === 'student')      window.location.href = '/student/dashboard';
    else if (role.includes('alumni')) window.location.href = '/alumni/dashboard';
    else                              window.location.href = '/student/dashboard';
  }, 600);
}

/* ================================================================
   REGISTER
   ================================================================ */
async function handleRegister(e) {
  e.preventDefault();
  clearErrors();

  const alertEl   = document.getElementById('register_alert');
  const btn       = document.getElementById('register_btn');
  const email     = document.getElementById('email').value.trim();
  const username  = document.getElementById('username').value.trim();
  const full_name = document.getElementById('full_name').value.trim();
  const password  = document.getElementById('password').value;
  const role      = (document.querySelector('input[name="role"]:checked') || {}).value || 'student';

  let hasError = false;
  if (!full_name) { fieldError('full_name', 'Full name is required.');  hasError = true; }
  if (!username)  { fieldError('username',  'Username is required.');   hasError = true; }
  if (!email)     { fieldError('email',     'Email is required.');      hasError = true; }
  if (!password)  { fieldError('password',  'Password is required.');   hasError = true; }
  if (hasError) return;

  const { score, missing } = pwStrength(password);
  if (score < 3) { fieldError('password', missing.join(' ')); return; }

  setLoading(btn, true, 'Creating account…');
  hideAlert(alertEl);

  // department + graduation_year sent for ALL roles (always visible fields)
  const body = {
    email, username, full_name, password, role,
    department:      document.getElementById('department')?.value.trim()              || '',
    graduation_year: parseInt(document.getElementById('graduation_year')?.value) || null,
  };
  // Alumni-only extras
  if (role === 'alumni') {
    body.degree_program  = document.getElementById('degree_program')?.value.trim()   || '';
    body.gik_roll_number = document.getElementById('roll_number')?.value.trim()      || '';
  }

  let res, data;
  try {
    ({ res, data } = await postJSON(`${API}/register`, body));
  } catch (err) {
    showAlert(alertEl, `Server error: ${err.message}. Is Flask running?`);
    setLoading(btn, false);
    return;
  }

  setLoading(btn, false);

  if (!res.ok) {
    if (data.errors) {
      Object.entries(data.errors).forEach(([f, m]) => fieldError(f, Array.isArray(m) ? m.join(' ') : m));
    } else {
      showAlert(alertEl, data.error || 'Registration failed. Please try again.');
    }
    return;
  }

  // ✅ Success — go to login
  showAlert(alertEl, '✅ Account created! Redirecting to login…', 'success');
  setTimeout(() => { window.location.href = '/login?registered=1'; }, 1800);
}

/* ================================================================
   LOGOUT
   ================================================================ */
async function handleLogout() {
  try { await postJSON(`${API}/logout`, {}); } finally {
    window.location.href = '/login';
  }
}

/* ================================================================
   SESSION GUARD (used by dashboard pages)
   ================================================================ */
async function requireAuth(allowedRoles = []) {
  try {
    const res = await fetch(`${API}/me`, { credentials: 'include' });
    if (!res.ok) { window.location.href = '/login'; return null; }
    const user = await res.json();
    if (allowedRoles.length && !allowedRoles.includes(user.role)) {
      window.location.href = '/login'; return null;
    }
    return user;
  } catch {
    window.location.href = '/login'; return null;
  }
}

/* ================================================================
   BOOT
   ================================================================ */
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('login_form')   ?.addEventListener('submit', handleLogin);
  document.getElementById('register_form')?.addEventListener('submit', handleRegister);
  document.querySelector('[data-action="logout"]')?.addEventListener('click', handleLogout);

  // Password strength
  document.getElementById('password')?.addEventListener('input', function () { renderStrength(this.value); });

  // Password toggles
  document.querySelectorAll('.pw-eye').forEach(btn => {
    btn.addEventListener('click', () => {
      const t = document.getElementById(btn.dataset.target || 'password');
      if (!t) return;
      const show = t.type === 'password';
      t.type          = show ? 'text' : 'password';
      btn.textContent = show ? '🙈' : '👁';
    });
  });

  // Alumni extra fields
  document.querySelectorAll('input[name="role"]').forEach(r => {
    r.addEventListener('change', function () {
      const s = document.getElementById('alumni_fields');
      if (!s) return;
      s.classList.toggle('open', this.value === 'alumni');
      ['department','degree_program','graduation_year'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.required = this.value === 'alumni';
      });
    });
  });

  // Login page banners
  const loginAlert = document.getElementById('login_alert');
  if (loginAlert) {
    const p = new URLSearchParams(window.location.search);
    if (p.get('registered')) showAlert(loginAlert, '✅ Account created! You can now sign in.', 'success');
    if (p.get('verified'))   showAlert(loginAlert, '✅ Email verified! You can now sign in.',  'success');
  }
});
