(() => {
  "use strict";

  const root = document.querySelector("[data-operator-workflow-dashboard]");
  if (!root) return;

  const caseId = root.dataset.caseId;
  const csrfToken = root.dataset.csrfToken || "";
  const actionUrl = `/api/v1/operator/workflow-dashboard/${encodeURIComponent(caseId)}/actions`;
  const historyUrl = `${actionUrl}/history`;
  const banner = document.getElementById("operator-action-feedback");
  const historyBody = document.getElementById("operator-action-history-body");
  const historyEmpty = document.getElementById("operator-action-history-empty");
  const historyLoading = document.getElementById("operator-action-history-loading");
  const historyCount = document.getElementById("operator-action-history-count");
  const refreshHistoryButton = document.getElementById("refresh-action-history");

  const setBanner = (kind, message, detail = "") => {
    if (!banner) return;
    banner.hidden = false;
    banner.dataset.kind = kind;
    banner.className = `flash ${kind}`;
    banner.innerHTML = "";
    const strong = document.createElement("strong");
    strong.textContent = message;
    banner.appendChild(strong);
    if (detail) {
      const paragraph = document.createElement("p");
      paragraph.textContent = detail;
      banner.appendChild(paragraph);
    }
    banner.focus({ preventScroll: true });
  };

  const setBusy = (button, busy) => {
    if (!button) return;
    button.disabled = busy || button.dataset.permanentlyDisabled === "true";
    button.setAttribute("aria-busy", busy ? "true" : "false");
    if (busy) {
      button.dataset.originalLabel = button.textContent;
      button.textContent = "Working…";
    } else if (button.dataset.originalLabel) {
      button.textContent = button.dataset.originalLabel;
      delete button.dataset.originalLabel;
    }
  };

  const textCell = (value) => {
    const cell = document.createElement("td");
    cell.textContent = value || "—";
    return cell;
  };

  const renderHistory = (timeline) => {
    if (!historyBody) return;
    const entries = Array.isArray(timeline?.entries) ? timeline.entries : [];
    historyBody.innerHTML = "";
    entries.forEach((entry) => {
      const row = document.createElement("tr");
      row.appendChild(textCell(entry.recorded_at || "unknown"));
      row.appendChild(textCell(entry.label || entry.action || "unknown"));
      row.appendChild(textCell(entry.result_status || "unknown"));
      row.appendChild(textCell(entry.verification_status || "not verified"));
      row.appendChild(textCell(entry.action_target || "—"));
      row.appendChild(textCell((entry.action_receipt_id || "").slice(0, 12)));
      historyBody.appendChild(row);
    });
    if (historyCount) historyCount.textContent = `${timeline?.entry_count || 0} event(s)`;
    if (historyEmpty) historyEmpty.hidden = entries.length > 0;
    const table = historyBody.closest("table");
    if (table) table.hidden = entries.length === 0;
  };

  const refreshHistory = async ({ quiet = false } = {}) => {
    if (historyLoading) historyLoading.hidden = false;
    if (refreshHistoryButton) setBusy(refreshHistoryButton, true);
    try {
      const response = await fetch(historyUrl, {
        method: "GET",
        headers: { Accept: "application/json" },
        credentials: "same-origin",
      });
      if (!response.ok) throw new Error(`History refresh failed (${response.status})`);
      renderHistory(await response.json());
      if (!quiet) setBanner("success", "Action history refreshed.");
    } catch (error) {
      setBanner("error", "Unable to refresh action history.", error.message);
    } finally {
      if (historyLoading) historyLoading.hidden = true;
      if (refreshHistoryButton) setBusy(refreshHistoryButton, false);
    }
  };

  const launchAction = async (button) => {
    const action = button.dataset.action;
    const requiresConfirmation = button.dataset.requiresConfirmation === "true";
    if (requiresConfirmation) {
      const prompt = button.dataset.confirmMessage || "Confirm this operator action?";
      if (!window.confirm(prompt)) {
        setBanner("warning", "Action cancelled.", "No state-changing action plan was created.");
        return;
      }
    }

    setBusy(button, true);
    setBanner("info", "Submitting operator action…", button.textContent);
    try {
      const response = await fetch(actionUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          "X-CSRF-Token": csrfToken,
        },
        body: JSON.stringify({ action, confirmed: requiresConfirmation }),
      });
      const payload = await response.json();
      if (payload.action_history) renderHistory(payload.action_history);

      if (response.ok && payload.status === "launched") {
        const target = payload.action_plan?.target || payload.action_plan?.command || "Action plan created";
        setBanner("success", payload.label || "Operator action launched.", target);
        if (payload.action_plan?.type === "navigation" && payload.action_plan?.target) {
          window.location.assign(payload.action_plan.target);
        }
      } else if (payload.status === "confirmation_required") {
        setBanner("warning", "Explicit confirmation is required.", payload.next_action || "Confirm the action and retry.");
      } else {
        const detail = Array.isArray(payload.blockers)
          ? payload.blockers.map((item) => item.detail || item.key).join("; ")
          : "The action could not be launched.";
        setBanner("error", "Operator action blocked.", detail);
      }
    } catch (error) {
      setBanner("error", "Operator action request failed.", error.message);
    } finally {
      setBusy(button, false);
    }
  };

  document.querySelectorAll("[data-workflow-action]").forEach((button) => {
    button.addEventListener("click", () => launchAction(button));
  });

  if (refreshHistoryButton) {
    refreshHistoryButton.addEventListener("click", () => refreshHistory());
  }

  if (historyLoading) historyLoading.hidden = true;
})();
