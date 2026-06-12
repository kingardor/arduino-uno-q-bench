// SPDX-License-Identifier: MPL-2.0 — UNO Q VLM Chat
'use strict';
const $ = s => document.querySelector(s);
const logEl = $('#log'), statusEl = $('#status'), modelSel = $('#model'),
      stageLabel = $('#stage-label'), textEl = $('#text'), sendBtn = $('#send'),
      fileEl = $('#file'), attachBtn = $('#attach-btn'), chip = $('#attach-chip'),
      thumb = $('#attach-thumb'), attachRemove = $('#attach-remove'), form = $('#composer');

let messages = [];          // {role, content, image?}
let pendingImage = null;    // data URL for next send
let busy = false;

/* ---------------- config ---------------- */
async function loadConfig() {
  try {
    const c = await (await fetch('/config')).json();
    (c.models || []).forEach(m => {
      const o = document.createElement('option');
      o.value = m.id; o.textContent = m.label; modelSel.appendChild(o);
    });
    if (c.default) modelSel.value = c.default;
  } catch (e) {
    const o = document.createElement('option');
    o.value = 'smolvlm'; o.textContent = 'SmolVLM2-256M ⚡'; modelSel.appendChild(o);
  }
}

/* ---------------- viz state machine ---------------- */
const STATUS = { boot:'booting', idle:'idle', processing:'thinking', done:'done', error:'error', detecting:'scanning' };
const LABEL  = { boot:'waking up…', idle:'ready', processing:'thinking…', done:'done', error:'error', detecting:'scanning…' };
let viz = 'boot', bootStart = performance.now(), doneAt = 0;
function setViz(s) {
  viz = s;
  if (s === 'done') doneAt = performance.now();
  if (s === 'boot') bootStart = performance.now();
  statusEl.dataset.state = s;
  statusEl.textContent = STATUS[s] || s;
  stageLabel.textContent = LABEL[s] || '';
}

/* ---------------- canvas animation ---------------- */
const cvs = $('#stage'), ctx = cvs.getContext('2d');
let DPR = Math.min(2, window.devicePixelRatio || 1);
function resize() {
  const r = cvs.getBoundingClientRect();
  DPR = Math.min(2, window.devicePixelRatio || 1);
  cvs.width = Math.max(1, r.width * DPR); cvs.height = Math.max(1, r.height * DPR);
}
window.addEventListener('resize', resize);

const COL = { boot:'#ffb23e', idle:'#2ad1d1', processing:'#45e0e0', done:'#16c784', error:'#ff5a5a', detecting:'#45e0e0' };
const NP = 46;
let particles = [];
for (let i = 0; i < NP; i++) {
  particles.push({ a: Math.random()*6.28, base: 26 + Math.random()*58,
                   sp: 0.2 + Math.random()*0.7, sz: 1 + Math.random()*2.2, ph: Math.random()*6 });
}
function hexA(hex, a) {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${n>>16&255},${n>>8&255},${n&255},${a})`;
}
function dot(x, y, r, c, alpha) {
  ctx.globalAlpha = alpha; ctx.fillStyle = c;
  ctx.beginPath(); ctx.arc(x, y, r, 0, 6.2832); ctx.fill(); ctx.globalAlpha = 1;
}
function drawCheck(cx, cy, r) {
  ctx.strokeStyle = '#eaffff'; ctx.lineWidth = 3*DPR; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  ctx.beginPath();
  ctx.moveTo(cx - r*0.55, cy + r*0.05);
  ctx.lineTo(cx - r*0.12, cy + r*0.48);
  ctx.lineTo(cx + r*0.62, cy - r*0.5);
  ctx.stroke();
}
let last = performance.now();
function frame(now) {
  const dt = Math.min(0.05, (now - last) / 1000); last = now;
  const w = cvs.width, h = cvs.height, cx = w/2, cy = h/2, t = now/1000, s = DPR;
  ctx.clearRect(0, 0, w, h);
  const color = COL[viz] || COL.idle;

  let speed = 1, coreR = 14*s, reach = 1;
  if (viz === 'boot') { const e = Math.min(1,(now-bootStart)/2600); speed = .4+e*1.2; coreR=(3+18*e)*s; reach=e; }
  else if (viz === 'idle') { speed = .8; coreR = (12+3*Math.sin(t*1.6))*s; }
  else if (viz === 'processing') { speed = 3.4; coreR = (11+4*Math.sin(t*7))*s; }
  else if (viz === 'done') { speed = 1.4; coreR = 16*s; reach = 1.5; }
  else if (viz === 'error') { speed = .6; coreR = (13+3*Math.sin(t*20))*s; }
  else if (viz === 'detecting') { speed = 2.5; coreR = (12+3*Math.sin(t*6))*s; }

  // soft core glow
  const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, coreR*4.2);
  g.addColorStop(0, color); g.addColorStop(.28, hexA(color, .45)); g.addColorStop(1, 'transparent');
  ctx.fillStyle = g; ctx.beginPath(); ctx.arc(cx, cy, coreR*4.2, 0, 6.2832); ctx.fill();
  dot(cx, cy, coreR, '#eaffff', .92);

  // orbiting particles (vertically squashed to fit the band)
  for (const p of particles) {
    p.a += p.sp * speed * dt;
    let rr;
    if (viz === 'processing') rr = (p.base*0.72 + 6*Math.sin(t*5 + p.ph)) * s;
    else if (viz === 'boot')  rr = p.base * reach * s;
    else if (viz === 'done')  rr = (p.base*reach + 8*Math.sin(t*3 + p.ph)) * s;
    else                      rr = (p.base + 5*Math.sin(t*1.2 + p.ph)) * s;
    const x = cx + Math.cos(p.a)*rr, y = cy + Math.sin(p.a)*rr*0.6;
    dot(x, y, p.sz*s, color, .85);
  }

  if (viz === 'processing') {
    ctx.strokeStyle = color; ctx.lineWidth = 2.5*s; ctx.globalAlpha = .9;
    const a0 = t*4.5; ctx.beginPath(); ctx.arc(cx, cy, coreR*2.5, a0, a0+1.8); ctx.stroke();
    ctx.globalAlpha = 1;
  }
  if (viz === 'detecting') {
    const a = t*3.2; ctx.strokeStyle = color; ctx.lineWidth = 2.5*s; ctx.globalAlpha = .9;
    ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.cos(a)*62*s, cy + Math.sin(a)*62*s*0.6); ctx.stroke();
    ctx.globalAlpha = 1;
  }
  if (viz === 'done') {
    const age = (now - doneAt)/1000;
    ctx.strokeStyle = hexA(color, Math.max(0, 1 - age/1.3)); ctx.lineWidth = 3*s;
    ctx.beginPath(); ctx.arc(cx, cy, age*150*s, 0, 6.2832); ctx.stroke();
    drawCheck(cx, cy, coreR*1.05);
  }
  requestAnimationFrame(frame);
}

/* ---------------- chat ---------------- */
function addMsg(role, content, image) {
  const el = document.createElement('div');
  el.className = 'msg ' + (role === 'user' ? 'user' : 'bot');
  if (image) { const im = document.createElement('img'); im.className = 'att'; im.src = image; el.appendChild(im); }
  const tx = document.createElement('span'); tx.textContent = content; el.appendChild(tx);
  logEl.appendChild(el); logEl.scrollTop = logEl.scrollHeight;
  return el;
}
function thinkingMsg() {
  const el = document.createElement('div'); el.className = 'msg bot thinking';
  el.innerHTML = '<span class="dots"><i></i><i></i><i></i></span>';
  logEl.appendChild(el); logEl.scrollTop = logEl.scrollHeight; return el;
}
async function send() {
  const txt = textEl.value.trim();
  if ((!txt && !pendingImage) || busy) return;
  busy = true; sendBtn.disabled = true;
  const image = pendingImage;
  addMsg('user', txt || '🖼 image', image);
  messages.push({ role: 'user', content: txt || 'Describe this image.', image: image || undefined });
  clearAttachment(); textEl.value = ''; autoGrow();

  const think = thinkingMsg(); setViz('processing');

  // send history, but keep only the most-recent image to spare bandwidth/model
  let lastImg = -1;
  messages.forEach((m, i) => { if (m.image) lastImg = i; });
  const payload = messages.map((m, i) => ({
    role: m.role, content: m.content, image: (i === lastImg ? m.image : undefined)
  }));

  try {
    const r = await fetch('/chat', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: payload, model: modelSel.value })
    });
    const d = await r.json(); think.remove();
    if (d.ok) {
      const el = addMsg('bot', d.reply || '(no reply)');
      if (d.timing != null) {
        const m = document.createElement('span'); m.className = 'meta';
        m.textContent = `${modelSel.options[modelSel.selectedIndex].text} · ${d.timing}s`;
        el.appendChild(m);
      }
      messages.push({ role: 'assistant', content: d.reply || '' });
      setViz('done'); setTimeout(() => { if (viz === 'done') setViz('idle'); }, 1300);
    } else {
      addMsg('bot', '⚠ ' + (d.error || 'error')); setViz('error');
      setTimeout(() => { if (viz === 'error') setViz('idle'); }, 1600);
    }
  } catch (e) {
    think.remove(); addMsg('bot', '⚠ network error: ' + e.message);
    setViz('error'); setTimeout(() => { if (viz === 'error') setViz('idle'); }, 1600);
  }
  busy = false; sendBtn.disabled = false; textEl.focus();
}

/* ---------------- image input ---------------- */
function setAttachment(url) { pendingImage = url; thumb.src = url; chip.classList.remove('hidden'); }
function clearAttachment() { pendingImage = null; chip.classList.add('hidden'); fileEl.value = ''; }
function downscale(dataURL, max, cb) {
  const img = new Image();
  img.onload = () => {
    const sc = Math.min(1, max / Math.max(img.width, img.height));
    const c = document.createElement('canvas');
    c.width = Math.round(img.width*sc); c.height = Math.round(img.height*sc);
    c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
    cb(c.toDataURL('image/jpeg', 0.85));
  };
  img.onerror = () => cb(dataURL);
  img.src = dataURL;
}
function readImg(file) {
  if (!file) return;
  const r = new FileReader();
  r.onload = () => downscale(r.result, 512, setAttachment);
  r.readAsDataURL(file);
}
attachBtn.onclick = () => fileEl.click();
fileEl.onchange = () => readImg(fileEl.files[0]);
attachRemove.onclick = clearAttachment;
['dragenter', 'dragover'].forEach(ev => window.addEventListener(ev, e => {
  if (e.dataTransfer && [...e.dataTransfer.types].includes('Files')) { e.preventDefault(); document.body.classList.add('dragging'); }
}));
window.addEventListener('dragleave', e => { if (!e.relatedTarget) document.body.classList.remove('dragging'); });
window.addEventListener('drop', e => {
  if (document.getElementById('app').dataset.tab !== 'chat') return;
  e.preventDefault(); document.body.classList.remove('dragging');
  const f = [...(e.dataTransfer.files || [])].find(f => f.type.startsWith('image/'));
  if (f) readImg(f);
});
window.addEventListener('paste', e => {
  if (document.getElementById('app').dataset.tab !== 'chat') return;
  const it = [...(e.clipboardData.items || [])].find(i => i.type.startsWith('image/'));
  if (it) readImg(it.getAsFile());
});

/* ---------------- composer ---------------- */
function autoGrow() { textEl.style.height = 'auto'; textEl.style.height = Math.min(140, textEl.scrollHeight) + 'px'; }
textEl.addEventListener('input', autoGrow);
textEl.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } });
form.addEventListener('submit', e => { e.preventDefault(); send(); });

/* ---------------- boot ---------------- */
resize();
setViz('boot');
loadConfig();
fetch('/boot', { method: 'POST' }).catch(() => {});  // replay the physical matrix twinkle on every page load
requestAnimationFrame(frame);
setTimeout(() => {
  if (viz === 'boot') setViz('idle');
  addMsg('bot', "Hey — I'm UNO Q. Drop in an image, or just ask me something.");
}, 3000);

/* ---------------- tabs ---------------- */
const appEl = document.getElementById('app');
document.querySelectorAll('#tabs .tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#tabs .tab').forEach(b => b.classList.toggle('active', b === btn));
    const tab = btn.dataset.tab; appEl.dataset.tab = tab;
    document.getElementById('chat-view').classList.toggle('active', tab === 'chat');
    document.getElementById('detect-view').classList.toggle('active', tab === 'detect');
    if (tab === 'detect' && detImage) detDraw();
  });
});

/* ---------------- detect ---------------- */
const detCanvas = document.getElementById('det-canvas'), detCtx = detCanvas.getContext('2d');
const detFile = document.getElementById('det-file'), detUpload = document.getElementById('det-upload');
const detRun = document.getElementById('det-run'), detMeta = document.getElementById('det-meta');
const detResults = document.getElementById('det-results'), detEmpty = document.getElementById('det-empty');
let detImage = null, detBoxes = [];
const DET_COLORS = ['#00e5ff','#ff2bd6','#22ff9c','#ffb23e','#b14bff','#45e0e0','#ff6fe4','#ffd23e'];
const detClassesEl = document.getElementById('det-classes');
if (detClassesEl) detClassesEl.textContent = 'person · car · dog · cat · bottle · cup · phone · laptop';

function detLoad(file) {
  if (!file) return;
  const r = new FileReader();
  r.onload = () => {
    const img = new Image();
    img.onload = () => {
      detImage = { dataURL: r.result, img, w: img.width, h: img.height }; detBoxes = [];
      detEmpty.classList.add('hidden'); detMeta.textContent = ''; detResults.innerHTML = ''; detDraw();
    };
    img.src = r.result;
  };
  r.readAsDataURL(file);
}
function detDraw() {
  if (!detImage) return;
  const wrap = document.getElementById('det-stage').getBoundingClientRect();
  const scale = Math.min(wrap.width / detImage.w, wrap.height / detImage.h) || 1;
  const cw = Math.max(1, Math.round(detImage.w * scale)), ch = Math.max(1, Math.round(detImage.h * scale));
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  detCanvas.width = cw * dpr; detCanvas.height = ch * dpr;
  detCanvas.style.width = cw + 'px'; detCanvas.style.height = ch + 'px';
  detCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
  detCtx.clearRect(0, 0, cw, ch);
  detCtx.drawImage(detImage.img, 0, 0, cw, ch);
  const s = cw / detImage.w;
  detBoxes.forEach((b, i) => {
    const c = DET_COLORS[i % DET_COLORS.length];
    const x = b.x1 * s, y = b.y1 * s, w = (b.x2 - b.x1) * s, h = (b.y2 - b.y1) * s;
    detCtx.lineWidth = 2; detCtx.strokeStyle = c; detCtx.shadowColor = c; detCtx.shadowBlur = 8;
    detCtx.strokeRect(x, y, w, h); detCtx.shadowBlur = 0;
    const label = `${b.label} ${Math.round(b.conf * 100)}%`;
    detCtx.font = '600 11px ui-monospace, monospace';
    const tw = detCtx.measureText(label).width + 8;
    detCtx.fillStyle = c; detCtx.fillRect(x, Math.max(0, y - 15), tw, 15);
    detCtx.fillStyle = '#04070a'; detCtx.fillText(label, x + 4, Math.max(11, y - 4));
  });
}
window.addEventListener('resize', () => { if (detImage && appEl.dataset.tab === 'detect') detDraw(); });
detUpload.onclick = () => detFile.click();
detFile.onchange = () => detLoad(detFile.files[0]);

async function runDetect() {
  if (!detImage || detRun.disabled) return;
  detRun.disabled = true; detMeta.textContent = 'scanning…'; setViz('detecting');
  try {
    const r = await fetch('/detect', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image: detImage.dataURL }) });
    const d = await r.json();
    if (d.ok) {
      detBoxes = (d.boxes || []).filter(b => b.conf >= 0.45);
      detDraw();
      detMeta.textContent = `${detBoxes.length} object${detBoxes.length === 1 ? '' : 's'} · ${d.ms} ms`;
      detResults.innerHTML = '';
      detBoxes.forEach((b, i) => {
        const c = DET_COLORS[i % DET_COLORS.length];
        const el = document.createElement('span'); el.className = 'det-chip';
        el.style.borderColor = c; el.style.color = c;
        el.textContent = `${b.label} ${Math.round(b.conf * 100)}%`;
        detResults.appendChild(el);
      });
      if (!detBoxes.length)
        detResults.innerHTML = '<span class="det-chip muted">no objects ≥ 45%</span>';
      setViz('done'); setTimeout(() => { if (viz === 'done') setViz('idle'); }, 1200);
    } else {
      detMeta.textContent = '⚠ ' + (d.error || 'error'); setViz('error'); setTimeout(() => { if (viz === 'error') setViz('idle'); }, 1500);
    }
  } catch (e) {
    detMeta.textContent = '⚠ ' + e.message; setViz('error'); setTimeout(() => { if (viz === 'error') setViz('idle'); }, 1500);
  }
  detRun.disabled = false;
}
detRun.onclick = runDetect;
window.addEventListener('drop', e => {
  if (appEl.dataset.tab !== 'detect') return;
  e.preventDefault(); document.body.classList.remove('dragging');
  const f = [...(e.dataTransfer.files || [])].find(f => f.type.startsWith('image/'));
  if (f) detLoad(f);
});
