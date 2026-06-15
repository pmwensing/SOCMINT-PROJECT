(() => {
  "use strict";
  const root = document.querySelector("[data-case-closure-workspace]");
  const readinessButton = document.getElementById("record-closure-readiness-review");
  const decisionButton = document.getElementById("record-supervisor-closure-decision");
  const retentionButton = document.getElementById("record-retention-assignment");
  const archiveButton = document.getElementById("generate-case-archive-package");
  const reopenRequestButton = document.getElementById("record-reopen-request");
  const reopenAuthorizationButton = document.getElementById("record-reopen-authorization");
  if (!root) return;

  const show = (kind, message) => {
    const feedback = document.getElementById("case-closure-feedback");
    feedback.hidden = false;
    feedback.className = `flash ${kind}`;
    feedback.textContent = message;
  };

  const post = async (path, body = {}) => {
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

  retentionButton?.addEventListener("click", async () => {
    retentionButton.disabled = true;
    try {
      const {response, payload} = await post("/retention-assignment", {
        policy_id: document.getElementById("retention-policy-id").value,
        confirmed: document.getElementById("retention-assignment-confirmed").checked,
        note: document.getElementById("retention-assignment-note").value,
      });
      document.getElementById("retention-assignment-output").textContent = JSON.stringify(payload, null, 2);
      if (!response.ok) throw new Error(payload.blockers?.[0]?.key || "retention assignment blocked");
      show("success", "Retention policy assignment recorded.");
      window.location.reload();
    } catch (error) {
      show("error", error.message);
      retentionButton.disabled = false;
    }
  });

  archiveButton?.addEventListener("click", async () => {
    archiveButton.disabled = true;
    try {
      const {response, payload} = await post("/archive-package");
      document.getElementById("case-archive-package-output").textContent = JSON.stringify(payload, null, 2);
      if (!response.ok) throw new Error(payload.blockers?.[0]?.key || "archive package generation blocked");
      show("success", "Case archive package generated.");
      window.location.reload();
    } catch (error) {
      show("error", error.message);
      archiveButton.disabled = false;
    }
  });

  reopenRequestButton?.addEventListener("click", async () => {
    reopenRequestButton.disabled = true;
    try {
      const {response, payload} = await post("/reopen-request", {
        reason: document.getElementById("reopen-request-reason").value,
        confirmed: document.getElementById("reopen-request-confirmed").checked,
        note: document.getElementById("reopen-request-note").value,
      });
      document.getElementById("reopen-request-output").textContent = JSON.stringify(payload, null, 2);
      if (!response.ok) throw new Error(payload.blockers?.[0]?.key || "reopen request blocked");
      show("success", "Reopen request recorded.");
    } catch (error) {
      show("error", error.message);
      reopenRequestButton.disabled = false;
    }
  });

  reopenAuthorizationButton?.addEventListener("click", async () => {
    reopenAuthorizationButton.disabled = true;
    try {
      const {response, payload} = await post("/reopen-authorization", {
        decision: document.getElementById("reopen-authorization-decision").value,
        confirmed: document.getElementById("reopen-authorization-confirmed").checked,
        note: document.getElementById("reopen-authorization-note").value,
      });
      document.getElementById("reopen-authorization-output").textContent = JSON.stringify(payload, null, 2);
      if (!response.ok) throw new Error(payload.blockers?.[0]?.key || "reopen authorization blocked");
      show("success", "Reopen authorization decision recorded.");
    } catch (error) {
      show("error", error.message);
      reopenAuthorizationButton.disabled = false;
    }
  });
})();
