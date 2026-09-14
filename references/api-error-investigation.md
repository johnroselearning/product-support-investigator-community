# API Error Investigation Playbook

Use for HTTP failures, unexpected API responses, timeouts, malformed responses, and API regressions.

## 0. Identify the failure surface

Determine where the HTTP error is observed before assuming backend access: web, mobile, API client, CLI, backend/service, or integration. Use relevant connected read-only sources first. Otherwise guide a small collection check appropriate to the user's surface and access; do not assume every user has browser or device diagnostics.

## 1. Capture request identity

Extract:
- method and endpoint;
- environment/base URL;
- timestamp and timezone;
- request/correlation ID;
- account/customer;
- resource/object ID;
- status code;
- response body/error code;
- relevant request headers and payload fields, excluding secrets.

Never request credentials, bearer tokens, API secrets, or private keys.

## 2. Interpret by status family

### 400 / 422
Check schema, validation, required fields, data types, enum values, content type, version changes, and payload differences.

### 401
Check token presence/expiry, issuer/audience, clock skew, token refresh, API-key validity, and environment mismatch.

### 403
Check scopes/roles, account permissions, feature entitlement, object ownership, IP/network policy, and tenant boundary.

### 404
Check resource ID, endpoint/version, environment, deletion state, tenant/account, eventual consistency, and routing.

### 409
Check duplicate/idempotent requests, state transition conflicts, concurrency, stale version, and resource locks.

### 429
Check per-key/account/IP limits, burst vs sustained rate, Retry-After, client retry behavior, and recent policy changes.

### 500
A verified 500 indicates a server-side request failure, but does not identify its origin or root cause. A reported 500 still needs confirmation through available evidence.

First identify the failing request. With connected logs/traces, search its request/correlation ID, or correlate timestamp, endpoint, environment, and error fingerprint. Locate the earliest evidence-supported failing stage.

Without direct telemetry, choose an accessible check:
- **Web:** open Browser DevTools -> Network, reproduce once if safe, and select the request returning 500. Capture method, endpoint, response/error code, timestamp with timezone, and request/correlation ID if present.
- **Mobile:** capture the failing action, app version, visible error, and timestamp. Distinguish an app crash from an HTTP response. If developer diagnostics are available, inspect the matching network response or scoped app/device logs.
- **API client:** inspect the failed request's method, endpoint, status, response body, timestamp, and request ID.
- **CLI:** capture the exact command and relevant error output; inspect verbose/debug HTTP output only if supported and safe.
- **Backend/service:** inspect matching request logs or traces when the user has access.

Do not repeat payments, writes, or other side-effecting actions just to reproduce an error without appropriate authorization. Never share tokens, cookies, signed URLs, or personal data.

Explain the next branch: a request ID enables log correlation; otherwise use timestamp plus endpoint and environment. One failing endpoint narrows the search to its path; multiple unrelated failures justify checking shared boundaries without proving a shared cause. If no request returns 500, verify where the displayed error originated.

Then investigate exceptions, regressions, edge cases, database/dependency failures, bad state, and configuration changes as evidence supports them. Avoid listing these as equally likely generic causes before they help distinguish checks.

### 502 / 503 / 504
Check upstream health, gateway/proxy, dependency latency, service saturation, connection pools, DNS/network, scaling, and maintenance/deploy events.

## 3. Compare failed vs successful requests

Compare:
- endpoint and method;
- account/tenant;
- payload shape;
- headers (without exposing secrets);
- resource state;
- app/API version;
- region;
- dependency path;
- timing;
- feature flags.

A single difference may be a discriminator, not proof.

## 4. Telemetry checks when available

Use any available telemetry source (Datadog is optional):
- search exact request/correlation ID;
- inspect trace span where failure originates;
- identify first failing service/span;
- inspect error fingerprint and stack trace;
- compare dependency/DB spans;
- check latency/saturation around the event;
- check same endpoint across customers;
- check deployment/config/flag changes.

## 5. Regression test

For suspected regression:
- establish last known good;
- establish first known bad;
- compare versions;
- map code/config changes touching the failing path;
- check whether rollback/disable/old-version traffic behaves differently.

## 6. Output ownership

Classify likely ownership:
- customer/client-side;
- product/application;
- platform/infrastructure;
- third-party dependency;
- shared/multi-factor;
- unknown.

Do not assign blame without evidence.

## 7. Minimum useful next evidence and how to obtain it

If the case is under-specified, obtain the smallest evidence that materially narrows the investigation. Useful fields include:
1. request/correlation ID;
2. timestamp + timezone;
3. endpoint/action;
4. environment;
5. exact response/error;
6. affected resource/account.

Retrieve these from connected read-only sources when possible. Otherwise give a concrete check: where to look, what action to perform, what result to capture, what sensitive fields to redact, and how the result determines the next branch. Ask only essential remaining questions, then continue from the result before requesting broader information.
