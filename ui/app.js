const stateView = document.getElementById('stateView');
const commandInput = document.getElementById('commandInput');
const payloadInput = document.getElementById('payloadInput');
const errorBox = document.getElementById('errorBox');

let wakeActiveUntil = 0;

function asGlass(content) {
  return `<div class="glass">${content}</div>`;
}

function renderBase(model) {
  const p = model.next_prayer.phase_progress;
  const hue = model.next_prayer.phase === 'day' ? (0 + p * 120) : (120 - p * 120);
  document.body.style.setProperty('--dynamic-hue', String(Math.round(hue)));

  return `<section class="base-screen">
      ${asGlass(`<div class="day-title">день ${model.day}</div><div class="progress"><span style="width:${model.month_progress * 100}%"></span></div>`) }
      ${asGlass(`<p>До ${model.next_prayer.next}</p><h1>${model.next_prayer.countdown}</h1><p>Сухур ${model.next_prayer.suhoor} · Ифтар ${model.next_prayer.iftar}</p>`) }
      ${asGlass(`<p>${model.today_task}</p>`) }
    </section>`;
}

function renderTaskInfo(model) {
  const scores = model.closed ? `<div>${model.scores_line.join(' · ')}</div>` : '';
  return `<section class="task-info-screen">${asGlass(`<h1>Задание дня ${model.day}</h1><p>${model.task_text}</p>${scores}`)}</section>`;
}

function renderMap(model) {
  const circles = model.circles.map((circle) => {
    const icon = circle.status === 'completed' ? '✓' : circle.day;
    return `<div class="circle ${circle.status} ${circle.selected ? 'selected' : ''}">${icon}</div>`;
  }).join('');
  const warning = model.warning ? `<div class="warning">${model.warning}</div>` : '';
  return `<section class="map-screen">${asGlass(`<div class="grid">${circles}</div>${warning}`)}</section>`;
}

function renderReview(model) {
  const done = model.completed ? '<h1>День завершен!</h1>' : '';
  const options = model.score_options.map((s) => `<div class="score">${s.emoji}<small>${s.label}</small></div>`).join('');
  return `<section class="review-screen">${asGlass(`<h2>${model.task_text}</h2><h1>Отвечает: ${model.child ?? '-'}</h1><div class="score-row">${options}</div>${done}`)}</section>`;
}

function renderEid(model) {
  return `<section class="eid-screen"><div class="confetti"></div>${asGlass(`<h1>${model.message}</h1>`)}</section>`;
}

function renderState(model) {
  if (model.view === 'base_state') return renderBase(model);
  if (model.view === 'task_info_state') return renderTaskInfo(model);
  if (model.view === 'tasks_map_state') return renderMap(model);
  if (model.view === 'day_review_state') return renderReview(model);
  if (model.view === 'eid_state') return renderEid(model);
  return '<section><h1>Неизвестный state</h1></section>';
}

function updateWakeBorder() {
  document.body.classList.toggle('wake-active', Date.now() < wakeActiveUntil);
}

async function refreshState() {
  const response = await fetch('/api/state');
  const data = await response.json();
  stateView.innerHTML = renderState(data.view_model);
  updateWakeBorder();
}

async function sendCommand() {
  errorBox.textContent = '';
  const command = commandInput.value.trim();
  if (!command) {
    errorBox.textContent = 'Введите команду';
    return;
  }

  let payload = null;
  if (payloadInput.value.trim()) {
    try { payload = JSON.parse(payloadInput.value.trim()); } catch {
      errorBox.textContent = 'Payload должен быть JSON';
      return;
    }
  }

  wakeActiveUntil = Date.now() + 6000;
  updateWakeBorder();

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
  stateView.innerHTML = renderState(data.view_model);
}

document.getElementById('sendBtn').addEventListener('click', sendCommand);
refreshState();
setInterval(refreshState, 1000);
