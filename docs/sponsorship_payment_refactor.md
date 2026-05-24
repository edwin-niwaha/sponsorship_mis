# Sponsorship Payment Refactor Rollout

## Phase 1: Additive Schema

- Deploy the `SupportProgram` and unified `Payment` tables with the legacy tables still in place.
- Keep existing `ChildPayments`, `StaffPayments`, and `DonorPayment` write paths active.
- Seed default support programs through migration `finance.0005` or by running `create_support_programs`.

## Phase 2: Backfill

- Run `python manage.py migrate_legacy_payments --dry-run` first and review counts.
- Run `python manage.py migrate_legacy_payments` during a low-traffic window.
- The command is idempotent because each copied row stores `source_model` and `source_id`.

## Phase 3: Reporting Cutover

- Use `Sponsor.objects.real_sponsors_only()` or `Sponsor.objects.exclude_one_time_only_donors()` for sponsor reports.
- Use `Payment.objects.real_support_payments()` for unified payment reports.
- One-time-only donors are excluded from sponsor reports, but sponsors with both real support and one-time donations remain included.

## Phase 4: Dual Write

- After the backfill is verified, update legacy payment creation views to also create a unified `Payment`.
- Keep the source fields populated so duplicate writes remain detectable.
- Monitor counts between legacy payment tables and unified payments before removing any read path.

## Phase 5: Legacy Retirement

- Only after multiple verified releases, switch reports fully to unified payments.
- Archive legacy models or mark admin views read-only before considering table removal.
- Deleting legacy tables should be a separate, explicit migration after backups and stakeholder sign-off.

## Rollback

- The schema is additive, so rolling back application code can continue using legacy tables.
- If a backfill produces bad unified rows, delete only rows with the affected `source_model` values from `payments`; do not touch legacy tables.
- Keep a database backup before running the non-dry-run migration command in production.

## Optimization Notes

- Keep indexes on `Payment(sponsor, program)`, `payment_date`, and `(source_model, source_id)`.
- Use `select_related("sponsor", "program", "child", "staff")` for payment lists.
- Use sponsor queryset helpers instead of repeating multi-join `Q` filters in views.
- For larger datasets, backfill in batches and run reports from read replicas where available.
