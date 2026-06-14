(() => {
  "use strict";
  const root = document.querySelector("[data-dossier-release-workspace]");
  const previewButton = document.getElementById("preview-release-readiness");
  const authorizeButton = document.getElementById("authorize-release-selection");
  const acknowledgeButton = document.getElementById("acknowledge-release-preview");
  const dispatchButton = document.getElementById("dispatch-secure-distribution");
  const receiptButton = document.getElementById("record-delivery-receipt");
  const recipientAckButton = document.getElementById("record-recipient-acknowledgement");
  if (!root || !previewButton) return;

  const post = async (path, body) => {
    const response = await fetch(
      "/api/v1/dossier-release/" + root.dataset.caseId + path,
      {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": root.dataset.csrfToken || "",
        },
        body: JSON.stringify(body),
      }
    );
    return {response, payload: await response.json()};
  };

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
    previewButton.disabled = true;
    try {
      const {response, payload} = await post("/preview", selection());
      document.getElementById("release-preview-output").textContent = JSON.stringify(payload, null, 2);
      show(response.ok ? "success" : "warning", response.ok ? "Release configuration is ready for the case-delivery workspace." : (payload.blockers?.[0]?.key || "Release configuration needs review."));
    } catch (error) { show("error", error.message); } finally { previewButton.disabled = false; }
  });

  authorizeButton?.addEventListener("click", async () => {
    authorizeButton.disabled = true;
    try {
      const {response, payload} = await post("/authorize", {
        ...selection(),
        confirmed: document.getElementById("release-authorization-confirmed").checked,
        note: document.getElementById("release-authorization-note").value,
      });
      document.getElementById("release-authorization-output").textContent = JSON.stringify(payload, null, 2);
      if (!response.ok) throw new Error(payload.blockers?.[0]?.key || "release authorization blocked");
      show("success", "Recipient and delivery channel authorized.");
      window.location.reload();
    } catch (error) { show("error", error.message); authorizeButton.disabled = false; }
  });

  acknowledgeButton?.addEventListener("click", async () => {
    acknowledgeButton.disabled = true;
    try {
      const {response, payload} = await post("/package-preview/acknowledge", {
        acknowledged: document.getElementById("release-preview-acknowledged").checked,
        note: document.getElementById("release-preview-note").value,
      });
      document.getElementById("release-package-preview-output").textContent = JSON.stringify(payload, null, 2);
      if (!response.ok) throw new Error(payload.blockers?.[0]?.key || "release preview acknowledgement blocked");
      show(payload.release_ready ? "success" : "warning", payload.release_ready ? "Release package preview acknowledged and ready." : "Preview recorded with unresolved blockers.");
      window.location.reload();
    } catch (error) { show("error", error.message); acknowledgeButton.disabled = false; }
  });

  dispatchButton?.addEventListener("click", async () => {
    dispatchButton.disabled = true;
    try {
      const {response, payload} = await post("/dispatch", {
        confirmed: document.getElementById("secure-distribution-confirmed").checked,
        note: document.getElementById("secure-distribution-note").value,
      });
      document.getElementById("secure-distribution-output").textContent = JSON.stringify(payload, null, 2);
      if (!response.ok) throw new Error(payload.blockers?.[0]?.key || "secure distribution blocked");
      show("success", "Secure distribution request recorded through Case Delivery.");
      window.location.reload();
    } catch (error) { show("error", error.message); dispatchButton.disabled = false; }
  });

  receiptButton?.addEventListener("click", async () => {
    receiptButton.disabled = true;
    try {
      const {response, payload} = await post("/delivery-receipt", {
        delivery_result: document.getElementById("delivery-result").value,
        provider_message_id: document.getElementById("provider-message-id").value,
        transport_status: document.getElementById("transport-status").value,
        delivered_at: document.getElementById("delivered-at").value,
        failure_code: document.getElementById("delivery-failure-code").value,
        failure_detail: document.getElementById("delivery-failure-detail").value,
        note: document.getElementById("delivery-receipt-note").value,
      });
      document.getElementById("delivery-receipt-output").textContent = JSON.stringify(payload, null, 2);
      if (!response.ok) throw new Error(payload.blockers?.[0]?.key || "delivery receipt blocked");
      show("success", "Delivery receipt recorded.");
      window.location.reload();
    } catch (error) { show("error", error.message); receiptButton.disabled = false; }
  });

  recipientAckButton?.addEventListener("click", async () => {
    recipientAckButton.disabled = true;
    try {
      const {response, payload} = await post("/recipient-acknowledgement", {
        acknowledged: document.getElementById("recipient-acknowledged").checked,
        recipient_name: document.getElementById("recipient-ack-name").value,
        acknowledgement_method: document.getElementById("recipient-ack-method").value,
        acknowledged_at: document.getElementById("recipient-ack-at").value,
        note: document.getElementById("recipient-ack-note").value,
      });
      document.getElementById("recipient-acknowledgement-output").textContent = JSON.stringify(payload, null, 2);
      if (!response.ok) throw new Error(payload.blockers?.[0]?.key || "recipient acknowledgement blocked");
      show("success", "Recipient acknowledgement recorded.");
      window.location.reload();
    } catch (error) { show("error", error.message); recipientAckButton.disabled = false; }
  });
})();
