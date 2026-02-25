const API = 'http://localhost:8000';
let data = null;
let frame = 0;
let playing = false;
let animId = null;

const $ = id => document.getElementById(id);
const loading = $('loading');
const canvas = $('canvas');
const ctx = canvas.getContext('2d');

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

function draw() {
	if (!data) return;

	const w = canvas.width / devicePixelRatio;
	const h = canvas.height / devicePixelRatio;

	ctx.fillStyle = '#12121a';
	ctx.fillRect(0, 0, w, h);

	const allX = [...data.track.x, ...data.driver.x];
	const allY = [...data.track.y, ...data.driver.y];
	const minX = Math.min(...allX);
	const maxX = Math.max(...allX);
	const minY = Math.min(...allY);
	const maxY = Math.max(...allY);
	const scale = Math.min(w, h) * 0.8 / Math.max(maxX - minX, maxY - minY);
	const offsetX = (w - (maxX - minX) * scale) / 2 - minX * scale;
	const offsetY = (h - (maxY - minY) * scale) / 2 - minY * scale;

	const transform = (x, y) => [x * scale + offsetX, y * scale + offsetY];

	// Tracé du circuit de référence
	ctx.strokeStyle = 'rgba(255,255,255,0.2)';
	ctx.lineWidth = 6;
	ctx.beginPath();
	const [sx, sy] = transform(data.track.x[0], data.track.y[0]);
	ctx.moveTo(sx, sy);
	for (let i = 1; i < data.track.x.length; i++) {
		const [x, y] = transform(data.track.x[i], data.track.y[i]);
		ctx.lineTo(x, y);
	}
	ctx.closePath();
	ctx.stroke();

	// Numéros de virages
	ctx.fillStyle = '#666';
	ctx.font = '10px monospace';
		ctx.textAlign = 'center';
		ctx.textBaseline = 'middle';
		for (const c of data.corners) {
		const [tx, ty] = transform(c.text_x, c.text_y);
			ctx.beginPath();
			ctx.arc(tx, ty, 10, 0, Math.PI * 2);
			ctx.fill();
			ctx.fillStyle = '#fff';
			ctx.fillText(c.number, tx, ty);
		ctx.fillStyle = '#666';
	}

	// Trajectoire parcourue du pilote
	if (frame > 0) {
		ctx.strokeStyle = data.driver.color;
		ctx.lineWidth = 2;
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

		// Halo blanc autour de la voiture
		ctx.strokeStyle = '#fff';
		ctx.lineWidth = 1.5;
		ctx.beginPath();
		ctx.arc(cx, cy, 7, 0, Math.PI * 2);
		ctx.stroke();
	}

	// Mise à jour de la barre de progression
	$('progress-fill').style.width = `${(frame / data.driver.x.length) * 100}%`;
}

function animate() {
	if (!playing || !data) return;
	
	if (!animate.frameCounter) animate.frameCounter = 0;
	animate.frameCounter++;
	
	if (animate.frameCounter >= 5) {
		frame++;
		if (frame >= data.driver.x.length) frame = 0;
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