# Redis ACL Hardening Design

**Status:** Proposed implementation design, approved in conversation on 2026-10-22.

## Goal

Require authenticated, least-privilege access to Redis from every Landlords service while keeping Redis unreachable from the VM's public interfaces.

## Current evidence

- The live Redis container accepted unauthenticated `PING` (`PONG`).
- The live API reports `APP_ENV=development` and no configured Redis password; its Redis ping succeeds without authentication.
- Compose currently conditionally enables `requirepass`, uses the Redis default user, and does not publish Redis port 6379 to the VM host.

## Design

- Use Redis 7 ACLs rather than only setting `requirepass`: provide named service users, turn the `default` user off, and scope commands and key patterns to observed application needs. Redis documents ACLs as the mechanism for named users and command/key restrictions: <https://redis.io/docs/latest/operate/oss_and_stack/management/security/acl/>.
- Give API, worker/beat, and development Flower distinct credentials where their command sets allow it. Keep the initial role set small; do not claim least privilege until Celery, redis-py locks, readiness, and ops checks pass with the actual rules.
- Prefix Celery broker/result keys and application lock/ops keys. ACL key patterns must match these prefixes. Use command allow-lists or safe command categories that deny administrative/dangerous operations such as `CONFIG`, `ACL`, and `FLUSH*`.
- Mount ACL and password files as read-only Compose secrets sourced from host-only files. Keep them out of Git, file synchronization, image layers, command arguments, and logs. Application settings read password files and construct authenticated Redis connections without printing DSNs.
- Preserve the private Compose network and absence of a host-published Redis port. Add Redis TLS only if clients move outside the trusted same-host Docker network; AUTH is not encryption for untrusted network transport.
- Production startup rejects missing ACL identity/secret configuration. Development/test environments may use isolated, explicitly unauthenticated Redis instances.

## Migration and operations

1. Create the host-only secret and ACL files without transferring or printing them.
2. Validate ACL syntax and client command/key requirements against Redis 7 in an isolated test environment.
3. Update Compose and application settings; check effective Compose configuration without revealing rendered secret values.
4. With an approved maintenance window, recreate Redis and dependent API/worker/beat services so every process uses the same ACL identities.
5. Verify unauthenticated and invalid credentials fail; each named identity can perform only its required operations; API readiness, task publish/consume, locks, beat, Flower (when enabled), and results work.
6. Rotate credentials by adding a replacement ACL credential, deploying clients, verifying traffic, then removing the old credential.

## Acceptance criteria

- Unauthenticated and invalid-auth Redis commands are rejected from the application network.
- Default user is disabled; configured service users do not have unrestricted administrative access.
- API, Celery worker, beat, and optional Flower pass live connection/operation checks with their assigned identities.
- Redis port remains unpublished on the VM host.
- Production refuses to start without the configured ACL secret files.
- No secret appears in Git, synchronized files, logs, command output, or image layers.

## Constraints

- The current VM has no internet access. Use the existing Redis 7 image and offline build/sync workflow; do not depend on downloading a new image at deployment time.
- The currently running development Redis is unauthenticated. Do not modify it until the exact service change and restart are approved.
- Redis AUTH does not encrypt traffic; use TLS if the trust boundary changes.
