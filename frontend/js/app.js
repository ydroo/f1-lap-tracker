const API = 'http://localhost:8000';
let data = null;
let frame = 0;
let playing = false;
let animId = null;
let userRotation = 0; // rotation en radians ajoutée par l'utilisateur

const $ = id => document.getElementById(id);
const loading = $('loading');
const canvas = $('canvas');
const ctx = canvas.getContext('2d');

// Injecter les boutons de rotation dans le DOM
(function injectRotationButtons() {
	const controls = $('controls');
	const btn = (label, fn) => {
		const b = document.createElement('button');
		b.textContent = label;
		b.style.cssText = 'background:#222;color:#fff;border:1px solid #444;padding:6px 12px;cursor:pointer;border-radius:4px;font-size:16px;';
		b.addEventListener('click', fn);
		return b;
	};
	const wrap = document.createElement('div');
	wrap.style.cssText = 'display:flex;gap:8px;align-items:center;margin-top:8px;';
	const label = document.createElement('span');
	label.textContent = 'Rotation :';
	label.style.cssText = 'color:#aaa;font-size:13px;';
	wrap.appendChild(label);
	wrap.appendChild(btn('↺', () => rotate(-Math.PI / 24)));
	wrap.appendChild(btn('↻', () => rotate(+Math.PI / 24)));
	wrap.appendChild(btn('Reset', () => { userRotation = 0; saveRotation(); draw(); }));
	controls.appendChild(wrap);
})();

function rotate(delta) {
	userRotation += delta;
	saveRotation();
	draw();
}

function saveRotation() {
	if (!data) return;
	const event = $('event').value;
	const year  = $('year').value;
	localStorage.setItem(`rotation_${year}_${event}`, userRotation);
}

function loadRotation() {
	const event = $('event').value;
	const year  = $('year').value;
	const saved = localStorage.getItem(`rotation_${year}_${event}`);
	userRotation = saved !== null ? parseFloat(saved) : 0;
}

(async () => {
	loading.classList.add('active');
	const years = await fetch(`${API}/years`).then(r => r.json());
	$('year').innerHTML = years.map(y => `<option value="${y}">${y}</option>`).join('');
	$('year').value = '2023';
	await loadEvents();
	loading.classList.remove('active');
})();

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
	const year = $('year').value;
	const event = $('event').value;
	const session = $('session').value;

	loading.classList.add('active');
	const drivers = await fetch(`${API}/drivers/${year}/${encodeURIComponent(event)}/${session}`).then(r => r.json());
	$('driver').innerHTML = drivers.map(d => `<option value="${d.code}">${d.code} — ${d.team}</option>`).join('');
	$('driver').disabled = false;
	await loadLaps();
	loading.classList.remove('active');
}

async function loadLaps() {
	const year = $('year').value;
	const event = $('event').value;
	const session = $('session').value;
	const driver = $('driver').value;

	const laps = await fetch(`${API}/laps/${year}/${encodeURIComponent(event)}/${session}/${driver}`).then(r => r.json());
	$('lap').innerHTML = laps.map(l => {
		const ms = l.lap_time_ms;
		const time = ms ? `${Math.floor(ms/60000)}:${String(Math.floor((ms%60000)/1000)).padStart(2,'0')}.${String(ms%1000).padStart(3,'0')}` : '?';
		return `<option value="${l.lap_number}">Tour ${l.lap_number} — ${time} (${l.compound || '?'})</option>`;
	}).join('');
	$('lap').disabled = false;
	$('visualize').disabled = false;
}

async function visualize() {
	const year = $('year').value;
	const event = $('event').value;
	const session = $('session').value;
	const driver = $('driver').value;
	const lap = $('lap').value;

	loading.classList.add('active');
	data = await fetch(`${API}/position/${year}/${encodeURIComponent(event)}/${session}/${driver}/${lap}`).then(r => r.json());
	frame = 0;
	playing = false;
	loadRotation(); // charger la rotation sauvegardée pour ce circuit
	$('controls').classList.add('active');
	setupCanvas();
	draw();
	loading.classList.remove('active');
}

function setupCanvas() {
	const rect = canvas.getBoundingClientRect();
	canvas.width = rect.width * devicePixelRatio;
	canvas.height = rect.height * devicePixelRatio;
	ctx.scale(devicePixelRatio, devicePixelRatio);
}

function buildTransform() {
	const w = canvas.width / devicePixelRatio;
	const h = canvas.height / devicePixelRatio;

	// Appliquer la rotation utilisateur aux coordonnées brutes
	const cos = Math.cos(userRotation);
	const sin = Math.sin(userRotation);
	const rotatePoint = (x, y) => [x * cos - y * sin, x * sin + y * cos];

	const cornerTextX = data.corners ? data.corners.map(c => c.text_x) : [];
	const cornerTextY = data.corners ? data.corners.map(c => c.text_y) : [];
	const allRawX = [...data.track.x, ...data.driver.x, ...cornerTextX];
	const allRawY = [...data.track.y, ...data.driver.y, ...cornerTextY];
	const rotated = allRawX.map((x, i) => rotatePoint(x, allRawY[i]));
	const allX = rotated.map(p => p[0]);
	const allY = rotated.map(p => p[1]);

	const minX = Math.min(...allX);
	const maxX = Math.max(...allX);
	const minY = Math.min(...allY);
	const maxY = Math.max(...allY);

	const padding = 15;
	const scaleX = (w - padding * 2) / (maxX - minX);
	const scaleY = (h - padding * 2) / (maxY - minY);
	const scale = Math.min(scaleX, scaleY);
	const offsetX = (w - (maxX - minX) * scale) / 2 - minX * scale;
	const offsetY = (h + (maxY + minY) * scale) / 2;

	return (x, y) => {
		const [rx, ry] = rotatePoint(x, y);
		return [rx * scale + offsetX, -ry * scale + offsetY];
	};
}

function drawTrack(transform) {
	const path = new Path2D();
	const [sx, sy] = transform(data.track.x[0], data.track.y[0]);
	path.moveTo(sx, sy);
	for (let i = 1; i < data.track.x.length; i++) {
		const [x, y] = transform(data.track.x[i], data.track.y[i]);
		path.lineTo(x, y);
	}
	path.closePath();

	// Bordure extérieure
	ctx.strokeStyle = '#888';
	ctx.lineWidth = 18;
	ctx.lineJoin = 'round';
	ctx.lineCap = 'round';
	ctx.stroke(path);

	// Asphalte
	ctx.strokeStyle = '#2e2e2e';
	ctx.lineWidth = 12;
	ctx.stroke(path);
}

function drawCornerLabels(transform) {
	if (!data.corners || data.corners.length === 0) return;

	for (const c of data.corners) {
		const [tx, ty] = transform(c.track_x, c.track_y);
		const [lx, ly] = transform(c.text_x, c.text_y);

		ctx.strokeStyle = 'rgba(255,255,255,0.25)';
		ctx.lineWidth = 1;
		ctx.beginPath();
		ctx.moveTo(tx, ty);
		ctx.lineTo(lx, ly);
		ctx.stroke();

		ctx.fillStyle = '#444';
		ctx.beginPath();
		ctx.arc(lx, ly, 10, 0, Math.PI * 2);
		ctx.fill();

		ctx.fillStyle = '#fff';
		ctx.font = '9px monospace';
		ctx.textAlign = 'center';
		ctx.textBaseline = 'middle';
		ctx.fillText(c.number, lx, ly);
	}
}

function draw() {
	if (!data) return;

	const w = canvas.width / devicePixelRatio;
	const h = canvas.height / devicePixelRatio;

	ctx.fillStyle = '#12121a';
	ctx.fillRect(0, 0, w, h);

	const transform = buildTransform();

	drawTrack(transform);
	drawCornerLabels(transform);

	// Trajectoire parcourue du pilote
	if (frame > 0) {
		ctx.strokeStyle = data.driver.color;
		ctx.lineWidth = 2;
		ctx.lineJoin = 'round';
		ctx.lineCap = 'round';
		ctx.beginPath();
		const [px0, py0] = transform(data.driver.x[0], data.driver.y[0]);
		ctx.moveTo(px0, py0);
		for (let i = 1; i <= frame; i++) {
			const [px, py] = transform(data.driver.x[i], data.driver.y[i]);
			ctx.lineTo(px, py);
		}
		ctx.stroke();
	}

	// Position actuelle de la voiture
	if (frame < data.driver.x.length) {
		const [cx, cy] = transform(data.driver.x[frame], data.driver.y[frame]);

		ctx.fillStyle = data.driver.color;
		ctx.beginPath();
		ctx.arc(cx, cy, 6, 0, Math.PI * 2);
		ctx.fill();

		ctx.strokeStyle = '#fff';
		ctx.lineWidth = 1.5;
		ctx.beginPath();
		ctx.arc(cx, cy, 7, 0, Math.PI * 2);
		ctx.stroke();
	}

	$('progress-fill').style.width = `${(frame / data.driver.x.length) * 100}%`;
}

function animate() {
	if (!playing || !data) return;

	if (!animate.frameCounter) animate.frameCounter = 0;
	animate.frameCounter++;

	if (animate.frameCounter >= 5) {
		frame++;
		if (frame >= data.driver.x.length) {
			frame = data.driver.x.length - 1;
			playing = false;
			$('play').textContent = '▶';
			return;
		}
		animate.frameCounter = 0;
	}

	draw();
	animId = requestAnimationFrame(animate);
}

// Event listeners
$('year').addEventListener('change', loadEvents);
$('load').addEventListener('click', loadSession);
$('driver').addEventListener('change', loadLaps);
$('visualize').addEventListener('click', visualize);

$('play').addEventListener('click', () => {
	playing = !playing;
	$('play').textContent = playing ? '⏸' : '▶';
	if (playing) animate();
	else if (animId) cancelAnimationFrame(animId);
});

$('progress').addEventListener('click', e => {
	if (!data) return;
	const rect = $('progress').getBoundingClientRect();
	const percent = (e.clientX - rect.left) / rect.width;
	frame = Math.floor(percent * data.driver.x.length);
	draw();
});

window.addEventListener('resize', () => {
	if (data) { setupCanvas(); draw(); }
});