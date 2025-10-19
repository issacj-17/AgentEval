# Submission Freeze Plan

**Objective:** Ensure no prohibited modifications are made after the Oct 20 2025 17:00 PT deadline
(Oct 21 08:00 SGT).

## Timeline

- **Oct 18 2025 09:00 SGT** – Feature freeze. Only bug fixes allowed.
- **Oct 19 2025 18:00 SGT** – Code freeze. Tag release candidate, lock dependency versions, and
  archive SBOM.
- **Oct 20 2025 13:00 SGT (Oct 19 22:00 PT)** – Content freeze. Final README/Devpost text, demo
  links, and artifacts approved.
- **Oct 21 2025 08:00 SGT (deadline)** – Submit on Devpost. After submission, only changes requested
  by Sponsor/Admin (e.g., IP/PII removal) may be made.

## Responsibilities

| Role                | Owner | Duties                                             |
| ------------------- | ----- | -------------------------------------------------- |
| Release Manager     |       | Coordinate freezes, own final submission checklist |
| QA Lead             |       | Run regression + smoke tests, capture evidence     |
| Documentation Lead  |       | Finalise README, Devpost answers, attribution docs |
| Infrastructure Lead |       | Keep deployment live through Nov 13 2025 08:00 SGT |

## Checklist

- [ ] All open PRs merged or closed before code freeze.
- [ ] `CHANGE_LOG.md` updated with final entries.
- [ ] Demo video and captions uploaded (link verified).
- [ ] Submission package zipped and backed up.
- [ ] Post-submission monitoring schedule assigned (uptime, credential validity).
- [ ] Contingency plan documented for rollback or hotfix (if allowed).

Store signed approval of this plan in `req-docs/signatures/SUBMISSION_FREEZE_SIGNOFF.pdf`.
