(() => {
  "use strict";

  const root = document.querySelector("[data-supervisor-assignment-queue]");
  if (!root) return;

  const csrfToken = root.dataset.csrfToken || "";
  const feedback = document.getElementById("supervisor-assignment-feedback");
  const body = document.getElementById("supervisor-assignment-queue-body");

  const banner = (kind, message) => {
    feedback.hidden = false;
    feedback.className = `flash ${kind}`;
    feedback.textContent = message;
    feedback.focus({ preventScroll: true });
  };

  const saveAssignment = async (row, button) => {
    const caseId = row.dataset.caseId;
    const decisionRecordId = row.dataset.decisionRecordId;
    const reviewer = row.querySelector(".assignment-reviewer").value.trim();
    const note = row.querySelector(".assignment-note").value.trim();

    if (!reviewer) {
      banner("error", "A reviewer username is required.");
      return;
    }
    if (!window.confirm(`Assign decision ${decisionRecordId} to ${reviewer}?`)) {
      banner("warning", "Assignment cancelled.");
      return;
    }

    button.disabled = true;
    try {
      const response = await fetch(
        `/api/v1/case-intelligence-review/supervisor-queue/${encodeURIComponent(caseId)}/decisions/${encodeURIComponent(decisionRecordId)}/assignment`,
        {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
            "X-CSRF-Token": csrfToken,
          },
          body: JSON.stringify({ assigned_reviewer: reviewer, note }),
        }
      );
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.blockers?.[0]?.detail || "assignment blocked");
      }
      const reviewerCell = row.querySelector(".assigned-reviewer-value");
      reviewerCell.textContent = payload.assigned_reviewer;
      const meta = document.createElement("small");
      meta.textContent = `by ${payload.assigned_by} · ${payload.assigned_at || ""}`;
      reviewerCell.append(document.createElement("br"), meta);
      button.textContent = "Reassign";
      banner("success", `Decision assigned to ${payload.assigned_reviewer}.`);
    } catch (error) {
      banner("error", error.message);
    } finally {
      button.disabled = false;
    }
  };

  body?.addEventListener("click", (event) => {
    const button = event.target.closest(".save-supervisor-assignment");
    if (!button) return;
    saveAssignment(button.closest("tr"), button);
  });
})();
