/**
 * auth.js
 * Handles login, registration, logout, and session state.
 * All requests include credentials (cookies) for session-based auth.
 */

const API = '/auth';

/* ---- Shared helpers ---- */

function showAlert(el, msg, type = 'danger') {
  el.className = `alert alert-${type}`;
  el.textContent = msg;
  el.classList.remove('hidden');
}

function hideAlert(el) { el.classList.add('hidden'); }

function setLoading(btn, loading) {
  btn.disabled = loading;
  btn.dataset.orig = btn.dataset.orig || btn.textContent;
  btn.textContent = loading ? 'Please wait…' : btn.dataset.orig;
}

function fieldError(inputId, msg) {
  const el = document.getElementById(inputId + '_error');
  if (!el) return;
  el.textContent = msg;
  el.classList.toggle('visible', !!msg);
}

function clearFieldErrors() {
  document.querySelectorAll('.form-error').forEach(e => {
    e.textContent = ''; e.classList.remove('visible');
  });
}

/* ---- Login ---- */

async function handleLogin(e) {
  e.preventDefault();
  clearFieldErrors();

  const alert = document.getElementById('login_alert');
  const btn   = document.getElementById('login_btn');
  const email = document.getElementById('email').value.trim();
  const pass  = document.getElementById('password').value;

  if (!email) { fieldError('email', 'Email is required.'); return; }
  if (!pass)  { fieldError('password', 'Password is required.'); return; }

  setLoading(btn, true);
  hideAlert(alert);

  try {
    const res = await fetch(`${API}/login`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password: pass }),
    });
    const data = await res.json();

    if (!res.ok) {
      showAlert(alert, data.error || 'Login failed.');
      return;
    }

    // Redirect based on role
    const role = data.user?.role;
    if (role === 'admin')            window.location.href = '/admin/dashboard';
    else if (role === 'student')     window.location.href = '/student/dashboard';
    else                             window.location.href = '/alumni/dashboard';

  } catch {
    showAlert(alert, 'Network error. Please try again.');
  } finally {
    setLoading(btn, false);
  }
}

/* ---- Register ---- */

async function handleRegister(e) {
  e.preventDefault();
  clearFieldErrors();

  const alert     = document.getElementById('register_alert');
  const btn       = document.getElementById('register_btn');
  const email     = document.getElementById('email').value.trim();
  const username  = document.getElementById('username').value.trim();
  const full_name = document.getElementById('full_name').value.trim();
  const password  = document.getElementById('password').value;
  const role      = document.getElementById('role').value;

  let hasError = false;
  if (!email)     { fieldError('email',     'Email is required.');      hasError = true; }
  if (!username)  { fieldError('username',  'Username is required.');   hasError = true; }
  if (!full_name) { fieldError('full_name', 'Full name is required.');  hasError = true; }
  if (!password)  { fieldError('password',  'Password is required.');   hasError = true; }
  if (hasError) return;

  setLoading(btn, true);
  hideAlert(alert);

  try {
    const res = await fetch(`${API}/register`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, username, full_name, password, role }),
    });
    const data = await res.json();

    if (!res.ok) {
      // Field-level errors from backend
      if (data.errors) {
        Object.entries(data.errors).forEach(([field, msg]) => {
          fieldError(field, Array.isArray(msg) ? msg.join(' ') : msg);
        });
      } else {
        showAlert(alert, data.error || 'Registration failed.');
      }
      return;
    }

    const msg = data.pending_verification
      ? 'Account created! Your alumni profile is pending admin verification.'
      : 'Account created! You can now log in.';
    showAlert(alert, msg, 'success');

    setTimeout(() => { window.location.href = '/login'; }, 2000);

  } catch {
    showAlert(alert, 'Network error. Please try again.');
  } finally {
    setLoading(btn, false);
  }
}

/* ---- Logout ---- */

async function handleLogout() {
  try {
    await fetch(`${API}/logout`, { method: 'POST', credentials: 'include' });
  } finally {
    window.location.href = '/login';
  }
}

/* ---- Session guard (call on protected pages) ---- */

async function requireAuth(allowedRoles = []) {
  try {
    const res = await fetch(`${API}/me`, { credentials: 'include' });
    if (!res.ok) { window.location.href = '/login'; return null; }
    const user = (await res.json());
    if (allowedRoles.length && !allowedRoles.includes(user.role)) {
      window.location.href = '/login'; return null;
    }
    return user;
  } catch {
    window.location.href = '/login'; return null;
  }
}

/* ---- Bind forms on DOMContentLoaded ---- */

document.addEventListener('DOMContentLoaded', () => {
  const loginForm    = document.getElementById('login_form');
  const registerForm = document.getElementById('register_form');
  const logoutBtn    = document.querySelector('[data-action="logout"]');

  if (loginForm)    loginForm.addEventListener('submit', handleLogin);
  if (registerForm) registerForm.addEventListener('submit', handleRegister);
  if (logoutBtn)    logoutBtn.addEventListener('click', handleLogout);
});
