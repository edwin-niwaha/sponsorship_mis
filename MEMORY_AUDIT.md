# Memory Audit

## Executive summary

The Railway Celery worker memory issue is most likely caused by process model and result-storage overhead rather than CPU-bound work. The application had no explicit Celery worker memory controls in Django settings, used Redis as both broker and result backend, and left fire-and-forget notification tasks storing unused task results. The Procfile used `--concurrency=1`, but without `--pool=solo` Celery still runs a parent plus child process in the default prefork pool.

The implemented changes reduce idle worker memory, cap task-processing memory for prefork deployments, avoid unused Redis result writes for notification tasks, stream loan command querysets in chunks, avoid retaining ORM loan objects in reminder summaries, and add optional RSS logging around the two long-running loan notification commands.

## Root causes found

- `Procfile` worker used the default prefork pool. Even with `--concurrency=1`, this creates more than one Python/Django process.
- Celery had `CELERY_RESULT_BACKEND` configured to Redis but no result expiration in settings.
- Notification tasks returned small values but no code consumed task return values, causing unnecessary Redis result storage.
- Celery settings lacked explicit worker concurrency, prefetch, task-child, memory-child, and task time-limit defaults.
- `send_loan_notifications` accumulated `(loan, info)` tuples for the management summary, retaining ORM objects after borrower emails were processed.
- `send_sms_notifications` imported Twilio at module import time and iterated a queryset without chunked iteration or `select_related("borrower")`.
- Profile avatar resizing opened Pillow images and `BytesIO` buffers without guaranteed cleanup.

## High-risk files

- `core/settings/base.py`: Redis broker/result backend and Celery runtime defaults.
- `Procfile`: Railway worker process model.
- `apps/loans/tasks.py`: all Celery tasks are email notification tasks.
- `apps/loans/management/commands/send_loan_notifications.py`: potentially long-running borrower reminder job.
- `apps/loans/management/commands/send_sms_notifications.py`: potentially long-running SMS job with external SDK usage.
- `apps/loans/management/commands/update_loan_statuses.py`: batch loan status maintenance.
- `apps/users/models.py`: Pillow image processing during avatar upload.
- `apps/loans/views.py` and `apps/loans/services/reporting.py`: report views still build in-memory page/export datasets and should be monitored for very large portfolios.

## Exact problematic code patterns

- Celery worker command lacked `--pool=solo`, so `--concurrency=1` still used prefork.
- `CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND") or REDIS_URL` was present without `CELERY_RESULT_EXPIRES`.
- `@shared_task` notification tasks did not specify `ignore_result=True`.
- `for loan in disbursed_loans:` in `send_sms_notifications` evaluated with normal queryset caching.
- `summary[info["category"]].append((loan, info))` retained ORM objects for the reminder summary.
- `img = Image.open(self.avatar)` and `output = BytesIO()` were not protected by context/finally cleanup.

## Changes made

- Added Celery memory/runtime defaults in `core/settings/base.py`:
  - `CELERY_WORKER_CONCURRENCY = 1`
  - `CELERY_WORKER_PREFETCH_MULTIPLIER = 1`
  - `CELERY_WORKER_MAX_TASKS_PER_CHILD = 50`
  - `CELERY_WORKER_MAX_MEMORY_PER_CHILD = 300000`
  - `CELERY_TASK_SOFT_TIME_LIMIT = 300`
  - `CELERY_TASK_TIME_LIMIT = 360`
  - `CELERY_RESULT_EXPIRES = 3600`
- Updated `Procfile` worker to use the lower-memory solo pool.
- Marked all current Celery notification tasks with `ignore_result=True`.
- Added `core/memory.py` with optional `psutil`-based RSS logging.
- Added memory logs to `send_loan_notifications` and `send_sms_notifications` start/finish points.
- Changed `send_loan_notifications` to `iterator(chunk_size=200)` and summary dict payloads instead of retained ORM tuples.
- Changed `send_sms_notifications` to lazy-import Twilio, `select_related("borrower")`, and `iterator(chunk_size=200)`.
- Changed `update_loan_statuses` batch persistence from per-row saves to `bulk_update()`.
- Wrapped avatar image processing in a Pillow context manager and closed the `BytesIO` buffer in `finally`.
- Added targeted tests for Celery memory defaults, ignored task results, and reminder summary payload shape.

## Tasks using excessive memory

Current Celery tasks in `apps/loans/tasks.py` are small email notification tasks. They were not individually heavy, but collectively wrote unused results to Redis. Results are now ignored per task.

Management commands with higher memory risk:

- `send_loan_notifications`: loops through active loans, computes schedules, sends email, and sends a summary. Now chunked and avoids retaining loan ORM objects in the summary.
- `send_sms_notifications`: loops through disbursed loans, computes schedules, and calls Twilio. Now chunked, borrower-selecting, and lazy-loads Twilio.
- `update_loan_statuses`: already chunked; now uses `bulk_update()` for changed statuses.

## Periodic task schedule review

No `CELERY_BEAT_SCHEDULE`, `beat_schedule`, `crontab`, or Django Celery Beat schedule was found in the codebase. `Procfile` defines a separate `beat` process, but no in-repo periodic tasks are registered for it.

No tasks running every minute or more frequently were found. No duplicate in-code Celery schedules were found. No Celery tasks enqueue themselves with `.delay()`, `.apply_async()`, `countdown`, or `eta`.

## Tasks recommended for Railway Cron

These jobs are fixed-interval management commands and are better suited to Railway Cron than Celery Beat in this application:

- `python manage.py update_loan_statuses`: run daily, for example early morning Africa/Kampala time.
- `python manage.py send_loan_notifications`: run Monday and Thursday, matching the command default weekdays, or run daily with the command's weekday gate.
- `python manage.py send_sms_notifications`: run daily if SMS reminders are required.
- `python manage.py send_birthday_emails`: run daily if staff birthday emails are required.

Do not remove the `beat` service until deployment scheduling is confirmed. If Railway Cron takes over all fixed schedules, the `beat` service can be disabled in Railway rather than embedded in the worker.

## Redis configuration findings

Redis is used as Celery broker through `CELERY_BROKER_URL` or `REDIS_URL` and as Celery result backend through `CELERY_RESULT_BACKEND` or `REDIS_URL`. No Django cache backend using Redis was configured in settings, so Django cache defaults to local memory unless overridden externally. No session backend using Redis was configured.

Celery result accumulation is reduced by `CELERY_RESULT_EXPIRES = 3600` and per-task `ignore_result=True` for all current notification tasks. The result backend remains configured for compatibility in case future tasks need results.

## Remaining risks

- Report views still construct in-memory lists for portfolio, due/overdue, PAR, repayment, and CSV views. This is acceptable for current web pagination behavior but should be revisited if loan counts grow substantially.
- Some report contexts are cacheable for an hour; if a Redis cache backend is introduced externally, avoid caching large ORM-containing page contexts.
- `psutil` is not installed, so memory logging is currently a no-op unless the package is added. This avoids adding a dependency without need.
- Full test suite currently has unrelated failures in loan document and sponsor feedback tests; see Testing performed.

## Expected memory impact

- The largest idle-worker reduction should come from the Procfile change to `--pool=solo`, which avoids the extra prefork child process for this single-concurrency worker.
- Redis memory pressure should drop because notification task results are no longer stored and remaining results expire after one hour.
- Long-running notification commands should hold fewer ORM objects and avoid full queryset result caching.
- The prefork safety limits remain available if the worker command is changed away from solo in the future.

## Recommended Railway worker start command

```bash
celery -A core worker --loglevel=INFO --pool=solo --concurrency=1 --prefetch-multiplier=1 --without-gossip --without-mingle
```

Do not run `worker -B`. Keep Beat separate only if in-code schedules are later added, or prefer Railway Cron for fixed interval management commands.

## Recommended Railway memory and CPU limits

```text
Worker replicas: 1
Worker memory limit: 512 MB
Worker CPU limit: 0.5 vCPU
```

If real RSS remains above 512 MB after deploying the solo worker, inspect imported packages and report commands with `log_process_memory` enabled via `psutil` before increasing limits.

## Testing performed

Passed:

- `.\.smsvenv\Scripts\python.exe manage.py check`
- `.\.smsvenv\Scripts\python.exe manage.py test apps.loans.tests.LoanWorkflowTests.test_celery_memory_defaults_and_fire_and_forget_task_results apps.loans.tests.LoanWorkflowTests.test_loan_reminder_summary_item_does_not_retain_model_instance apps.loans.tests.LoanWorkflowTests.test_loan_notification_command_sends_one_day_arrears_despite_cooldown --keepdb`
- `.\.smsvenv\Scripts\ruff.exe check --no-fix core\memory.py core\settings\base.py apps\loans\tasks.py apps\loans\management\commands\send_loan_notifications.py apps\loans\management\commands\send_sms_notifications.py apps\loans\management\commands\update_loan_statuses.py apps\users\models.py`

Full suite:

- `.\.smsvenv\Scripts\python.exe manage.py test --keepdb` ran 89 tests and failed with 2 failures and 1 error in areas not modified by this audit:
  - `apps.loans.tests.ClientSelfServiceLoanApplicationTests.test_staff_approval_workflow_accepts_self_service_loan`: missing required Bank Statement document.
  - `apps.loans.tests.LoanWorkflowTests.test_loan_detail_shows_missing_required_documents_warning`: expected text `Required documents missing` not found.
  - `apps.sponsor.tests.test_sponsor_feedback.SponsorFeedbackTests.test_sponsor_can_submit_feedback_from_portal`: expected 1 email, observed 2.