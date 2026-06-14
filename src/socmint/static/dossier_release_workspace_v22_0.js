(() => {
  "use strict";
  const root = document.querySelector("[data-dossier-release-workspace]");
  const button = document.getElementById("preview-release-readiness");
  if (!root || !button) return;

  button.addEventListener("click", async () => {
    const feedback = document.getElementById("release-workspace-feedback");
    const output = document.getElementById("release-preview-output");
    button.disabled = true;
    try {
      const response = await fetch(
        "/api/v1/dossier-release/" + root.dataset.caseId + "/preview",
        {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": root.dataset.csrfToken || "",
          },
          body: JSON.stringify({
            recipient_id: document.getElementById("release-recipient").value,
            delivery_channel: document.getElementById("release-channel").value,
          }),
        }
      );
      const payload = await response.json();
      output.textContent = JSON.stringify(payload, null, 2);
      feedback.hidden = false;
      feedback.className = response.ok ? "flash success" : "flash warning";
      feedback.textContent = response.ok
        ? "Release configuration is ready for the case-delivery workspace."
        : (payload.blockers?.[0]?.key || "Release configuration needs review.");
      const link = document.getElementById("open-case-delivery-workspace");
      if (payload.case_delivery_workspace?.href) {
        link.href = payload.case_delivery_workspace.href;
      }
    } catch (error) {
      feedback.hidden = false;
      feedback.className = "flash error";
      feedback.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  });
})();
