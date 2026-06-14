(() => {
  "use strict";
  const root = document.querySelector("[data-dossier-quality-review]");
  const button = document.getElementById("save-quality-review-snapshot");
  if (!root || !button) return;

  button.addEventListener("click", async () => {
    const feedback = document.getElementById("quality-review-feedback");
    const output = document.getElementById("quality-review-output");
    button.disabled = true;
    try {
      const url = "/api/v1/dossier-assembly/" + root.dataset.caseId +
        "/quality-review-snapshot?subject_id=" + root.dataset.subjectId;
      const response = await fetch(url, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": root.dataset.csrfToken || "",
        },
        body: "{}",
      });
      const payload = await response.json();
      output.textContent = JSON.stringify(payload, null, 2);
      if (!response.ok) throw new Error("quality review snapshot blocked");
      feedback.hidden = false;
      feedback.className = "flash success";
      feedback.textContent = "Quality review snapshot saved.";
      window.location.reload();
    } catch (error) {
      feedback.hidden = false;
      feedback.className = "flash error";
      feedback.textContent = error.message;
      button.disabled = false;
    }
  });
})();
