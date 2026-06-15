(() => {
  "use strict";
  const root = document.querySelector("[data-case-closure-workspace]");
  const button = document.getElementById("record-closure-readiness-review");
  if (!root || !button) return;

  const show = (kind, message) => {
    const feedback = document.getElementById("case-closure-feedback");
    feedback.hidden = false;
    feedback.className = `flash ${kind}`;
    feedback.textContent = message;
  };

  button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      const response = await fetch(
        `/api/v1/case-closure/${root.dataset.caseId}/readiness-review`,
        {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": root.dataset.csrfToken || "",
          },
          body: JSON.stringify({
            decision: document.getElementById("closure-readiness-decision").value,
            confirmed: document.getElementById("closure-readiness-confirmed").checked,
            note: document.getElementById("closure-readiness-note").value,
          }),
        }
      );
      const payload = await response.json();
      document.getElementById("closure-readiness-review-output").textContent = JSON.stringify(payload, null, 2);
      if (!response.ok) {
        throw new Error(payload.blockers?.[0]?.key || "closure readiness review blocked");
      }
      show("success", "Closure readiness review recorded.");
      window.location.reload();
    } catch (error) {
      show("error", error.message);
      button.disabled = false;
    }
  });
})();
