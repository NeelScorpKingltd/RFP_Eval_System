# Acceptance walkthrough

This follows [PRD.md §12](../PRD.md#12-demonstration-script-acceptance-walkthrough). Use synthetic data only. On a deployed app, configure a low-limit demo key in Streamlit Cloud secrets first; locally, use your own provider key.

## Successful run

1. Open the app in a fresh browser session. Select **Use Free Default Demo Model** if configured, or choose a provider and enter your own key in the sidebar.
2. On **1 · Criteria**, confirm five active criteria totaling 100%.
3. On **2 · Suppliers**, select **Load demo suppliers**. Confirm four PDFs are accepted with their dates and ratings.
4. On **3 · Run & leaderboard**, select **Evaluate**. Confirm the live steps finish and the leaderboard has ranks 1–4. Expand the What-If simulator and move one slider to see recomputed ranks.
5. On **4 · Scorecard & risks**, inspect evidence and gaps. BrightPath Tech's synthetic proposal includes travel pass-through, limited compliance evidence, and capped SLA credits; check the Risk Radar for model-extracted caveats.
6. On **5 · Playbook & details**, inspect ranking explanations and warnings, then download **Unified Run JSON**. Select **Generate BAFO Negotiation Playbook** and download the Markdown briefing.
7. Return to **3 · Run & leaderboard** and evaluate the same four PDFs again. The cache should show four hits and zero LLM calls.

The checked-in [`sample_run.json`](../sample_data/sample_run.json) demonstrates a four-supplier completed run with deterministic fake replies; it is suitable for inspecting the export without a key.

## Error and validation cases

1. Set one active criterion weight so the total is 95%. The readiness banner must show the weight error and **Evaluate** must be disabled. Restore the weights and save.
2. Upload `sample_data/edge_cases/too_many_pages.pdf` or `image_only.pdf`. The supplier card should explain the rejection; valid suppliers remain available.
3. With a configured demo key, enable **Simulate Malformed LLM Output (Demo Mode)** and evaluate. The run should complete with a supplier-level fallback or normalization warnings, and no cache reads or writes for that run.

## Offline verification

Run `make check` (or the four equivalent commands in the README) and `make sample-run`. The sample export generation runs PDF sanitation, fake evaluation, validation, ranking, persistence, and unified export without network access. The integration tests cover a malformed reply, a rejected PDF, an authentication failure, and the run gate.

## Deployment review record

Before marking FR-DEL-04 and FR-DEL-06 complete, record the public URL, deployment date, reviewer browser, and a link to the walkthrough recording here. These depend on a project-specific repository, Cloud access, and a demo credential and are not represented by the offline sample.
