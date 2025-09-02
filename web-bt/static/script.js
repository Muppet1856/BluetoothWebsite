// --- Element refs ---
const scanToggle   = document.getElementById('scanToggle');
const scanText     = document.getElementById('scanText');
const scanMsg      = document.getElementById('scanMsg');
const deviceList   = document.getElementById('deviceList');
const statusArea   = document.getElementById('statusArea');
const connectBtn   = document.getElementById('connectBtn');
const disconnectBtn= document.getElementById('disconnectBtn');
const forgetBtn    = document.getElementById('forgetBtn');
const refreshBtn   = document.getElementById('refreshBtn');
const clearLogBtn  = document.getElementById('clearLogBtn');
const copyLogBtn   = document.getElementById('copyLogBtn');
const countEl      = document.getElementById('count');
const logBox       = document.getElementById('logBox');
const audioOnlyChk = document.getElementById('audioOnly');
const testAudioBtn = document.getElementById('testAudioBtn');
const apSsid = document.getElementById('apSsid');
const apSsidBtn = document.getElementById('apSsidBtn');
const scanWifiBtn = document.getElementById('scanWifiBtn');
const wifiList = document.getElementById('wifiList');
const wifiInfo = document.getElementById('wifiInfo');
const versionEl  = document.getElementById('version');

// --- ANSI renderer (client-side) ---
if (window.APP_VERSION) {
  console.debug('App version:', window.APP_VERSION);
  if (versionEl) versionEl.textContent = window.APP_VERSION.slice(0, 7);
}
const ansi = new AnsiToHtml();          // from CDN in index.html
let lastLogRaw = "";                    // plain text for "Copy" button

function showLogRAW(raw) {
  lastLogRaw = raw || "";
  logBox.innerHTML = ansi.toHtml(lastLogRaw);
  logBox.scrollTop = logBox.scrollHeight; // autoscroll
}

// --- State ---
let devices = [];
let selectedMac = "";
let polling = null;
let audioOnly = true;

// --- Helpers ---
function badge(label, ok, yes='Yes', no='No') {
  return `<span class="badge ${ok ? 'text-bg-success' : 'text-bg-danger'} me-1">${label}: ${ok ? yes : no}</span>`;
}

function deviceStateBadge(d) {
  if (d.connected) return '<span class="badge text-bg-success">Connected</span>';
  if (d.paired && d.trusted) return '<span class="badge text-bg-info">Paired</span>';
  return '<span class="badge text-bg-secondary">New</span>';
}

function renderStatus(info) {
  if (!info) {
    statusArea.innerHTML = '<span class="text-secondary">No device selected.</span>';
    connectBtn.disabled = true; disconnectBtn.disabled = true; forgetBtn.disabled = true; testAudioBtn.disabled = true;
    return;
  }
  statusArea.innerHTML =
    `${badge('Paired', info.paired)} ${badge('Trusted', info.trusted)} ${badge('Connected', info.connected)}`;
  connectBtn.disabled    = info.connected || !selectedMac;
  disconnectBtn.disabled = !info.connected || !selectedMac;
  forgetBtn.disabled     = !(info.paired || info.trusted) || !selectedMac;
  testAudioBtn.disabled  = !info.connected || !selectedMac;
}

function renderList() {
  deviceList.innerHTML = "";
  countEl.textContent = devices.length;

  devices.forEach(d => {
    const alias = d.alias || d.name || "(unknown)";
    const identityLink = d.identity && d.identity !== d.mac
      ? `<a href="#" class="ms-2 small identity-link" data-mac="${d.identity}">→ ${d.identity}</a>`
      : "";
    const item = document.createElement('button');
    item.type = "button";
    item.className = "list-group-item list-group-item-action d-flex justify-content-between align-items-center";
    item.innerHTML = `
      <div>
        <div class="fw-semibold">${alias}</div>
        <div class="badge text-bg-secondary rounded-pill mac">${d.mac}</div>${identityLink}
      </div>
      <div>${deviceStateBadge(d)}</div>
    `;
    if (d.mac === selectedMac) item.classList.add('active');
    item.addEventListener('click', async () => {
      selectedMac = d.mac;
      renderList();
      await refreshDeviceInfo();
    });
    deviceList.appendChild(item);

    if (identityLink) {
      const link = item.querySelector('.identity-link');
      link.addEventListener('click', async (e) => {
        e.preventDefault();
        e.stopPropagation();
        selectedMac = link.getAttribute('data-mac');
        renderList();
        await refreshDeviceInfo();
      });
    }
  });

  if (devices.length === 0) {
    const empty = document.createElement('div');
    empty.className = "list-group-item text-secondary";
    empty.textContent = "No devices yet. Turn scan on and put your speaker in pairing mode.";
    deviceList.appendChild(empty);
  }

  if (!selectedMac && devices[0]) selectedMac = devices[0].mac;
}

// --- API calls ---
async function fetchDevices() {
  const res = await fetch('/api/devices?audio_only=' + (audioOnly ? '1' : '0'));
  const data = await res.json();
  devices = data.devices || [];
  renderList();
  await refreshDeviceInfo();
}

async function refreshDeviceInfo() {
  if (!selectedMac) { renderStatus(null); return; }
  const res = await fetch('/api/info?mac=' + encodeURIComponent(selectedMac));
  const info = await res.json();
  renderStatus(info);

  const idx = devices.findIndex(d => d.mac === selectedMac);
  if (idx >= 0) {
    devices[idx] = { ...devices[idx], ...info, alias: info.alias || devices[idx].alias };
    renderList();
  }
}

async function updateScanUI() {
  const js = await (await fetch('/api/scan_status')).json();
  const st = js.status || {};
  const running = !!js.running;
  const on = js.wanted || st.discovering || running;
  scanText.textContent = on ? "Scan Off" : "Scan On";
  scanMsg.innerHTML = on
    ? '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>Scanning…'
    : 'Idle';
  if (on && !polling) {
    polling = setInterval(fetchDevices, 2500);
  } else if (!on && polling) {
    clearInterval(polling); polling = null;
  }
}

// --- Event handlers ---
scanToggle.addEventListener('click', async () => {
  scanToggle.disabled = true;
  try {
    const turningOn = scanText.textContent.includes("On");
    await fetch(turningOn ? '/api/scan_on' : '/api/scan_off', { method: 'POST' });
    await updateScanUI();
    if (!turningOn) {
      await fetchDevices();
    }
  } finally {
    scanToggle.disabled = false;
  }
});

connectBtn.addEventListener('click', async () => {
  if (!selectedMac) return;
  connectBtn.disabled = true;
  try {
    const res = await fetch('/api/connect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mac: selectedMac })
    });
    const data = await res.json();
    showLogRAW(data.log || "");
    if (!data.ok) alert("Connect failed" + (data.stage ? ` (stage: ${data.stage})` : ""));
  } catch (e) {
    showLogRAW(String(e));
    alert("Connect failed");
  }
  await refreshDeviceInfo();
});

disconnectBtn.addEventListener('click', async () => {
  if (!selectedMac) return;
  disconnectBtn.disabled = true;
  try {
    const res = await fetch('/api/disconnect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mac: selectedMac })
    });
    const data = await res.json();
    showLogRAW(data.log || "");
    if (!data.ok) alert("Disconnect may not have completed");
  } catch (e) {
    showLogRAW(String(e));
    alert("Disconnect failed");
  }
  await refreshDeviceInfo();
});

forgetBtn.addEventListener('click', async () => {
  if (!selectedMac) return;
  if (!confirm("Forget this device? This will unpair and remove it.")) return;
  forgetBtn.disabled = true;
  try {
    const res = await fetch('/api/forget', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mac: selectedMac })
    });
    const data = await res.json();
    showLogRAW(data.log || "");
    if (!data.ok) alert("Forget may not have completed");
  } catch (e) {
    showLogRAW(String(e));
    alert("Forget failed");
  }
  await fetchDevices();
  selectedMac = devices[0]?.mac || "";
  await refreshDeviceInfo();
  forgetBtn.disabled = false;
});

testAudioBtn.addEventListener('click', async () => {
  testAudioBtn.disabled = true;
  try {
    const res = await fetch('/api/test_audio', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mac: selectedMac })
    });
    const data = await res.json();
    showLogRAW(data.log || "");
    if (!data.ok) alert('Test audio failed');
  } catch (e) {
    showLogRAW(String(e));
    alert('Test audio failed');
  }
  testAudioBtn.disabled = false;
});

refreshBtn.addEventListener('click', async () => {
  refreshBtn.disabled = true;
  try {
    await fetchDevices();
  } finally {
    refreshBtn.disabled = false;
  }
});

audioOnlyChk.addEventListener('change', async () => {
  audioOnly = audioOnlyChk.checked;
  await fetchDevices();
});


async function loadAp(){
  try {
    const res = await fetch('/api/ap');
    const data = await res.json();
    if (apSsid) apSsid.value = data.ssid || '';
  } catch(e) {}
}

async function setAp(){
  const ssid = apSsid.value.trim();
  if (!ssid) return;
  apSsidBtn.disabled = true;
  try {
    await fetch('/api/ap', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ssid})});
  } finally {
    apSsidBtn.disabled = false;
  }
}

async function updateWifiInfo(){
  try{
    const res = await fetch('/api/wifi_info');
    const data = await res.json();
    const ifaces = Object.keys(data || {});
    if (ifaces.length){
      const parts = [];
      ifaces.forEach(iface => {
        const info = data[iface] || {};
        if (info.ip){
          parts.push(`${iface}: ${info.ip}/${info.mask || '?'}, GW: ${info.gateway || '?'}`);
        }
      });
      wifiInfo.textContent = parts.join(' | ') || 'No IP address';
    } else {
      wifiInfo.textContent = 'No IP address';
    }
  } catch(e){
    wifiInfo.textContent = 'No IP address';
  }
}

async function scanWifi(){
  scanWifiBtn.disabled = true;
  wifiList.innerHTML = '';
  try {
    const res = await fetch('/api/wifi');
    const data = await res.json();
    const nets = data.networks || [];
    if (data.has_wifi === false) {
      const li=document.createElement('li');
      li.className='list-group-item text-danger';
      li.textContent='No Wi-Fi interface detected';
      wifiList.appendChild(li);
    } else if (nets.length === 0){
      const li=document.createElement('li');
      li.className='list-group-item text-secondary';
      li.textContent='No networks';
      wifiList.appendChild(li);
    } else {
      nets.forEach(n => {
        const li=document.createElement('li');
        li.className='list-group-item list-group-item-action';
        li.textContent=n;
        li.addEventListener('click', ()=>connectWifi(n));
        wifiList.appendChild(li);
      });
    }
  } finally {
    scanWifiBtn.disabled = false;
  }
}

async function connectWifi(ssid){
  await fetch('/api/wifi', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ssid})});
  await updateWifiInfo();
}
// Copy / Clear log
clearLogBtn?.addEventListener('click', () => showLogRAW(""));
copyLogBtn?.addEventListener('click', async () => {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(lastLogRaw);
    } else {
      const ta = document.createElement('textarea');
      ta.value = lastLogRaw;
      document.body.appendChild(ta);
      ta.select(); document.execCommand('copy'); ta.remove();
    }
    copyLogBtn.classList.replace('btn-outline-secondary', 'btn-success');
    copyLogBtn.textContent = 'Copied';
    setTimeout(() => {
      copyLogBtn.textContent = 'Copy';
      copyLogBtn.classList.replace('btn-success', 'btn-outline-secondary');
    }, 1200);
  } catch (e) {
    alert('Copy failed: ' + e);
  }
});


apSsidBtn?.addEventListener('click', setAp);
scanWifiBtn?.addEventListener('click', scanWifi);

// --- Init ---
(async function init() {
  try {
    await updateScanUI();
    await fetchDevices();
    await loadAp();
    await updateWifiInfo();
  } catch (e) {
    showLogRAW(String(e));
  }
})();
