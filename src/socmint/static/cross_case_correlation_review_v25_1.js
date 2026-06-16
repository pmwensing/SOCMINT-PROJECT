(() => {
  "use strict";
  const root = document.querySelector("[data-cross-case-intelligence-workspace]");
  if (!root) return;
  const feedback = document.getElementById("cross-case-review-feedback");

  const show = (kind, text) => {
    feedback.hidden = false;
    feedback.className = `flash ${kind}`;
    feedback.textContent = text;
  };

  root.querySelectorAll("[data-correlation-candidate]").forEach((card) => {
    const button = card.querySelector("[data-action='record-review']");
    button?.addEventListener("click", async () => {
      const correlationId = card.dataset.correlationCandidate;
      const category = card.dataset.category;
      const decision = card.querySelector("[data-field='decision']")?.value || "";
      const reason = card.querySelector("[data-field='reason']")?.value || "";
      const confirmed = card.querySelector("[data-field='confirmed']")?.checked === true;
      const checked = [...card.querySelectorAll("[data-occurrence-hash]:checked")].map((node) => node.dataset.occurrenceHash);
      const all = [...card.querySelectorAll("[data-occurrence-hash]")].map((node) => node.dataset.occurrenceHash);
      const unchecked = all.filter((value) => !checked.includes(value));
      const body = {category, decision, reason, confirmed};
      if (decision === "split") {
        body.split_groups = [
          {
            group_id: "group-a",
            label: card.querySelector("[data-field='group_a_label']")?.value || "Group A",
            occurrence_provenance_sha256: checked,
          },
          {
            group_id: "group-b",
            label: card.querySelector("[data-field='group_b_label']")?.value || "Group B",
            occurrence_provenance_sha256: unchecked,
          },
        ];
      }
      button.disabled = true;
      try {
        const response = await fetch(`/api/v1/cross-case-intelligence/${correlationId}/review`, {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": root.dataset.csrfToken || "",
          },
          body: JSON.stringify(body),
        });
        const payload = await response.json();
        card.querySelector("[data-output]").textContent = JSON.stringify(payload, null, 2);
        if (!response.ok) {
          throw new Error(payload.blockers?.[0]?.key || "Correlation review blocked");
        }
        show("success", `${decision} decision recorded for ${correlationId}.`);
        window.location.reload();
      } catch (error) {
        show("error", error.message);
        button.disabled = false;
      }
    });
  });
})();
