# ADR-002: Quality and readability of external integration logs

## Context

The integration with the DataJud Public API (CNJ, the Brazilian National Council of Justice) started failing with
HTTP 403 on every court -- an external cause, even with the official CNJ public key. The existing Error Log only
recorded `"Processo X, tribunal Y: DataJudError. Dados anteriores preservados."` ("Lawsuit X, court Y: DataJudError.
Previous data preserved."): no endpoint, method, HTTP status, response body or traceback. Diagnosing the root cause
required reading the source code, not the log. At the same time, each failing lawsuit became its own record on every
run -- with 56 lawsuits failing, that was 56 entries per round, flooding the Error Log and hiding the signal (what the
real error is) in the noise (how many times it repeated).

See [docs/datajud-log-quality.md](datajud-log-quality.md) for the complete fix applied to DataJud.

## Decision

Every integration with an external service (third-party API, webhook, queue) in this app must log enough to diagnose
the cause without rereading the source code, and without flooding the Error Log:

1. **Structured context, not just the exception message**: endpoint/URL, HTTP method, HTTP status, response time, the
   first ~1,000 characters of the response body, the exception type and the traceback -- everything DataJud now
   writes to `DataJud Sync Log` is the expected floor, not a special case of that integration.
2. **Never write a secret in clear text**: API key, token, password or the full `Authorization` header never go to the
   log; when it is useful to confirm *which* key was used (e.g. during rotation), only a masked prefix is written
   (see `_mascarar_chave` in `juridico/datajud.py`).
3. **Classify the error**, do not just repeat the raw exception: at least authentication/authorization, rate limit,
   not found, unavailability and invalid data are distinct enough categories to decide the action (change the key vs.
   wait vs. nothing to do).
4. **Group repeated failures of the same run by error type**, with a count and the list of affected records, instead
   of one record per processed item. A systemic failure (the whole API down) must generate a few clear log records,
   not one entry per lawsuit/record/row on every run.
5. **Summarize the current state in a visible place** (last success, last error, status of the last error,
   consecutive failures) in the integration's own settings record, so that confirming "is it working?" does not
   require opening the Error Log.

This guideline is the reason behind the DataJud design (`DataJud Sync Log` + summary in `DataJud Settings`) and
applies to any future or existing external integration in this app (WhatsApp/Evolution, Bionexo, `busca_cnpj`,
etc.): when touching an external integration for another reason, take the opportunity to align its log with this
standard.

## Consequences

- PR review: a new or changed external integration that only writes `frappe.log_error(str(exc))` without HTTP
  status/body/classification is not complete.
- This does not replace `frappe.log_error` with a dedicated DocType everywhere -- simple, low-failure-volume
  APIs/webhooks may keep using the Error Log, as long as it carries the structured context of item 1. A dedicated
  DocType (like `DataJud Sync Log`) is justified when the failure volume per run calls for grouping (item 4) or when
  the summary of item 5 needs queryable fields.
