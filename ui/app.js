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

function formatClock(totalSeconds) {
  const safe = Math.max(0, totalSeconds);
  const hh = Math.floor(safe / 3600);
  const mm = Math.floor((safe % 3600) / 60);
  return `${String(hh).padStart(2, '0')}${String(mm).padStart(2, '0')}`;
}

function lerpColor(from, to, t) {
  const clamped = Math.min(1, Math.max(0, Number(t) || 0));
  const f = from.map((v, i) => Math.round(v + (to[i] - v) * clamped));
  return `rgb(${f[0]}, ${f[1]}, ${f[2]})`;
}

function updateDynamicPalette(phase, progress) {
  const p = Math.min(1, Math.max(0, Number(progress) || 0));
  const dayBg = lerpColor([43, 10, 10], [22, 7, 28], p);
  const dayBlob1 = lerpColor([255, 94, 98], [255, 146, 70], p);
  const dayBlob2 = lerpColor([255, 153, 102], [255, 94, 98], p);
  const dayBlob3 = lerpColor([241, 39, 17], [196, 56, 122], p);

  const nightBg = lerpColor([5, 11, 20], [14, 7, 32], p);
  const nightBlob1 = lerpColor([0, 198, 255], [84, 130, 255], p);
  const nightBlob2 = lerpColor([0, 114, 255], [120, 70, 220], p);
  const nightBlob3 = lerpColor([31, 28, 44], [4, 26, 56], p);

  const isNight = phase === 'night';
  const root = document.documentElement;
  root.style.setProperty('--color-bg', isNight ? nightBg : dayBg);
  root.style.setProperty('--color-blob1', isNight ? nightBlob1 : dayBlob1);
  root.style.setProperty('--color-blob2', isNight ? nightBlob2 : dayBlob2);
  root.style.setProperty('--color-blob3', isNight ? nightBlob3 : dayBlob3);
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
  const progress = Math.round((Number(model.next_prayer.phase_progress || 0) || 0) * 100);
  const eventName = `До ${model.next_prayer.next}`;
  return `<section class="base-screen" data-view="base_state">
    <div class="lava-background">
      <div class="blob"></div>
      <div class="blob"></div>
      <div class="blob"></div>
    </div>

    <div class="wake-frame"></div>

    <div class="progress-wrapper">
      <div class="progress-labels">
        <span id="event-name">${eventName}</span>
        <span id="event-time-left">${model.next_prayer.countdown}</span>
      </div>
      <div class="progress-container">
        <div class="progress-bar" id="progress-bar" style="width:${progress}%"></div>
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
      <div class="clock">
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
      <div class="task-meta" id="prayerTimesLabel">Сухур ${model.next_prayer.suhoor} · Ифтар ${model.next_prayer.iftar}</div>
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
  const eventName = document.getElementById('event-name');
  const eventTime = document.getElementById('event-time-left');
  const progressBar = document.getElementById('progress-bar');
  const taskText = document.getElementById('daily-task');
  const prayerTimesLabel = document.getElementById('prayerTimesLabel');

  if (eventName) eventName.textContent = `До ${model.next_prayer.next}`;
  if (eventTime) eventTime.textContent = model.next_prayer.countdown;
  if (taskText) taskText.textContent = model.today_task;
  if (prayerTimesLabel) prayerTimesLabel.textContent = `Сухур ${model.next_prayer.suhoor} · Ифтар ${model.next_prayer.iftar}`;
  if (progressBar) {
    progressBar.style.width = `${Math.round((Number(model.next_prayer.phase_progress || 0) || 0) * 100)}%`;
  }

  updateDynamicPalette(model.next_prayer.phase, Number(model.next_prayer.phase_progress || 0));
  updateJellyClock(formatClock(parseCountdownToSeconds(model.next_prayer.countdown)));
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
    endAt: Date.now() + countdownSeconds * 1000,
    phase: model.next_prayer.phase,
    phaseTotalSeconds: Math.max(1, Number(model.next_prayer.phase_total_seconds) || 1),
    awaitingResync: false,
  };

  patchBaseView(model);

  baseTickTimer = setInterval(() => {
    if (currentState !== 'base_state' || !baseRuntime) return;

    const now = Date.now();
    const secondsLeft = Math.max(0, Math.ceil((baseRuntime.endAt - now) / 1000));
    const elapsedInPhase = Math.max(0, baseRuntime.phaseTotalSeconds - secondsLeft);
    const phaseProgress = Math.min(1, elapsedInPhase / baseRuntime.phaseTotalSeconds);
    const formattedCountdown = formatCountdown(secondsLeft);

    const eventTime = document.getElementById('event-time-left');
    if (eventTime) eventTime.textContent = formattedCountdown;

    const progressBar = document.getElementById('progress-bar');
    if (progressBar) progressBar.style.width = `${Math.round(phaseProgress * 100)}%`;

    updateDynamicPalette(baseRuntime.phase, phaseProgress);
    updateJellyClock(formatClock(secondsLeft));

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
updateDynamicPalette('day', 0.5);
refreshState(true);

setInterval(() => {
  refreshState().catch(() => {});
}, 1000);
