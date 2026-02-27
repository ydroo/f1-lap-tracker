const API = 'http://localhost:8000';

let sessionDrivers = []; // pilotes de la session chargée
let driversData    = []; // données GPS de chaque slot
let trackData      = null; // circuit de référence (commun)
let corners        = [];

let playing        = false;
let animId         = null;
let animTime       = 0;     // temps courant de l'animation en secondes
let lastTs         = null;  // timestamp rAF précédent
let maxTime        = 0;     // durée max parmi tous les pilotes
let userRotation   = 0;
let playbackSpeed  = 1;

const $ = id => document.getElementById(id);
const loading = $('loading');
const canvas  = $('canvas');
const ctx     = canvas.getContext('2d');

(async () => {
	loading.classList.add('active');
	const years = await fetch(`${API}/years`).then(r => r.json());
	$('year').innerHTML = years.map(y => `<option value="${y}">${y}</option>`).join('');
	$('year').value = '2023';
	await loadEvents();
	loading.classList.remove('active');
})();

let slotCounter = 0;
addSlot();

(function injectRotationButtons() {
	const controls = $('controls');
	const btn = (label, fn) => {
		const b = document.createElement('button');
		b.textContent = label;
		b.style.cssText = 'background:#222;color:#fff;border:1px solid #444;padding:6px 12px;cursor:pointer;border-radius:4px;font-size:16px;flex-shrink:0;';
		b.addEventListener('click', fn);
		return b;
	};
	const wrap = document.createElement('div');
	wrap.style.cssText = 'display:flex;gap:8px;align-items:center;margin-top:8px;';
	const label = document.createElement('span');
	label.textContent = 'Rotation :';
	label.style.cssText = 'color:#aaa;font-size:13px;';
	wrap.appendChild(label);
	wrap.appendChild(btn('↺', () => applyRotation(-Math.PI / 24)));
	wrap.appendChild(btn('↻', () => applyRotation(+Math.PI / 24)));
	wrap.appendChild(btn('Reset', () => { userRotation = 0; saveRotation(); draw(); }));

	const sep = document.createElement('span');
	sep.style.cssText = 'color:#444;margin:0 4px;';
	sep.textContent = '|';
	wrap.appendChild(sep);
	const speedLabel = document.createElement('span');
	speedLabel.style.cssText = 'color:#aaa;font-size:13px;';
	speedLabel.textContent = 'Vitesse :';
	wrap.appendChild(speedLabel);
	const speeds = [0.5, 1, 2, 4];
	let speedBtns;
	speedBtns = speeds.map(s => {
		const b = btn(`${s}x`, () => {
			playbackSpeed = s;
			speedBtns.forEach(([sb, sv]) => sb.style.background = sv === s ? '#ff1744' : '#222');
		});
		b.style.background = s === 1 ? '#ff1744' : '#222';
		wrap.appendChild(b);
		return [b, s];
	});
	controls.appendChild(wrap);
})();

function applyRotation(delta) {
	userRotation += delta;
	saveRotation();
	draw();
}
function saveRotation() {
	const key = `rotation_${$('year').value}_${$('event').value}`;
	localStorage.setItem(key, userRotation);
}
function loadRotation() {
	const key = `rotation_${$('year').value}_${$('event').value}`;
	const saved = localStorage.getItem(key);
	userRotation = saved !== null ? parseFloat(saved) : 0;
}


async function loadEvents() {
	const year = $('year').value;
	loading.classList.add('active');
	const events = await fetch(`${API}/events/${year}`).then(r => r.json());
	$('event').innerHTML = events.map(e => `<option value="${e.circuit}">${e.circuit}</option>`).join('');
	$('event').disabled = false;
	$('session').disabled = false;
	$('load').disabled = false;
	loading.classList.remove('active');
}

async function loadSession() {
	const year    = $('year').value;
	const event   = $('event').value;
	const session = $('session').value;

	loading.classList.add('active');
	sessionDrivers = await fetch(`${API}/drivers/${year}/${encodeURIComponent(event)}/${session}`).then(r => r.json());

	document.querySelectorAll('.driver-slot').forEach(slot => {
		populateDriverSelect(slot);
	});

	$('driver-actions').style.display = 'flex';
	loading.classList.remove('active');
}

function addSlot() {
	slotCounter++;
	const id = slotCounter;

	const slot = document.createElement('div');
	slot.className = 'driver-slot';
	slot.dataset.slotId = id;

	const colorDot = document.createElement('div');
	colorDot.className = 'driver-color';
	colorDot.style.background = '#555';

	const driverGroup = document.createElement('div');
	driverGroup.className = 'control-group';
	const driverLabel = document.createElement('label');
	driverLabel.textContent = `Pilote ${id}`;
	const driverSelect = document.createElement('select');
	driverSelect.className = 'driver-select';
	driverSelect.disabled = sessionDrivers.length === 0;
	driverGroup.appendChild(driverLabel);
	driverGroup.appendChild(driverSelect);

	const lapGroup = document.createElement('div');
	lapGroup.className = 'control-group';
	const lapLabel = document.createElement('label');
	lapLabel.textContent = 'Tour';
	const lapSelect = document.createElement('select');
	lapSelect.className = 'lap-select';
	lapSelect.disabled = true;
	lapGroup.appendChild(lapLabel);
	lapGroup.appendChild(lapSelect);

	const removeBtn = document.createElement('button');
	removeBtn.className = 'slot-remove';
	removeBtn.textContent = '×';
	removeBtn.addEventListener('click', () => removeSlot(slot));

	slot.appendChild(colorDot);
	slot.appendChild(driverGroup);
	slot.appendChild(lapGroup);
	slot.appendChild(removeBtn);

	$('drivers-container').appendChild(slot);

	if (sessionDrivers.length > 0) populateDriverSelect(slot);

	driverSelect.addEventListener('change', () => loadLapsForSlot(slot));
}

function removeSlot(slot) {
	const container = $('drivers-container');
	if (container.children.length <= 1) return; // garder au moins 1
	container.removeChild(slot);
	checkVisualizeButton();
}

function populateDriverSelect(slot) {
	const driverSelect = slot.querySelector('.driver-select');
	driverSelect.innerHTML = sessionDrivers.map(d =>
		`<option value="${d.code}">${d.code} — ${d.team}</option>`
	).join('');
	driverSelect.disabled = false;
	loadLapsForSlot(slot);
}

async function loadLapsForSlot(slot) {
	const year    = $('year').value;
	const event   = $('event').value;
	const session = $('session').value;
	const driver  = slot.querySelector('.driver-select').value;
	const lapSelect = slot.querySelector('.lap-select');
	const colorDot  = slot.querySelector('.driver-color');
	const driverInfo = sessionDrivers.find(d => d.code === driver);
	if (driverInfo) colorDot.style.background = `#${driverInfo.team_color}`;

	lapSelect.disabled = true;
	lapSelect.innerHTML = '<option>Chargement...</option>';

	const laps = await fetch(`${API}/laps/${year}/${encodeURIComponent(event)}/${session}/${driver}`).then(r => r.json());
	lapSelect.innerHTML = laps.map(l => {
		const ms   = l.lap_time_ms;
		const time = ms ? `${Math.floor(ms/60000)}:${String(Math.floor((ms%60000)/1000)).padStart(2,'0')}.${String(ms%1000).padStart(3,'0')}` : '?';
		return `<option value="${l.lap_number}">Tour ${l.lap_number} — ${time} (${l.compound || '?'})</option>`;
	}).join('');
	lapSelect.disabled = false;

	checkVisualizeButton();
}

function checkVisualizeButton() {
	const allReady = [...document.querySelectorAll('.lap-select')].every(s => !s.disabled);
	$('visualize').disabled = !allReady;
}

async function visualize() {
	const year    = $('year').value;
	const event   = $('event').value;
	const session = $('session').value;

	loading.classList.add('active');
	playing  = false;
	animTime = 0;
	lastTs   = null;
	$('play').textContent = '▶';

	const slots = [...document.querySelectorAll('.driver-slot')];
	const fetches = slots.map(slot => {
		const driver = slot.querySelector('.driver-select').value;
		const lap    = slot.querySelector('.lap-select').value;
		return fetch(`${API}/position/${year}/${encodeURIComponent(event)}/${session}/${driver}/${lap}`).then(r => r.json());
	});

	const results = await Promise.all(fetches);

	trackData = results[0].track;
	corners   = results[0].corners || [];

	driversData = results.map(r => ({
		code:  r.driver.code,
		color: r.driver.color,
		x:     r.driver.x,
		y:     r.driver.y,
		t:     r.driver.t,
	}));

	maxTime = Math.max(...driversData.map(d => d.t[d.t.length - 1]));

	loadRotation();
	$('controls').classList.add('active');
	setupCanvas();
	draw();
	loading.classList.remove('active');
}

function setupCanvas() {
	const rect = canvas.getBoundingClientRect();
	canvas.width  = rect.width  * devicePixelRatio;
	canvas.height = rect.height * devicePixelRatio;
	ctx.scale(devicePixelRatio, devicePixelRatio);
}

function buildTransform() {
	const w = canvas.width  / devicePixelRatio;
	const h = canvas.height / devicePixelRatio;

	const cos = Math.cos(userRotation);
	const sin = Math.sin(userRotation);
	const rotPt = (x, y) => [x * cos - y * sin, x * sin + y * cos];

	const cornerTextX = corners.map(c => c.text_x);
	const cornerTextY = corners.map(c => c.text_y);

	const allDriverX = driversData.flatMap(d => d.x);
	const allDriverY = driversData.flatMap(d => d.y);

	const allRawX = [...trackData.x, ...allDriverX, ...cornerTextX];
	const allRawY = [...trackData.y, ...allDriverY, ...cornerTextY];

	const rotated = allRawX.map((x, i) => rotPt(x, allRawY[i]));
	const allX = rotated.map(p => p[0]);
	const allY = rotated.map(p => p[1]);

	const minX = Math.min(...allX), maxX = Math.max(...allX);
	const minY = Math.min(...allY), maxY = Math.max(...allY);

	const padding = 15;
	const scaleX = (w - padding * 2) / (maxX - minX);
	const scaleY = (h - padding * 2) / (maxY - minY);
	const scale  = Math.min(scaleX, scaleY);

	const offsetX = (w - (maxX - minX) * scale) / 2 - minX * scale;
	const offsetY = (h + (maxY + minY) * scale) / 2;

	return (x, y) => {
		const [rx, ry] = rotPt(x, y);
		return [rx * scale + offsetX, -ry * scale + offsetY];
	};
}

function frameForTime(driverData, time) {
	const t = driverData.t;
	let lo = 0, hi = t.length - 1;
	while (lo < hi) {
		const mid = (lo + hi + 1) >> 1;
		if (t[mid] <= time) lo = mid;
		else hi = mid - 1;
	}
	return lo;
}

function drawTrack(transform) {
	const path = new Path2D();
	const [sx, sy] = transform(trackData.x[0], trackData.y[0]);
	path.moveTo(sx, sy);
	for (let i = 1; i < trackData.x.length; i++) {
		const [x, y] = transform(trackData.x[i], trackData.y[i]);
		path.lineTo(x, y);
	}
	path.closePath();

	ctx.strokeStyle = '#888';
	ctx.lineWidth   = 18;
	ctx.lineJoin    = 'round';
	ctx.lineCap     = 'round';
	ctx.stroke(path);

	ctx.strokeStyle = '#2e2e2e';
	ctx.lineWidth   = 12;
	ctx.stroke(path);
}

function drawCornerLabels(transform) {
	if (!corners.length) return;
	for (const c of corners) {
		const [tx, ty] = transform(c.track_x, c.track_y);
		const [lx, ly] = transform(c.text_x,  c.text_y);

		ctx.strokeStyle = 'rgba(255,255,255,0.25)';
		ctx.lineWidth   = 1;
		ctx.beginPath();
		ctx.moveTo(tx, ty);
		ctx.lineTo(lx, ly);
		ctx.stroke();

		ctx.fillStyle = '#444';
		ctx.beginPath();
		ctx.arc(lx, ly, 10, 0, Math.PI * 2);
		ctx.fill();

		ctx.fillStyle    = '#fff';
		ctx.font         = '9px monospace';
		ctx.textAlign    = 'center';
		ctx.textBaseline = 'middle';
		ctx.fillText(c.number, lx, ly);
	}
}

function draw() {
	if (!trackData) return;

	const w = canvas.width  / devicePixelRatio;
	const h = canvas.height / devicePixelRatio;

	ctx.fillStyle = '#12121a';
	ctx.fillRect(0, 0, w, h);

	const transform = buildTransform();

	drawTrack(transform);
	drawCornerLabels(transform);

	// Trajectoires et voitures
	for (const d of driversData) {
		const frame = frameForTime(d, animTime);
		const color = d.color.startsWith('#') ? d.color : `#${d.color}`;

		// Trajectoire parcourue
		if (frame > 0) {
			ctx.strokeStyle = color;
			ctx.lineWidth   = 2;
			ctx.lineJoin    = 'round';
			ctx.lineCap     = 'round';
			ctx.beginPath();
			const [px0, py0] = transform(d.x[0], d.y[0]);
			ctx.moveTo(px0, py0);
			for (let i = 1; i <= frame; i++) {
				const [px, py] = transform(d.x[i], d.y[i]);
				ctx.lineTo(px, py);
			}
			ctx.stroke();
		}

		// Point voiture
		const [cx, cy] = transform(d.x[frame], d.y[frame]);
		ctx.fillStyle = color;
		ctx.beginPath();
		ctx.arc(cx, cy, 6, 0, Math.PI * 2);
		ctx.fill();

		ctx.strokeStyle = '#fff';
		ctx.lineWidth   = 1.5;
		ctx.beginPath();
		ctx.arc(cx, cy, 7, 0, Math.PI * 2);
		ctx.stroke();

		// Label pilote
		ctx.fillStyle    = '#fff';
		ctx.font         = 'bold 10px monospace';
		ctx.textAlign    = 'center';
		ctx.textBaseline = 'bottom';
		ctx.fillText(d.code, cx, cy - 9);
	}
	$('progress-fill').style.width = `${(animTime / maxTime) * 100}%`;
}

function animate(ts) {
	if (!playing) return;

	if (lastTs === null) lastTs = ts;
	const delta = (ts - lastTs) / 1000;
	lastTs = ts;

	animTime += delta * playbackSpeed;

	if (animTime >= maxTime) {
		animTime = maxTime;
		playing  = false;
		$('play').textContent = '▶';
		draw();
		return;
	}

	draw();
	animId = requestAnimationFrame(animate);
}

$('year').addEventListener('change', loadEvents);
$('load').addEventListener('click', loadSession);
$('add-driver').addEventListener('click', addSlot);
$('visualize').addEventListener('click', visualize);

$('play').addEventListener('click', () => {
	if (!trackData) return;
	playing = !playing;
	$('play').textContent = playing ? '⏸' : '▶';
	if (playing) {
		lastTs = null;
		animId = requestAnimationFrame(animate);
	} else {
		cancelAnimationFrame(animId);
	}
});

$('progress').addEventListener('click', e => {
	if (!trackData) return;
	const rect    = $('progress').getBoundingClientRect();
	const percent = (e.clientX - rect.left) / rect.width;
	animTime = percent * maxTime;
	draw();
});

window.addEventListener('resize', () => {
	if (trackData) { setupCanvas(); draw(); }
});