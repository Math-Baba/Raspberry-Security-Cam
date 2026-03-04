const $ = (id) => document.getElementById(id);

const state = {
  active: false,
  pendingTarget: null
};

function formatUptime(sec) {
  if (sec == null) return "—";
  const d = Math.floor(sec / 86400);
  sec %= 86400;
  const h = Math.floor(sec / 3600);
  sec %= 3600;
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  const parts = [];
  if (d) parts.push(`${d}j`);
  parts.push(`${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`);
  return parts.join(" ");
}

function setSwitch(on) {
  state.active = on;
  const sw = $("toggleSwitch");
  sw.dataset.on = on ? "true" : "false";

  $("sysText").textContent = on ? "Actif" : "Inactif";
  const dot = $("dot");
  dot.style.background = on ? "rgba(34,197,94,0.9)" : "rgba(239,68,68,0.9)";
  dot.style.boxShadow = on ? "0 0 0 4px rgba(34,197,94,0.15)" : "0 0 0 4px rgba(239,68,68,0.15)";
  $("toggleHint").textContent = on
    ? "La surveillance est active. Désactivation protégée par PIN."
    : "La surveillance est inactive. Activation protégée par PIN.";

  // overlay vidéo si OFF
  const overlay = $("videoOverlay");
  if (overlay) {
    overlay.classList.toggle("hidden", on);
  }
}

function openModal(id) {
  $(id).classList.remove("hidden");
}
function closeModal(id) {
  $(id).classList.add("hidden");
}

document.addEventListener("click", (e) => {
  const closeId = e.target?.dataset?.close;
  if (closeId) closeModal(closeId);
});

async function loadStatus() {
  const res = await fetch("/api/status");
  const data = await res.json();
  if (!data.ok) return;

  setSwitch(!!data.active);
  $("uptime").textContent = formatUptime(data.uptime_s);

  $("lastLogin").textContent = data.last_login_iso ? data.last_login_iso : "—";

  const ul = $("logs");
  ul.innerHTML = "";
  (data.logs || []).forEach(item => {
    const li = document.createElement("li");
    li.className = "text-sm flex items-start justify-between gap-4 border border-white/5 rounded-xl p-3 bg-white/5";
    li.innerHTML = `
      <span class="text-slate-200">${escapeHtml(item.msg || "")}</span>
      <span class="font-mono text-xs text-slate-400">${escapeHtml(item.ts || "")}</span>
    `;
    ul.appendChild(li);
  });

  if ((data.logs || []).length === 0) {
    ul.innerHTML = `<li class="text-slate-400 text-sm">Aucun événement.</li>`;
  }
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&","&amp;")
    .replaceAll("<","&lt;")
    .replaceAll(">","&gt;")
    .replaceAll('"',"&quot;")
    .replaceAll("'","&#039;");
}

// Toggle flow (PIN modal)
$("toggleSwitch").addEventListener("click", () => {
  state.pendingTarget = !state.active;
  $("pinConfirm").value = "";
  $("pinErr").classList.add("hidden");
  openModal("modalPin");
});

$("btnConfirmToggle").addEventListener("click", async () => {
  const pin = $("pinConfirm").value.trim();
  const target = state.pendingTarget;

  const res = await fetch("/api/toggle", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({ pin, target })
  });

  const data = await res.json().catch(()=>({}));
  if (!res.ok || !data.ok) {
    $("pinErr").textContent = data.error || "Erreur.";
    $("pinErr").classList.remove("hidden");
    return;
  }

  closeModal("modalPin");
  await loadStatus();
});

// Change PIN
$("btnChangePin").addEventListener("click", () => {
  $("oldPin").value = "";
  $("newPin").value = "";
  $("pinChangeErr").classList.add("hidden");
  openModal("modalChangePin");
});

$("btnSavePin").addEventListener("click", async () => {
  const old_pin = $("oldPin").value.trim();
  const new_pin = $("newPin").value.trim();

  const res = await fetch("/api/pin", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({ old_pin, new_pin })
  });

  const data = await res.json().catch(()=>({}));
  if (!res.ok || !data.ok) {
    $("pinChangeErr").textContent = data.error || "Erreur.";
    $("pinChangeErr").classList.remove("hidden");
    return;
  }

  closeModal("modalChangePin");
  await loadStatus();
});

// Logout
$("btnLogout").addEventListener("click", async () => {
  await fetch("/logout", { method: "POST" });
  window.location.href = "/login";
});

$("btnRefresh").addEventListener("click", loadStatus);

// Auto refresh (widgets)
loadStatus();
setInterval(loadStatus, 5000);