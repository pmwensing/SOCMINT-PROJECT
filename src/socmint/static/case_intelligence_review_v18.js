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
  const applyFiltersButton = document.getElementById(
    "apply-persistent-decision-filters"
  );
  const clearFiltersButton = document.getElementById(
    "clear-persistent-decision-filters"
  );
  const previousButton = document.getElementById("persistent-page-previous");
  const nextButton = document.getElementById("persistent-page-next");
  const pageStatus = document.getElementById("persistent-page-status");
  const historyBody = document.getElementById("case-review-history-body");
  const empty = document.getElementById("case-review-history-empty");
  const persistentBody = document.getElementById(
    "persistent-decision-history-body"
  );
  const persistentEmpty = document.getElementById(
    "persistent-decision-history-empty"
  );
  const persistentCount = document.getElementById("persistent-decision-count");
  let persistentPage = 1;

  const banner = (kind, message) => {
    feedback.hidden = false;
    feedback.className = `flash ${kind}`;
    feedback.textContent = message;
    feedback.focus({ preventScroll: true });
  };

  const addCell = (row, value) => {
    const cell = document.createElement("td");
    cell.textContent = value || "—";
    row.appendChild(cell);
    return cell;
  };

  const renderHistory = (history) => {
    const entries = Array.isArray(history?.entries) ? history.entries : [];
    historyBody.innerHTML = "";
    entries.forEach((item) => {
      const row = document.createElement("tr");
      [item.recorded_at, item.operator, item.decision, item.note || "—"].forEach(
        (value) => addCell(row, value)
      );
      historyBody.appendChild(row);
    });
    historyBody.closest("table").hidden = entries.length === 0;
    empty.hidden = entries.length > 0;
  };

  const reviewControl = (item, states) => {
    const container = document.createElement("div");
    const select = document.createElement("select");
    select.className = "persistent-review-state";
    states.forEach((state) => {
      const option = document.createElement("option");
      option.value = state;
      option.textContent = state;
      option.selected = item.review_state === state;
      select.appendChild(option);
    });
    const note = document.createElement("input");
    note.className = "persistent-review-note";
    note.type = "text";
    note.placeholder = "Review note";
    note.value = item.review_note || "";
    const save = document.createElement("button");
    save.type = "button";
    save.className = "save-persistent-review-state";
    save.textContent = "Save";
    container.append(select, note, save);
    return container;
  };

  const renderPersistentHistory = (history) => {
    const entries = Array.isArray(history?.entries) ? history.entries : [];
    const states = Array.isArray(history?.review_states)
      ? history.review_states
      : ["unreviewed", "reviewed", "needs_follow_up", "accepted"];
    persistentBody.innerHTML = "";
    entries.forEach((item) => {
      const row = document.createElement("tr");
      row.dataset.decisionRecordId = item.decision_record_id;
      [
        item.actor,
        item.decision,
        item.note || "—",
        item.source_recorded_at || "—",
        item.persisted_at || "—",
      ].forEach((value) => addCell(row, value));
      const reviewCell = addCell(row, item.review_state || "unreviewed");
      if (item.reviewed_by) {
        const meta = document.createElement("small");
        meta.textContent = `${item.reviewed_by} · ${item.reviewed_at || ""}`;
        reviewCell.append(document.createElement("br"), meta);
      }
      const controlCell = document.createElement("td");
      controlCell.appendChild(reviewControl(item, states));
      row.appendChild(controlCell);
      persistentBody.appendChild(row);
    });
    persistentBody.closest("table").hidden = entries.length === 0;
    persistentEmpty.hidden = entries.length > 0;
    persistentCount.textContent = `${history?.total_entries || 0} matching record(s)`;
    persistentPage = history?.pagination?.page || 1;
    pageStatus.textContent = `Page ${persistentPage} of ${history?.pagination?.page_count || 0}`;
    previousButton.disabled = !history?.pagination?.has_previous;
    nextButton.disabled = !history?.pagination?.has_next;
  };

  const persistentQuery = (page = persistentPage) => {
    const params = new URLSearchParams();
    const fields = {
      actor: document.getElementById("persistent-filter-actor").value.trim(),
      decision: document.getElementById("persistent-filter-decision").value,
      date_from: document.getElementById("persistent-filter-date-from").value,
      date_to: document.getElementById("persistent-filter-date-to").value,
      review_state: document.getElementById("persistent-filter-review-state").value,
      page_size: document.getElementById("persistent-page-size").value,
    };
    Object.entries(fields).forEach(([key, value]) => {
      if (value) params.set(key, value);
    });
    params.set("page", page);
    return params;
  };

  const refreshHistory = async () => {
    refreshButton.disabled = true;
    try {
      const response = await fetch(
        `/api/v1/case-intelligence-review/${encodeURIComponent(caseId)}/history`,
        { credentials: "same-origin", headers: { Accept: "application/json" } }
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

  const refreshPersistentHistory = async (page = persistentPage, quiet = false) => {
    persistentRefreshButton.disabled = true;
    try {
      const query = persistentQuery(page);
      const response = await fetch(
        `/api/v1/case-intelligence-review/${encodeURIComponent(caseId)}/decisions/persistent?${query.toString()}`,
        { credentials: "same-origin", headers: { Accept: "application/json" } }
      );
      if (!response.ok) {
        throw new Error(`durable history refresh failed (${response.status})`);
      }
      renderPersistentHistory(await response.json());
      if (!quiet) banner("success", "Persistent decision history refreshed.");
    } catch (error) {
      banner("error", error.message);
    } finally {
      persistentRefreshButton.disabled = false;
    }
  };

  const saveReviewState = async (row, button) => {
    const decisionRecordId = row.dataset.decisionRecordId;
    const reviewState = row.querySelector(".persistent-review-state").value;
    const note = row.querySelector(".persistent-review-note").value;
    button.disabled = true;
    try {
      const response = await fetch(
        `/api/v1/case-intelligence-review/${encodeURIComponent(caseId)}/decisions/${encodeURIComponent(decisionRecordId)}/review-state`,
        {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
            "X-CSRF-Token": csrfToken,
          },
          body: JSON.stringify({ review_state: reviewState, note }),
        }
      );
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.blockers?.[0]?.detail || "review state blocked");
      }
      await refreshPersistentHistory(persistentPage, true);
      banner("success", `Review state recorded: ${payload.review_state}`);
    } catch (error) {
      banner("error", error.message);
    } finally {
      button.disabled = false;
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
      persistentPage = 1;
      await refreshPersistentHistory(1, true);
      banner("success", `Decision recorded and persisted: ${payload.decision}`);
    } catch (error) {
      banner("error", error.message);
    } finally {
      decisionButton.disabled = false;
    }
  });

  persistentBody.addEventListener("click", (event) => {
    const button = event.target.closest(".save-persistent-review-state");
    if (!button) return;
    saveReviewState(button.closest("tr"), button);
  });
  refreshButton.addEventListener("click", refreshHistory);
  persistentRefreshButton.addEventListener("click", () =>
    refreshPersistentHistory(persistentPage)
  );
  applyFiltersButton.addEventListener("click", () => refreshPersistentHistory(1));
  clearFiltersButton.addEventListener("click", () => {
    [
      "persistent-filter-actor",
      "persistent-filter-decision",
      "persistent-filter-date-from",
      "persistent-filter-date-to",
      "persistent-filter-review-state",
    ].forEach((id) => {
      document.getElementById(id).value = "";
    });
    refreshPersistentHistory(1);
  });
  previousButton.addEventListener("click", () =>
    refreshPersistentHistory(Math.max(1, persistentPage - 1))
  );
  nextButton.addEventListener("click", () =>
    refreshPersistentHistory(persistentPage + 1)
  );
})();
