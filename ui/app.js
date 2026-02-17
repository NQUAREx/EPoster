const stateName = document.getElementById('stateName');
const viewModelBox = document.getElementById('viewModelBox');
const stateView = document.getElementById('stateView');
const commandInput = document.getElementById('commandInput');
const payloadInput = document.getElementById('payloadInput');
const errorBox = document.getElementById('errorBox');
const quickButtons = document.getElementById('quickButtons');

const quickCommands = [
  'open_map',
  'open_summary',
  'open_settings',
  'back',
  'finish_day',
  'next_day',
  'restart'
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

function formatPairs(obj) {
  if (!obj) return '<p>Нет данных.</p>';
  return Object.entries(obj)
    .map(([key, value]) => `<span class="pill">${key}: ${value === null ? '—' : value}</span>`)
    .join('');
}

function renderStateView(model) {
  if (!model) {
    stateView.innerHTML = '<p>Нет данных состояния.</p>';
    return;
  }

  if (model.view === 'day_review') {
    stateView.innerHTML = `<p>День: <b>${model.day}</b></p><p>Задание: ${model.task.text}</p>${formatPairs(model.scores)}`;
    return;
  }
  if (model.view === 'task_map') {
    stateView.innerHTML = `<p>День: <b>${model.day}</b>, можно закрыть: <b>${model.can_close_day}</b></p>${formatPairs(model.scores)}`;
    return;
  }
  if (model.view === 'summary') {
    stateView.innerHTML = `<p>Сводка дня ${model.day}</p><h3>Сумма баллов</h3>${formatPairs(model.totals)}`;
    return;
  }
  if (model.view === 'settings') {
    stateView.innerHTML = `<p>Язык: ${model.language}</p><p>Секретная команда: ${model.secret_celebration_command}</p>`;
    return;
  }
  if (model.view === 'celebration') {
    stateView.innerHTML = `<h3>${model.message}</h3>${formatPairs(model.totals)}`;
    return;
  }

  stateView.innerHTML = '<p>Неизвестное состояние.</p>';
}

async function refreshState() {
  errorBox.textContent = '';
  const response = await fetch('/api/state');
  const data = await response.json();
  stateName.textContent = data.state;
  viewModelBox.textContent = JSON.stringify(data.view_model, null, 2);
  renderStateView(data.view_model);
}

async function sendCommand(forcedCommand = null) {
  errorBox.textContent = '';
  const command = forcedCommand || commandInput.value.trim();
  if (!command) {
    errorBox.textContent = 'Введите command';
    return;
  }

  let payload = null;
  const payloadRaw = payloadInput.value.trim();
  if (payloadRaw) {
    try {
      payload = JSON.parse(payloadRaw);
    } catch (error) {
      errorBox.textContent = 'Payload должен быть валидным JSON';
      return;
    }
  }

  const response = await fetch('/api/command', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ command, payload }),
  });

  const data = await response.json();
  if (!response.ok) {
    errorBox.textContent = data.error || 'Ошибка команды';
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
