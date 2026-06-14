(() => {
  "use strict";
  const root = document.querySelector("[data-dossier-citation-workspace]");
  const button = document.getElementById("save-citation-snapshot");
  if (!root || !button) return;

  button.addEventListener("click", async () => {
    const feedback = document.getElementById("citation-mapping-feedback");
    const output = document.getElementById("citation-snapshot-output");
    button.disabled = true;
    try {
      const url = "/api/v1/dossier-assembly/" + root.dataset.caseId +
        "/citation-snapshot?subject_id=" + root.dataset.subjectId;
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
      if (!response.ok) throw new Error("citation snapshot blocked");
      feedback.hidden = false;
      feedback.className = "flash success";
      feedback.textContent = "Citation mapping snapshot saved.";
      window.location.reload();
    } catch (error) {
      feedback.hidden = false;
      feedback.className = "flash error";
      feedback.textContent = error.message;
      button.disabled = false;
    }
  });
})();
