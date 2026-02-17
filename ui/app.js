const stateView = document.getElementById('stateView');
const commandInput = document.getElementById('commandInput');
const payloadInput = document.getElementById('payloadInput');
const errorBox = document.getElementById('errorBox');
const wakeBtn = document.getElementById('wakeBtn');

let wakeActiveUntil = 0;
let refreshTimer = null;
let baseTickTimer = null;
let currentState = '';
let lastModelSignature = '';
let baseRuntime = null;

function asGlass(content) {
  return `<div class="glass">${content}</div>`;
}

function textGradient(text) {
  return `<span class="water-text">${text}</span>`;
}

function parseCountdownToSeconds(value) {
  const [h, m, s] = String(value || '00:00:00').split(':').map((x) => parseInt(x, 10) || 0);
  return h * 3600 + m * 60 + s;
}

function formatCountdown(totalSeconds) {
  const safe = Math.max(0, totalSeconds);
  const hh = Math.floor(safe / 3600);
  const mm = Math.floor((safe % 3600) / 60);
  const ss = safe % 60;
  return `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}`;
}

function renderBase(model) {
  const p = model.next_prayer.phase_progress;
  const hue = model.next_prayer.phase === 'day' ? (12 + p * 110) : (122 - p * 110);
  document.body.style.setProperty('--dynamic-hue', String(Math.round(hue)));

  return `<section class="base-screen state-enter">
      ${asGlass(`<div class="day-title">${textGradient(`день ${model.day}`)}</div><div class="progress"><span id="monthProgressBar" style="width:${model.month_progress * 100}%"></span></div>`)}
      ${asGlass(`<p id="nextPrayerLabel">${textGradient(`До ${model.next_prayer.next}`)}</p><h1 id="countdownClock" class="liquid-clock">${textGradient(model.next_prayer.countdown)}</h1><p>${textGradient(`Сухур ${model.next_prayer.suhoor} · Ифтар ${model.next_prayer.iftar}`)}</p>`)}
      ${asGlass(`<p class="large-copy">${textGradient(model.today_task)}</p>`)}
    </section>`;
}

function renderTaskInfo(model) {
  const scores = model.closed
    ? `<div class="scores-line">${model.scores_line.map((item) => `<span>${item.child}: <span class="emoji-plain">${item.emoji}</span></span>`).join(' · ')}</div>`
    : '';
  return `<section class="task-info-screen state-enter">${asGlass(`<h1>${textGradient(`Задание дня ${model.day}`)}</h1><p class="large-copy">${textGradient(model.task_text)}</p>${scores}`)}</section>`;
}

function renderMap(model) {
  const circles = model.circles.map((circle) => {
    const icon = circle.status === 'completed' ? '✓' : circle.day;
    const lock = circle.status === 'locked' && !circle.viewed ? '<span class="lock-overlay">🔒</span>' : '';
    return `<div class="circle-wrap"><div class="circle ${circle.status} ${circle.selected ? 'selected' : ''}"><span>${icon}</span>${lock}</div></div>`;
  }).join('');
  const warning = model.warning ? `<div class="warning">${textGradient(model.warning)}</div>` : '';
  return `<section class="map-screen state-enter">${asGlass(`<div class="grid">${circles}</div>${warning}`)}</section>`;
}

function renderReview(model) {
  const done = model.completed ? `<h1>${textGradient('День завершен!')}</h1>` : '';
  const options = model.score_options.map((s) => `<div class="score">${s.emoji}<small>${textGradient(s.label)}</small></div>`).join('');
  return `<section class="review-screen state-enter">${asGlass(`<h2>${textGradient(model.task_text)}</h2><h1>${textGradient(`Отвечает: ${model.child ?? '-'}`)}</h1><div class="score-row">${options}</div>${done}`)}</section>`;
}

function renderEid(model) {
  return `<section class="eid-screen state-enter"><div class="confetti"></div>${asGlass(`<h1>${textGradient(model.message)}</h1>`)}</section>`;
}

function renderState(model) {
  if (model.view === 'base_state') return renderBase(model);
  if (model.view === 'task_info_state') return renderTaskInfo(model);
  if (model.view === 'tasks_map_state') return renderMap(model);
  if (model.view === 'day_review_state') return renderReview(model);
  if (model.view === 'eid_state') return renderEid(model);
  return `<section class="state-enter">${asGlass(`<h1>${textGradient('Неизвестный state')}</h1>`)}</section>`;
}

function updateWakeBorder() {
  document.body.classList.toggle('wake-active', Date.now() < wakeActiveUntil);
}

function stopBaseTicker() {
  if (baseTickTimer) {
    clearInterval(baseTickTimer);
    baseTickTimer = null;
  }
  baseRuntime = null;
}

function startBaseTicker(model) {
  stopBaseTicker();

  const countdownSeconds = parseCountdownToSeconds(model.next_prayer.countdown);
  baseRuntime = {
    day: model.day,
    startMonthProgress: Number(model.month_progress || 0),
    startedAt: Date.now(),
    endAt: Date.now() + countdownSeconds * 1000,
    phase: model.next_prayer.phase,
    phaseProgressAtStart: Number(model.next_prayer.phase_progress || 0),
    phaseTotalSeconds: Math.max(1, Number(model.next_prayer.phase_total_seconds || 1)),
  };

  baseTickTimer = setInterval(() => {
    if (currentState !== 'base_state' || !baseRuntime) return;

    const now = Date.now();
    const secondsLeft = Math.max(0, Math.ceil((baseRuntime.endAt - now) / 1000));
    const clock = document.getElementById('countdownClock');
    if (clock) {
      clock.innerHTML = textGradient(formatCountdown(secondsLeft));
      clock.classList.remove('tick-bump');
      void clock.offsetWidth;
      clock.classList.add('tick-bump');
    }

    const elapsedDayShare = (now - baseRuntime.startedAt) / 1000 / 86400 / 30;
    const progress = Math.min(1, baseRuntime.startMonthProgress + elapsedDayShare);
    const progressBar = document.getElementById('monthProgressBar');
    if (progressBar) {
      progressBar.style.width = `${(progress * 100).toFixed(4)}%`;
    }

    const phaseProgressDelta = ((now - baseRuntime.startedAt) / 1000) / baseRuntime.phaseTotalSeconds;
    const phaseProgressNow = Math.max(0, Math.min(1, baseRuntime.phaseProgressAtStart + phaseProgressDelta));
    const hue = baseRuntime.phase === 'day' ? (12 + phaseProgressNow * 110) : (122 - phaseProgressNow * 110);
    document.body.style.setProperty('--dynamic-hue', String(Math.round(hue)));
  }, 1000);
}

function animateDynamicHueOutsideBase() {
  if (currentState === 'base_state') return;
  const now = new Date();
  const seconds = now.getHours() * 3600 + now.getMinutes() * 60 + now.getSeconds();
  const hue = 20 + Math.round((seconds / 86400) * 120);
  document.body.style.setProperty('--dynamic-hue', String(hue));
}

function getModelSignature(model) {
  return JSON.stringify({
    view: model.view,
    day: model.day,
    child: model.child,
    selected_day: model.selected_day,
    current_day: model.current_day,
    warning: model.warning,
    countdown: model.next_prayer?.countdown,
    month_progress: model.month_progress,
    today_task: model.today_task,
    circles: model.circles,
    task_text: model.task_text,
    scores_line: model.scores_line,
    completed: model.completed,
  });
}

function applyViewModel(model, { force = false } = {}) {
  const stateChanged = currentState && currentState !== model.view;
  const modelSignature = getModelSignature(model);
  const shouldRerender = force || stateChanged || modelSignature !== lastModelSignature;

  currentState = model.view;
  if (shouldRerender) {
    stateView.innerHTML = renderState(model);
    lastModelSignature = modelSignature;
    if (stateChanged) {
      document.body.classList.add('state-transitioning');
      setTimeout(() => document.body.classList.remove('state-transitioning'), 350);
    }
  }

  if (model.view === 'base_state') {
    startBaseTicker(model);
  } else {
    stopBaseTicker();
  }

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
  const delay = stateName === 'base_state' ? 15000 : 12000;
  refreshTimer = setTimeout(refreshState, delay);
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
    body: JSON.stringify({ source: 'manual' }),
  });
  const data = await response.json();
  applyViewModel(data.view_model, { force: true });
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
    try {
      payload = JSON.parse(payloadInput.value.trim());
    } catch {
      errorBox.textContent = 'Payload должен быть JSON';
      return;
    }
  }

  const response = await fetch('/api/command', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ command, payload, source: 'manual', wake_word_detected: false }),
  });

  const data = await response.json();
  if (!response.ok) {
    errorBox.textContent = data.detail || 'Ошибка команды';
    return;
  }

  applyViewModel(data.view_model, { force: true });
}

document.getElementById('sendBtn').addEventListener('click', sendCommand);
wakeBtn.addEventListener('click', sendWake);
document.addEventListener('visibilitychange', () => {
  if (!document.hidden) {
    refreshState();
  }
});

setInterval(updateWakeBorder, 200);
setInterval(animateDynamicHueOutsideBase, 1000);
refreshState();
