# Interview Documentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Make the repository landing page and interview guide clearly present Landlords, demonstrate its real workflows, and link to implementation evidence.

**Architecture:** Keep Markdown. Use the root README as the landing page and `docs/PORTFOLIO.md` as the short interview/demo route. Point developer setup to the existing technical guide rather than repeating it.

**Tech Stack:** Markdown, Mermaid, existing SVG/PNG assets, repository code and configuration as evidence.

**Spec:** `docs/superpowers/specs/2026-10-28-documentation-overhaul-design.md`

## Global Constraints

- Documentation-only changes; do not edit application code or alter runtime behavior.
- Preserve existing relative links or update every affected link when a page is moved or renamed.
- Keep Russian prose, English identifiers/commands/configuration keys, and the existing Markdown format.
- Do not expose secrets or personal data from local configuration or runtime files.
- Verify Markdown links, command paths, configuration names, and cited symbols against the repository before describing them as current.
- Do not invent screenshots or claims; label missing real captures as a follow-up.

## Review Focus

- A described feature is absent or behaves differently in current code — verify every README feature and flow against routes/UI/tests before writing it.
- A demo command depends on an unmentioned env or Compose mode — check it against `.env.example`, CLI help and compose files.
- A screenshot is a placeholder presented as a real product screen — inventory `docs/assets/` and label assets accurately.
- Interview claims imply production availability or measured outcomes — retain only evidence-backed facts and state limitations.
- The developer entry route is buried or duplicates setup instructions — link to the canonical getting-started guide.

---

### Task 1: Turn README into the project landing page

**Files:**
- Modify: `README.md`
- Read: `backend/app/`, `frontend/src/`, `.env.example`, `docker-compose.yml`, `docs/architecture/overview.md`, `docs/maintenance/technical-debt.md`

- [x] Build a fact sheet for the product problem, target user, core workflow, and current features from implementation; mark any claim without evidence for omission or qualification.
- [x] Rewrite README sections in reader order: product in one paragraph, core workflow/value, visual/architecture overview, engineering highlights with links, demo route, limitations, and two explicit links for interview exploration and developer onboarding.
- [x] Keep only one concise local run/demo entry point; link detailed setup, testing, configuration and deployment to their canonical guides.
- [x] Ensure README distinguishes implemented behavior, optional integrations, demo-only setup, and unverified production conditions.
- [x] Review all relative Markdown links and Mermaid diagrams in README.

### Task 2: Make the portfolio guide a repeatable interview walkthrough

**Files:**
- Modify: `docs/PORTFOLIO.md`
- Read: `docs/use-cases-contracts-payments.md`, `docs/architecture/overview.md`, `docs/api/overview.md`, `docs/maintenance/technical-debt.md`

- [x] Replace the stale publication checklist with a concise 5–10 minute walkthrough: login/demo setup, one rental workflow, money/ledger, account isolation/roles, async processing, and one technical trade-off.
- [x] For each engineering point, link to its current source document and a relevant source/test path; do not claim a test proves more than it asserts.
- [x] Add a short “limitations and next steps” section using only current, evidence-backed risks.
- [x] Keep any useful pre-publication safety notes, but link to the deployment/security guides for operational steps.
- [x] Check commands and URLs against the actual CLI, routes, and local Compose setup.

### Task 3: Reconcile screenshot assets and instructions

**Files:**
- Modify: `docs/assets/README.md`, `README.md`, `docs/PORTFOLIO.md`
- Read: `docs/assets/`

- [x] Inventory available screenshots and SVG placeholders; identify which assets represent the current UI.
- [x] Align filenames and image references across the README, guide, and asset instructions.
- [x] Use existing authentic screenshots only; if none exist, keep the gap explicit and avoid implying placeholders are screenshots.
- [x] Verify every referenced asset path exists.

### Task 4: Validate the interview path

**Files:**
- Modify: `docs/index.md`
- Review: `README.md`, `docs/PORTFOLIO.md`, `docs/assets/README.md`

**Dependency:** Complete `technical-documentation` and `operations-and-product-documentation` plans before finalizing the index links.

- [x] Walk every relative link from the three pages and fix broken targets.
- [x] Check the guide can be followed by someone with only the repository and the documented demo setup.
- [x] Confirm the README exposes a separate new-developer link to `docs/development/getting-started.md`.
- [x] Organize `docs/index.md` by interview, development and operations audiences; label product plans and review history so they are not confused with current technical guidance.
- [x] Add or update documentation maintenance rules: source-of-truth precedence, when subsystem docs change, how to label historical material, and how to distinguish unverified live claims.
