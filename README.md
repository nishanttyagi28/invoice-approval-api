# invoice-approval-api

REST API for a small business to record vendor GST invoices (India) and run them through an
approval flow before payment. Amounts above an organization limit need two different approvers,
and every status change is written to an audit log that cannot be edited or deleted.

Built with Python 3.12, Django 5, Django REST Framework, PostgreSQL, JWT (simplejwt), Celery and
Redis, drf-spectacular for the OpenAPI docs.

## Approval flow

```
draft -> submitted -> reviewed -> approved -> paid
              \           \
               +-----------+-> rejected
```

- `draft`: created, can still be edited or deleted by its creator (or a finance admin).
- `submitted`: sent for approval with `POST /api/invoices/{id}/submit/`. Locked for editing.
- `approve`: if the total is at or below the organization limit, one approval moves the invoice
  straight to `approved`. Above the limit, the first approval moves it to `reviewed` and a second,
  different approver moves it to `approved`.
- `reject`: an approver can reject a `submitted` or `reviewed` invoice.
- `mark-paid`: finance admins only, and only for `approved` invoices.

Roles: `submitter`, `approver`, `finance_admin`. Everyone sees only the data of their own
organization. The creator of an invoice can never approve or reject it. Paid invoices cannot be
edited.

GST rules checked on every invoice:

- the vendor GSTIN must match the 15 character format;
- if the vendor state code (first two digits of the GSTIN) equals the organization state code,
  the invoice uses CGST and SGST and IGST must be zero; otherwise it uses IGST only;
- `total` must equal `taxable_value + cgst + sgst + igst`, rounded to 2 decimals;
- the same `invoice_no` cannot be used twice for one vendor.

## Run with docker-compose

```
cp .env.example .env      # optional, set a real DJANGO_SECRET_KEY
docker compose up --build
```

This starts `db` (PostgreSQL 16), `redis`, `web` (migrations, then gunicorn on port 8000) and
`worker` (Celery worker with the beat scheduler). Then:

```
docker compose exec web python manage.py seed_demo
docker compose exec web python manage.py createsuperuser
```

API docs are at http://localhost:8000/api/docs/ and the schema at `/api/schema/`.

`seed_demo` creates an organization called "Demo Org (demo data)", 3 vendors named `DEMO ...`,
8 invoices numbered `DEMO-001` to `DEMO-008` in different statuses, and four users
(`demo_submitter`, `demo_approver1`, `demo_approver2`, `demo_finance`, password `demo-pass-123`).
Running it again does nothing.

## Run locally and run the tests

```
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
ruff check .
pytest
```

Without `DATABASE_URL` the project uses a local SQLite file, which is enough for the tests. To use
PostgreSQL set `DATABASE_URL=postgres://user:password@localhost:5432/dbname`. Redis is only needed
to run the Celery worker, not for the tests.

Last run: `105 passed`, on SQLite and on PostgreSQL 16. CI runs ruff and the tests against a
PostgreSQL service on every push.

## API examples

Get a token (the token endpoints are throttled, 10 requests per minute by default):

```
curl -s -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "demo_submitter", "password": "demo-pass-123"}'

curl -s -X POST http://localhost:8000/api/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "<refresh token>"}'
```

Create a vendor (finance admin only) and an invoice:

```
curl -s -X POST http://localhost:8000/api/vendors/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "Acme Supplies", "gstin": "29AABCU9603R1ZX"}'

curl -s -X POST http://localhost:8000/api/invoices/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"vendor": 1, "invoice_no": "INV-2001", "invoice_date": "2026-11-10",
       "taxable_value": "10000.00", "cgst": "900.00", "sgst": "900.00", "total": "11800.00"}'
```

List with filters, search and pagination:

```
curl -s "http://localhost:8000/api/invoices/?status=submitted&vendor=1&date_from=2026-10-01&date_to=2026-10-31&search=INV&page=1" \
  -H "Authorization: Bearer $TOKEN"
```

Move an invoice through the flow and read its audit trail:

```
curl -s -X POST http://localhost:8000/api/invoices/9/submit/ -H "Authorization: Bearer $TOKEN"
curl -s -X POST http://localhost:8000/api/invoices/9/approve/ \
  -H "Authorization: Bearer $APPROVER_TOKEN" -H "Content-Type: application/json" \
  -d '{"comment": "matches the purchase order"}'
curl -s -X POST http://localhost:8000/api/invoices/9/mark-paid/ -H "Authorization: Bearer $FINANCE_TOKEN"
curl -s http://localhost:8000/api/invoices/9/audit/ -H "Authorization: Bearer $TOKEN"
```

Summary of counts and totals by status and by month (approvers and finance admins):

```
curl -s http://localhost:8000/api/reports/summary/ -H "Authorization: Bearer $APPROVER_TOKEN"
```

## Reminders

A Celery beat job runs every hour (`pending-invoice-reminders`). It looks for invoices that have
been `submitted` or `reviewed` for more than 48 hours and were not reminded in the last 48 hours.
For each organization it emails the approvers and finance admins and, if the organization has a
`webhook_url`, posts the list of invoices there as JSON. Email uses the console backend unless
`EMAIL_BACKEND` and the `EMAIL_*` variables are set.

## Layout

```
config/           settings, urls, celery app
apps/accounts/    organization, user, roles, token views
apps/vendors/     vendor model, GSTIN validation, vendor API
apps/invoices/    invoice model, GST amount rules, invoice API, seed_demo
apps/approvals/   approvals, audit log, workflow service, reminder task
apps/reports/     summary endpoint
tests/            pytest and factory_boy tests
```

## Design notes

**Append-only audit log.** The audit log is the record of who moved an invoice and when, so it has
to be trustworthy. `AuditLog.save()` refuses to update an existing row, `delete()` is blocked, and
the queryset methods `update()`, `bulk_update()` and `delete()` raise as well. Invoices with log
entries cannot be deleted (the foreign key is `PROTECT`), the API only has a read endpoint for the
log, and the admin shows it read-only. This guards against mistakes in application code. Someone
with direct database access can still change rows, so in production the database role used by the
app should only have `INSERT` and `SELECT` on that table.

**Two approvers above the limit.** One person approving a large payment is a common fraud and
error risk, so invoices above the organization's `approval_limit` need two different approvers.
Each approver can record only one decision per invoice (unique constraint), and the creator of an
invoice cannot be one of the approvers. A total exactly equal to the limit needs one approval.

**Status changes live in one service.** All transitions go through `apps/approvals/services.py`,
which locks the invoice row, checks the current status and role rules, and writes the approval and
the audit entry in the same transaction.

**Querying.** Lists use `select_related`, and a test asserts that the invoice list runs in 2 queries
(count and page) no matter how many rows it returns.
