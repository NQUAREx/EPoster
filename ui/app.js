const stateName = document.getElementById('stateName');
const viewModelBox = document.getElementById('viewModelBox');
const stateView = document.getElementById('stateView');
const commandInput = document.getElementById('commandInput');
const payloadInput = document.getElementById('payloadInput');
const errorBox = document.getElementById('errorBox');
const quickButtons = document.getElementById('quickButtons');

const quickCommands = [
  'start_day_review',
  'set_score',
  'open_map',
  'open_summary',
  'open_settings',
  'next_day',
  'back'
];

function renderQuickButtons() {
  quickButtons.innerHTML = '';
  for (const command of quickCommands) {
    const button = document.createElement('button');
    button.className = 'btn secondary';
    button.textContent = command;
    button.addEventListener('click', () => sendCommand(command));
    quickButtons.appendChild(button);
  }
}

function pills(map) {
  return Object.entries(map || {})
    .map(([key, value]) => `<span class="pill">${key}: ${value ?? '—'}</span>`)
    .join('');
}

function renderStateView(model) {
  if (!model) {
    stateView.innerHTML = '<p>Нет данных состояния.</p>';
    return;
  }

  if (model.view === 'base') {
    stateView.innerHTML = `
      <h2>Домашний экран</h2>
      <p>День: <b>${model.day}</b></p>
      <p>До сухура: <b>${model.time_to_suhur}</b></p>
      <p>До ифтара: <b>${model.time_to_iftar}</b></p>
      <p>Задание на сегодня: ${model.today_task}</p>
    `;
    return;
  }

  if (model.view === 'day_review') {
    stateView.innerHTML = `
      <div class="full-screen-card">
        <p class="label">День ${model.day}</p>
        <h2>${model.active_child ?? 'Проверка завершена'}</h2>
        <p>${model.task.text}</p>
        <p>Порядок: ${model.review_order.join(' → ')}</p>
        <div>${pills(model.scores)}</div>
      </div>
    `;
    return;
  }

  if (model.view === 'task_map') {
    stateView.innerHTML = `<h2>Карта дня</h2><p>День: ${model.day}</p><div>${pills(model.scores)}</div>`;
    return;
  }

  if (model.view === 'summary') {
    stateView.innerHTML = `<h2>Сводка дня ${model.day}</h2><div>${pills(model.totals)}</div>`;
    return;
  }

  if (model.view === 'settings') {
    stateView.innerHTML = `<h2>Настройки</h2><p>Язык: русский</p><p>Секретная команда: ${model.secret_celebration_command}</p>`;
    return;
  }

  if (model.view === 'celebration') {
    stateView.innerHTML = `<h2>${model.message}</h2><div>${pills(model.totals)}</div>`;
  }
}

async function refreshState() {
  errorBox.textContent = '';
  const response = await fetch('/api/state');
  const data = await response.json();
  stateName.textContent = data.state;
  viewModelBox.textContent = JSON.stringify(data.view_model, null, 2);
  renderStateView(data.view_model);
}

async function sendCommand(forced = null) {
  errorBox.textContent = '';
  const command = forced || commandInput.value.trim();
  if (!command) {
    errorBox.textContent = 'Введите command';
    return;
  }

  let payload = null;
  const payloadRaw = payloadInput.value.trim();
  if (payloadRaw) {
    try {
      payload = JSON.parse(payloadRaw);
    } catch {
      errorBox.textContent = 'Payload должен быть валидным JSON';
      return;
    }
  }

  if (command === 'set_score' && !payload) {
    payload = { score: 3 };
  }

  const response = await fetch('/api/command', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ command, payload })
  });

  const data = await response.json();
  if (!response.ok) {
    errorBox.textContent = data.detail || 'Ошибка команды';
    return;
  }

  stateName.textContent = data.state;
  viewModelBox.textContent = JSON.stringify(data.view_model, null, 2);
  renderStateView(data.view_model);
}

document.getElementById('sendBtn').addEventListener('click', () => sendCommand());
document.getElementById('refreshBtn').addEventListener('click', refreshState);

renderQuickButtons();
refreshState();
