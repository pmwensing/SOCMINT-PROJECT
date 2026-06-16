(() => {
  "use strict";
  const root = document.querySelector("[data-confirmed-link-registry]");
  if (!root) return;
  const feedback = document.getElementById("confirmed-link-feedback");

  const show = (kind, text) => {
    feedback.hidden = false;
    feedback.className = `flash ${kind}`;
    feedback.textContent = text;
  };

  root.querySelectorAll("[data-pending-confirmed-link]").forEach((card) => {
    const button = card.querySelector("[data-action='register-confirmed-link']");
    button?.addEventListener("click", async () => {
      const correlationId = card.dataset.pendingConfirmedLink;
      const note = card.querySelector("[data-field='note']")?.value || "";
      const confirmed = card.querySelector("[data-field='confirmed']")?.checked === true;
      button.disabled = true;
      try {
        const response = await fetch(`/api/v1/cross-case-intelligence/${correlationId}/confirmed-link`, {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": root.dataset.csrfToken || "",
          },
          body: JSON.stringify({note, confirmed}),
        });
        const payload = await response.json();
        card.querySelector("[data-output]").textContent = JSON.stringify(payload, null, 2);
        if (!response.ok) {
          throw new Error(payload.blockers?.[0]?.key || "Confirmed link registration blocked");
        }
        show("success", `Confirmed link registered for ${correlationId}.`);
        window.location.reload();
      } catch (error) {
        show("error", error.message);
        button.disabled = false;
      }
    });
  });
})();
