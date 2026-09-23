// public/app.js — 前端邏輯：呼叫 /api/forecast，渲染圖表、表格、地圖與帶傘提醒。
const UMBRELLA_THRESHOLD = 50;

const TEMP_BINS = [
  { max: 20, color: "#3b82f6", label: "< 20°C" },
  { max: 25, color: "#22c55e", label: "20–25°C" },
  { max: 30, color: "#f59e0b", label: "25–30°C" },
  { max: Infinity, color: "#ef4444", label: "> 30°C" },
];

function colorByTemp(t) {
  if (t === null || t === undefined || Number.isNaN(t)) return "#9ca3af";
  for (const b of TEMP_BINS) if (t < b.max) return b.color;
  return "#ef4444";
}

let DATA = null;
let chart = null;
let map = null;
let markerLayer = null;

async function init() {
  const status = document.getElementById("status");
  try {
    const resp = await fetch("/api/forecast");
    const json = await resp.json();
    if (!resp.ok || !json.success) {
      throw new Error(json.error || `HTTP ${resp.status}`);
    }
    DATA = json;
  } catch (err) {
    status.hidden = false;
    status.textContent = "無法取得天氣資料：" + err.message +
      "（請確認 Vercel 已設定 CWA_API_KEY 環境變數）";
    return;
  }

  document.getElementById("source").textContent = "資料來源：" + DATA.source;

  buildRegionSelect();
  buildDaySelect();
  buildLegend();
  initMap();

  document.getElementById("region").addEventListener("change", renderRegion);
  document.getElementById("day").addEventListener("change", renderMap);

  renderRegion();
  renderMap();
}

function buildRegionSelect() {
  const sel = document.getElementById("region");
  sel.innerHTML = "";
  DATA.regions.forEach((r) => {
    const opt = document.createElement("option");
    opt.value = r.geocode;
    opt.textContent = r.label;
    sel.appendChild(opt);
  });
}

function buildDaySelect() {
  const sel = document.getElementById("day");
  sel.innerHTML = "";
  DATA.days.forEach((d) => {
    const opt = document.createElement("option");
    opt.value = d;
    opt.textContent = d;
    sel.appendChild(opt);
  });
}

function currentGeocode() {
  return document.getElementById("region").value;
}

function renderRegion() {
  const geo = currentGeocode();
  const rows = DATA.daily[geo] || [];
  const label = (DATA.meta[geo] && DATA.meta[geo].county) || geo;
  document.getElementById("chart-title").textContent = `${label}　一週每日高低溫`;

  renderChart(rows);
  renderTable(rows);
  renderUmbrella(rows);
}

function renderChart(rows) {
  const labels = rows.map((r) => r.day);
  const maxs = rows.map((r) => r.dayMaxT);
  const mins = rows.map((r) => r.dayMinT);
  const ctx = document.getElementById("chart");
  if (chart) chart.destroy();
  chart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        { label: "每日最高溫", data: maxs, borderColor: "#ef4444",
          backgroundColor: "#ef4444", tension: 0.3, spanGaps: true },
        { label: "每日最低溫", data: mins, borderColor: "#3b82f6",
          backgroundColor: "#3b82f6", tension: 0.3, spanGaps: true },
      ],
    },
    options: {
      responsive: true,
      scales: { y: { title: { display: true, text: "°C" } } },
      plugins: { legend: { position: "top" } },
    },
  });
}

function renderTable(rows) {
  const tbody = document.querySelector("#table tbody");
  tbody.innerHTML = "";
  const fmt = (v) => (v === null || v === undefined ? "—" : v);
  rows.forEach((r) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${r.day}</td><td>${fmt(r.dayMinT)}</td>` +
                   `<td>${fmt(r.dayMaxT)}</td><td>${fmt(r.dayPop)}</td>`;
    tbody.appendChild(tr);
  });
}

function renderUmbrella(rows) {
  const box = document.getElementById("umbrella");
  const over = rows.filter((r) => r.dayPop !== null && r.dayPop !== undefined
                                  && r.dayPop > UMBRELLA_THRESHOLD);
  if (over.length === 0) { box.hidden = true; return; }
  const maxPop = Math.max(...over.map((r) => r.dayPop));
  const days = over.map((r) => r.day).slice(0, 5).join("、");
  box.hidden = false;
  box.innerHTML = `☔ <b>記得帶傘！</b> 最高降雨機率 <b>${maxPop}%</b>` +
                  `（門檻 ${UMBRELLA_THRESHOLD}%）。較可能降雨日期：${days}`;
}

function initMap() {
  map = L.map("map").setView([23.7, 121.0], 7);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap",
  }).addTo(map);
  markerLayer = L.layerGroup().addTo(map);
}

function renderMap() {
  const day = document.getElementById("day").value;
  document.getElementById("map-title").textContent = `${day}　全台各縣市當日最高溫`;
  markerLayer.clearLayers();

  Object.keys(DATA.daily).forEach((geo) => {
    const meta = DATA.meta[geo];
    if (!meta || meta.lat === null || meta.lng === null) return;
    const row = (DATA.daily[geo] || []).find((r) => r.day === day);
    if (!row) return;
    const color = colorByTemp(row.dayMaxT);
    const fmt = (v) => (v === null || v === undefined ? "—" : v);
    L.circleMarker([meta.lat, meta.lng], {
      radius: 9, color, fillColor: color, fillOpacity: 0.85, weight: 1,
    }).bindPopup(
      `${meta.county}<br>最高 ${fmt(row.dayMaxT)}°C / 最低 ${fmt(row.dayMinT)}°C` +
      `<br>降雨機率 ${fmt(row.dayPop)}%`
    ).bindTooltip(meta.county).addTo(markerLayer);
  });
}

function buildLegend() {
  const el = document.getElementById("legend");
  const items = TEMP_BINS.map((b) =>
    `<span class="legend-item"><span class="legend-dot" style="background:${b.color}"></span>${b.label}</span>`
  );
  items.push('<span class="legend-item"><span class="legend-dot" style="background:#9ca3af"></span>無資料</span>');
  el.innerHTML = items.join("");
}

init();
