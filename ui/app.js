const stateView = document.getElementById('stateView');
const commandInput = document.getElementById('commandInput');
const payloadInput = document.getElementById('payloadInput');
const errorBox = document.getElementById('errorBox');
const wakeBtn = document.getElementById('wakeBtn');

let wakeActiveUntil = 0;
let refreshTimer = null;

function asGlass(content) {
  return `<div class="glass">${content}</div>`;
}

function textGradient(text) {
  return `<span class="water-text">${text}</span>`;
}

function renderBase(model) {
  const p = model.next_prayer.phase_progress;
  const hue = model.next_prayer.phase === 'day' ? (0 + p * 120) : (120 - p * 120);
  document.body.style.setProperty('--dynamic-hue', String(Math.round(hue)));

  return `<section class="base-screen">
      ${asGlass(`<div class="day-title">${textGradient(`день ${model.day}`)}</div><div class="progress"><span style="width:${model.month_progress * 100}%"></span></div>`)}
      ${asGlass(`<p>${textGradient(`До ${model.next_prayer.next}`)}</p><h1>${textGradient(model.next_prayer.countdown)}</h1><p>${textGradient(`Сухур ${model.next_prayer.suhoor} · Ифтар ${model.next_prayer.iftar}`)}</p>`)}
      ${asGlass(`<p class="large-copy">${textGradient(model.today_task)}</p>`)}
    </section>`;
}

function renderTaskInfo(model) {
  const scores = model.closed ? `<div>${textGradient(model.scores_line.join(' · '))}</div>` : '';
  return `<section class="task-info-screen">${asGlass(`<h1>${textGradient(`Задание дня ${model.day}`)}</h1><p class="large-copy">${textGradient(model.task_text)}</p>${scores}`)}</section>`;
}

function renderMap(model) {
  const circles = model.circles.map((circle) => {
    const icon = circle.status === 'completed' ? '✓' : circle.day;
    return `<div class="circle ${circle.status} ${circle.selected ? 'selected' : ''}">${icon}</div>`;
  }).join('');
  const warning = model.warning ? `<div class="warning">${textGradient(model.warning)}</div>` : '';
  return `<section class="map-screen">${asGlass(`<div class="grid">${circles}</div>${warning}`)}</section>`;
}

function renderReview(model) {
  const done = model.completed ? `<h1>${textGradient('День завершен!')}</h1>` : '';
  const options = model.score_options.map((s) => `<div class="score">${s.emoji}<small>${textGradient(s.label)}</small></div>`).join('');
  return `<section class="review-screen">${asGlass(`<h2>${textGradient(model.task_text)}</h2><h1>${textGradient(`Отвечает: ${model.child ?? '-'}`)}</h1><div class="score-row">${options}</div>${done}`)}</section>`;
}

function renderEid(model) {
  return `<section class="eid-screen"><div class="confetti"></div>${asGlass(`<h1>${textGradient(model.message)}</h1>`)}</section>`;
}

function renderState(model) {
  if (model.view === 'base_state') return renderBase(model);
  if (model.view === 'task_info_state') return renderTaskInfo(model);
  if (model.view === 'tasks_map_state') return renderMap(model);
  if (model.view === 'day_review_state') return renderReview(model);
  if (model.view === 'eid_state') return renderEid(model);
  return `<section>${asGlass(`<h1>${textGradient('Неизвестный state')}</h1>`)}</section>`;
}

function updateWakeBorder() {
  document.body.classList.toggle('wake-active', Date.now() < wakeActiveUntil);
}

function applyViewModel(model) {
  stateView.innerHTML = renderState(model);
  if (model.wake_active) {
    wakeActiveUntil = Date.now() + 6000;
  }
  updateWakeBorder();
  scheduleRefresh(model.view);
}

function scheduleRefresh(stateName) {
  if (refreshTimer) {
    clearTimeout(refreshTimer);
    refreshTimer = null;
  }

  if (stateName === 'base_state') {
    refreshTimer = setTimeout(refreshState, 60000);
  }
}

async function refreshState() {
  const response = await fetch('/api/state');
  const data = await response.json();
  applyViewModel(data.view_model);
}

async function sendWake() {
  const response = await fetch('/api/wake', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source: 'manual' })
  });
  const data = await response.json();
  applyViewModel(data.view_model);
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

  const response = await fetch('/api/command', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ command, payload, source: 'manual', wake_word_detected: false })
  });

  const data = await response.json();
  if (!response.ok) {
    errorBox.textContent = data.detail || 'Ошибка команды';
    return;
  }

  applyViewModel(data.view_model);
}

document.getElementById('sendBtn').addEventListener('click', sendCommand);
wakeBtn.addEventListener('click', sendWake);
document.addEventListener('visibilitychange', () => {
  if (!document.hidden) {
    refreshState();
  }
});

setInterval(updateWakeBorder, 200);
refreshState();
