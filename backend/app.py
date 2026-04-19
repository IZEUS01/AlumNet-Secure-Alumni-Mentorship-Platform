<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="referrer" content="strict-origin-when-cross-origin" />
  <title>Admin Panel — AlumNet</title>
  <link rel="stylesheet" href="/static/css/styles.css" />
  <style>
    .admin-sidebar {
      position: fixed;
      left: 0;
      top: 64px;
      bottom: 0;
      width: 220px;
      background: var(--bg-card);
      border-right: 1px solid var(--border);
      padding: 1.5rem 0.75rem;
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
      overflow-y: auto;
      z-index: 100;
    }

    .admin-sidebar-label {
      font-size: 0.68rem;
      font-weight: 700;
      color: var(--text-muted);
      letter-spacing: 0.1em;
      text-transform: uppercase;
      padding: 0.6rem 0.75rem 0.3rem;
      margin-top: 0.75rem;
    }

    .sidebar-link {
      display: flex;
      align-items: center;
      gap: 0.7rem;
      padding: 0.6rem 0.85rem;
      border-radius: 9px;
      font-size: 0.865rem;
      font-weight: 500;
      color: var(--text-muted);
      cursor: pointer;
      background: none;
      border: none;
      width: 100%;
      text-align: left;
      transition: all 0.2s ease;
      font-family: 'Outfit', sans-serif;
    }

    .sidebar-link:hover {
      background: var(--cyan-dim);
      color: var(--text);
    }

    .sidebar-link.active {
      background: var(--cyan-dim);
      color: var(--cyan);
    }

    .sidebar-link .sidebar-badge {
      margin-left: auto;
      background: var(--amber-dim);
      color: var(--amber);
      border-radius: var(--radius-full);
      font-size: 0.68rem;
      font-weight: 700;
      padding: 0.1rem 0.45rem;
    }

    .admin-main {
      margin-left: 220px;
      padding: 0;
    }

    /* Stats cards with animated counters */
    .stats-row {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1rem;
      margin-bottom: 2rem;
      animation: fade-up 0.4s ease;
    }

    .stat-trend {
      display: flex;
      align-items: center;
      gap: 0.3rem;
      font-size: 0.72rem;
      margin-top: 0.4rem;
    }

    .stat-trend.up   { color: var(--emerald); }
    .stat-trend.down { color: var(--rose); }

    /* Action buttons in table */
    .action-group { display: flex; gap: 0.4rem; flex-wrap: wrap; }

    /* User row status */
    .user-status { display: flex; align-items: center; gap: 0.4rem; }

    /* Activity feed */
    .activity-item {
      display: flex;
      align-items: flex-start;
      gap: 0.85rem;
      padding: 0.85rem 0;
      border-bottom: 1px solid var(--border);
    }

    .activity-item:last-child { border-bottom: none; }

    .activity-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      margin-top: 6px;
      flex-shrink: 0;
    }

    .activity-time {
      font-size: 0.72rem;
      color: var(--text-muted);
      white-space: nowrap;
    }

    .activity-msg { font-size: 0.83rem; }

    /* Section panels */
    .admin-section { display: none; }
    .admin-section.active { display: block; animation: fade-up 0.3s ease; }

    @media (max-width: 900px) {
      .admin-sidebar { display: none; }
      .admin-main    { margin-left: 0; }
      .stats-row     { grid-template-columns: repeat(2, 1fr); }
    }
  </style>
</head>
<body class="page-wrapper">

<nav class="navbar" id="navbar">
  <div class="container flex-between">
    <a href="/" class="navbar-brand">
      Alum<span>Net</span>
      <span style="font-size: 0.7rem; color: var(--amber); margin-left: 0.4rem; font-family: 'Outfit',sans-serif; font-weight: 700; letter-spacing: 0.05em;">ADMIN</span>
    </a>
    <ul class="navbar-nav">
      <li>
        <span style="font-size: 0.83rem; color: var(--text-muted); padding: 0 0.5rem;">
          🔑 <span id="user_name"></span>
        </span>
      </li>
      <li>
        <button class="btn btn-ghost btn-sm" data-action="logout">Sign out</button>
      </li>
    </ul>
  </div>
</nav>

<!-- Sidebar -->
<aside class="admin-sidebar">
  <div class="sidebar-link active" onclick="showSection('overview')">
    📊 Overview
  </div>
  <div class="sidebar-link" onclick="showSection('pending')" id="pending_link">
    ⏳ Pending Verification
    <span class="sidebar-badge" id="sidebar_pending_count" style="display:none;"></span>
  </div>

  <div class="admin-sidebar-label">User Management</div>
  <div class="sidebar-link" onclick="showSection('users')">👥 All Users</div>
  <div class="sidebar-link" onclick="showSection('mentorships')">🤝 Mentorships</div>

  <div class="admin-sidebar-label">System</div>
  <div class="sidebar-link" onclick="showSection('audit')">📋 Audit Log</div>
</aside>

<div class="admin-main">
<main class="main-content">
  <div class="container">

    <!-- =========================================================
         OVERVIEW SECTION
         ========================================================= -->
    <div class="admin-section active" id="section_overview">
      <div class="page-header" style="animation: fade-up 0.4s ease;">
        <h1>Admin Panel</h1>
        <p>Platform overview and quick actions</p>
      </div>

      <!-- Stats -->
      <div class="stats-row" id="stats_row">
        <div class="stat-card">
          <div class="stat-label">Total Users</div>
          <div class="stat-value accent" id="stat_total">—</div>
          <div class="stat-trend up">↑ active platform</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Students</div>
          <div class="stat-value" id="stat_students">—</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Verified Alumni</div>
          <div class="stat-value success" id="stat_verified">—</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Pending Review</div>
          <div class="stat-value" style="color: var(--amber);" id="stat_pending">—</div>
          <div class="stat-trend" id="stat_pending_trend"></div>
        </div>
      </div>

      <!-- Recent activity -->
      <div class="card">
        <div class="card-title">
          <div class="card-icon">📋</div>
          Recent Activity
        </div>
        <div id="recent_activity">
          <div style="text-align: center; padding: 2rem;">
            <div class="spinner" style="margin: 0 auto;"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- =========================================================
         PENDING VERIFICATION SECTION
         ========================================================= -->
    <div class="admin-section" id="section_pending">
      <div class="page-header">
        <h1>Pending Verification</h1>
        <p>Review and approve alumni profiles</p>
      </div>

      <div id="pending_alert" class="alert hidden mb-2" role="alert"></div>

      <div class="table-wrap">
        <table id="pending_table">
          <thead>
            <tr>
              <th>Alumni</th>
              <th>Email</th>
              <th>Department</th>
              <th>Grad Year</th>
              <th>Roll No.</th>
              <th>Docs</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody id="pending_body">
            <tr>
              <td colspan="7" class="text-center text-muted" style="padding: 3rem;">
                <div class="spinner" style="margin: 0 auto 1rem;"></div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="flex-between mt-2" id="pending_pagination"></div>
    </div>

    <!-- =========================================================
         USERS SECTION
         ========================================================= -->
    <div class="admin-section" id="section_users">
      <div class="page-header">
        <h1>All Users</h1>
        <p>Search and manage platform users</p>
      </div>

      <div class="flex-between mb-2">
        <div class="flex-center gap-sm flex-wrap">
          <input class="form-control" id="user_search" placeholder="Search name or email…"
                 style="width: 220px;" oninput="debounceSearch()" maxlength="120" />
          <select class="form-control" id="users_role_filter" style="width: auto;" onchange="loadUsers(1)">
            <option value="">All Roles</option>
            <option value="student">Student</option>
            <option value="verified_alumni">Verified Alumni</option>
            <option value="unverified_alumni">Unverified Alumni</option>
            <option value="admin">Admin</option>
          </select>
        </div>
        <div id="users_count" style="font-size: 0.83rem; color: var(--text-muted);"></div>
      </div>

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>User</th>
              <th>Email</th>
              <th>Role</th>
              <th>Joined</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody id="users_body">
            <tr>
              <td colspan="6" class="text-center text-muted" style="padding: 3rem;">
                <div class="spinner" style="margin: 0 auto 1rem;"></div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="flex-between mt-2" id="users_pagination"></div>
    </div>

    <!-- =========================================================
         MENTORSHIPS SECTION
         ========================================================= -->
    <div class="admin-section" id="section_mentorships">
      <div class="page-header">
        <h1>Mentorship Activity</h1>
        <p>Overview of all mentorship requests on the platform</p>
      </div>
      <div id="mentorship_list">
        <div style="text-align: center; padding: 3rem 0;">
          <div class="spinner" style="margin: 0 auto 1rem;"></div>
        </div>
      </div>
    </div>

    <!-- =========================================================
         AUDIT LOG SECTION
         ========================================================= -->
    <div class="admin-section" id="section_audit">
      <div class="page-header">
        <h1>Security Audit Log</h1>
        <p>Immutable record of all security events and admin actions</p>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Event</th>
              <th>User</th>
              <th>IP Address</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody id="audit_body">
            <tr>
              <td colspan="5" class="text-center text-muted" style="padding: 3rem;">
                Audit log will display here once loaded.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

  </div>
</main>
</div>

<!-- Rejection reason modal -->
<div class="modal-overlay" id="reject_modal">
  <div class="modal" style="max-width: 440px;">
    <div class="modal-header">
      <h2 class="modal-title">Reject Application</h2>
      <button class="modal-close" onclick="closeRejectModal()">✕</button>
    </div>
    <p style="font-size: 0.875rem; color: var(--text-muted); margin-bottom: 1.25rem;">
      Provide a brief reason. This will be logged for the audit trail.
    </p>
    <div class="form-group">
      <label class="form-label" for="rejection_reason">Rejection Reason</label>
      <textarea class="form-control" id="rejection_reason" rows="3"
                placeholder="e.g. Incomplete documents, graduation year mismatch…"
                maxlength="500"></textarea>
    </div>
    <input type="hidden" id="reject_user_id" />
    <div style="display: flex; gap: 0.75rem; justify-content: flex-end; margin-top: 0.75rem;">
      <button class="btn btn-ghost" onclick="closeRejectModal()">Cancel</button>
      <button class="btn btn-danger" onclick="confirmReject()">Confirm Reject</button>
    </div>
  </div>
</div>

<div id="toast-container"></div>

<script src="/static/js/auth.js"></script>
<script src="/static/js/admin.js"></script>
<script>
  // Navbar scroll
  window.addEventListener('scroll', () => {
    document.getElementById('navbar').classList.toggle('scrolled', window.scrollY > 20);
  });

  // Section navigation — always reloads data when switching sections
  function showSection(name) {
    document.querySelectorAll('.admin-section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.sidebar-link').forEach(l => l.classList.remove('active'));

    const section = document.getElementById('section_' + name);
    if (section) section.classList.add('active');

    const link = document.querySelector(`.sidebar-link[onclick="showSection('${name}')"]`);
    if (link) link.classList.add('active');

    if (name === 'pending') loadPending(1);
    if (name === 'users')   loadUsers(1);
    if (name === 'audit')   loadAuditLog();
  }

  // Reject modal helpers
  function openRejectModal(userId) {
    document.getElementById('reject_user_id').value = userId;
    document.getElementById('rejection_reason').value = '';
    document.getElementById('reject_modal').classList.add('active');
  }

  function closeRejectModal() {
    document.getElementById('reject_modal').classList.remove('active');
  }

  async function confirmReject() {
    const userId = document.getElementById('reject_user_id').value;
    const reason = document.getElementById('rejection_reason').value.trim();
    if (!reason) {
      document.getElementById('rejection_reason').focus();
      return;
    }
    await rejectAlumni(userId, reason);
    closeRejectModal();
  }
</script>
</body>
</html>
