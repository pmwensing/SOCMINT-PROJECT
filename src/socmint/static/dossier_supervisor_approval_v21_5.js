(() => {
  "use strict";
  const root = document.querySelector("[data-dossier-supervisor-approval]");
  const button = document.getElementById("save-supervisor-decision");
  if (!root || !button) return;

  button.addEventListener("click", async () => {
    const feedback = document.getElementById("supervisor-approval-feedback");
    const output = document.getElementById("supervisor-approval-output");
    button.disabled = true;
    try {
      const response = await fetch(
        "/api/v1/dossier-assembly/" + root.dataset.caseId +
        "/supervisor-decision?subject_id=" + root.dataset.subjectId,
        {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": root.dataset.csrfToken || "",
          },
          body: JSON.stringify({
            decision: document.getElementById("supervisor-decision").value,
            note: document.getElementById("supervisor-decision-note").value,
          }),
        }
      );
      const payload = await response.json();
      output.textContent = JSON.stringify(payload, null, 2);
      if (!response.ok) {
        throw new Error(payload.blockers?.[0]?.key || "supervisor decision blocked");
      }
      feedback.hidden = false;
      feedback.className = "flash success";
      feedback.textContent = "Supervisor decision recorded: " + payload.status;
      window.location.reload();
    } catch (error) {
      feedback.hidden = false;
      feedback.className = "flash error";
      feedback.textContent = error.message;
      button.disabled = false;
    }
  });
})();
