(() => {
  const root = document.querySelector('[data-case-team-role-assignment]');
  if (!root) return;

  const caseId = root.dataset.caseId;
  const csrf = root.dataset.csrfToken || '';
  const feedback = document.getElementById('case-team-feedback');

  const show = (message, ok = true) => {
    if (!feedback) return;
    feedback.hidden = false;
    feedback.textContent = message;
    feedback.className = `flash ${ok ? 'success' : 'error'}`;
  };

  const post = async (url, payload) => {
    const response = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': csrf,
      },
      body: JSON.stringify(payload),
    });
    const body = await response.json();
    return { response, body };
  };

  document.getElementById('record-case-team-assignment')?.addEventListener('click', async () => {
    const payload = {
      user_identity: document.getElementById('case-team-user')?.value || '',
      role: document.getElementById('case-team-role')?.value || '',
      reason: document.getElementById('case-team-reason')?.value || '',
      effective_from: document.getElementById('case-team-effective-from')?.value || null,
      effective_until: document.getElementById('case-team-effective-until')?.value || null,
      confirmed: document.getElementById('case-team-confirmed')?.checked === true,
    };
    const output = document.getElementById('case-team-assignment-output');
    try {
      const { response, body } = await post(`/api/v1/cases/${encodeURIComponent(caseId)}/team/assignments`, payload);
      if (output) output.textContent = JSON.stringify(body, null, 2);
      show(response.ok ? 'Case-team assignment recorded.' : 'Case-team assignment was blocked.', response.ok);
      if (response.ok) window.location.reload();
    } catch (error) {
      show(`Assignment request failed: ${error}`, false);
    }
  });

  root.querySelectorAll('[data-action="revoke-case-team-role"]').forEach((button) => {
    button.addEventListener('click', async () => {
      const assignmentId = button.dataset.assignmentId;
      const reason = window.prompt('Reason for revocation:');
      if (!reason) return;
      if (!window.confirm('Record an immutable role revocation event?')) return;
      try {
        const { response, body } = await post(
          `/api/v1/cases/${encodeURIComponent(caseId)}/team/assignments/${encodeURIComponent(assignmentId)}/revoke`,
          { reason, confirmed: true },
        );
        show(response.ok ? 'Role revocation recorded.' : `Revocation blocked: ${JSON.stringify(body.blockers || body)}`, response.ok);
        if (response.ok) window.location.reload();
      } catch (error) {
        show(`Revocation request failed: ${error}`, false);
      }
    });
  });
})();
