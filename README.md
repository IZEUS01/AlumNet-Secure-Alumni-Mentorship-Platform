<p align="center">
<img src="https://readme-typing-svg.herokuapp.com?font=Orbitron&size=40&duration=3000&pause=1000&color=00F5FF&center=true&vCenter=true&width=900&lines=ALUMNET;Secure+Alumni+Mentorship+Platform;Security+Built+From+Day+One;Bridging+Trust+With+Technology" />
</p>

<p align="center">
<img src="https://img.shields.io/badge/STATUS-Production_Ready-00f5ff?style=for-the-badge">
<img src="https://img.shields.io/badge/SECURITY-First-ff00ff?style=for-the-badge">
<img src="https://img.shields.io/badge/SSDLC-Integrated-00ff9f?style=for-the-badge">
<img src="https://img.shields.io/badge/BUILT_WITH-Python-black?style=for-the-badge&logo=python">
</p>

<p align="center">
<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0f0c29,50:302b63,100:24243e&height=200&section=header&text=ALUMNET&fontSize=60&fontColor=00F5FF&animation=fadeIn"/>
</p>

A secure digital bridge between students and verified alumni. > No fake profiles. No data leaks. No trust issues.

AlumNet is a security-first mentorship platform engineered using Secure Software Development Lifecycle (SSDLC) principles.

Built like a startup. Designed like a security lab.

🛠 Tech Stack
<p align="center">
<img src="https://skillicons.dev/icons?i=python,flask,postgresql,html,css,git" />
</p>

<p align="center">
<img src="https://media.giphy.com/media/xT9IgzoKnwFNmISR8I/giphy.gif" width="700"/>
</p>

🔐 Core Security Capabilities
Security is implemented in architecture — not patched later.

⚡ Role-Based Access Control: Strict authorization checks at every endpoint.

⚡ Secure Password Hashing: Utilizing modern hashing algorithms (bcrypt/PBKDF2).

⚡ Input Validation & XSS Prevention: Rigorous sanitization of all user-supplied data.

⚡ SQL Injection Protection: Enforced through SQLAlchemy parameterized queries.

⚡ Secure File Upload Handling: Strict MIME-type checking and randomized renaming.

⚡ HTTPS Enforcement: Secure data in transit.

⚡ Session Expiration Control: Time-bound, secure JWT or session cookies.

⚡ Backend-Only Sensitive Logic: The frontend only displays data; the backend verifies everything.

🏗 Architecture
Backend handles all validation, frontend only displays secure data.

Plaintext
  Student / Alumni / Admin
             │
             ▼
       Flask Backend
             │
             ▼
  Secure Authentication Layer
             │
             ▼
    PostgreSQL Database
🧠 Roles
Each role is isolated with strict permission boundaries ensuring the K.I.S.S. principle is maintained across the access control matrix.

🎓 Student: Can browse verified profiles and request mentorship.

👔 Unverified Alumni: Can build a profile and upload verification documents. (Read-only access to the rest of the platform).

✅ Verified Alumni: Can set mentorship slots, approve requests, and message students.

🛠️ Admin: Can verify identities, manage platform health, and revoke access.
