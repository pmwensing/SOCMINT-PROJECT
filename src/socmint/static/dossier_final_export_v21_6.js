(() => {
  "use strict";
  const root = document.querySelector("[data-dossier-final-export]");
  const button = document.getElementById("generate-final-export");
  if (!root || !button) return;

  button.addEventListener("click", async () => {
    const feedback = document.getElementById("final-export-feedback");
    const output = document.getElementById("final-export-output");
    button.disabled = true;
    try {
      const response = await fetch(
        "/api/v1/dossier-assembly/" + root.dataset.caseId +
        "/final-export?subject_id=" + root.dataset.subjectId,
        {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": root.dataset.csrfToken || "",
          },
          body: "{}",
        }
      );
      const payload = await response.json();
      output.textContent = JSON.stringify(payload, null, 2);
      if (!response.ok) {
        throw new Error(payload.blockers?.[0]?.key || "final export blocked");
      }
      feedback.hidden = false;
      feedback.className = "flash success";
      feedback.textContent = "Final export package generated.";
      window.location.reload();
    } catch (error) {
      feedback.hidden = false;
      feedback.className = "flash error";
      feedback.textContent = error.message;
      button.disabled = false;
    }
  });
})();
