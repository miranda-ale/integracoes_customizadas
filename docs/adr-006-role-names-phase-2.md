# ADR-006: Phase 2: name of the Role created by the app

Status: proposed (merge needs L5, staging).

## Context

ADR-005 renamed Reports, Print Formats, Cards and Workspaces. The only Role the app creates, `Usuário Jurídico`, stayed
in Portuguese. A Role is a persisted name: it is assigned to users (Has Role) and listed in the permissions of the Legal
DocTypes and Reports and in the Legal Workspace. No other app of the bench cites it.

## Decision

| Old | New |
|---|---|
| Usuário Jurídico | Integ Legal User |

- Patch `s04_rename_roles` (`[pre_model_sync]`): `frappe.rename_doc` rewrites the links and the `role_name` field. When
  the old and the new Role both exist the old one is merged into the new, so no user loses access.
- The exact-name check does not use SQL: `frappe.db.exists` ignores accents and case.
- Code, DocType and Report JSON permissions, the fixture, the export filter in `hooks.py`, tests and documentation use
  the new name.

## Consequences

- Not rewritten (outside the repository): Server Scripts, Custom Scripts, saved Reports and hand-written Notifications that
  cite the Role as free text. Search the real site before L5.
- Whoever has the old Role keeps it under the new name; no permission is added or removed.
- Rollback: restore the backup taken before `bench migrate`. There is no reverse patch.

## Evidence

Tests (`tests/test_role_names.py`), L3/L4 on the production baseline (users keep the role, second migrate identical,
restore identical to before). L5 (real staging) is pending.
