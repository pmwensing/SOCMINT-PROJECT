(() => {
  "use strict";
  const root = document.querySelector("[data-case-closure-workspace]");
  const readinessButton = document.getElementById("record-closure-readiness-review");
  const decisionButton = document.getElementById("record-supervisor-closure-decision");
  if (!root) return;

  const show = (kind, message) => {
    const feedback = document.getElementById("case-closure-feedback");
    feedback.hidden = false;
    feedback.className = `flash ${kind}`;
    feedback.textContent = message;
  };

  const post = async (path, body) => {
    const response = await fetch(
      `/api/v1/case-closure/${root.dataset.caseId}${path}`,
      {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": root.dataset.csrfToken || "",
        },
        body: JSON.stringify(body),
      }
    );
    return {response, payload: await response.json()};
  };

  readinessButton?.addEventListener("click", async () => {
    readinessButton.disabled = true;
    try {
      const {response, payload} = await post("/readiness-review", {
        decision: document.getElementById("closure-readiness-decision").value,
        confirmed: document.getElementById("closure-readiness-confirmed").checked,
        note: document.getElementById("closure-readiness-note").value,
      });
      document.getElementById("closure-readiness-review-output").textContent = JSON.stringify(payload, null, 2);
      if (!response.ok) throw new Error(payload.blockers?.[0]?.key || "closure readiness review blocked");
      show("success", "Closure readiness review recorded.");
      window.location.reload();
    } catch (error) {
      show("error", error.message);
      readinessButton.disabled = false;
    }
  });

  decisionButton?.addEventListener("click", async () => {
    decisionButton.disabled = true;
    try {
      const {response, payload} = await post("/closure-decision", {
        decision: document.getElementById("supervisor-closure-decision").value,
        confirmed: document.getElementById("supervisor-closure-confirmed").checked,
        note: document.getElementById("supervisor-closure-note").value,
      });
      document.getElementById("supervisor-closure-decision-output").textContent = JSON.stringify(payload, null, 2);
      if (!response.ok) throw new Error(payload.blockers?.[0]?.key || "supervisor closure decision blocked");
      show("success", "Supervisor closure decision recorded.");
      window.location.reload();
    } catch (error) {
      show("error", error.message);
      decisionButton.disabled = false;
    }
  });
})();
