(() => {
  const root = document.querySelector('[data-collaboration-requests-handoffs]');
  if (!root) return;

  const caseId = root.dataset.caseId;
  const csrf = root.dataset.csrfToken || '';
  const feedback = document.getElementById('v26-3-feedback');

  const show = (message, ok = true) => {
    if (!feedback) return;
    feedback.hidden = false;
    feedback.textContent = message;
    feedback.className = `flash ${ok ? 'success' : 'error'}`;
  };

  const postJson = async (url, payload) => {
    const response = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': csrf,
      },
      body: JSON.stringify(payload),
    });
    return { response, body: await response.json() };
  };

  document.getElementById('v26-3-create-request')?.addEventListener('click', async () => {
    const payload = {
      requested_from: document.getElementById('v26-3-requested-from')?.value || '',
      request_type: document.getElementById('v26-3-request-type')?.value || '',
      priority: document.getElementById('v26-3-request-priority')?.value || 'normal',
      due_at: document.getElementById('v26-3-request-due')?.value || null,
      reason: document.getElementById('v26-3-request-reason')?.value || '',
      confirmed: document.getElementById('v26-3-request-confirmed')?.checked === true,
    };
    const { response, body } = await postJson(
      `/api/v1/cases/${encodeURIComponent(caseId)}/collaboration-requests`,
      payload,
    );
    show(response.ok ? 'Review request recorded.' : `Request blocked: ${JSON.stringify(body)}`, response.ok);
    if (response.ok) window.location.reload();
  });

  document.getElementById('v26-3-create-handoff')?.addEventListener('click', async () => {
    const payload = {
      handoff_to: document.getElementById('v26-3-handoff-to')?.value || '',
      handoff_type: document.getElementById('v26-3-handoff-type')?.value || '',
      priority: document.getElementById('v26-3-handoff-priority')?.value || 'normal',
      due_at: document.getElementById('v26-3-handoff-due')?.value || null,
      reason: document.getElementById('v26-3-handoff-reason')?.value || '',
      confirmed: document.getElementById('v26-3-handoff-confirmed')?.checked === true,
    };
    const { response, body } = await postJson(
      `/api/v1/cases/${encodeURIComponent(caseId)}/collaboration-handoffs`,
      payload,
    );
    show(response.ok ? 'Task handoff recorded.' : `Handoff blocked: ${JSON.stringify(body)}`, response.ok);
    if (response.ok) window.location.reload();
  });
})();
