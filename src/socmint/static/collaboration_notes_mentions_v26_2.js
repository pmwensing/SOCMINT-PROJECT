(() => {
  const root = document.querySelector('[data-collaboration-notes]');
  if (!root) return;
  const caseId = root.dataset.caseId;
  const csrf = root.dataset.csrfToken || '';
  const feedback = document.getElementById('collaboration-note-feedback');
  const show = (message, ok = true) => {
    if (!feedback) return;
    feedback.hidden = false;
    feedback.textContent = message;
    feedback.className = `flash ${ok ? 'success' : 'error'}`;
  };
  const post = async (url, payload = {}) => {
    const response = await fetch(url, {
      method: 'POST', credentials: 'same-origin',
      headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf},
      body: JSON.stringify(payload),
    });
    return {response, body: await response.json()};
  };
  document.getElementById('record-collaboration-note')?.addEventListener('click', async () => {
    const mentions = (document.getElementById('collaboration-note-mentions')?.value || '').split(',').map(v => v.trim()).filter(Boolean);
    const payload = {
      body: document.getElementById('collaboration-note-body')?.value || '',
      target_type: document.getElementById('collaboration-note-target-type')?.value || 'case',
      target_id: document.getElementById('collaboration-note-target-id')?.value || null,
      mentioned_users: mentions,
      visibility: document.getElementById('collaboration-note-visibility')?.value || 'case_team',
      priority: document.getElementById('collaboration-note-priority')?.value || 'normal',
      acknowledgement_required: document.getElementById('collaboration-note-ack-required')?.checked === true,
      confirmed: document.getElementById('collaboration-note-confirmed')?.checked === true,
    };
    try {
      const {response, body} = await post(`/api/v1/cases/${encodeURIComponent(caseId)}/collaboration-notes`, payload);
      document.getElementById('collaboration-note-output').textContent = JSON.stringify(body, null, 2);
      show(response.ok ? 'Collaboration note recorded.' : 'Collaboration note was blocked.', response.ok);
      if (response.ok) window.location.reload();
    } catch (error) { show(`Note request failed: ${error}`, false); }
  });
  root.querySelectorAll('[data-action="correct-note"]').forEach(button => button.addEventListener('click', async () => {
    const body = window.prompt('Corrected note body:');
    if (!body) return;
    const reason = window.prompt('Reason for correction:');
    if (!reason) return;
    const {response, body: result} = await post(`/api/v1/cases/${encodeURIComponent(caseId)}/collaboration-notes/${encodeURIComponent(button.dataset.noteId)}/correct`, {body, reason, confirmed: true});
    show(response.ok ? 'Correction recorded.' : `Correction blocked: ${JSON.stringify(result)}`, response.ok);
    if (response.ok) window.location.reload();
  }));
  root.querySelectorAll('[data-action="ack-note"]').forEach(button => button.addEventListener('click', async () => {
    const responseText = window.prompt('Optional acknowledgement response:') || '';
    const {response, body} = await post(`/api/v1/cases/${encodeURIComponent(caseId)}/collaboration-notes/${encodeURIComponent(button.dataset.noteId)}/acknowledge`, {response: responseText, confirmed: true});
    show(response.ok ? 'Acknowledgement recorded.' : `Acknowledgement blocked: ${JSON.stringify(body)}`, response.ok);
    if (response.ok) window.location.reload();
  }));
  root.querySelectorAll('[data-action="read-note"]').forEach(button => button.addEventListener('click', async () => {
    const {response, body} = await post(`/api/v1/cases/${encodeURIComponent(caseId)}/collaboration-notes/${encodeURIComponent(button.dataset.noteId)}/read`);
    show(response.ok ? 'Note marked read.' : `Read update blocked: ${JSON.stringify(body)}`, response.ok);
    if (response.ok) window.location.reload();
  }));
})();
