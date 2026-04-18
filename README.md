<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0d1117,50:161b22,100:0d1117&height=120&section=header"/>

<br/>

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=700&size=38&duration=2800&pause=1200&color=58A6FF&center=true&vCenter=true&width=800&lines=AlumNet;Secure+Alumni+Mentorship+Platform;SSDLC+%E2%80%94+Security+From+Day+One" alt="AlumNet" />

<br/><br/>

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-ORM-D71F00?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlalchemy.org)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](LICENSE)
[![OWASP](https://img.shields.io/badge/OWASP-Top_10_Compliant-000000?style=for-the-badge)](https://owasp.org)
[![Status](https://img.shields.io/badge/Status-Active_Development-f59e0b?style=for-the-badge)]()

<br/>

> **A security-first alumni mentorship platform built under the Secure Software Development Lifecycle (SSDLC).**  
> No fake profiles. No data leaks. No trust gaps.

<br/>

</div>

---

## Table of Contents

- [Overview](#overview)
- [Problem Statement](#problem-statement)
- [Architecture](#architecture)
- [Security Model](#security-model)
- [Role System](#role-system)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Security Controls Reference](#security-controls-reference)
- [SSDLC Phases](#ssdlc-phases)
- [Risk Register](#risk-register)
- [Team](#team)

---

## Overview

**AlumNet** is a university networking platform that connects students with verified alumni through a structured, security-enforced mentorship workflow. Every feature is designed with threat modeling, risk assessment, and the OWASP Top 10 in mind — security is part of the architecture, not an afterthought.

The platform is developed as part of the **Secure Software Design (SSD)** course at the **Ghulam Ishaq Khan Institute of Engineering Sciences and Technology**, demonstrating real-world application of SSDLC principles.

---

## Problem Statement

Existing alumni networking platforms suffer from:

| Issue | Impact |
|---|---|
| Unverified alumni profiles | Impersonation and fake credentials |
| Weak role separation | Students accessing restricted alumni data |
| Insecure password storage | Mass credential exposure on breach |
| Missing input validation | XSS and injection vulnerabilities |
| No audit trail | Repudiation — actions cannot be traced |
| Insecure file uploads | Malicious file execution on the server |

AlumNet addresses every one of these with purpose-built security controls.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    CLIENT LAYER                         │
│         Student UI │ Alumni UI │ Admin Panel            │
└───────────────────────┬─────────────────────────────────┘
                        │  HTTPS (TLS enforced)
┌───────────────────────▼─────────────────────────────────┐
│                  FLASK BACKEND                          │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │   Auth &    │  │    RBAC      │  │    Input      │  │
│  │  Sessions   │  │  Middleware  │  │  Validation   │  │
│  └─────────────┘  └──────────────┘  └───────────────┘  │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │    Rate     │  │   Secure     │  │    Audit      │  │
│  │  Limiting   │  │File Handling │  │   Logging     │  │
│  └─────────────┘  └──────────────┘  └───────────────┘  │
└───────────────────────┬─────────────────────────────────┘
                        │  SQLAlchemy ORM (parameterized)
┌───────────────────────▼─────────────────────────────────┐
│              PostgreSQL / SQLite Database               │
│    users │ students │ alumni │ mentorship_requests      │
│    verification_documents │ audit_logs                  │
└─────────────────────────────────────────────────────────┘
```

**Key principle:** The frontend is display-only. All validation, role enforcement, and business logic lives exclusively on the backend.

---

## Security Model

AlumNet implements defence-in-depth across seven security layers:

### Authentication & Session Management

| Control | Implementation |
|---|---|
| `AUTH-01` | Unique email + username identity |
| `AUTH-02` | `bcrypt` (12 rounds) — passwords never stored in plaintext |
| `AUTH-03` | Enforced password complexity (length, uppercase, digit, special char) |
| `AUTH-04` | Account lockout after 5 failed attempts (15-minute cooldown) |
| `AUTH-05` | Cryptographically secure session tokens via Flask-Login |
| `AUTH-06` | 30-minute inactivity session expiration |
| `AUTH-07` | Server-side session invalidation on logout |

### Application Security

| Control | Implementation |
|---|---|
| `APP-01` | Server-side input validation on every endpoint |
| `APP-02` | Output encoding via Jinja2 auto-escaping (XSS prevention) |
| `APP-03` | CSRF tokens on all state-changing requests (Flask-WTF) |
| `APP-04` | HTTPS enforcement + HSTS + secure HTTP headers (Flask-Talisman) |
| `APP-05` | Generic error messages — no stack traces or internal paths exposed |
| `APP-06` | Immutable security audit log for all critical events |

### Data Security

| Control | Implementation |
|---|---|
| `DATA-01` | Role-scoped data access — users only see what their role permits |
| `DATA-02` | File MIME-type validated via magic bytes (not just extension) |
| `DATA-03` | File size capped at 5 MB per upload |
| `DATA-04` | Uploads stored outside the web root — never served statically |
| `DATA-05` | SQLAlchemy ORM — parameterized queries, no raw SQL |

---

## Role System

Access control is enforced server-side at every route. Clients cannot self-assign or escalate roles.

```
┌────────────────┬──────────────────────────────────────────────────────┐
│ Role           │ Permissions                                          │
├────────────────┼──────────────────────────────────────────────────────┤
│ 🎓 Student     │ Browse verified alumni profiles                      │
│                │ Send mentorship requests                             │
│                │ Manage own profile                                   │
├────────────────┼──────────────────────────────────────────────────────┤
│ ⏳ Unverified  │ Build alumni profile                                 │
│    Alumni      │ Upload verification documents                        │
│                │ Read-only access to rest of platform                 │
├────────────────┼──────────────────────────────────────────────────────┤
│ ✅ Verified    │ All Unverified Alumni permissions                    │
│    Alumni      │ Set mentorship availability                          │
│                │ Accept / reject mentorship requests                  │
│                │ Appear in student-facing search                      │
├────────────────┼──────────────────────────────────────────────────────┤
│ 🛡️ Admin       │ Review and verify alumni identity documents          │
│                │ Approve / reject alumni accounts                     │
│                │ Deactivate users                                     │
│                │ View full audit logs                                 │
│                │ Manage platform health                               │
└────────────────┴──────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Backend | Python 3.11 + Flask 3.0 | Core application server |
| ORM | SQLAlchemy 2.0 | Database abstraction, SQL injection prevention |
| Auth | Flask-Login + bcrypt | Session management, password hashing |
| CSRF | Flask-WTF | Cross-Site Request Forgery protection |
| Rate Limiting | Flask-Limiter | Brute-force and DoS mitigation |
| Security Headers | Flask-Talisman | HSTS, CSP, X-Frame-Options |
| Input Validation | marshmallow + bleach | Schema validation and XSS sanitization |
| Database | PostgreSQL (prod) / SQLite (dev) | Persistent data store |
| Migrations | Alembic | Schema version control |

---

## Project Structure

```
alumnet/
├── backend/
│   ├── app.py                   # Application factory
│   ├── config.py                # Environment-based configuration
│   ├── requirements.txt
│   │
│   ├── auth/                    # Authentication module
│   │   ├── routes.py            # /register /login /logout /change-password
│   │   ├── decorators.py        # @role_required @admin_required
│   │   └── utils.py             # bcrypt, password policy, lockout helpers
│   │
│   ├── models/                  # SQLAlchemy ORM models
│   │   ├── user.py              # Base user + RBAC role + lockout fields
│   │   ├── student.py           # Student academic profile
│   │   ├── alumni.py            # Alumni professional profile + verification
│   │   ├── admin.py             # Admin metadata + action counters
│   │   ├── mentorship.py        # Mentorship request lifecycle
│   │   ├── verification.py      # Alumni document upload metadata
│   │   └── audit_log.py         # Immutable security event log
│   │
│   ├── routes/                  # Feature blueprints (coming soon)
│   │   ├── student.py
│   │   ├── alumni.py
│   │   ├── admin.py
│   │   └── mentorship.py
│   │
│   ├── security/                # Security controls (coming soon)
│   │   ├── input_validation.py
│   │   ├── file_upload.py
│   │   ├── rate_limiter.py
│   │   └── headers.py
│   │
│   └── uploads/                 # Secure file storage (non-web-accessible)
│
├── docs/
│   ├── project_proposal.docx
│   ├── threat_model.docx
│   ├── risk_management.docx
│   └── security_requirements.docx
│
└── security-reports/
    ├── stride_threat_model.md
    ├── risk_register.md
    └── security_test_report.md
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- pip
- (Optional) PostgreSQL for production

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-username/alumnet.git
cd alumnet/backend

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp ../.env.example .env
# Edit .env with your SECRET_KEY, DATABASE_URL, etc.

# 5. Run the development server
flask run
```

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | ✅ | Flask session signing key (use a long random string) |
| `JWT_SECRET_KEY` | ✅ | JWT token signing key |
| `DATABASE_URL` | ✅ | Database connection string |
| `FLASK_ENV` | ✅ | `development` / `testing` / `production` |
| `REDIS_URL` | ⬜ | Redis URI for rate limiter backend (optional) |
| `LOG_LEVEL` | ⬜ | `DEBUG` / `INFO` / `WARNING` |
| `ALLOWED_ORIGINS` | ⬜ | Comma-separated CORS-allowed origins |

> ⚠️ **Never commit `.env` to version control.** The `.gitignore` excludes it by default.

---

## Security Controls Reference

Full mapping of requirements to SSDLC documents:

| ID | Control | Threat Mitigated | Document |
|---|---|---|---|
| AUTH-02 | bcrypt password hashing | Credential exposure on breach | Security Requirements |
| AUTH-04 | Account lockout (5 attempts) | Brute-force (R10) | Risk Management |
| APP-03 | CSRF tokens | CSRF attacks | Security Requirements |
| APP-04 | HTTPS + HSTS | MITM, session interception | Threat Model |
| APP-06 | Audit logging | Repudiation (STRIDE) | Threat Model |
| DATA-02 | Magic-byte MIME validation | Malicious file upload (Tampering) | Threat Model |
| DATA-05 | SQLAlchemy ORM | SQL Injection (R02) | Risk Management |
| RBAC-06 | Server-side role enforcement | Privilege escalation | Security Requirements |

---

## SSDLC Phases

```
Phase 1 — Requirements Analysis     ✅  Security requirements defined
Phase 2 — Threat Modeling           ✅  STRIDE model completed
Phase 3 — Risk Management           ✅  Risk register with mitigations
Phase 4 — Secure Design             ✅  Architecture and data model
Phase 5 — Secure Implementation     🔄  In progress
Phase 6 — Security Testing          ⬜  Planned
Phase 7 — Secure Deployment         ⬜  Planned
```

---

## Risk Register Summary

| ID | Risk | Likelihood | Impact | Score | Priority |
|---|---|---|---|---|---|
| R01 | Unauthorized access | 3 | 5 | **15** | 🔴 High |
| R02 | SQL Injection | 3 | 4 | **12** | 🔴 High |
| R03 | XSS attacks | 3 | 4 | **12** | 🔴 High |
| R04 | PII data leakage | 2 | 5 | **10** | 🔴 High |
| R05 | Server downtime | 3 | 4 | **12** | 🔴 High |
| R06 | Session hijacking | 2 | 4 | **8** | 🟡 Medium |
| R07 | Weak passwords | 3 | 3 | **9** | 🟡 Medium |
| R10 | Brute-force login | 2 | 3 | **6** | 🟢 Low |

Full risk register with mitigations available in [`docs/risk_management.docx`](docs/risk_management.docx).

---

## Team

<table>
<tr>
<td align="center">
<b>M. Haider Iqbal</b><br/>
<code>2023416</code>
</td>
<td align="center">
<b>Shehroz Majeed</b><br/>
<code>2023649</code>
</td>
</tr>
</table>

**Institution:** Ghulam Ishaq Khan Institute of Engineering Sciences and Technology  
**Course:** Secure Software Development and Design (SSD)

---

<div align="center">

**Security is not a feature. It is the foundation.**

<br/>

[![OWASP](https://img.shields.io/badge/Follows-OWASP_Top_10-000000?style=flat-square)](https://owasp.org/Top10/)
[![NIST](https://img.shields.io/badge/Follows-NIST_RMF-003087?style=flat-square)](https://csrc.nist.gov/projects/risk-management)
[![ISO27001](https://img.shields.io/badge/Aligned-ISO_IEC_27001-0076C0?style=flat-square)](https://www.iso.org/isoiec-27001-information-security.html)

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0d1117,50:161b22,100:0d1117&height=80&section=footer"/>

</div>
