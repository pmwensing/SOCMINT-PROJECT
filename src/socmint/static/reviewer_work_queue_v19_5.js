(() => {
  "use strict";

  const root = document.querySelector("[data-reviewer-work-queue]");
  if (!root) return;

  const csrfToken = root.dataset.csrfToken || "";
  const feedback = document.getElementById("reviewer-work-queue-feedback");
  const body = document.getElementById("reviewer-work-queue-body");
  const refreshButton = document.getElementById("refresh-reviewer-work-queue");

  const banner = (kind, message) => {
    feedback.hidden = false;
    feedback.className = `flash ${kind}`;
    feedback.textContent = message;
    feedback.focus({ preventScroll: true });
  };

  const refreshQueue = async () => {
    refreshButton.disabled = true;
    try {
      const response = await fetch(
        "/api/v1/case-intelligence-review/my-assignments",
        { credentials: "same-origin", headers: { Accept: "application/json" } }
      );
      if (!response.ok) throw new Error(`queue refresh failed (${response.status})`);
      window.location.reload();
    } catch (error) {
      banner("error", error.message);
      refreshButton.disabled = false;
    }
  };

  const saveReviewState = async (row, button) => {
    const caseId = row.dataset.caseId;
    const decisionRecordId = row.dataset.decisionRecordId;
    const reviewState = row.querySelector(".reviewer-state-select").value;
    const note = row.querySelector(".reviewer-state-note").value.trim();
    button.disabled = true;
    try {
      const response = await fetch(
        `/api/v1/case-intelligence-review/my-assignments/${encodeURIComponent(caseId)}/decisions/${encodeURIComponent(decisionRecordId)}/review-state`,
        {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
            "X-CSRF-Token": csrfToken,
          },
          body: JSON.stringify({ review_state: reviewState, note }),
        }
      );
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.blockers?.[0]?.detail || "review state blocked");
      }
      row.querySelector(".reviewer-state-value").textContent = payload.review_state;
      banner("success", `Review state recorded: ${payload.review_state}`);
    } catch (error) {
      banner("error", error.message);
    } finally {
      button.disabled = false;
    }
  };

  body?.addEventListener("click", (event) => {
    const button = event.target.closest(".save-reviewer-state");
    if (!button) return;
    saveReviewState(button.closest("tr"), button);
  });

  refreshButton?.addEventListener("click", refreshQueue);
})();
