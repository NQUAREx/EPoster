const stateView = document.getElementById('stateView');

let wakeActiveUntil = 0;
let baseTickTimer = null;
let currentState = '';
let baseRuntime = null;

function asGlass(content) {
  return `<div class="glass">${content}</div>`;
}

function textGradient(text) {
  return `<span class="water-text">${text}</span>`;
}

function computePhaseHue(phase, progress) {
  const clampedProgress = Math.min(1, Math.max(0, Number(progress) || 0));
  const minHue = 0;
  const maxHue = 120;
  if (phase === 'night') {
    return Math.round(maxHue - clampedProgress * (maxHue - minHue));
  }
  return Math.round(minHue + clampedProgress * (maxHue - minHue));
}

function updateDynamicHue(phase, progress) {
  document.body.style.setProperty('--dynamic-hue', String(computePhaseHue(phase, progress)));
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

function renderMonthSegments(monthProgress) {
  const total = 30;
  const scaled = Number(monthProgress || 0) * total;
  const completed = Math.floor(scaled);
  return Array.from({ length: total }, (_, index) => {
    const part = index + 1;
    const active = part <= completed ? 'active' : '';
    return `<span class="segment ${active}" data-segment="${part}"></span>`;
  }).join('');
}

function renderBase(model) {
  return `<section class="base-screen" data-view="base_state">
      <div class="lava-background" aria-hidden="true"><span class="blob"></span><span class="blob"></span><span class="blob"></span></div>
      <div class="base-layout">
        <header class="base-top glass">
          <div class="base-top-row"><div class="day-title" id="baseDayTitle">${textGradient(`день ${model.day}`)}</div><p id="nextPrayerLabel">${textGradient(`До ${model.next_prayer.next}`)}</p></div>
          <div class="progress-30" id="monthProgressBar">${renderMonthSegments(model.month_progress)}</div>
        </header>
        <div class="base-clock-wrap">
          <h1 id="countdownClock" class="liquid-clock">${textGradient(model.next_prayer.countdown)}</h1>
          <p id="prayerTimesLabel">${textGradient(`Сухур ${model.next_prayer.suhoor} · Ифтар ${model.next_prayer.iftar}`)}</p>
        </div>
        <footer class="base-task-wrap glass"><p class="large-copy" id="todayTaskText">${textGradient(model.today_task)}</p></footer>
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
  const circles = model.circles.map((circle) => {
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
  const dayTitle = document.getElementById('baseDayTitle');
  const nextPrayerLabel = document.getElementById('nextPrayerLabel');
  const prayerTimesLabel = document.getElementById('prayerTimesLabel');
  const todayTaskText = document.getElementById('todayTaskText');
  const progressBar = document.getElementById('monthProgressBar');

  if (dayTitle) dayTitle.innerHTML = textGradient(`день ${model.day}`);
  if (nextPrayerLabel) nextPrayerLabel.innerHTML = textGradient(`До ${model.next_prayer.next}`);
  if (prayerTimesLabel) prayerTimesLabel.innerHTML = textGradient(`Сухур ${model.next_prayer.suhoor} · Ифтар ${model.next_prayer.iftar}`);
  if (todayTaskText) todayTaskText.innerHTML = textGradient(model.today_task);
  if (progressBar) progressBar.innerHTML = renderMonthSegments(model.month_progress);
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
    startMonthProgress: Number(model.month_progress || 0),
    startedAt: Date.now(),
    endAt: Date.now() + countdownSeconds * 1000,
    phase: model.next_prayer.phase,
    phaseTotalSeconds: Math.max(1, Number(model.next_prayer.phase_total_seconds) || 1),
    lastHueMinuteMark: null,
    awaitingResync: false,
  };

  updateDynamicHue(baseRuntime.phase, Number(model.next_prayer.phase_progress || 0));

  baseTickTimer = setInterval(() => {
    if (currentState !== 'base_state' || !baseRuntime) return;

    const now = Date.now();
    const secondsLeft = Math.max(0, Math.ceil((baseRuntime.endAt - now) / 1000));
    const elapsedInPhase = Math.max(0, baseRuntime.phaseTotalSeconds - secondsLeft);
    const phaseProgress = Math.min(1, elapsedInPhase / baseRuntime.phaseTotalSeconds);

    const minuteMark = Math.floor(now / 60000);
    if (baseRuntime.lastHueMinuteMark !== minuteMark) {
      baseRuntime.lastHueMinuteMark = minuteMark;
      updateDynamicHue(baseRuntime.phase, phaseProgress);
    }

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
      progressBar.innerHTML = renderMonthSegments(progress);
    }

    if (secondsLeft <= 0 && !baseRuntime.awaitingResync) {
      baseRuntime.awaitingResync = true;
      refreshState(true);
    }
  }, 1000);
}

function applyViewModel(model, { forceFullRender = false } = {}) {
  const stateChanged = currentState !== model.view;
  currentState = model.view;
  document.body.classList.toggle('base-active', model.view === 'base_state');

  if (forceFullRender || stateChanged || !stateView.firstElementChild) {
    stateView.innerHTML = renderState(model);
    const section = stateView.querySelector('section');
    if (section) {
      section.classList.add('state-enter');
    }
    if (stateChanged) {
      document.body.classList.add('state-transitioning');
      setTimeout(() => document.body.classList.remove('state-transitioning'), 320);
    }
  } else {
    patchCurrentView(model);
  }

  if (model.view === 'base_state' && (stateChanged || forceFullRender || !baseTickTimer)) {
    startBaseTicker(model);
  }
  if (model.view !== 'base_state') {
    stopBaseTicker();
  }

  if (model.wake_active) {
    wakeActiveUntil = Date.now() + 6000;
  }

  updateWakeBorder();
  if (model.view !== 'base_state') {
    updateDynamicHue('day', 0.5);
  }
}

async function refreshState(forceFullRender = false) {
  const response = await fetch('/api/state');
  const data = await response.json();
  applyViewModel(data.view_model, { forceFullRender });
}

document.addEventListener('visibilitychange', () => {
  if (!document.hidden) {
    refreshState();
  }
});

setInterval(updateWakeBorder, 200);
updateDynamicHue('day', 0.5);
refreshState(true);

setInterval(() => {
  refreshState().catch(() => {});
}, 1000);
