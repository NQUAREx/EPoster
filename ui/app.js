const stateView = document.getElementById('stateView');

let wakeActiveUntil = 0;
let wakeSync = null;
let wakeAnimationFrame = null;
let currentState = '';
let refreshInFlight = null;
let stateSocket = null;
let reconnectTimer = null;
let baseCountdownSeconds = null;
let wsConnected = false;
let appInstanceId = null;
let reloadInProgress = false;
let backendUnreachableSince = null;
let deployNoticeVisible = false;
let refreshFailCount = 0;
const DEPLOY_NOTICE_DELAY_MS = 2500;
const baseViewCache = {
  nextPrayerLabel: null,
  progressTitle: null,
  progressBar: null,
  taskLabel: null,
  taskText: null,
  lastTaskText: '',
  lastTaskLabelText: '',
  lastNextPrayerText: '',
  lastProgressTitleText: '',
  lastProgressPercent: null,
};

function asGlass(content) {
  return `<div class="glass">${content}</div>`;
}

function textGradient(text) {
  return `<span class="water-text">${text}</span>`;
}

function asWakeFrame() {
  return '<div class="wake-frame"></div>';
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

function formatRamadanTitle(progressPercent) {
  return `Рамадан · ${progressPercent.toFixed(3)}%`;
}

function renderBase(model) {
  const progressPercent = Math.min(100, Math.max(0, Number(model.ramadan_progress_percent) || 0));
  const taskType = String(model.today_task_type || '').trim();
  const taskMeta = taskType ? ` · ${taskType}` : '';
  const nextPrayerSourceDate = model.next_prayer.source_date || '—';
  const nextPrayerText = `До ${model.next_prayer.next}`;
  return `<section class="base-screen" data-view="base_state">
    <div class="lava-background">
      <div class="blob"></div>
      <div class="blob"></div>
      <div class="blob"></div>
    </div>

    <div class="wake-frame"></div>

    <div class="progress-wrapper">
      <div class="progress-title" id="progress-title">${formatRamadanTitle(progressPercent)}</div>
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
      <div class="next-prayer-label" id="nextPrayerLabel">
        <span class="next-prayer-source-date">${nextPrayerSourceDate}</span>
        <span class="next-prayer-divider" aria-hidden="true">·</span>
        <span class="next-prayer-main-text">${nextPrayerText}</span>
      </div>
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
  return `<section class="task-info-screen" data-view="task_info_state">${asWakeFrame()}${asGlass(`<div class="task-glass ${taskTypeClass(model.task_type)}"><h1>${textGradient(`Задание дня ${model.day}`)}</h1><p class="large-copy">${textGradient(model.task_text)}</p>${scores}</div>`)}</section>`;
}


function renderCalibration(model) {
  const color = model.screen_color_css || 'rgb(0, 0, 0)';
  const step = Number(model.step || 1);
  const total = Number(model.total_steps || 1);
  return `<section class="calibration-screen" data-view="calibration_state" style="--calibration-color:${color}">
    <div class="calibration-color"></div>
    <div class="calibration-panel">
      <h1>${escapeHtml(model.title || 'Калибровка')}</h1>
      <p>Шаг ${step} / ${total}</p>
      <p>${escapeHtml(model.hint || '')}</p>
      <p>Цвет: ${escapeHtml(color)}</p>
    </div>
  </section>`;
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
  return `<section class="map-screen" data-view="tasks_map_state"><div class="background-fix"></div><div class="chalkboard-overlay"></div>${asWakeFrame()}<div class="tasks-grid">${circles}</div>${warning}</section>`;
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
    if (score === null) {
      return '<svg class="score-icon score-icon-skip" viewBox="0 0 64 64" aria-hidden="true"><circle cx="32" cy="32" r="29"/><path d="M20 22l14 10-14 10z"/><path d="M36 22l14 10-14 10z"/><path d="M50 20v24"/></svg>';
    }
    return '<svg class="score-icon score-icon-good" viewBox="0 0 64 64" aria-hidden="true"><circle cx="32" cy="32" r="29"/><circle cx="22" cy="25" r="3.2"/><circle cx="42" cy="25" r="3.2"/><path d="M19 39c3.5 6 8.3 9 13 9s9.5-3 13-9"/></svg>';
  };
  const options = model.score_options.map((s) => `<div class="score">${scoreSvg(s.score)}<small>${textGradient(s.label)}</small></div>`).join('');
  const childName = model.child == null ? '-' : model.child;
  return `<section class="review-screen" data-view="day_review_state">${asWakeFrame()}${asGlass(`<div class="task-glass ${taskTypeClass(model.task_type)}"><h2 id="reviewTaskText">${textGradient(model.task_text)}</h2><h1 id="reviewChildText">${textGradient(`Отвечает: ${childName}`)}</h1><div class="score-row">${options}</div>${done}</div>`)}</section>`;
}

function renderEid(model) {
  return `<section class="eid-screen" data-view="eid_state"><div class="confetti"></div>${asWakeFrame()}${asGlass(`<h1>${textGradient(model.message)}</h1>`)}</section>`;
}

function extractViewModel(apiPayload) {
  if (!apiPayload || typeof apiPayload !== 'object') return null;
  if (apiPayload.view_model && typeof apiPayload.view_model === 'object') return apiPayload.view_model;
  if (apiPayload.view && typeof apiPayload.view === 'string') return apiPayload;
  return null;
}

function renderState(model) {
  if (model.view === 'base_state') return renderBase(model);
  if (model.view === 'task_info_state') return renderTaskInfo(model);
  if (model.view === 'tasks_map_state') return renderMap(model);
  if (model.view === 'day_review_state') return renderReview(model);
  if (model.view === 'calibration_state') return renderCalibration(model);
  if (model.view === 'eid_state') return renderEid(model);
  return `<section class="state-enter">${asGlass(`<h1>${textGradient('Неизвестный state')}</h1>`)}</section>`;
}

function patchBaseView(model) {
  baseViewCache.nextPrayerLabel = baseViewCache.nextPrayerLabel || document.getElementById('nextPrayerLabel');
  baseViewCache.progressTitle = baseViewCache.progressTitle || document.getElementById('progress-title');
  baseViewCache.progressBar = baseViewCache.progressBar || document.getElementById('progress-bar');
  baseViewCache.taskLabel = baseViewCache.taskLabel || document.getElementById('daily-task-label');
  baseViewCache.taskText = baseViewCache.taskText || document.getElementById('daily-task');

  const nextPrayerSourceDate = model.next_prayer.source_date || '—';
  const nextPrayerText = `До ${model.next_prayer.next}`;
  const nextPrayerLabelText = `${nextPrayerSourceDate} · ${nextPrayerText}`;
  if (baseViewCache.nextPrayerLabel && baseViewCache.lastNextPrayerText !== nextPrayerLabelText) {
    baseViewCache.nextPrayerLabel.innerHTML = `<span class="next-prayer-source-date">${escapeHtml(nextPrayerSourceDate)}</span><span class="next-prayer-divider" aria-hidden="true">·</span><span class="next-prayer-main-text">${escapeHtml(nextPrayerText)}</span>`;
    baseViewCache.lastNextPrayerText = nextPrayerLabelText;
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

  const progressPercent = Math.min(100, Math.max(0, Number(model.ramadan_progress_percent) || 0));
  const progressTitleText = formatRamadanTitle(progressPercent);
  if (baseViewCache.progressTitle && baseViewCache.lastProgressTitleText !== progressTitleText) {
    baseViewCache.progressTitle.textContent = progressTitleText;
    baseViewCache.lastProgressTitleText = progressTitleText;
  }

  if (baseViewCache.progressBar) {
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

function patchCalibrationView(model) {
  const section = stateView.querySelector('.calibration-screen');
  if (!section) return;

  const color = model.screen_color_css || 'rgb(0, 0, 0)';
  section.style.setProperty('--calibration-color', color);

  const lines = section.querySelectorAll('.calibration-panel p');
  if (lines.length >= 3) {
    const step = Number(model.step || 1);
    const total = Number(model.total_steps || 1);
    lines[0].textContent = `Шаг ${step} / ${total}`;
    lines[1].textContent = model.hint || '';
    lines[2].textContent = `Цвет: ${color}`;
  }
}

function patchCurrentView(model) {
  if (model.view === 'base_state') patchBaseView(model);
  if (model.view === 'tasks_map_state') patchMapView(model);
  if (model.view === 'day_review_state') patchReviewView(model);
  if (model.view === 'calibration_state') patchCalibrationView(model);
}

function wakePulse(progress, minBlend, maxBlend) {
  const oscillation = (1 - Math.cos(2 * Math.PI * progress)) / 2;
  return minBlend + ((maxBlend - minBlend) * oscillation);
}

function renderWakeFrame() {
  const frame = document.querySelector('.wake-frame');
  const nowMs = Date.now();
  const active = wakeSync && nowMs < Number(wakeSync.active_until_epoch_ms || 0);
  document.body.classList.toggle('wake-active', Boolean(active));

  if (!frame || !wakeSync || !active) {
    document.documentElement.style.setProperty('--wake-frame-shadow', 'inset 0 0 0 0 rgba(0, 150, 255, 0)');
    wakeAnimationFrame = requestAnimationFrame(renderWakeFrame);
    return;
  }

  const profile = wakeSync.profile || {};
  const color = Array.isArray(profile.color) ? profile.color : [100, 210, 255];
  const periodMs = Math.max(200, Math.round((Number(profile.period_seconds) || 1.5) * 1000));
  const elapsedMs = Math.max(0, nowMs - Number(wakeSync.started_at_epoch_ms || nowMs));
  const progress = (elapsedMs % periodMs) / periodMs;

  const minBlend = Math.max(0, Math.min(1, Number(profile.min_blend) || 0.2));
  const maxBlend = Math.max(minBlend, Math.min(1.2, Number(profile.max_blend) || 1.0));
  const pulse = wakePulse(progress, minBlend, maxBlend);

  const spread = 10 + (30 * pulse);
  const alpha = Math.max(0, Math.min(1, pulse * 0.9));
  const shadow = `inset 0 0 ${Math.round(30 + (70 * pulse))}px ${Math.round(spread)}px rgba(${color[0]}, ${color[1]}, ${color[2]}, ${alpha.toFixed(3)})`;
  document.documentElement.style.setProperty('--wake-frame-shadow', shadow);

  wakeAnimationFrame = requestAnimationFrame(renderWakeFrame);
}

function updateWakeBorder() {
  const active = Date.now() < wakeActiveUntil;
  if (!active) {
    wakeSync = null;
  }
  document.body.classList.toggle('wake-active', active);
}

function hardReloadPage() {
  if (reloadInProgress) return;
  reloadInProgress = true;
  const url = new URL(window.location.href);
  url.searchParams.set('reload_ts', String(Date.now()));
  window.location.replace(url.toString());
}

function trackAppInstance(instanceId) {
  if (!instanceId) return;
  if (!appInstanceId) {
    appInstanceId = instanceId;
    return;
  }

  if (appInstanceId !== instanceId) {
    hardReloadPage();
  }
}

function applyViewModel(model, { forceFullRender = false } = {}) {
  const stateChanged = currentState !== model.view;
  currentState = model.view;
  document.body.classList.toggle('base-active', model.view === 'base_state');

  if (forceFullRender || stateChanged || !stateView.firstElementChild) {
    stateView.innerHTML = renderState(model);
    baseViewCache.nextPrayerLabel = null;
    baseViewCache.progressTitle = null;
    baseViewCache.progressBar = null;
    baseViewCache.taskText = null;
    baseViewCache.lastTaskText = '';
    baseViewCache.lastNextPrayerText = '';
    baseViewCache.lastProgressTitleText = '';
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

  if (model.wake_sync) {
    wakeSync = model.wake_sync;
    wakeActiveUntil = Number(model.wake_sync.active_until_epoch_ms || 0);
  } else if (model.wake_active) {
    wakeActiveUntil = Date.now() + 6000;
  }

  updateWakeBorder();
}

function setDeployNoticeVisible(visible) {
  deployNoticeVisible = Boolean(visible);
  if (typeof window.setDeployUpdateBadgeVisible === 'function') {
    window.setDeployUpdateBadgeVisible(deployNoticeVisible);
    return;
  }

  const deployUpdateBadge = document.getElementById('deployUpdateBadge');
  if (!deployUpdateBadge) return;
  deployUpdateBadge.hidden = !deployNoticeVisible;
}

function markBackendReachable() {
  backendUnreachableSince = null;
  refreshFailCount = 0;
  setDeployNoticeVisible(false);
}

function markBackendUnreachable() {
  if (!wsConnected) {
    if (backendUnreachableSince == null) {
      backendUnreachableSince = Date.now();
    }

    const offlineDurationMs = Date.now() - backendUnreachableSince;
    if (refreshFailCount >= 2 && offlineDurationMs >= DEPLOY_NOTICE_DELAY_MS) {
      setDeployNoticeVisible(true);
    }
  }
}

async function refreshState(forceFullRender = false) {
  if (refreshInFlight) {
    return refreshInFlight;
  }

  refreshInFlight = (async () => {
    try {
      const response = await fetch('/api/state', { cache: 'no-store' });
      if (!response.ok) {
        throw new Error(`State API error: ${response.status}`);
      }
      const data = await response.json();
      trackAppInstance(data.app_instance_id);
      const viewModel = extractViewModel(data);
      if (!viewModel) {
        throw new Error('State API payload has no view model');
      }
      applyViewModel(viewModel, { forceFullRender });
      markBackendReachable();
    } catch (error) {
      refreshFailCount += 1;
      markBackendUnreachable();
      throw error;
    }
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
    markBackendReachable();
  });

  stateSocket.addEventListener('message', (event) => {
    try {
      const data = JSON.parse(event.data);
      trackAppInstance(data?.app_instance_id);
      const viewModel = extractViewModel(data);
      if (!viewModel) {
        refreshState().catch(() => {});
        return;
      }
      applyViewModel(viewModel);
      markBackendReachable();
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
let ambilightCaptureReady = false;
let ambilightCaptureTried = false;
let ambilightCaptureVideo = null;
let ambilightCaptureCanvas = null;
let ambilightCaptureCtx = null;
let ambilightEdgeLayout = { right: 30, top: 52, left: 30, bottom: 52 };

const AMBILIGHT_EDGE_DEPTH_PX = 30;
const AMBILIGHT_PUSH_INTERVAL_MS = 130;

function estimateEdgeLayout(totalLeds) {
  const baseline = { right: 30, top: 52, left: 30, bottom: 52 };
  const baseTotal = baseline.right + baseline.top + baseline.left + baseline.bottom;
  const total = Math.max(12, Number(totalLeds) || baseTotal);
  const scale = total / baseTotal;
  const scaled = {
    right: Math.max(1, Math.floor(baseline.right * scale)),
    top: Math.max(1, Math.floor(baseline.top * scale)),
    left: Math.max(1, Math.floor(baseline.left * scale)),
    bottom: Math.max(1, Math.floor(baseline.bottom * scale)),
  };

  let missing = total - (scaled.right + scaled.top + scaled.left + scaled.bottom);
  const edges = ['right', 'top', 'left', 'bottom'];
  let idx = 0;
  while (missing !== 0) {
    const edge = edges[idx % edges.length];
    const step = missing > 0 ? 1 : -1;
    if (scaled[edge] + step >= 1) {
      scaled[edge] += step;
      missing -= step;
    }
    idx += 1;
  }
  return scaled;
}

async function fetchAmbilightConfig() {
  try {
    const response = await fetch('/api/ambilight/config');
    if (!response.ok) return;
    const payload = await response.json();
    ambilightEdgeLayout = estimateEdgeLayout(payload?.led_count);
  } catch (_) {
    // Best effort only.
  }
}

async function ensureAmbilightCapture() {
  if (ambilightCaptureReady || ambilightCaptureTried || !navigator.mediaDevices?.getDisplayMedia) {
    return;
  }

  ambilightCaptureTried = true;
  try {
    const stream = await navigator.mediaDevices.getDisplayMedia({
      video: {
        frameRate: { ideal: 30, max: 60 },
        cursor: 'never',
      },
      audio: false,
    });
    const video = document.createElement('video');
    video.srcObject = stream;
    video.muted = true;
    await video.play();

    const track = stream.getVideoTracks()[0];
    if (track) {
      track.addEventListener('ended', () => {
        ambilightCaptureReady = false;
      });
    }

    ambilightCaptureVideo = video;
    ambilightCaptureCanvas = document.createElement('canvas');
    ambilightCaptureCtx = ambilightCaptureCanvas.getContext('2d', { willReadFrequently: true });
    ambilightCaptureReady = Boolean(ambilightCaptureCtx);
  } catch (_) {
    ambilightCaptureReady = false;
  }
}

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

function sampleFromCapture(x, y) {
  if (!ambilightCaptureReady || !ambilightCaptureVideo || !ambilightCaptureCtx || !ambilightCaptureCanvas) {
    return null;
  }

  const sourceWidth = ambilightCaptureVideo.videoWidth || window.innerWidth;
  const sourceHeight = ambilightCaptureVideo.videoHeight || window.innerHeight;
  if (!sourceWidth || !sourceHeight) {
    return null;
  }

  if (ambilightCaptureCanvas.width !== sourceWidth || ambilightCaptureCanvas.height !== sourceHeight) {
    ambilightCaptureCanvas.width = sourceWidth;
    ambilightCaptureCanvas.height = sourceHeight;
  }

  ambilightCaptureCtx.drawImage(ambilightCaptureVideo, 0, 0, sourceWidth, sourceHeight);
  const px = Math.max(0, Math.min(sourceWidth - 1, Math.round((x / Math.max(1, window.innerWidth - 1)) * (sourceWidth - 1))));
  const py = Math.max(0, Math.min(sourceHeight - 1, Math.round((y / Math.max(1, window.innerHeight - 1)) * (sourceHeight - 1))));

  const pixel = ambilightCaptureCtx.getImageData(px, py, 1, 1).data;
  return [pixel[0], pixel[1], pixel[2]];
}

function samplePixelColorAt(x, y) {
  const captured = sampleFromCapture(x, y);
  if (captured) {
    return captured;
  }

  const clampedX = Math.max(0, Math.min(window.innerWidth - 1, Math.round(x)));
  const clampedY = Math.max(0, Math.min(window.innerHeight - 1, Math.round(y)));
  const element = document.elementFromPoint(clampedX, clampedY);
  if (!element) return [0, 0, 0];
  return resolveVisualColor(element);
}

function collectEdgeSamples(count, edge) {
  const width = Math.max(1, window.innerWidth);
  const height = Math.max(1, window.innerHeight);
  const samples = [];

  for (let i = 0; i < count; i += 1) {
    const t = count === 1 ? 0 : i / (count - 1);
    let x = 0;
    let y = 0;

    if (edge === 'top') {
      x = t * (width - 1);
      y = AMBILIGHT_EDGE_DEPTH_PX;
    } else if (edge === 'right') {
      x = width - AMBILIGHT_EDGE_DEPTH_PX;
      y = t * (height - 1);
    } else if (edge === 'bottom') {
      x = t * (width - 1);
      y = height - AMBILIGHT_EDGE_DEPTH_PX;
    } else {
      x = AMBILIGHT_EDGE_DEPTH_PX;
      y = t * (height - 1);
    }

    samples.push(samplePixelColorAt(x, y));
  }

  return samples;
}

function collectEdgeColors() {
  const width = Math.max(1, window.innerWidth);
  const height = Math.max(1, window.innerHeight);

  return {
    top: collectEdgeSamples(ambilightEdgeLayout.top, 'top'),
    right: collectEdgeSamples(ambilightEdgeLayout.right, 'right'),
    bottom: collectEdgeSamples(ambilightEdgeLayout.bottom, 'bottom'),
    left: collectEdgeSamples(ambilightEdgeLayout.left, 'left'),
    viewport: { width, height },
  };
}

async function pushAmbilightFrame() {
  if (ambilightInFlight || document.hidden) {
    return;
  }

  ambilightInFlight = true;
  try {
    const payload = collectEdgeColors();
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
    ensureAmbilightCapture();
  }
});

document.addEventListener('pointerdown', () => {
  ensureAmbilightCapture();
}, { once: true });

document.addEventListener('keydown', () => {
  ensureAmbilightCapture();
}, { once: true });

fetchAmbilightConfig();
if (wakeAnimationFrame == null) {
  wakeAnimationFrame = requestAnimationFrame(renderWakeFrame);
}
refreshState(true);
connectStateSocket();
setInterval(tickBaseCountdown, 1000);
setInterval(fallbackRefreshTick, 3000);
setInterval(pushAmbilightFrame, AMBILIGHT_PUSH_INTERVAL_MS);
