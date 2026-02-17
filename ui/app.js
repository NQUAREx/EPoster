const stateView = document.getElementById('stateView');
const commandInput = document.getElementById('commandInput');
const payloadInput = document.getElementById('payloadInput');
const errorBox = document.getElementById('errorBox');

function renderBase(model) {
  return `
    <section class="base-screen">
      <div class="clock-box">
        <p>До ${model.next_prayer.next}</p>
        <h1>${model.next_prayer.countdown}</h1>
        <p>Сухур: ${model.next_prayer.suhoor} · Ифтар: ${model.next_prayer.iftar}</p>
      </div>
      <div class="task-box">Задание на сегодня: ${model.today_task}</div>
    </section>`;
}

function renderMap(model) {
  const circles = model.circles
    .map((circle) => {
      const css = `circle ${circle.status} ${circle.selected ? 'selected' : ''}`;
      const mark = circle.status === 'completed' ? '✓' : circle.day;
      return `<div class="${css}">${mark}</div>`;
    })
    .join('');
  return `<section class="map-screen"><div class="grid">${circles}</div></section>`;
}

function renderReview(model) {
  const options = model.score_dialog_open
    ? `<div class="score-modal">
        <div class="score red">😟 1</div>
        <div class="score yellow">🙂 2</div>
        <div class="score green">😄 3</div>
      </div>`
    : '';
  return `<section class="review-screen"><h1>Отвечает: ${model.current_child}</h1>${options}</section>`;
}

function renderTask(model) {
  return `<section class="task-screen"><h1>Задание дня ${model.day}</h1><p>${model.task_text}</p></section>`;
}

function renderEid(model) {
  const totals = Object.entries(model.children_totals).map(([name, score]) => `<div>${name}: ${score}</div>`).join('');
  return `<section class="eid-screen"><h1>${model.message}</h1><div>${totals}</div><h2>Общий счет: ${model.total_points}</h2></section>`;
}

function renderState(model) {
  if (model.view === 'base') return renderBase(model);
  if (model.view === 'task_map') return renderMap(model);
  if (model.view === 'day_review') return renderReview(model);
  if (model.view === 'task') return renderTask(model);
  if (model.view === 'eid') return renderEid(model);
  return '<section><h1>Неизвестный state</h1></section>';
}

async function refreshState() {
  const response = await fetch('/api/state');
  const data = await response.json();
  stateView.innerHTML = renderState(data.view_model);
}

async function sendCommand() {
  errorBox.textContent = '';
  const command = commandInput.value.trim();
  if (!command) {
    errorBox.textContent = 'Введите command';
    return;
  }
  let payload = null;
  if (payloadInput.value.trim()) {
    try {
      payload = JSON.parse(payloadInput.value.trim());
    } catch {
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
  stateView.innerHTML = renderState(data.view_model);
}

document.getElementById('sendBtn').addEventListener('click', sendCommand);
refreshState();
setInterval(refreshState, 30000);
