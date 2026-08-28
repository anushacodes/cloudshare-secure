---
title: "1.4 Frontend Upload & Recipient Access User Interface"
type: "feature"
created: "2026-08-28"
baseline_commit: "e89c8c5"
status: "done"
review_loop_iteration: 0
context:
  - "{project-root}/AGENTS.md"
  - "{project-root}/_bmad-output/specs/spec-cloudshare-secure/stack.md"
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Users and recipients need a modern web UI to upload files with dynamic recipient fields, monitor upload progress, and access shared downloads securely via token links.

**Approach:** Build a React + TypeScript single-page application using Vite, providing an API client (`api/client.ts`), a responsive upload form component (`UploadForm.tsx`) with dynamic recipient inputs, and a recipient access landing component (`RecipientAccess.tsx`) with download triggers and error states.

## Boundaries & Constraints

**Always:**
- Frontend must never talk to AWS directly or hold AWS credentials; all requests route to FastAPI backend.
- Validate email syntax on the client before submission.
- Provide clear error feedback if upload fails or if an access link is invalid/expired.
- Support dynamic recipient list manipulation (add and remove email rows).

**Ask First:**
- Adding third-party UI component libraries (e.g. Chakra, MUI) beyond lightweight styling / Lucide icons.

**Never:**
- Hardcode backend URLs directly into components without an environment variable fallback (`VITE_API_URL` or default `/api` / `http://localhost:8000`).
- Allow file submissions with empty recipient lists.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Happy Path Upload | File selected + 2 valid emails | Upload progress displayed, success card with copyable recipient links shown | N/A |
| Invalid Email Format | User enters "not-an-email" | Client-side validation blocks submit, highlights invalid field | Inline validation error |
| Recipient Opens Link | Browser loads `?file_id=...&token=...` | Verifies link with backend, shows filename, size, and Download button | Show download button |
| Expired / Invalid Link | Browser loads corrupted token | Displays "File not found or link has expired" message | Clean error card |

</frozen-after-approval>

## Code Map

- `frontend/package.json` -- React, TypeScript, Vite, and Lucide icons configuration
- `frontend/vite.config.ts` & `frontend/index.html` -- Vite build setup and HTML template
- `frontend/src/api/client.ts` -- Typed API client for `/files/upload` and `/files/{id}/access`
- `frontend/src/components/UploadForm.tsx` -- Dynamic recipient input and file upload UI
- `frontend/src/components/RecipientAccess.tsx` -- Recipient download landing page
- `frontend/src/components/Header.tsx` -- Application header & branding
- `frontend/src/App.tsx` -- Main app router / view switcher

## Tasks & Acceptance

**Execution:**
- [x] `frontend/package.json` & config files -- Setup Vite, TypeScript, and HTML entry point
- [x] `frontend/src/api/client.ts` -- Implement backend API client with error handling
- [x] `frontend/src/components/UploadForm.tsx` -- Implement file upload UI with dynamic recipient rows
- [x] `frontend/src/components/RecipientAccess.tsx` -- Implement recipient download landing view
- [x] `frontend/src/App.tsx` -- Integrate header, view routing, and responsive layout

**Acceptance Criteria:**
- Given a user on the React app, when selecting a file and entering recipient emails, then `POST /files/upload` is sent and a success confirmation with copyable access links is displayed.
- Given a recipient visiting with `file_id` and `token` query parameters, when the component loads, then it verifies the link with `GET /files/{file_id}/access?token=...` and offers direct file download.
- Given client-side form interactions, then adding/removing recipient rows and email validation operate seamlessly without crashes.

## Verification

**Commands:**
- Inspect generated TypeScript and React components for syntax and type correctness.

## Suggested Review Order

**Frontend Entry & View Switcher**

- Main router switching between Upload Form and Recipient Download based on URL params
  [`App.tsx:6`](../../frontend/src/App.tsx#L6)

**Components**

- File upload form with dynamic recipient row add/remove and copyable access links
  [`UploadForm.tsx:4`](../../frontend/src/components/UploadForm.tsx#L4)

- Recipient download page verifying tokens and handling download states
  [`RecipientAccess.tsx:9`](../../frontend/src/components/RecipientAccess.tsx#L9)

- Application branding header
  [`Header.tsx:3`](../../frontend/src/components/Header.tsx#L3)

**API Integration & Setup**

- Typed API client communicating with backend
  [`client.ts:19`](../../frontend/src/api/client.ts#L19)

- Vite and package setup
  [`package.json:1`](../../frontend/package.json#L1)
