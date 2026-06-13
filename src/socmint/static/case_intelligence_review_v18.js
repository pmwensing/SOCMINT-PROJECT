(() => {
  "use strict";
  const root = document.querySelector("[data-case-intelligence-review]");
  if (!root) return;
  const caseId = root.dataset.caseId;
  const csrfToken = root.dataset.csrfToken || "";
  const feedback = document.getElementById("case-review-feedback");
  const decisionButton = document.getElementById("record-review-decision");
  const refreshButton = document.getElementById("refresh-review-history");
  const persistentRefreshButton = document.getElementById(
    "refresh-persistent-decision-history"
  );
  const historyBody = document.getElementById("case-review-history-body");
  const empty = document.getElementById("case-review-history-empty");
  const persistentBody = document.getElementById(
    "persistent-decision-history-body"
  );
  const persistentEmpty = document.getElementById(
    "persistent-decision-history-empty"
  );
  const persistentCount = document.getElementById("persistent-decision-count");

  const banner = (kind, message) => {
    feedback.hidden = false;
    feedback.className = `flash ${kind}`;
    feedback.textContent = message;
    feedback.focus({ preventScroll: true });
  };

  const addCells = (row, values) => {
    values.forEach((value) => {
      const cell = document.createElement("td");
      cell.textContent = value || "—";
      row.appendChild(cell);
    });
  };

  const renderHistory = (history) => {
    const entries = Array.isArray(history?.entries) ? history.entries : [];
    historyBody.innerHTML = "";
    entries.forEach((item) => {
      const row = document.createElement("tr");
      addCells(row, [
        item.recorded_at,
        item.operator,
        item.decision,
        item.note || "—",
      ]);
      historyBody.appendChild(row);
    });
    historyBody.closest("table").hidden = entries.length === 0;
    empty.hidden = entries.length > 0;
  };

  const renderPersistentHistory = (history) => {
    const entries = Array.isArray(history?.entries) ? history.entries : [];
    persistentBody.innerHTML = "";
    entries.forEach((item) => {
      const row = document.createElement("tr");
      addCells(row, [
        item.actor,
        item.decision,
        item.note || "—",
        item.source_recorded_at || "—",
        item.persisted_at || "—",
      ]);
      persistentBody.appendChild(row);
    });
    persistentBody.closest("table").hidden = entries.length === 0;
    persistentEmpty.hidden = entries.length > 0;
    persistentCount.textContent = `${history?.entry_count || 0} record(s)`;
  };

  const refreshHistory = async () => {
    refreshButton.disabled = true;
    try {
      const response = await fetch(
        `/api/v1/case-intelligence-review/${encodeURIComponent(caseId)}/history`,
        {
          credentials: "same-origin",
          headers: { Accept: "application/json" },
        }
      );
      if (!response.ok) {
        throw new Error(`session history refresh failed (${response.status})`);
      }
      renderHistory(await response.json());
      banner("success", "Case review session history refreshed.");
    } catch (error) {
      banner("error", error.message);
    } finally {
      refreshButton.disabled = false;
    }
  };

  const refreshPersistentHistory = async () => {
    persistentRefreshButton.disabled = true;
    try {
      const response = await fetch(
        `/api/v1/case-intelligence-review/${encodeURIComponent(caseId)}/decisions/persistent`,
        {
          credentials: "same-origin",
          headers: { Accept: "application/json" },
        }
      );
      if (!response.ok) {
        throw new Error(`durable history refresh failed (${response.status})`);
      }
      renderPersistentHistory(await response.json());
      banner("success", "Persistent decision history refreshed.");
    } catch (error) {
      banner("error", error.message);
    } finally {
      persistentRefreshButton.disabled = false;
    }
  };

  decisionButton.addEventListener("click", async () => {
    const decision = document.getElementById("review-decision").value;
    const note = document.getElementById("review-note").value;
    if (!window.confirm(`Record analyst decision: ${decision}?`)) {
      banner("warning", "Decision cancelled.");
      return;
    }
    decisionButton.disabled = true;
    try {
      const response = await fetch(
        `/api/v1/case-intelligence-review/${encodeURIComponent(caseId)}/decisions`,
        {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
            "X-CSRF-Token": csrfToken,
          },
          body: JSON.stringify({ decision, note }),
        }
      );
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.blockers?.[0]?.detail || "decision blocked");
      }
      renderHistory(payload.review_history);
      renderPersistentHistory(payload.persistent_decision_history);
      banner("success", `Decision recorded and persisted: ${payload.decision}`);
    } catch (error) {
      banner("error", error.message);
    } finally {
      decisionButton.disabled = false;
    }
  });

  refreshButton.addEventListener("click", refreshHistory);
  persistentRefreshButton.addEventListener("click", refreshPersistentHistory);
})();
