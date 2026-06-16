(() => {
  const root = document.querySelector('[data-collaboration-responses]');
  if (!root) return;
  const caseId = root.dataset.caseId;
  const csrf = root.dataset.csrfToken || '';
  const feedback = document.getElementById('v26-4-feedback');
  const show = (message, ok = true) => {
    if (!feedback) return;
    feedback.hidden = false;
    feedback.textContent = message;
    feedback.className = `flash ${ok ? 'success' : 'error'}`;
  };
  document.getElementById('v26-4-record-response')?.addEventListener('click', async () => {
    const payload = {
      target_type: document.getElementById('v26-4-target-type')?.value || '',
      target_id: document.getElementById('v26-4-target-id')?.value || '',
      response_type: document.getElementById('v26-4-response-type')?.value || '',
      resolution_code: document.getElementById('v26-4-resolution-code')?.value || null,
      reason: document.getElementById('v26-4-reason')?.value || '',
      unresolved_reason: document.getElementById('v26-4-unresolved-reason')?.value || null,
      confirmed: document.getElementById('v26-4-confirmed')?.checked === true,
    };
    const response = await fetch(`/api/v1/cases/${encodeURIComponent(caseId)}/collaboration-responses`, {
      method: 'POST', credentials: 'same-origin',
      headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf},
      body: JSON.stringify(payload),
    });
    const body = await response.json();
    document.getElementById('v26-4-output').textContent = JSON.stringify(body, null, 2);
    show(response.ok ? 'Collaboration response recorded.' : `Response blocked: ${JSON.stringify(body)}`, response.ok);
    if (response.ok) window.location.reload();
  });
})();
