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
  taskLabel: null,
  taskText: null,
  lastTaskText: '',
  lastTaskLabelText: '',
  lastNextPrayerText: '',
  lastProgressPercent: null,
};

function asGlass(content) {
  return `<div class="glass">${content}</div>`;
}

function textGradient(text) {
  return `<span class="water-text">${text}</span>`;
}


function taskTypeClass(taskType) {
  const normalized = String(taskType || '').trim().toLowerCase();
  if (normalized === 'сложное') return 'task-type-hard';
  if (normalized === 'литературный') return 'task-type-literary';
  if (normalized === 'общественный') return 'task-type-social';
  if (normalized === 'развлекательный') return 'task-type-fun';
  return '';
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
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
  const palette = model && model.next_prayer ? model.next_prayer.palette : null;
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
  const taskType = String(model.today_task_type || '').trim();
  const taskMeta = taskType ? ` · ${taskType}` : '';
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

    <div class="task-container ${taskTypeClass(model.today_task_type)}">
      <div class="task-label" id="daily-task-label">Задание на сегодня · День ${model.day}${taskMeta}</div>
      <div class="task-text" id="daily-task">${model.today_task}</div>
    </div>
  </section>`;
}

function renderTaskInfo(model) {
  const scores = model.closed
    ? `<div class="scores-line">${model.scores_line.map((item) => `<span>${item.child}: <span class="emoji-plain">${item.emoji}</span></span>`).join(' · ')}</div>`
    : '';
  return `<section class="task-info-screen" data-view="task_info_state">${asGlass(`<div class="task-glass ${taskTypeClass(model.task_type)}"><h1>${textGradient(`Задание дня ${model.day}`)}</h1><p class="large-copy">${textGradient(model.task_text)}</p>${scores}</div>`)}</section>`;
}

function renderMap(model) {
  const circlesData = Array.isArray(model.circles) ? model.circles : [];
  const circles = circlesData.map((circle) => {
    const safeText = escapeHtml(circle.task_text || '');
    const isLocked = circle.status === 'locked' || circle.status === 'closed';
    const isCompleted = circle.status === 'completed';
    const lock = '<svg class="lock-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 17a2 2 0 100-4 2 2 0 000 4z"/><path d="M18 10V7c0-3.3-2.7-6-6-6S6 3.7 6 7v3H5c-1.1 0-2 .9-2 2v8c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2v-8c0-1.1-.9-2-2-2h-1zm-6-7c2.2 0 4 1.8 4 4v3H8V7c0-2.2 1.8-4 4-4z"/></svg>';
    const check = '<svg class="check-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 13l4 4L19 7" stroke-linecap="round" stroke-linejoin="round"/></svg>';
    let content = `<div class="card-text">${safeText}</div>`;
    if (isLocked) {
      content = `${lock}<div class="skeleton-line"></div><div class="skeleton-line"></div>`;
    }
    if (isCompleted) {
      content = check;
    }
    const typeClass = taskTypeClass(circle.task_type);
    return `<article data-day="${circle.day}" class="task-card ${typeClass} ${isLocked ? 'locked' : circle.status} ${circle.selected ? 'selected' : ''}"><span class="pin" aria-hidden="true"></span><div class="day-number">${circle.day}</div><div class="card-content">${content}</div></article>`;
  }).join('');
  const warning = model.warning ? `<div class="warning" id="mapWarning">${textGradient(model.warning)}</div>` : '<div class="warning" id="mapWarning"></div>';
  return `<section class="map-screen" data-view="tasks_map_state"><div class="background-fix"></div><div class="chalkboard-overlay"></div><div class="wake-frame"></div><div class="tasks-grid">${circles}</div>${warning}</section>`;
}

function renderReview(model) {
  const done = model.completed ? `<h1>${textGradient('День завершен!')}</h1>` : '';
  const scoreSvg = (score) => {
    if (score === 1) {
      return '<svg class="score-icon score-icon-bad" viewBox="0 0 64 64" aria-hidden="true"><circle cx="32" cy="32" r="29"/><circle cx="22" cy="25" r="3.2"/><circle cx="42" cy="25" r="3.2"/><path d="M19 45c3.5-6 8.3-9 13-9s9.5 3 13 9"/></svg>';
    }
    if (score === 2) {
      return '<svg class="score-icon score-icon-mid" viewBox="0 0 64 64" aria-hidden="true"><circle cx="32" cy="32" r="29"/><circle cx="22" cy="25" r="3.2"/><circle cx="42" cy="25" r="3.2"/><path d="M19 41h26"/></svg>';
    }
    return '<svg class="score-icon score-icon-good" viewBox="0 0 64 64" aria-hidden="true"><circle cx="32" cy="32" r="29"/><circle cx="22" cy="25" r="3.2"/><circle cx="42" cy="25" r="3.2"/><path d="M19 39c3.5 6 8.3 9 13 9s9.5-3 13-9"/></svg>';
  };
  const options = model.score_options.map((s) => `<div class="score">${scoreSvg(s.score)}<small>${textGradient(s.label)}</small></div>`).join('');
  const childName = model.child == null ? '-' : model.child;
  return `<section class="review-screen" data-view="day_review_state">${asGlass(`<div class="task-glass ${taskTypeClass(model.task_type)}"><h2 id="reviewTaskText">${textGradient(model.task_text)}</h2><h1 id="reviewChildText">${textGradient(`Отвечает: ${childName}`)}</h1><div class="score-row">${options}</div>${done}</div>`)}</section>`;
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
  baseViewCache.taskLabel = baseViewCache.taskLabel || document.getElementById('daily-task-label');
  baseViewCache.taskText = baseViewCache.taskText || document.getElementById('daily-task');

  const nextPrayerText = `До ${model.next_prayer.next}`;
  if (baseViewCache.nextPrayerLabel && baseViewCache.lastNextPrayerText !== nextPrayerText) {
    baseViewCache.nextPrayerLabel.textContent = nextPrayerText;
    baseViewCache.lastNextPrayerText = nextPrayerText;
  }

  const taskType = String(model.today_task_type || '').trim();
  const taskMeta = taskType ? ` · ${taskType}` : '';
  const taskLabelText = `Задание на сегодня · День ${model.day}${taskMeta}`;
  if (baseViewCache.taskLabel && baseViewCache.lastTaskLabelText !== taskLabelText) {
    baseViewCache.taskLabel.textContent = taskLabelText;
    baseViewCache.lastTaskLabelText = taskLabelText;
  }

  if (baseViewCache.taskText && baseViewCache.lastTaskText !== model.today_task) {
    baseViewCache.taskText.textContent = model.today_task;
    baseViewCache.lastTaskText = model.today_task;
  }

  const taskContainer = stateView.querySelector('.task-container');
  if (taskContainer) {
    taskContainer.classList.remove('task-type-hard', 'task-type-literary', 'task-type-social', 'task-type-fun');
    const currentTypeClass = taskTypeClass(model.today_task_type);
    if (currentTypeClass) {
      taskContainer.classList.add(currentTypeClass);
    }
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
    const node = stateView.querySelector(`.task-card[data-day="${circle.day}"]`);
    if (!node) continue;

    const isLocked = circle.status === 'locked' || circle.status === 'closed';
    const isCompleted = circle.status === 'completed';

    node.classList.toggle('completed', isCompleted);
    node.classList.toggle('open', circle.status === 'open');
    node.classList.toggle('locked', isLocked);
    node.classList.toggle('selected', Boolean(circle.selected));

    node.classList.remove('task-type-hard', 'task-type-literary', 'task-type-social', 'task-type-fun');
    const currentTypeClass = taskTypeClass(circle.task_type);
    if (currentTypeClass) {
      node.classList.add(currentTypeClass);
    }

    const contentNode = node.querySelector('.card-content');
    if (contentNode) {
      const safeText = escapeHtml(circle.task_text || '');
      if (isCompleted) {
        contentNode.innerHTML = '<svg class="check-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 13l4 4L19 7" stroke-linecap="round" stroke-linejoin="round"/></svg>';
      } else if (isLocked) {
        contentNode.innerHTML = '<svg class="lock-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 17a2 2 0 100-4 2 2 0 000 4z"/><path d="M18 10V7c0-3.3-2.7-6-6-6S6 3.7 6 7v3H5c-1.1 0-2 .9-2 2v8c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2v-8c0-1.1-.9-2-2-2h-1zm-6-7c2.2 0 4 1.8 4 4v3H8V7c0-2.2 1.8-4 4-4z"/></svg><div class="skeleton-line"></div><div class="skeleton-line"></div>';
      } else {
        contentNode.innerHTML = `<div class="card-text">${safeText}</div>`;
      }
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
    const childName = model.child == null ? '-' : model.child;
    childText.innerHTML = textGradient(`Отвечает: ${childName}`);
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


let ambilightInFlight = false;

function parseCssColorToRgb(colorValue) {
  const source = String(colorValue || '').trim();
  const rgbaMatch = source.match(/rgba?\(([^)]+)\)/i);
  if (rgbaMatch) {
    const parts = rgbaMatch[1].split(',').map((v) => v.trim());
    const [r, g, b] = parts.slice(0, 3).map((v) => Math.max(0, Math.min(255, parseInt(v, 10) || 0)));
    const alpha = Math.max(0, Math.min(1, parseFloat(parts[3] || '1') || 0));
    return [r, g, b, alpha];
  }
  const hex = source.startsWith('#') ? source.slice(1) : '';
  if (hex.length === 3) {
    return [...hex.split('').map((c) => parseInt(`${c}${c}`, 16)), 1];
  }
  if (hex.length === 6) {
    return [parseInt(hex.slice(0, 2), 16), parseInt(hex.slice(2, 4), 16), parseInt(hex.slice(4, 6), 16), 1];
  }
  return [0, 0, 0, 0];
}

function resolveVisualColor(element) {
  let node = element;
  while (node && node !== document.documentElement) {
    const style = window.getComputedStyle(node);
    const [r, g, b, alpha] = parseCssColorToRgb(style.backgroundColor);
    if (alpha > 0.04) {
      return [r, g, b];
    }
    node = node.parentElement;
  }

  const [bodyR, bodyG, bodyB] = parseCssColorToRgb(window.getComputedStyle(document.body).backgroundColor);
  return [bodyR, bodyG, bodyB];
}

function samplePixelColorAt(x, y) {
  const clampedX = Math.max(0, Math.min(window.innerWidth - 1, Math.round(x)));
  const clampedY = Math.max(0, Math.min(window.innerHeight - 1, Math.round(y)));
  const element = document.elementFromPoint(clampedX, clampedY);
  if (!element) return [0, 0, 0];
  return resolveVisualColor(element);
}

function collectEdgeColors(samplesPerEdge = 18) {
  const width = Math.max(1, window.innerWidth);
  const height = Math.max(1, window.innerHeight);
  const edgePadding = 6;

  const top = [];
  const right = [];
  const bottom = [];
  const left = [];

  for (let i = 0; i < samplesPerEdge; i += 1) {
    const t = samplesPerEdge === 1 ? 0 : i / (samplesPerEdge - 1);
    const x = t * (width - 1);
    const y = t * (height - 1);

    top.push(samplePixelColorAt(x, edgePadding));
    right.push(samplePixelColorAt(width - edgePadding, y));
    bottom.push(samplePixelColorAt(x, height - edgePadding));
    left.push(samplePixelColorAt(edgePadding, y));
  }

  return { top, right, bottom, left, viewport: { width, height } };
}

async function pushAmbilightFrame() {
  if (ambilightInFlight || document.hidden) {
    return;
  }

  ambilightInFlight = true;
  try {
    const payload = collectEdgeColors(16);
    await fetch('/api/ambilight/frame', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  } catch (_) {
    // Ambilight is best-effort and should never break UI rendering.
  } finally {
    ambilightInFlight = false;
  }
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
setInterval(pushAmbilightFrame, 220);
