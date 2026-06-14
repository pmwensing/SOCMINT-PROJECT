(() => {
  "use strict";
  const root = document.querySelector("[data-dossier-release-workspace]");
  const previewButton = document.getElementById("preview-release-readiness");
  const authorizeButton = document.getElementById("authorize-release-selection");
  if (!root || !previewButton) return;

  const selection = () => ({
    recipient_id: document.getElementById("release-recipient").value,
    delivery_channel: document.getElementById("release-channel").value,
  });

  const show = (kind, message) => {
    const feedback = document.getElementById("release-workspace-feedback");
    feedback.hidden = false;
    feedback.className = `flash ${kind}`;
    feedback.textContent = message;
  };

  previewButton.addEventListener("click", async () => {
    const output = document.getElementById("release-preview-output");
    previewButton.disabled = true;
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
          body: JSON.stringify(selection()),
        }
      );
      const payload = await response.json();
      output.textContent = JSON.stringify(payload, null, 2);
      show(
        response.ok ? "success" : "warning",
        response.ok
          ? "Release configuration is ready for the case-delivery workspace."
          : (payload.blockers?.[0]?.key || "Release configuration needs review.")
      );
    } catch (error) {
      show("error", error.message);
    } finally {
      previewButton.disabled = false;
    }
  });

  authorizeButton?.addEventListener("click", async () => {
    const output = document.getElementById("release-authorization-output");
    authorizeButton.disabled = true;
    try {
      const response = await fetch(
        "/api/v1/dossier-release/" + root.dataset.caseId + "/authorize",
        {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": root.dataset.csrfToken || "",
          },
          body: JSON.stringify({
            ...selection(),
            confirmed: document.getElementById("release-authorization-confirmed").checked,
            note: document.getElementById("release-authorization-note").value,
          }),
        }
      );
      const payload = await response.json();
      output.textContent = JSON.stringify(payload, null, 2);
      if (!response.ok) {
        throw new Error(payload.blockers?.[0]?.key || "release authorization blocked");
      }
      show("success", "Recipient and delivery channel authorized.");
      window.location.reload();
    } catch (error) {
      show("error", error.message);
      authorizeButton.disabled = false;
    }
  });
})();
