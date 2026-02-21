const stateView = document.getElementById('stateView');

let wakeActiveUntil = 0;
let currentState = '';
let refreshInFlight = null;
let stateSocket = null;
let reconnectTimer = null;
let baseCountdownSeconds = null;
let wsConnected = false;
const baseViewCache = {
  nextPrayerLabel: null,
  progressBar: null,
  taskText: null,
  lastTaskText: '',
  lastNextPrayerText: '',
  lastProgressPercent: null,
};

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

function formatClock(totalSeconds) {
  const safe = Math.max(0, totalSeconds);
  const hh = Math.floor(safe / 3600);
  const mm = Math.floor((safe % 3600) / 60);
  return `${String(hh).padStart(2, '0')}${String(mm).padStart(2, '0')}`;
}

function applyPaletteFromModel(model) {
  const palette = model?.next_prayer?.palette;
  if (!palette) return;
  const root = document.documentElement;
  root.style.setProperty('--color-bg', String(palette.bg || ''));
  root.style.setProperty('--color-blob1', String(palette.blob1 || ''));
  root.style.setProperty('--color-blob2', String(palette.blob2 || ''));
  root.style.setProperty('--color-blob3', String(palette.blob3 || ''));
}

function updateDigit(id, newValue) {
  const container = document.getElementById(id);
  if (!container) return;
  const currentDigit = container.querySelector('.digit.in');

  if (currentDigit && currentDigit.innerText === newValue) return;

  const newDigit = document.createElement('div');
  newDigit.className = 'digit prepare';
  newDigit.innerText = newValue;
  container.appendChild(newDigit);

  void newDigit.offsetWidth;

  if (currentDigit) {
    currentDigit.classList.remove('in');
    currentDigit.classList.add('out');
    setTimeout(() => currentDigit.remove(), 800);
  }

  newDigit.classList.remove('prepare');
  newDigit.classList.add('in');
}

function updateJellyClock(clockDigits) {
  updateDigit('h1', clockDigits[0]);
  updateDigit('h2', clockDigits[1]);
  updateDigit('m1', clockDigits[2]);
  updateDigit('m2', clockDigits[3]);
}

function renderBase(model) {
  const progressPercent = Math.min(100, Math.max(0, Number(model.ramadan_progress_percent) || 0));
  return `<section class="base-screen" data-view="base_state">
    <div class="lava-background">
      <div class="blob"></div>
      <div class="blob"></div>
      <div class="blob"></div>
    </div>

    <div class="wake-frame"></div>

    <div class="progress-wrapper">
      <div class="progress-title">Рамадан</div>
      <div class="progress-container">
        <div class="progress-bar" id="progress-bar" style="width:${progressPercent}%"></div>
      </div>
    </div>

    <svg class="goo-filter" aria-hidden="true">
      <defs>
        <filter id="goo">
          <feGaussianBlur in="SourceGraphic" stdDeviation="15" result="blur" />
          <feColorMatrix in="blur" mode="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 25 -10" result="goo" />
          <feBlend in="SourceGraphic" in2="goo" />
        </filter>
      </defs>
    </svg>

    <div class="clock-container">
      <div class="next-prayer-label" id="nextPrayerLabel">До ${model.next_prayer.next}</div>
      <div class="clock" aria-label="countdown-clock">
        <div class="digit-box" id="h1"></div>
        <div class="digit-box" id="h2"></div>
        <div class="colon">:</div>
        <div class="digit-box" id="m1"></div>
        <div class="digit-box" id="m2"></div>
      </div>
    </div>

    <div class="task-container">
      <div class="task-label">Задание на сегодня · День ${model.day}</div>
      <div class="task-text" id="daily-task">${model.today_task}</div>
    </div>
  </section>`;
}

function renderTaskInfo(model) {
  const scores = model.closed
    ? `<div class="scores-line">${model.scores_line.map((item) => `<span>${item.child}: <span class="emoji-plain">${item.emoji}</span></span>`).join(' · ')}</div>`
    : '';
  return `<section class="task-info-screen" data-view="task_info_state">${asGlass(`<h1>${textGradient(`Задание дня ${model.day}`)}</h1><p class="large-copy">${textGradient(model.task_text)}</p>${scores}`)}</section>`;
}

function renderMap(model) {
  const circlesData = Array.isArray(model.circles) ? model.circles : [];
  const circles = circlesData.map((circle) => {
    const icon = circle.status === 'completed' ? '✓' : `День ${circle.day}`;
    const lock = circle.status === 'locked' && !circle.viewed ? '<span class="lock-overlay">🔒</span>' : '';
    return `<div class="note-wrap"><div data-day="${circle.day}" class="task-note ${circle.status} ${circle.selected ? 'selected' : ''}"><span class="pin-head" aria-hidden="true"></span><span class="note-icon">${icon}</span>${lock}</div></div>`;
  }).join('');
  const warning = model.warning ? `<div class="warning" id="mapWarning">${textGradient(model.warning)}</div>` : '<div class="warning" id="mapWarning"></div>';
  return `<section class="map-screen" data-view="tasks_map_state">${asGlass(`<div class="paper-board"><div class="grid">${circles}</div>${warning}</div>`)}</section>`;
}

function renderReview(model) {
  const done = model.completed ? `<h1>${textGradient('День завершен!')}</h1>` : '';
  const options = model.score_options.map((s) => `<div class="score">${s.emoji}<small>${textGradient(s.label)}</small></div>`).join('');
  return `<section class="review-screen" data-view="day_review_state">${asGlass(`<h2 id="reviewTaskText">${textGradient(model.task_text)}</h2><h1 id="reviewChildText">${textGradient(`Отвечает: ${model.child ?? '-'}`)}</h1><div class="score-row">${options}</div>${done}`)}</section>`;
}

function renderEid(model) {
  return `<section class="eid-screen" data-view="eid_state"><div class="confetti"></div>${asGlass(`<h1>${textGradient(model.message)}</h1>`)}</section>`;
}

function renderState(model) {
  if (model.view === 'base_state') return renderBase(model);
  if (model.view === 'task_info_state') return renderTaskInfo(model);
  if (model.view === 'tasks_map_state') return renderMap(model);
  if (model.view === 'day_review_state') return renderReview(model);
  if (model.view === 'eid_state') return renderEid(model);
  return `<section class="state-enter">${asGlass(`<h1>${textGradient('Неизвестный state')}</h1>`)}</section>`;
}

function patchBaseView(model) {
  baseViewCache.nextPrayerLabel = baseViewCache.nextPrayerLabel || document.getElementById('nextPrayerLabel');
  baseViewCache.progressBar = baseViewCache.progressBar || document.getElementById('progress-bar');
  baseViewCache.taskText = baseViewCache.taskText || document.getElementById('daily-task');

  const nextPrayerText = `До ${model.next_prayer.next}`;
  if (baseViewCache.nextPrayerLabel && baseViewCache.lastNextPrayerText !== nextPrayerText) {
    baseViewCache.nextPrayerLabel.textContent = nextPrayerText;
    baseViewCache.lastNextPrayerText = nextPrayerText;
  }

  if (baseViewCache.taskText && baseViewCache.lastTaskText !== model.today_task) {
    baseViewCache.taskText.textContent = model.today_task;
    baseViewCache.lastTaskText = model.today_task;
  }

  if (baseViewCache.progressBar) {
    const progressPercent = Math.min(100, Math.max(0, Number(model.ramadan_progress_percent) || 0));
    if (baseViewCache.lastProgressPercent !== progressPercent) {
      baseViewCache.progressBar.style.width = `${progressPercent}%`;
      baseViewCache.lastProgressPercent = progressPercent;
    }
  }

  applyPaletteFromModel(model);
  baseCountdownSeconds = parseCountdownToSeconds(model.next_prayer.countdown);
  updateJellyClock(formatClock(baseCountdownSeconds));
}

function patchMapView(model) {
  for (const circle of model.circles) {
    const node = stateView.querySelector(`.task-note[data-day="${circle.day}"]`);
    if (!node) continue;

    node.classList.toggle('completed', circle.status === 'completed');
    node.classList.toggle('open', circle.status === 'open');
    node.classList.toggle('locked', circle.status === 'locked');
    node.classList.toggle('selected', Boolean(circle.selected));

    const iconNode = node.querySelector('.note-icon');
    if (iconNode) iconNode.textContent = circle.status === 'completed' ? '✓' : `День ${circle.day}`;

    const existingLock = node.querySelector('.lock-overlay');
    const shouldLock = circle.status === 'locked' && !circle.viewed;
    if (shouldLock && !existingLock) {
      node.insertAdjacentHTML('beforeend', '<span class="lock-overlay">🔒</span>');
    }
    if (!shouldLock && existingLock) {
      existingLock.remove();
    }
  }

  const warningNode = document.getElementById('mapWarning');
  if (warningNode) {
    warningNode.innerHTML = model.warning ? textGradient(model.warning) : '';
  }
}

function patchReviewView(model) {
  const childText = document.getElementById('reviewChildText');
  if (childText) {
    childText.innerHTML = textGradient(`Отвечает: ${model.child ?? '-'}`);
  }
}

function patchCurrentView(model) {
  if (model.view === 'base_state') patchBaseView(model);
  if (model.view === 'tasks_map_state') patchMapView(model);
  if (model.view === 'day_review_state') patchReviewView(model);
}

function updateWakeBorder() {
  document.body.classList.toggle('wake-active', Date.now() < wakeActiveUntil);
}

function applyViewModel(model, { forceFullRender = false } = {}) {
  const stateChanged = currentState !== model.view;
  currentState = model.view;
  document.body.classList.toggle('base-active', model.view === 'base_state');

  if (forceFullRender || stateChanged || !stateView.firstElementChild) {
    stateView.innerHTML = renderState(model);
    baseViewCache.nextPrayerLabel = null;
    baseViewCache.progressBar = null;
    baseViewCache.taskText = null;
    baseViewCache.lastTaskText = '';
    baseViewCache.lastNextPrayerText = '';
    baseViewCache.lastProgressPercent = null;
    const section = stateView.querySelector('section');
    if (section) {
      section.classList.add('state-enter');
    }
    if (stateChanged) {
      document.body.classList.add('state-transitioning');
      setTimeout(() => document.body.classList.remove('state-transitioning'), 320);
    }
  }

  patchCurrentView(model);

  if (model.wake_active) {
    wakeActiveUntil = Date.now() + 6000;
  }

  updateWakeBorder();
}

async function refreshState(forceFullRender = false) {
  if (refreshInFlight) {
    return refreshInFlight;
  }

  refreshInFlight = (async () => {
    const response = await fetch('/api/state');
    const data = await response.json();
    applyViewModel(data.view_model, { forceFullRender });
  })();

  try {
    await refreshInFlight;
  } finally {
    refreshInFlight = null;
  }
}

function scheduleSocketReconnect() {
  if (reconnectTimer) return;
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    connectStateSocket();
  }, 1500);
}

function connectStateSocket() {
  if (stateSocket && (stateSocket.readyState === WebSocket.OPEN || stateSocket.readyState === WebSocket.CONNECTING)) {
    return;
  }

  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  stateSocket = new WebSocket(`${protocol}://${window.location.host}/ws/state`);

  stateSocket.addEventListener('open', () => {
    wsConnected = true;
  });

  stateSocket.addEventListener('message', (event) => {
    try {
      const data = JSON.parse(event.data);
      if (!data?.view_model) {
        refreshState().catch(() => {});
        return;
      }
      applyViewModel(data.view_model);
    } catch (_) {
      refreshState().catch(() => {});
    }
  });

  stateSocket.addEventListener('close', () => {
    wsConnected = false;
    stateSocket = null;
    scheduleSocketReconnect();
  });

  stateSocket.addEventListener('error', () => {
    wsConnected = false;
    stateSocket?.close();
  });
}

function fallbackRefreshTick() {
  if (wsConnected) return;
  refreshState().catch(() => {});
}

function tickBaseCountdown() {
  if (currentState !== 'base_state' || baseCountdownSeconds == null) {
    return;
  }
  baseCountdownSeconds = Math.max(0, baseCountdownSeconds - 1);
  updateJellyClock(formatClock(baseCountdownSeconds));
  if (baseCountdownSeconds === 0) {
    refreshState().catch(() => {});
  }
}

document.addEventListener('visibilitychange', () => {
  if (!document.hidden) {
    refreshState();
    connectStateSocket();
  }
});

setInterval(updateWakeBorder, 200);
refreshState(true);
connectStateSocket();
setInterval(tickBaseCountdown, 1000);
setInterval(fallbackRefreshTick, 3000);
