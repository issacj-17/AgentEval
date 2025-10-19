# Submission Prep Action Items (as of 2025-10-19 22:36:01 SGT)

## Immediate (0-12h)
- Populate and sign `req-docs/TEAM_INFO.md`; export to `req-docs/signatures/TEAM_INFO.pdf`.
- Add MIT `LICENSE` file; complete `req-docs/ASSET_LICENSES.md` with actual media entries.
- Finalize `req-docs/JUDGE_ACCESS.md` with production URL, uptime window, and judge credentials.
- Rerun live demo (`scripts/run-live-demo.sh`) to produce non-zero success metrics and refresh `demo/evidence/`.
- Capture Devpost registration proof and summarize AWS credit usage in `req-docs/templates/aws_usage_form.md`.

## Next 12-24h
- Initialize GitHub repo, push current code, and generate `git log --since '2025-09-08T12:00:00-07:00'` evidence under `req-docs/change-evidence/`.
- Increase automated test coverage beyond 80% (current: 70%); retain log from `source .venv/bin/activate && pytest -q`.
- Produce ≤3 min demo video per `req-docs/video_plan/video_storyboard.md`; upload (unlisted) and store captions/license proofs.
- Update `README.md`, `SUBMISSION_GUIDE.md`, and Devpost draft with final build/run steps, architecture PNG, and value metrics.
- Complete `req-docs/templates/deliverables_template.md` (sections on multiple submissions, disclosures, publicity statement).

## By Submission Freeze (Oct 20 13:00 SGT)
- Sign off `req-docs/SUBMISSION_FREEZE.md` with named owners; store approval PDF.
- Generate SBOM/license manifest and attach to submission packet.
- Package evidence bundle in `req-docs/submission/` (logs, screenshots, dashboard exports).
- Verify deployment observability (health endpoints, reset workflow) and document support rota.

## Post-Submission Prep
- Schedule on-call coverage (Oct 20–Nov 13) and document rotation in deliverables template.
- Plan credential rotation immediately after judging window.
- Confirm privacy/publicity acknowledgment added to README and Devpost description.
