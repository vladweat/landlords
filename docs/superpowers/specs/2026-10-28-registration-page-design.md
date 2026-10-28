# Registration Page Design

## Intent

Let visitors create an account from the Landlords web interface; public registration is already enabled on the backend, but the frontend has no registration page.

## Chosen approach

Add a dedicated guest-only `/register` page matching the existing `/login` and `/invite` cards. Collect full name, email, password, and password confirmation; require a six-character password and matching confirmation. Submit through the existing `authApi.register`, then set the returned user in the auth store, fetch the account, and navigate to `/dashboard`. Add a clear registration link to `/login` and a login link to `/register`.

## Constraints

- Use the existing API endpoint and cookie/session flow; do not change backend behavior.
- Reuse the current Tailwind, React Hook Form, Zod, React Query, and shared UI components.
- Keep the registration form guest-only and surface API failures such as an already-registered email.
- Do not automatically alter production security settings as part of this UI feature.
