(() => {
  "use strict";
  const root = document.querySelector("[data-case-findings-workspace]");
  if (!root) return;
  const caseId = root.dataset.caseId;
  const csrf = root.dataset.csrfToken || "";
  const feedback = document.getElementById("case-findings-feedback");
  const body = document.getElementById("case-findings-body");
  const output = document.getElementById("dossier-package-output");
  const splitIds = (id) => document.getElementById(id).value
    .split(",").map((value) => value.trim()).filter(Boolean);
  const banner = (kind, text) => {
    feedback.hidden = false;
    feedback.className = `flash ${kind}`;
    feedback.textContent = text;
  };
  const request = async (url, options = {}) => {
    const response = await fetch(url, {
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "X-CSRF-Token": csrf,
        ...(options.headers || {}),
      },
      ...options,
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(
        payload.blockers?.[0]?.key || payload.error ||
        `request failed (${response.status})`
      );
    }
    return payload;
  };
  const refresh = () => window.location.reload();

  document.getElementById("propose-case-finding").addEventListener(
    "click",
    async () => {
      try {
        await request(
          `/api/v1/case-findings/${encodeURIComponent(caseId)}/proposals`,
          {
            method: "POST",
            body: JSON.stringify({
              text: document.getElementById("finding-text").value,
              confidence: document.getElementById("finding-confidence").value,
              claim_ids: splitIds("finding-claim-ids"),
              evidence_ids: splitIds("finding-evidence-ids"),
              entity_ids: splitIds("finding-entity-ids"),
              timeline_refs: splitIds("finding-timeline-refs"),
              note: document.getElementById("finding-note").value,
            }),
          }
        );
        banner("success", "Finding proposed with provenance.");
        refresh();
      } catch (error) {
        banner("error", error.message);
      }
    }
  );

  body?.addEventListener("click", async (event) => {
    const decisionButton = event.target.closest(".save-finding-decision");
    const revisionButton = event.target.closest(".revise-finding");
    const row = event.target.closest("tr");
    if (!row || (!decisionButton && !revisionButton)) return;
    try {
      if (decisionButton) {
        const payload = await request(
          `/api/v1/case-findings/${encodeURIComponent(caseId)}/${encodeURIComponent(row.dataset.findingId)}/decision`,
          {
            method: "POST",
            body: JSON.stringify({
              action: row.querySelector(".finding-decision").value,
              note: row.querySelector(".finding-decision-note").value,
            }),
          }
        );
        banner("success", `Finding ${payload.status}.`);
      } else {
        await request(
          `/api/v1/case-findings/${encodeURIComponent(caseId)}/${encodeURIComponent(row.dataset.findingId)}/revisions`,
          {
            method: "POST",
            body: JSON.stringify({
              text: row.querySelector(".revised-finding-text").value,
              confidence: row.querySelector(".revised-finding-confidence").value,
              note: row.querySelector(".revised-finding-note").value,
            }),
          }
        );
        banner("success", "Finding revision submitted.");
      }
      refresh();
    } catch (error) {
      banner("error", error.message);
    }
  });

  document.getElementById("refresh-case-findings").addEventListener("click", refresh);
  document.getElementById("preview-dossier-package").addEventListener(
    "click",
    async () => {
      try {
        output.textContent = JSON.stringify(
          await request(
            `/api/v1/case-findings/${encodeURIComponent(caseId)}/dossier-package`
          ),
          null,
          2
        );
      } catch (error) {
        banner("error", error.message);
      }
    }
  );
  document.getElementById("promote-dossier-package").addEventListener(
    "click",
    async () => {
      if (!window.confirm("Promote all approved findings to the dossier package?")) {
        return;
      }
      try {
        const payload = await request(
          `/api/v1/case-findings/${encodeURIComponent(caseId)}/dossier-package`,
          { method: "POST", body: "{}" }
        );
        output.textContent = JSON.stringify(payload, null, 2);
        banner("success", "Approved findings promoted to dossier package.");
      } catch (error) {
        banner("error", error.message);
      }
    }
  );
})();
