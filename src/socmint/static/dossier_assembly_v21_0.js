(() => {
  "use strict";

  const root = document.querySelector("[data-dossier-assembly-workspace]");
  if (!root) return;

  const caseId = root.dataset.caseId;
  const csrfToken = root.dataset.csrfToken || "";
  const feedback = document.getElementById("dossier-assembly-feedback");
  const saveButton = document.getElementById("save-dossier-arrangement");

  const banner = (kind, message) => {
    feedback.hidden = false;
    feedback.className = `flash ${kind}`;
    feedback.textContent = message;
    feedback.focus({ preventScroll: true });
  };

  const collectArrangement = () => {
    const sections = [...document.querySelectorAll(".dossier-section")];
    const ordered = sections
      .map((section) => ({
        sectionId: section.dataset.sectionId,
        position: Number(section.querySelector(".section-position").value || 0),
      }))
      .sort((left, right) => left.position - right.position)
      .map((item) => item.sectionId);
    const narratives = {};
    const findingSections = {};

    sections.forEach((section) => {
      const sectionId = section.dataset.sectionId;
      narratives[sectionId] = section.querySelector(".section-narrative").value;
      section.querySelectorAll("tr[data-finding-id]").forEach((row) => {
        findingSections[row.dataset.findingId] = row.querySelector(
          ".finding-section-select"
        ).value;
      });
    });

    return {
      section_order: ordered,
      finding_sections: findingSections,
      narratives,
    };
  };

  saveButton.addEventListener("click", async () => {
    saveButton.disabled = true;
    try {
      const response = await fetch(
        `/api/v1/dossier-assembly/${encodeURIComponent(caseId)}/arrangement`,
        {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
            "X-CSRF-Token": csrfToken,
          },
          body: JSON.stringify(collectArrangement()),
        }
      );
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error || "arrangement save failed");
      }
      banner(
        "success",
        `Dossier arrangement saved: ${payload.arrangement_record_id}`
      );
      window.location.reload();
    } catch (error) {
      banner("error", error.message);
    } finally {
      saveButton.disabled = false;
    }
  });
})();
