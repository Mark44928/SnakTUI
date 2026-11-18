(() => {
'use strict';

const WIDTH = 40;
const HEIGHT = 18;
const BASE_CELL = 20;
const DIFFICULTY = {
  chill: { label: 'Chill', speed: 5.2, step: 0.45, max: 10.5, combo: 3.2 },
  classic: { label: 'Classic', speed: 7.6, step: 0.68, max: 17.5, combo: 2.8 },
  insane: { label: 'Insane', speed: 10.0, step: 0.9, max: 21.5, combo: 2.25 },
};
const BEST_KEY = 'snaktoweb-best-v1';
const TILE_COLORS = ['#5dff8b', '#2de2e6', '#ff2bd6', '#ffd166'];
const SPECIALS = [
  { kind: 'speed', points: 15, glyph: '▲', color: '#2de2e6', weight: 23 },
  { kind: 'slow', points: 15, glyph: '◈', color: '#9da6d8', weight: 20 },
  { kind: 'ghost', points: 20, glyph: '○', color: '#b39cff', weight: 27 },
  { kind: 'frenzy', points: 25, glyph: '✦', color: '#ff2bd6', weight: 20 },
  { kind: 'golden', points: 50, glyph: '◆', color: '#ffd166', weight: 10 },
];

const canvas = document.getElementById('arena');
const ctx = canvas?.getContext('2d');
if (!canvas || !ctx) return;
canvas.width = WIDTH * BASE_CELL;
canvas.height = HEIGHT * BASE_CELL;

const ui = {
  score: document.getElementById('score'),
  level: document.getElementById('level'),
  best: document.getElementById('best'),
  overlay: document.getElementById('overlay'),
  start: document.getElementById('start-btn'),
  difficulty: document.getElementById('difficulty'),
  wrap: document.getElementById('wrap-walls'),
  obstacles: document.getElementById('obstacles'),
  lowFx: document.getElementById('low-fx'),
  restart: document.getElementById('restart'),
  mode: document.getElementById('display-mode'),
  effectSpeed: document.getElementById('effect-speed'),
  effectGhost: document.getElementById('effect-ghost'),
  effectFrenzy: document.getElementById('effect-frenzy'),
};

let state;
let direction = { x: 1, y: 0 };
let pending = [];
let loopId = null;
let lastFrame = 0;
let moveAccumulator = 0;
let flash = 0;
let shake = 0;

function readBest() {
  try { const n = Number(localStorage.getItem(BEST_KEY)); return Number.isFinite(n) && n > 0 ? Math.floor(n) : 0; } catch (_) { return 0; }
}

function writeBest(value) {
  try { localStorage.setItem(BEST_KEY, String(Math.floor(value))); } catch (_) {}
}

function cellKey(cell) { return `${cell.x},${cell.y}`; }

function freeCells(exclude = []) {
  const occupied = new Set(exclude.map(cellKey));
  const free = [];
  for (let y = 0; y < HEIGHT; y += 1) {
    for (let x = 0; x < WIDTH; x += 1) {
      if (!occupied.has(`${x},${y}`)) free.push({ x, y });
    }
  }
  return free;
}

function spawnFood(exclude = [], special = false) {
  const free = freeCells([...state.snake, ...state.obstacles, ...exclude]);
  if (!free.length) return null;
  const cell = free[(Math.random() * free.length) | 0];
  if (!special) return { ...cell, kind: 'apple', glyph: '●', color: '#ff4f6a', points: 10 };
  const total = SPECIALS.reduce((sum, item) => sum + item.weight, 0);
  let pick = Math.random() * total;
  for (const item of SPECIALS) {
    pick -= item.weight;
    if (pick <= 0) return { ...cell, ...item };
  }
  return { ...cell, ...SPECIALS[0] };
}

function obstacleCells() {
  return [...state.obstacles].map(key => {
    const [x, y] = key.split(',').map(Number);
    return { x, y };
  });
}

function spawnObstacles(count) {
  const obstructed = [...state.snake, state.food, ...obstacleCells()].filter(Boolean);
  const free = freeCells(obstructed);
  while (state.obstacles.size < count && free.length) {
    const index = (Math.random() * free.length) | 0;
    const [item] = free.splice(index, 1);
    if (Math.abs(item.x - WIDTH / 2) + Math.abs(item.y - HEIGHT / 2) < 5) continue;
    state.obstacles.add(cellKey(item));
  }
}

function makeState() {
  const difficulty = DIFFICULTY[ui.difficulty.value] || DIFFICULTY.classic;
  const center = { x: Math.floor(WIDTH / 2), y: Math.floor(HEIGHT / 2) };
  return {
    difficulty,
    wrap: ui.wrap.checked,
    obstacleMode: ui.obstacles.checked,
    score: 0,
    apples: 0,
    level: 1,
    combo: 0,
    best: readBest(),
    over: false,
    paused: false,
    snake: [
      { ...center },
      { x: center.x - 1, y: center.y },
      { x: center.x - 2, y: center.y },
      { x: center.x - 3, y: center.y },
    ],
    obstacles: new Set(),
    food: null,
    effects: { speed: 0, ghost: 0, frenzy: 0, slow: 0 },
    particles: [],
  };
}

function resetGame(showReady = true) {
  state = makeState();
  direction = { x: 1, y: 0 };
  pending = [];
  moveAccumulator = 0;
  flash = 0;
  shake = 0;
  if (state.obstacleMode) spawnObstacles(4);
  state.food = spawnFood(obstacleCells(), false);
  updateHud();
  ui.mode.textContent = state.wrap ? 'BROWSER · WRAP' : 'BROWSER · WALLS';
  if (showReady) showOverlay('READY?', 'Arrow keys or WASD to move', 'START RUN');
  else hideOverlay();
}

function currentSpeed() {
  let speed = Math.min(state.difficulty.max, state.difficulty.speed + (state.level - 1) * state.difficulty.step);
  if (state.effects.speed > 0) speed *= 1.45;
  if (state.effects.slow > 0) speed *= 0.62;
  return Math.max(2.2, speed);
}

function secondsForEffect(kind) {
  return kind === 'frenzy' ? 6 : kind === 'speed' ? 6 : kind === 'slow' ? 6 : 5;
}

function addParticles(cell, color, count = 12) {
  if (ui.lowFx.checked) return;
  for (let index = 0; index < count; index += 1) {
    const angle = Math.random() * Math.PI * 2;
    const speed = 30 + Math.random() * 90;
    state.particles.push({ x: cell.x + .5, y: cell.y + .5, vx: Math.cos(angle) * speed, vy: Math.sin(angle) * speed, life: .55 + Math.random() * .35, max: .9, color });
  }
}

function tickCombo() {
  state.combo = Math.min(9, state.combo + 1);
  return Math.min(5, Math.max(1, state.combo));
}

function consume(food) {
  const multiplier = tickCombo();
  let points = food.points * multiplier;
  if (state.effects.frenzy > 0) points *= 2;
  state.score += points;
  state.apples += 1;
  addParticles(food, food.color, food.kind === 'golden' ? 22 : 11);
  flash = .18;
  if (food.kind === 'speed') state.effects.speed = secondsForEffect('speed');
  else if (food.kind === 'slow') state.effects.slow = secondsForEffect('slow');
  else if (food.kind === 'ghost') state.effects.ghost = secondsForEffect('ghost');
  else if (food.kind === 'frenzy') state.effects.frenzy = secondsForEffect('frenzy');
  if (state.apples % 4 === 0 && state.level < 9) state.level += 1;
  state.best = Math.max(state.best, state.score);
  writeBest(state.best);
  state.food = spawnFood([...state.snake, ...obstacleCells()], state.apples % 7 === 0);
  if (state.obstacleMode && state.apples % 4 === 0) spawnObstacles(Math.min(18, 4 + state.level * 2));
  updateHud();
}

function setDirection(next) {
  const last = pending.at(-1) || direction;
  if (!last || (next.x === last.x && next.y === last.y) || next.x === -last.x && next.y === -last.y) return;
  if (pending.length < 3) pending.push(next);
}

function step() {
  if (pending.length) direction = pending.shift();
  const head = state.snake[0];
  let next = { x: head.x + direction.x, y: head.y + direction.y };
  if (state.wrap || state.effects.ghost > 0) {
    next = { x: (next.x + WIDTH) % WIDTH, y: (next.y + HEIGHT) % HEIGHT };
  } else if (next.x < 0 || next.y < 0 || next.x >= WIDTH || next.y >= HEIGHT) {
    return endGame('THE WALL WINS');
  }
  const ate = state.food && next.x === state.food.x && next.y === state.food.y;
  const body = ate ? state.snake : state.snake.slice(0, -1);
  if (state.effects.ghost <= 0) {
    if (body.some(cell => cell.x === next.x && cell.y === next.y)) return endGame('EATEN BY YOUR OWN TAIL');
    if (state.obstacles.has(cellKey(next))) return endGame('HAZARD CLAIMED YOU');
  }
  state.snake.unshift(next);
  if (ate) consume(state.food); else state.snake.pop();
}

function endGame(reason) {
  state.over = true;
  writeBest(state.best);
  shake = .55;
  showOverlay(reason, `Final score ${state.score} · Level ${state.level} · Best ${state.best}`, 'RUN IT BACK');
  updateHud();
}

function updateHud() {
  ui.score.textContent = String(state?.score || 0);
  ui.level.textContent = String(state?.level || 1);
  ui.best.textContent = String(state?.best || readBest());
  ui.effectSpeed.textContent = state?.effects.speed > 0 ? `${Math.ceil(state.effects.speed)}s` : '—';
  ui.effectGhost.textContent = state?.effects.ghost > 0 ? `${Math.ceil(state.effects.ghost)}s` : '—';
  ui.effectFrenzy.textContent = state?.effects.frenzy > 0 ? `${Math.ceil(state.effects.frenzy)}s` : '—';
}

function showOverlay(title, detail, button) {
  ui.overlay.querySelector('strong').textContent = title;
  ui.overlay.querySelector('span').textContent = detail;
  ui.start.textContent = button;
  ui.overlay.classList.add('show');
}
function hideOverlay() { ui.overlay.classList.remove('show'); }

function drawGrid() {
  if (ui.lowFx.checked) return;
  ctx.fillStyle = '#07091b';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = '#161c3d';
  ctx.lineWidth = 1;
  for (let x = 1; x < WIDTH; x += 1) { ctx.beginPath(); ctx.moveTo(x * BASE_CELL, 0); ctx.lineTo(x * BASE_CELL, canvas.height); ctx.stroke(); }
  for (let y = 1; y < HEIGHT; y += 1) { ctx.beginPath(); ctx.moveTo(0, y * BASE_CELL); ctx.lineTo(canvas.width, y * BASE_CELL); ctx.stroke(); }
}

function drawHazard(key) {
  const [x, y] = key.split(',').map(Number);
  const px = x * BASE_CELL + 3, py = y * BASE_CELL + 3, size = BASE_CELL - 6;
  ctx.fillStyle = '#1a0c1e'; ctx.strokeStyle = '#ff2bd6'; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.roundRect(px, py, size, size, 4); ctx.fill(); ctx.stroke();
  ctx.strokeStyle = '#ff8ce9'; ctx.beginPath(); ctx.moveTo(px + 5, py + 5); ctx.lineTo(px + size - 5, py + size - 5); ctx.moveTo(px + size - 5, py + 5); ctx.lineTo(px + 5, py + size - 5); ctx.stroke();
}

function drawFood(food) {
  const cx = (food.x + .5) * BASE_CELL, cy = (food.y + .5) * BASE_CELL;
  ctx.save();
  if (!ui.lowFx.checked) { ctx.shadowBlur = food.kind === 'golden' ? 18 : 12; ctx.shadowColor = food.color; }
  ctx.fillStyle = food.color;
  ctx.beginPath(); ctx.arc(cx, cy, BASE_CELL * .27, 0, Math.PI * 2); ctx.fill();
  ctx.shadowBlur = 0; ctx.fillStyle = '#05060f'; ctx.font = 'bold 10px ui-monospace,monospace'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(food.glyph, cx, cy);
  ctx.restore();
}

function drawSnake() {
  state.snake.forEach((cell, index) => {
    const head = index === 0;
    const x = cell.x * BASE_CELL + 1, y = cell.y * BASE_CELL + 1, size = BASE_CELL - 2;
    ctx.save();
    if (!ui.lowFx.checked) { ctx.shadowBlur = head ? 20 : 10; ctx.shadowColor = head ? '#5dff8b' : '#2de2e6'; }
    ctx.fillStyle = head ? '#a7ff5d' : TILE_COLORS[(index / 3 | 0) % TILE_COLORS.length];
    ctx.beginPath(); ctx.roundRect(x, y, size, size, head ? 7 : 5); ctx.fill();
    ctx.restore();
    if (head) {
      ctx.fillStyle = '#05060f'; const eye = BASE_CELL / 2;
      ctx.beginPath(); ctx.arc(cell.x * BASE_CELL + eye + direction.x * 5 - direction.y * 4, cell.y * BASE_CELL + eye + direction.y * 5 - direction.x * 4, 2.2, 0, Math.PI * 2); ctx.fill();
      ctx.beginPath(); ctx.arc(cell.x * BASE_CELL + eye + direction.x * 5 + direction.y * 4, cell.y * BASE_CELL + eye + direction.y * 5 + direction.x * 4, 2.2, 0, Math.PI * 2); ctx.fill();
    }
  });
}

function drawParticles(dt) {
  state.particles = state.particles.filter(particle => particle.life > 0);
  for (const particle of state.particles) {
    particle.life -= dt;
    particle.x += particle.vx * dt / BASE_CELL;
    particle.y += particle.vy * dt / BASE_CELL;
    ctx.globalAlpha = Math.max(0, particle.life / particle.max);
    ctx.fillStyle = particle.color;
    ctx.fillRect(particle.x * BASE_CELL, particle.y * BASE_CELL, 3, 3);
  }
  ctx.globalAlpha = 1;
}

function draw() {
  const now = performance.now();
  const dt = Math.min(.05, (now - lastFrame) / 1000 || 0);
  lastFrame = now;
  if (state && !state.over && !state.paused && ui.overlay.classList.contains('show') === false) {
    moveAccumulator += dt;
    const interval = 1 / currentSpeed();
    while (moveAccumulator >= interval && !state.over) { moveAccumulator -= interval; step(); }
    for (const key of Object.keys(state.effects)) state.effects[key] = Math.max(0, state.effects[key] - dt);
    flash = Math.max(0, flash - dt); shake = Math.max(0, shake - dt);
    updateHud();
  }
  ctx.save();
  if (shake > 0 && !ui.lowFx.checked) ctx.translate((Math.random() - .5) * shake * 9, (Math.random() - .5) * shake * 9);
  drawGrid();
  for (const key of state.obstacles) drawHazard(key);
  if (state.food) drawFood(state.food);
  drawSnake();
  drawParticles(dt);
  if (flash > 0 && !ui.lowFx.checked) { ctx.globalAlpha = flash * 1.7; ctx.fillStyle = '#ffffff'; ctx.fillRect(0, 0, canvas.width, canvas.height); ctx.globalAlpha = 1; }
  ctx.restore();
  loopId = requestAnimationFrame(draw);
}

function startRun() {
  if (!state || state.over) resetGame(false);
  state.paused = false;
  hideOverlay();
}

function togglePause() {
  if (!state || state.over) return;
  state.paused = !state.paused;
  if (state.paused) showOverlay('PAUSED', 'Press SPACE or tap Resume', 'RESUME');
  else hideOverlay();
}

document.addEventListener('keydown', event => {
  const keys = { ArrowUp: {x:0,y:-1}, w: {x:0,y:-1}, W: {x:0,y:-1}, ArrowDown: {x:0,y:1}, s: {x:0,y:1}, S: {x:0,y:1}, ArrowLeft: {x:-1,y:0}, a: {x:-1,y:0}, A: {x:-1,y:0}, ArrowRight: {x:1,y:0}, d: {x:1,y:0}, D: {x:1,y:0} };
  if (keys[event.key]) { event.preventDefault(); setDirection(keys[event.key]); return; }
  if (event.key === ' ' || event.key.toLowerCase() === 'p') { event.preventDefault(); togglePause(); return; }
  if (event.key.toLowerCase() === 'r') { event.preventDefault(); resetGame(false); return; }
});
for (const button of document.querySelectorAll('.touch-controls [data-dir]')) button.addEventListener('click', () => { const dirs = { up: {x:0,y:-1}, down: {x:0,y:1}, left:{x:-1,y:0}, right:{x:1,y:0} }; setDirection(dirs[button.dataset.dir]); });
ui.start.addEventListener('click', startRun);
ui.restart.addEventListener('click', () => resetGame(false));
for (const control of [ui.difficulty, ui.wrap, ui.obstacles, ui.lowFx]) control.addEventListener('change', () => resetGame(true));
document.addEventListener('visibilitychange', () => { if (document.hidden && state && !state.over) state.paused = true; if (document.hidden && state?.paused) showOverlay('PAUSED', 'Return to the tab to resume', 'RESUME'); });

resetGame(true);
lastFrame = performance.now();
draw();
})();
