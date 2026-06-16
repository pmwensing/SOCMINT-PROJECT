(() => {
  "use strict";
  const root = document.querySelector("[data-portfolio-escalations]");
  if (!root) return;

  const feedback = document.getElementById("portfolio-escalation-feedback");
  const show = (kind, text) => {
    feedback.hidden = false;
    feedback.className = `flash ${kind}`;
    feedback.textContent = text;
  };

  root.querySelectorAll("[data-escalation-case]").forEach((panel) => {
    panel.querySelectorAll("[data-control]").forEach((button) => {
      button.addEventListener("click", async () => {
        const control = button.dataset.control;
        const caseId = panel.dataset.escalationCase;
        const value = (name) => panel.querySelector(`[data-field='${name}']`)?.value || "";
        const checked = panel.querySelector("[data-field='confirmed']")?.checked === true;
        const body = {
          confirmed: checked,
          reason: value("reason"),
          assigned_reviewer: value("assigned_reviewer"),
          resolution: value("resolution"),
          note: value("note"),
        };
        button.disabled = true;
        try {
          const response = await fetch(`/api/v1/portfolio-operations/${caseId}/${control}`, {
            method: "POST",
            credentials: "same-origin",
            headers: {
              "Content-Type": "application/json",
              "X-CSRF-Token": root.dataset.csrfToken || "",
            },
            body: JSON.stringify(body),
          });
          const payload = await response.json();
          panel.querySelector("[data-output]").textContent = JSON.stringify(payload, null, 2);
          if (!response.ok) throw new Error(payload.blockers?.[0]?.key || `${control} blocked`);
          show("success", `${control} recorded for ${caseId}.`);
          window.location.reload();
        } catch (error) {
          show("error", error.message);
          button.disabled = false;
        }
      });
    });
  });
})();
