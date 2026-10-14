# Demo Environment (`demofca.20kevit.ir`)

Isolated end-to-end demonstration deployment of the Academy Management
System with a complete synthetic academy. Demo-only weak credentials are
used; production is never touched by any demo procedure documented here.

## 1. Resources and boundaries

| Concern | Production | Demo |
|---|---|---|
| Hostname | `fca.20kevit.ir` | `demofca.20kevit.ir` |
| Checkout | `/opt/projects/school-manager` | `/opt/projects/school-manager-demo` |
| Branch | `main` | `demo/full-environment` |
| Venv | `.../school-manager/.venv` | `.../school-manager-demo/.venv` |
| systemd | `school-manager.service` | `school-manager-demo.service` |
| Local port | `127.0.0.1:8100` | `127.0.0.1:8101` |
| Nginx vhost | `sites-available/school-manager` | `sites-available/school-manager-demo` |
| TLS | `/etc/letsencrypt/live/fca.20kevit.ir/` | `/etc/letsencrypt/live/demofca.20kevit.ir/` |
| Env file | `/etc/school-manager/school-manager.env` | `/etc/school-manager/school-manager-demo.env` |
| PostgreSQL DB | `school_manager` | `school_manager_demo` |
| PostgreSQL role | `school_manager` | `school_manager_demo` |
| Uploads | `.../school-manager/data/uploads` | `.../school-manager-demo/data/uploads` |
| Evidence | n/a | `.../school-manager-demo/data/browser-evidence/` |

No mutable state is shared. The demo role has `CONNECT` revoked on the
production database, and the production checkout/service/config are never
modified by demo operations. The demo service runs as the same OS user
(`school-manager`) with the same systemd hardening as production; process
identity is distinct via the service name, port, database, and files.

DNS for both hostnames resolves via Cloudflare (proxied). The demo Nginx
vhost sends `X-Robots-Tag: noindex, nofollow`. Login throttling and CSRF
protections from the main stack apply unchanged.

## 2. Deployment revision

- Base: `0965a9a` (`origin/main` at provisioning time).
- Demo runs branch `demo/full-environment` (demo seeder, demo CLI,
  demo tests, this document). Production remains on its own release;
  advancing production is a separate, owner-authorized procedure.

## 3. Setup and deployment (demo only)

All commands run as **root** unless noted. Destructive commands always
target demo-named resources.

```bash
# 1. Database + least-privilege role (postgres OS user)
/usr/bin/su -s /bin/bash postgres -c \
  "psql -v ON_ERROR_STOP=1 -c \"CREATE ROLE school_manager_demo WITH LOGIN PASSWORD '<generated>'\""
/usr/bin/su -s /bin/bash postgres -c \
  "psql -v ON_ERROR_STOP=1 -c \"CREATE DATABASE school_manager_demo OWNER school_manager_demo\""
su -s /bin/bash postgres -c "psql -v ON_ERROR_STOP=1 \
  -c 'REVOKE CONNECT ON DATABASE school_manager FROM school_manager_demo' \
  -c 'REVOKE CONNECT ON DATABASE school_manager_demo FROM PUBLIC' \
  -c 'GRANT CONNECT ON DATABASE school_manager_demo TO school_manager_demo'"

# 2. Environment file (0600/0640, root:school-manager; values never logged)
#    FLASK_ENV=production, SECRET_KEY=<random 64 hex>,
#    DATABASE_URL=postgresql+psycopg2://school_manager_demo:<pw>@127.0.0.1:5432/school_manager_demo
#    FILE_STORAGE_PATH=/opt/projects/school-manager-demo/data/uploads,
#    ZARINPAL_SANDBOX=true, DEMO_MODE=true, ENABLE_SCHEDULER=<empty>

# 3. Code checkout + venv (as root, then fix ownership)
git clone /opt/projects/school-manager /opt/projects/school-manager-demo
cd /opt/projects/school-manager-demo
git remote set-url origin git@github-school-manager:20kevit/school-manager.git
git checkout demo/full-environment
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
mkdir -p data/uploads && chown -R school-manager:school-manager .

# 4. Schema (as school-manager, demo env only)
su -s /bin/bash school-manager -c 'set -a; . /etc/school-manager/school-manager-demo.env; set +a; \
  cd /opt/projects/school-manager-demo && .venv/bin/flask --app wsgi db upgrade'

# 5. Seed, then start
su -s /bin/bash school-manager -c 'set -a; . /etc/school-manager/school-manager-demo.env; set +a; \
  cd /opt/projects/school-manager-demo && .venv/bin/flask --app wsgi demo-seed'
systemctl enable --now school-manager-demo.service

# 6. Nginx + TLS (HTTP-only vhost first, then certbot, then full vhost)
ln -s /etc/nginx/sites-available/school-manager-demo /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
certbot certonly --webroot -w /var/www/letsencrypt -d demofca.20kevit.ir \
  --non-interactive --agree-tos --register-unsafely-without-email
# then deploy the full TLS vhost, nginx -t, reload
```

Updating demo to a newer revision (never touches production):

```bash
cd /opt/projects/school-manager-demo
git fetch origin && git checkout <new-demo-SHA>
chown -R school-manager:school-manager /opt/projects/school-manager-demo
# deps only if requirements.txt changed, then migrate (demo env), then:
systemctl restart school-manager-demo.service
curl -s http://127.0.0.1:8101/health  # expect {"status":"ok","database":"ok"}
# Re-seed ONLY via explicit demo-seed/demo-reset --yes; never on deploy.
```

## 4. Database isolation and safety checks

`app/demo_seed_full.py::assert_demo_environment()` fails closed unless
**all** hold: `DEMO_MODE=true`, `DATABASE_URL` contains
`school_manager_demo`, and `SELECT current_database()` returns
`school_manager_demo`. The `demo-seed` and `demo-reset` CLI commands
abort otherwise — including when accidentally run with the production
environment file. `demo-reset` additionally requires `--yes` and
truncates an explicit table allowlist that excludes `alembic_version`.

Verified refusals: no `DEMO_MODE` refuses; production env file + forced
`DEMO_MODE=true` refuses on URL identity.

## 5. Seed / reset commands

```bash
D='set -a; . /etc/school-manager/school-manager-demo.env; set +a; cd /opt/projects/school-manager-demo'
su -s /bin/bash school-manager -c "$D && .venv/bin/flask --app wsgi demo-seed"
su -s /bin/bash school-manager -c "$D && .venv/bin/flask --app wsgi demo-reset --yes"
```

Properties: deterministic seed `20261014`; idempotent (re-runs are
no-op fast paths; verified byte-identical counts); reset is
truncate + reseed with identical resulting counts (verified).
Baseline seed takes ~15–30 s; the database is ~11 MB.

## 6. Synthetic dataset and scenario coverage

Seed version `2026.10-demo.1` (`app/demo_seed_full.py`).

Counts: 125 users (1 admin, 3 staff + 1 blocked staff, 12 teachers —
teacher12 class-free, 100 students — student100 enrollment-free,
8 parents), 10 courses, 40 classes, 229 enrollments, 624 sessions,
1320 attendances, 60 activities, ~184 submissions, 40 assessments,
~38 results, ~252 transactions, 12 contracts, 19 payments, academic
years/semesters/calendar events, in-app announcements.

Coverage by module:

- **Auth**: correct/wrong logins, anonymous → login redirect (302),
  student/teacher → admin 403, role portals 200, inactive accounts,
  `must_change_password=false` for easy login.
- **Students/instructors**: full/minor/adult profiles, multi-class
  teachers, class-free teacher, multi-enrollment and zero-enrollment
  students, search/filter/pagination depth.
- **Courses/classes/schedules**: 10 Persian courses; classes PLANNED /
  ACTIVE / COMPLETED / CANCELLED; full class (capacity 8, +1 blocked
  pending), large class (40), empty planned class; past/current/future
  sessions; online links on classes/sessions.
- **Enrollments**: PENDING / APPROVED / REJECTED / CANCELLED with valid
  timestamps; capacity-blocked pending; duplicate prevention (unique
  constraint respected); 12-month history.
- **Attendance**: PRESENT / ABSENT / LATE / EXCUSED; complete, partial,
  and empty sessions; same-class/approved invariants enforced.
- **Assessments/grades**: QUIZ / MIDTERM / FINAL_EXAM / PROJECT /
  PRACTICAL / ORAL; DRAFT (no grades) through CANCELLED; absent/excused
  results; negative marking on one quiz; grade-history corrections.
- **Finance** (all via `finance_service`, balances reconcile):
  tuition charges (backdated 12 months), full/partial/unpaid, CASH/CARD/
  BANK_TRANSFER/ONLINE, discounts, linked full + partial refunds,
  one reversal, one correction, one goodwill adjustment,
  PENDING + FAILED online payments with gateway refs (sandbox
  simulation — no real money moves).
- **Payroll**: PER_SESSION + PERCENTAGE_OF_REVENUE contracts + generic
  fallback; PENDING / PAID / VOIDED payments across 3 periods.
- **Activities**: HOMEWORK / PROJECT / QUIZ / PRACTICE, required +
  optional, one deactivated; GRADED / SUBMITTED / RETURNED / unsubmitted.
- **Calendar**: 2 academic years, 4 semesters (1 active), 3 events.
- **Notifications**: in-app announcement to sample users; external
  providers unconfigured by design (graceful degradation).
- **Audit**: correction/reversal audit rows via services.

Names/content are Persian, fictional, deterministic; dates span ~12
months including month/year boundaries.

## 7. Demo credentials and roles

Shared demo password (demo accounts only, never production): `12345678`.
All passwords are Werkzeug-hashed; none stored plaintext.

| Role | Usernames | Notes |
|---|---|---|
| Administrator | `admin` | full access |
| Staff | `staff1`–`staff3` (`staff_blocked` inactive) | ADMIN role |
| Instructors | `teacher1`–`teacher12` | `teacher12` has no classes |
| Students | `student1`–`student100` | `student100` has no enrollments; every 10th is 18+ (finance visible) |
| Parents | `parent1`–`parent8` | linked to deterministic children |

## 8. Disabled external integrations

Real payments, SMS, Telegram/Bale, and SMTP are unconfigured in the demo
env (empty credentials → provider graceful degradation). Online payments
appear as PENDING/FAILED demo rows with `DEMO-` references; the ZarinPal
gateway runs sandbox-configured with no merchant id (NullGateway path).
No real message or money movement is possible from seeded data; the demo
announcement banner states this in Persian.

## 9. Backup and recovery

```bash
# Baseline backup (as root)
mkdir -p /var/backups/school-manager-demo
su -s /bin/bash postgres -c "pg_dump -Fc -d school_manager_demo \
  -f /var/backups/school-manager-demo/school_manager_demo-<date>.dump"
chmod 600 /var/backups/school-manager-demo/*.dump

# Restore (demo only; stops demo service, never production)
systemctl stop school-manager-demo.service
su -s /bin/bash postgres -c "pg_restore -c -d school_manager_demo <dump>"
systemctl start school-manager-demo.service
curl -s http://127.0.0.1:8101/health
```

Cheapest recovery is usually `demo-reset --yes` (deterministic
baseline, ~30 s). Use dump restore only when the schema/data itself is
suspect. No automated demo backup timer exists yet; production's daily
timer is untouched and demo dumps are excluded from it.

## 10. Verification summary

- `https://demofca.20kevit.ir` HTTPS 200 (LE cert to 2027-01-12),
  HTTP→HTTPS redirect, origin + Cloudflare edge both 200.
- Guard tests (7), seed tests (5: coverage, idempotency,
  integrity, finance reconcile, hashing) in `tests/test_demo_seed.py`.
- Full suite: 1058 passed, 9 pre-existing skips; Ruff check + format
  clean.
- Real-browser (headless Chrome, origin TLS): 4 viewports × login for
  3 roles + 13 module pages each — 52 checks, all 200, RTL true, zero
  horizontal overflow, zero console errors, zero failed requests.
  Screenshots: `data/browser-evidence/` (server-side, untracked).
- Production isolation: separate DB/role/service/vhost/env/uploads;
  prod checkout clean at `0965a9a`, prod DB holds 1 user (unchanged),
  prod service not restarted by this work, prod env file untouched.

Known limitations: egress IPv6 from the VPS is unreliable — validation
used IPv4/host-local resolution; external visitors are unaffected.
`student100`'s empty state and `teacher12`'s class-free state are
intentional edge cases, not gaps.
