# Landlords Documentation Overhaul Design

## Intent

Make the repository documentation credible and useful for an interview, while
keeping a clear, separate route for a new developer and a reliable reference for
the implemented system. The current documentation already covers most areas;
the work is to reconcile facts, remove conflicting sources, and give each page a
clear audience and purpose.

## Goals

- Present the product, its user value, architecture, and strongest engineering
  decisions clearly from the repository landing page.
- Give interviewers a short path from README to a repeatable product demo and
  supporting implementation evidence.
- Give new developers a separate path to setup, configuration, tests, API, and
  architecture references.
- Make technical and operational documents describe the current code and
  configuration, with assumptions and unverified production facts labeled.
- Preserve useful historical decisions without letting old plans and checklists
  appear to be current implementation guidance.
- Establish a lightweight structure and update rules that prevent the same fact
  from drifting across multiple documents.

## Non-goals

- Changing application behavior, APIs, infrastructure, CI behavior, or product
  scope.
- Adding a documentation website generator or third-party dependency.
- Claiming production availability, performance, compliance, or recovery
  guarantees that the repository cannot prove.
- Inventing screenshots, benchmark results, incidents, customer outcomes, or
  business claims.
- Deleting useful design and implementation history.

## Approaches considered

1. **Full documentation audit and editorial pass (selected).** Reconcile the
   complete active documentation set with code/configuration/CI, restructure
   entry points by audience, and archive or label historical planning material.
   This addresses the current cross-document contradictions and the interview
   goal, at the cost of reviewing and touching more pages.
2. **Interview landing-page polish only.** Improve README and portfolio guide,
   leaving the existing technical references and their inconsistencies in
   place. Faster, but it would preserve contradictory claims for anyone who
   follows the links.
3. **Generated documentation site.** Add a docs toolchain and maintain a
   separate site. It provides stronger navigation, but adds dependencies and
   maintenance without improving the underlying content accuracy.

The selected approach keeps Markdown and treats accuracy and information
architecture as the main work.

## Audiences and document structure

The repository landing page has two explicit paths:

- **Interview / explore the project:** product problem and core workflow, actual
  architecture, selected engineering decisions with trade-offs, demo steps,
  known limits, and links to evidence in code and tests.
- **Develop / operate:** existing setup, configuration, testing, API, data,
  background jobs, deployment, monitoring, troubleshooting, and security
  references.

`README.md` remains the landing page. `docs/PORTFOLIO.md` becomes the concise
interview/demo guide. `docs/index.md` remains the technical documentation hub
and clearly routes readers to developer and operator references.

## Content policy

- Treat source code, migrations, `.env.example`, Compose/Docker files, CI, and
  executed commands as evidence, in that order where relevant.
- Keep one authoritative location for each operational fact; link to it instead
  of copying detailed configuration and commands elsewhere.
- Use `docs/maintenance/technical-debt.md` as the only current technical-risk
  register. Retain backend/frontend review checklists and old roadmaps as
  explicitly historical material, without presenting their closed items as
  open work.
- Rewrite product-flow documents as concise descriptions of current behavior;
  retain old decision rationale in dated design records.
- Keep implementation plans/specifications under `docs/superpowers/` as records
  of proposed or completed work; mark status where it is not already clear.
- Mark claims that depend on live VPS, external providers, schedules, or
  restore drills as unverified unless direct evidence is available.
- Do not fabricate UI screenshots. Use existing image assets only when they
  reflect the current application; record any missing real captures as a clear
  follow-up rather than presenting placeholders as product screenshots.

## Scope

Review and update the root and contributor entry points (`README.md`,
`CONTRIBUTING.md`, `AGENTS.md`, `docs/index.md`), developer/API/architecture
references, deployment/security/operations instructions, current product-flow
documents, interview assets, and technical-debt/audit pages. Review
`backend/README`-equivalent material (`backend/ARCHITECTURE.md`, `backend/TODO.md`)
and frontend README/TODO as well. Inspect retained plans/specs for status and
links, but do not rewrite their historical implementation detail unless a
current document incorrectly cites it as authoritative.

## Known issues to resolve during the audit

- `docs/api/overview.md` describes a unified success envelope and later repeats
  that auth endpoints still use legacy top-level fields.
- `docs/architecture/background-jobs.md` describes the transactional outbox as
  implemented and later says the outbox is absent.
- `docs/security/overview.md` says `/openapi.json` remains exposed in production,
  while the API reference and current risk register say OpenAPI is disabled.
- The current technical-debt register still lists API response inconsistency,
  although the latest code commit standardized success responses.
- The documentation audit and index carry an October 12 review date, and the
  audit records response-format conclusions that changed afterward.
- The portfolio checklist, README, and asset guide disagree about the screenshots
  and demo flow; the portfolio, roadmap, and older TODO files present completed
  work as active checklists.
- Deployment and backup/recovery claims need to be distinguished between
  repository procedures, configured VPS state, and a verified restore drill.

## Constraints

- Documentation-only changes; do not edit application code or alter runtime
  behavior.
- Preserve existing relative links or update every affected link when a page is
  moved or renamed.
- Keep Russian prose, English identifiers/commands/configuration keys, and the
  existing Markdown format.
- Do not expose secrets or personal data from local configuration or runtime
  files.
- Verify Markdown links, command paths, configuration names, and cited symbols
  against the repository before describing them as current.

## Acceptance criteria

- A reader can identify the interview/demo route and the new-developer route
  from the root README without searching the repository.
- README and interview guide make accurate claims and distinguish working
  features, demo-only setup, and known limitations.
- Active documents have a clear audience, current status, and authoritative
  source; historical documents are labeled and not mistaken for runbooks or
  open backlogs.
- The documented API envelope, task/outbox behavior, security posture, backup
  procedures, and current tech debt match implementation and evidence.
- No stale relative Markdown links remain in the reviewed documentation set.
- The audit records what was checked, what could not be verified, and the date
  of the review.
