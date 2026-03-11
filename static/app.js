// ── STATE ──
let systemActive = false;
let servoMode    = 'auto';
let servoPosition = 90;
let intrusions   = [];
let lockPin      = '';
let modalPin     = '';
let lastIntrusionCount = 0;
let alarmPending = false;

// ── CLOCK ──
function updateClock() {
  const now = new Date();
  const pad = n => String(n).padStart(2, '0');
  const str = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
  document.getElementById('clock').textContent    = str;
  document.getElementById('statTime').textContent = str.slice(0, 5);
}
setInterval(updateClock, 1000);
updateClock();

// ── LOCK SCREEN ──
function lockInput(digit) {
  if (lockPin.length >= 4) return;
  lockPin += digit;
  updateLockDots();
  if (lockPin.length === 4) setTimeout(submitLock, 150);
}

function lockDelete() {
  lockPin = lockPin.slice(0, -1);
  updateLockDots();
  document.getElementById('lockError').classList.remove('show');
}

function updateLockDots() {
  for (let i = 0; i < 4; i++) {
    const dot = document.getElementById('d' + i);
    dot.classList.toggle('filled', i < lockPin.length);
    dot.classList.remove('error');
  }
}

async function submitLock() {
  const res = await fetch('/api/auth', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pin: lockPin })
  });

  if (res.ok) {
    const screen = document.getElementById('lockScreen');
    screen.style.opacity = '0';
    setTimeout(() => {
      screen.style.display = 'none';
      document.getElementById('app').classList.add('visible');
      startPolling();
      loadIntrusions();
    }, 400);
  } else {
    for (let i = 0; i < 4; i++) {
      const dot = document.getElementById('d' + i);
      dot.classList.remove('filled');
      dot.classList.add('error');
    }
    document.getElementById('lockError').classList.add('show');
    lockPin = '';
    setTimeout(() => {
      for (let i = 0; i < 4; i++) document.getElementById('d' + i).classList.remove('error');
      document.getElementById('lockError').classList.remove('show');
    }, 1200);
  }
}

// ── PIN MODAL ──
function openModal(sub) {
  modalPin = '';
  updateModalDots();
  document.getElementById('modalSub').textContent = sub || 'ENTREZ VOTRE CODE PIN';
  document.getElementById('modalError').classList.remove('show');
  document.getElementById('pinModal').classList.add('show');
}

function closeModal() {
  document.getElementById('pinModal').classList.remove('show');
  modalPin = '';
}

function modalInput(digit) {
  if (modalPin.length >= 4) return;
  modalPin += digit;
  updateModalDots();
  if (modalPin.length === 4) setTimeout(submitModal, 150);
}

function modalDelete() {
  modalPin = modalPin.slice(0, -1);
  updateModalDots();
  document.getElementById('modalError').classList.remove('show');
}

function updateModalDots() {
  for (let i = 0; i < 4; i++) {
    const dot = document.getElementById('m' + i);
    dot.classList.toggle('filled', i < modalPin.length);
    dot.classList.remove('error');
  }
}

async function submitModal() {
  const res = await fetch('/api/system/toggle', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pin: modalPin })
  });

  if (res.ok) {
    const data = await res.json();
    closeModal();
    applySystemState(data.active);
    showToast(data.active ? 'SYSTÈME ACTIVÉ' : 'SYSTÈME DÉSACTIVÉ',
              data.active ? 'success' : 'error');
  } else {
    for (let i = 0; i < 4; i++) {
      document.getElementById('m' + i).classList.remove('filled');
      document.getElementById('m' + i).classList.add('error');
    }
    document.getElementById('modalError').classList.add('show');
    modalPin = '';
    setTimeout(() => {
      for (let i = 0; i < 4; i++) document.getElementById('m' + i).classList.remove('error');
    }, 800);
  }
}

// ── SYSTEM TOGGLE ──
function requestToggle() {
  const action = systemActive ? 'DÉSACTIVER' : 'ACTIVER';
  openModal(`CONFIRMER POUR ${action}`);
}

function applySystemState(active) {
  systemActive = active;

  const dot  = document.getElementById('statusDot');
  const txt  = document.getElementById('statusText');
  const btn  = document.getElementById('sysToggleBtn');
  const btxt = document.getElementById('sysToggleTxt');
  const cam  = document.getElementById('camStream');
  const off  = document.getElementById('camOffline');
  const tag  = document.getElementById('camTag');
  const rec  = document.getElementById('recBadge');

  dot.className   = 'status-dot ' + (active ? 'active' : 'inactive');
  txt.textContent = active ? 'ACTIF' : 'INACTIF';
  btn.className   = 'system-toggle ' + (active ? 'off' : 'on');
  btxt.textContent = active ? 'DÉSACTIVER LE SYSTÈME' : 'ACTIVER LE SYSTÈME';

  if (active) {
    cam.src            = '/video_feed?' + Date.now();
    cam.style.display  = 'block';
    off.style.display  = 'none';
    tag.textContent    = '640×480 — 20FPS';
    rec.style.display  = 'flex';
  } else {
    cam.src            = '';
    cam.style.display  = 'none';
    off.style.display  = 'flex';
    tag.textContent    = 'HORS LIGNE';
    rec.style.display  = 'none';
  }

  updateServoButtons();
}

// ── SERVO ──
function setMode(mode) {
  servoMode = mode;
  fetch('/api/servo/mode', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode })
  });
  document.getElementById('btnAuto').classList.toggle('active', mode === 'auto');
  document.getElementById('btnManual').classList.toggle('active', mode === 'manual');
  document.getElementById('statMode').textContent = mode.toUpperCase();
  updateServoButtons();
  showToast('MODE ' + mode.toUpperCase() + ' ACTIVÉ', 'success');
}

function updateServoButtons() {
  const enabled = servoMode === 'manual' && systemActive;
  document.getElementById('btnLeft').disabled  = !enabled;
  document.getElementById('btnRight').disabled = !enabled;
}

async function moveServo(dir) {
  const res = await fetch('/api/servo/move', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ direction: dir })
  });
  const data = await res.json();
  servoPosition = data.position;
  document.getElementById('servoVal').textContent = servoPosition + '°';
}

// ── INTRUSIONS ──
async function loadIntrusions() {
  const res  = await fetch('/api/intrusions');
  const data = await res.json();
  intrusions = data;
  lastIntrusionCount = data.length;
  renderLog();
}

function renderLog() {
  const body  = document.getElementById('logBody');
  const empty = document.getElementById('logEmpty');
  const badge = document.getElementById('logBadge');
  const count = document.getElementById('statCount');

  badge.textContent = intrusions.length;
  count.textContent = intrusions.length;

  if (intrusions.length === 0) {
    body.innerHTML = '';
    body.appendChild(empty);
    empty.style.display = 'flex';
    return;
  }

  empty.style.display = 'none';
  body.innerHTML = '';

  intrusions.forEach((item, i) => {
    const div = document.createElement('div');
    div.className = 'log-item' + (i === 0 ? ' new' : '');
    div.innerHTML = `
      <div class="log-item-icon">
        <svg viewBox="0 0 24 24">
          <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
          <line x1="12" y1="9" x2="12" y2="13"/>
          <line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
      </div>
      <div class="log-item-info">
        <div class="log-item-title">INTRUSION DÉTECTÉE</div>
        <div class="log-item-time">${item.timestamp}</div>
      </div>
      <div class="log-item-id">#${String(item.id).padStart(3, '0')}</div>
    `;
    body.appendChild(div);
  });
}

function showNotif() {
  const n = document.getElementById('notifFlash');
  n.classList.add('show');
  setTimeout(() => n.classList.remove('show'), 3000);
}

async function clearLog() {
  await fetch('/api/intrusions/clear', { method: 'POST' });
  intrusions = [];
  lastIntrusionCount = 0;
  renderLog();
  showToast('JOURNAL EFFACÉ', 'success');
}

// ── POLLING ──
function startPolling() {
  setInterval(async () => {
    // Vérifier alarme en attente
    const alarmRes  = await fetch('/api/alarm/status');
    const alarmData = await alarmRes.json();

    if (alarmData.pending && !alarmPending) {
      alarmPending = true;
      showAlarmModal();
    }

    // Intrusions
    const res  = await fetch('/api/intrusions');
    const data = await res.json();
    if (data.length > lastIntrusionCount && lastIntrusionCount > 0) {
      intrusions = data;
      renderLog();
      showNotif();
    } else if (data.length !== intrusions.length) {
      intrusions = data;
      renderLog();
    }
    lastIntrusionCount = data.length;
  }, 2000);
}

// Afficher le modal d'alarme
function showAlarmModal() {
  document.getElementById('alarmModal').classList.add('show');
}

// Acquitter l'alarme
async function ackAlarm(action) {
  await fetch('/api/alarm/ack', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action })
  });
  alarmPending = false;
  document.getElementById('alarmModal').classList.remove('show');
  const msg = action === 'authorities' ? 'AUTORITÉS CONTACTÉES' : 'ALARME LEVÉE';
  showToast(msg, action === 'authorities' ? 'success' : 'error');
}

// ── TOAST ──
function showToast(msg, type) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className   = 'show ' + (type || '');
  setTimeout(() => { t.className = ''; }, 2200);
}

// ── KEYBOARD SUPPORT ──
document.addEventListener('keydown', e => {
  const lockVisible = document.getElementById('lockScreen').style.display !== 'none'
                   && document.getElementById('lockScreen').style.opacity  !== '0';
  const modalOpen   = document.getElementById('pinModal').classList.contains('show');

  if (lockVisible) {
    if (e.key >= '0' && e.key <= '9') lockInput(e.key);
    if (e.key === 'Backspace') lockDelete();
  } else if (modalOpen) {
    if (e.key >= '0' && e.key <= '9') modalInput(e.key);
    if (e.key === 'Backspace') modalDelete();
    if (e.key === 'Escape')    closeModal();
  }
});