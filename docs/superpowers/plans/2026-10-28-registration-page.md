# Registration Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let visitors create an account through a first-party registration page.

**Architecture:** Add a guest-only `/register` route and page using existing `authApi.register`, `useAuthStore`, React Hook Form, Zod, and shared UI components. On success establish the session and redirect to `/dashboard`; link the login page to registration.

**Tech Stack:** React 19, TypeScript, React Router, React Hook Form, Zod, TanStack Query, Tailwind CSS.

**Spec:** `docs/superpowers/specs/2026-10-28-registration-page-design.md`

## Global Constraints

- Do not change backend registration behavior or production registration settings.
- Password minimum is 6 characters and confirmation must match.
- Keep the registration and login routes guest-only.
- Use the existing auth cookie/session flow; do not expose a bearer token.

## Review Focus

- Empty or malformed email is rejected by form validation.
- Passwords shorter than six characters are rejected.
- Mismatched password confirmation is rejected.
- Duplicate email and API errors remain visible to the user.
- Successful registration loads account state before routing to `/dashboard`.

---

### Task 1: Add registration form and schema

**Files:**
- Modify: `frontend/src/features/auth/schema.ts`
- Create: `frontend/src/pages/register/RegisterPage.tsx`

- [ ] Define a registration schema for full name, email, password, and confirmation; require six password characters and matching confirmation.
- [ ] Build the page using the existing guest auth card, shared inputs, and submit button.
- [ ] Call `authApi.register`; display API errors, establish auth state, fetch the account, then navigate to `/dashboard`.
- [ ] Include a link back to `/login`.

### Task 2: Route and expose registration from login

**Files:**
- Modify: `frontend/src/app/router.tsx`
- Modify: `frontend/src/pages/login/LoginPage.tsx`

- [ ] Add lazy `/register` route wrapped in `GuestOnly`.
- [ ] Add a visible “Создать аккаунт” link to the login page.
- [ ] Run `npm run build` and confirm it exits successfully.
