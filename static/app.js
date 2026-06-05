async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || 'Error desconocido');
  return data;
}

function fillResult(id, value) {
  document.getElementById(id).textContent = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
}

function formDataToObject(form) {
  return Object.fromEntries(new FormData(form).entries());
}

async function refreshInitiative(id) {
  const data = await api(`/api/initiatives/${encodeURIComponent(id)}`);
  fillResult('initiativeView', data);
}

document.getElementById('initiativeForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = formDataToObject(e.target);
  payload.deadline_days = Number(payload.deadline_days || 90);
  try {
    const data = await api('/api/initiatives', { method: 'POST', body: JSON.stringify(payload) });
    fillResult('initiativeCreated', data);
    document.getElementById('statusBox').textContent = 'Iniciativa creada correctamente.';
  } catch (err) { fillResult('initiativeCreated', err.message); }
});

document.getElementById('loadForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    await refreshInitiative(e.target.initiative_id.value);
    document.getElementById('statusBox').textContent = 'Iniciativa cargada.';
  } catch (err) { fillResult('initiativeView', err.message); }
});

async function handleJsonForm(formId, endpoint, successMsg) {
  document.getElementById(formId).addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = formDataToObject(e.target);
    const initiativeId = payload.initiative_id;
    delete payload.initiative_id;
    try {
      const data = await api(`/api/initiatives/${encodeURIComponent(initiativeId)}${endpoint}`, { method: 'POST', body: JSON.stringify(payload) });
      document.getElementById('statusBox').textContent = data.message || successMsg;
      await refreshInitiative(initiativeId);
    } catch (err) {
      document.getElementById('statusBox').textContent = err.message;
    }
  });
}

handleJsonForm('signatureForm', '/signatures', 'Firma agregada');
handleJsonForm('commentForm', '/comments', 'Comentario agregado');
handleJsonForm('modForm', '/modifications', 'Modificación agregada');
handleJsonForm('resourceForm', '/resources', 'Recurso agregado');

document.getElementById('freezeForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const id = e.target.initiative_id.value;
  try {
    const data = await api(`/api/initiatives/${encodeURIComponent(id)}/freeze`, { method: 'POST' });
    document.getElementById('statusBox').textContent = `${data.message}\nHash: ${data.frozen_hash}`;
    await refreshInitiative(id);
  } catch (err) { document.getElementById('statusBox').textContent = err.message; }
});

document.getElementById('submitForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const id = e.target.initiative_id.value;
  try {
    const data = await api(`/api/initiatives/${encodeURIComponent(id)}/submit`, { method: 'POST' });
    document.getElementById('statusBox').textContent = data.message;
    await refreshInitiative(id);
  } catch (err) { document.getElementById('statusBox').textContent = err.message; }
});
