const APP_CONFIG = window.APP_CONFIG || {};

const PROFILE_COLORS = {
  visual_shortest: "#1f6feb",
  visual_safe: "#1f883d",
  wheelchair_shortest: "#d97a00",
  wheelchair_safe: "#c62828"
};

const SEGMENT_COLORS = {
  WALK: "#c62828",
  BUS: "#1565c0",
  SUBWAY: "#6a1b9a"
};

const PRESETS = [
  {
    id: "bansong-to-osiria-hybrid",
    label: "Hybrid: 반송시장 -> 오시리아역",
    start: { lat: 35.2269086, lng: 129.1486268 },
    end: { lat: 35.1962560, lng: 129.2082910 },
    preferredProfile: "wheelchair_safe"
  },
  {
    id: "visual-crossing-compare",
    label: "Walk: Visual crossing compare",
    start: { lat: 35.1497707, lng: 129.0656452 },
    end: { lat: 35.1578066, lng: 129.0510036 },
    preferredProfile: "visual_safe"
  },
  {
    id: "wheelchair-stairs-compare",
    label: "Walk: Wheelchair stairs compare",
    start: { lat: 35.1517986, lng: 129.0665998 },
    end: { lat: 35.1618369, lng: 129.0700577 },
    preferredProfile: "wheelchair_safe"
  }
];

const DETAILS = [
  "crossing",
  "surface",
  "has_curb_gap",
  "has_elevator",
  "has_audio_signal",
  "has_braille_block",
  "width_meter"
];

const state = {
  map: null,
  clickMode: null,
  overlayStore: {
    polylines: [],
    markers: []
  },
  lastPayload: null
};

function el(id) {
  return document.getElementById(id);
}

function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "-";
  }
  return Number(value).toFixed(digits);
}

function formatMinutes(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "-";
  }
  const minute = Number(value);
  if (minute >= 10) {
    return `${Math.round(minute)}분`;
  }
  return `${minute.toFixed(2)}분`;
}

function setStatus(type, title, message) {
  const node = el("config-status");
  node.className = `status-box status-${type}`;
  node.innerHTML = `<strong>${title}</strong><span>${message}</span>`;
}

function setSelectionHint(message, active = false) {
  const node = el("selection-hint");
  node.className = active ? "selection-hint active" : "selection-hint";
  node.textContent = message;
}

function setInputValue(id, value) {
  el(id).value = Number(value).toFixed(7);
}

function currentPreset() {
  return PRESETS.find((preset) => preset.id === el("preset-select").value) || PRESETS[0];
}

function populatePresets() {
  const select = el("preset-select");
  select.innerHTML = PRESETS.map((preset) => `<option value="${preset.id}">${preset.label}</option>`).join("");
  const preset = PRESETS[0];
  select.value = preset.id;
  el("profile-select").value = preset.preferredProfile;
  applyPresetCoordinates();
}

function applyPresetCoordinates() {
  const preset = currentPreset();
  setInputValue("start-lat-input", preset.start.lat);
  setInputValue("start-lng-input", preset.start.lng);
  setInputValue("end-lat-input", preset.end.lat);
  setInputValue("end-lng-input", preset.end.lng);
  el("profile-select").value = preset.preferredProfile;
  setSelectionHint(`Preset "${preset.label}" 좌표를 입력창에 반영했습니다.`);
  drawInputMarkers(readRoutePoints());
}

function readPoint(prefix) {
  const lat = Number(el(`${prefix}-lat-input`).value);
  const lng = Number(el(`${prefix}-lng-input`).value);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
    throw new Error(`${prefix === "start" ? "출발지" : "도착지"} 좌표를 확인해 주세요.`);
  }
  return {
    lat: Number(lat.toFixed(7)),
    lng: Number(lng.toFixed(7))
  };
}

function readRoutePoints() {
  return {
    start: readPoint("start"),
    end: readPoint("end")
  };
}

function toLatLng(point) {
  return new kakao.maps.LatLng(point.lat, point.lng);
}

function clearOverlays() {
  state.overlayStore.polylines.forEach((line) => line.setMap(null));
  state.overlayStore.markers.forEach((marker) => marker.setMap(null));
  state.overlayStore.polylines = [];
  state.overlayStore.markers = [];
}

function drawMarker(position, color, label) {
  if (!state.map || !window.kakao?.maps) {
    return;
  }
  const marker = new kakao.maps.Marker({
    position: toLatLng(position),
    map: state.map
  });

  const content = `
    <div style="padding:6px 8px;border-radius:999px;background:${color};color:#fff;
    font-size:12px;font-weight:700;white-space:nowrap;transform:translateY(-10px);">
      ${label}
    </div>
  `;
  const overlay = new kakao.maps.CustomOverlay({
    content,
    position: toLatLng(position),
    yAnchor: 1.7
  });
  overlay.setMap(state.map);
  state.overlayStore.markers.push(marker, overlay);
}

function drawPolyline(kind, coordinates, options = {}) {
  if (!state.map || !window.kakao?.maps || !Array.isArray(coordinates) || !coordinates.length) {
    return;
  }
  const path = coordinates.map(([lng, lat]) => new kakao.maps.LatLng(lat, lng));
  const polyline = new kakao.maps.Polyline({
    map: state.map,
    path,
    strokeWeight: options.strokeWeight || 6,
    strokeColor: options.strokeColor || SEGMENT_COLORS[kind] || "#333333",
    strokeOpacity: options.strokeOpacity || 0.85,
    strokeStyle: options.strokeStyle || "solid"
  });
  state.overlayStore.polylines.push(polyline);
}

function fitBounds(points) {
  if (!state.map || !window.kakao?.maps || !points.length) {
    return;
  }
  const bounds = new kakao.maps.LatLngBounds();
  points.forEach((point) => bounds.extend(toLatLng(point)));
  state.map.setBounds(bounds, 50, 50, 50, 50);
}

function drawInputMarkers(points) {
  if (!state.map || !window.kakao?.maps) {
    return;
  }
  clearOverlays();
  drawMarker(points.start, "#1d3557", "입력 출발");
  drawMarker(points.end, "#6d213c", "입력 도착");
  fitBounds([points.start, points.end]);
}

function summarizeDetails(details) {
  if (!details || Object.keys(details).length === 0) {
    return `<div class="empty-state">세부 정보가 없습니다.</div>`;
  }

  return `
    <div class="detail-pill-grid">
      ${Object.entries(details).map(([key, value]) => {
        let text = "-";
        if (Array.isArray(value)) {
          text = value.join(", ") || "-";
        } else if (typeof value === "object" && value) {
          text = Object.entries(value).map(([innerKey, innerValue]) => `${innerKey}:${innerValue}`).join(", ");
        } else {
          text = String(value);
        }
        return `<div class="detail-pill"><strong>${key}</strong><span>${text}</span></div>`;
      }).join("")}
    </div>
  `;
}

async function routeRequest(profile, points) {
  const params = new URLSearchParams();
  params.append("profile", profile);
  params.append("point", `${points.start.lat},${points.start.lng}`);
  params.append("point", `${points.end.lat},${points.end.lng}`);
  params.append("points_encoded", "false");
  params.append("instructions", "true");
  params.append("calc_points", "true");
  DETAILS.forEach((detail) => params.append("details", detail));

  const baseUrl = (APP_CONFIG.graphhopperBaseUrl || "").replace(/\/$/, "");
  const response = await fetch(`${baseUrl}/route?${params.toString()}`);
  if (!response.ok) {
    const payload = await response.text();
    throw new Error(`GraphHopper route 요청 실패: ${response.status} ${payload}`);
  }
  return response.json();
}

async function loadGraphhopperInfo() {
  const baseUrl = (APP_CONFIG.graphhopperBaseUrl || "").replace(/\/$/, "");
  const response = await fetch(`${baseUrl}/info`);
  if (!response.ok) {
    throw new Error(`/info 요청 실패: ${response.status}`);
  }
  return response.json();
}

async function loadHybridRoute(points, profile) {
  const baseUrl = (APP_CONFIG.hybridTransitApiBaseUrl || window.location.origin).replace(/\/$/, "");
  const params = new URLSearchParams({
    startLat: String(points.start.lat),
    startLng: String(points.start.lng),
    endLat: String(points.end.lat),
    endLng: String(points.end.lng),
    profile
  });
  const response = await fetch(`${baseUrl}/api/hybrid-route?${params.toString()}`);
  if (!response.ok) {
    const payload = await response.text();
    throw new Error(`Hybrid route 요청 실패: ${response.status} ${payload}`);
  }
  return response.json();
}

function lowFloorLabel(realtime) {
  if (!realtime) {
    return "저상버스 정보 없음";
  }
  if (realtime.lowplate1 === "1" || realtime.lowplate2 === "1") {
    return "저상버스 운행";
  }
  return "일반버스";
}

function renderHybridSummary(payload) {
  const node = el("route-summary");
  const summary = payload.summary || {};
  const segments = payload.segments || [];
  const sourceSummary = summary.dataSources || {};

  node.className = "info-card";
  node.innerHTML = `
    <div class="route-mode-card">
      <div>
        <div class="muted-label">경로 모드</div>
        <strong>${payload.mode}</strong>
      </div>
      <div>
        <div class="muted-label">1km 기준</div>
        <strong>${formatNumber(payload.thresholdMeter, 0)}m</strong>
      </div>
    </div>
    <div class="summary-kpis">
      <div class="summary-kpi">
        <span>총 거리</span>
        <strong>${formatNumber(summary.totalDistanceMeter, 1)}m</strong>
      </div>
      <div class="summary-kpi">
        <span>총 시간</span>
        <strong>${formatMinutes(summary.totalTimeMinute)}</strong>
      </div>
      <div class="summary-kpi">
        <span>총 요금</span>
        <strong>${summary.payment ? `${summary.payment.toLocaleString()}원` : "0원"}</strong>
      </div>
    </div>
    <div class="headline-card">${summary.headline || "요약 없음"}</div>
    <div class="source-card">
      <div><strong>도보</strong> ${Array.isArray(sourceSummary.walk) ? sourceSummary.walk.join(" + ") : "-"}</div>
      <div><strong>버스</strong> ${Array.isArray(sourceSummary.bus) ? sourceSummary.bus.join(" + ") : "-"}</div>
      <div><strong>지하철</strong> ${Array.isArray(sourceSummary.subway) ? sourceSummary.subway.join(" + ") : "-"}</div>
    </div>
    <div class="segment-summary-list">
      ${segments.map((segment, index) => {
        const extra = [];
        if (segment.type === "BUS") {
          extra.push(`${segment.routeNo || "-"} ${segment.startName || ""} -> ${segment.endName || ""}`.trim());
          if (segment.realtime) {
            extra.push(`실시간 ${segment.realtime.min1 || "-"}분 / ${lowFloorLabel(segment.realtime)}`);
          }
        } else if (segment.type === "SUBWAY") {
          extra.push(`${segment.lineName || "-"} ${segment.startName || ""} -> ${segment.endName || ""}`.trim());
          extra.push(`매칭 ${segment.matchStatus || "-"}`);
        } else {
          extra.push(`${segment.startName || "-"} -> ${segment.endName || "-"}`);
          extra.push(`Snap ${segment.snapStatus?.start || "-"} / ${segment.snapStatus?.end || "-"}`);
        }
        return `
          <div class="segment-card segment-${segment.type.toLowerCase()}">
            <div class="segment-card-header">
              <span class="segment-badge">${index + 1}. ${segment.type}</span>
              <strong>${segment.title || segment.type}</strong>
            </div>
            <div>${formatNumber(segment.distanceMeter, 1)}m / ${formatMinutes(segment.estimatedTimeMinute)}</div>
            ${extra.map((item) => `<div class="segment-extra">${item}</div>`).join("")}
          </div>
        `;
      }).join("")}
    </div>
  `;
}

function renderHybridDetails(payload) {
  const node = el("details-summary");
  const segments = payload.segments || [];

  node.className = "info-card";
  node.innerHTML = segments.map((segment, index) => {
    const sourceText = Array.isArray(segment.dataSources) ? segment.dataSources.join(" + ") : "-";
    let content = `
      <div class="detail-block">
        <div class="detail-block-header">
          <strong>${index + 1}. ${segment.type} - ${segment.title || segment.type}</strong>
          <span>${sourceText}</span>
        </div>
        <div class="detail-row"><strong>거리</strong><span>${formatNumber(segment.distanceMeter, 1)}m</span></div>
        <div class="detail-row"><strong>시간</strong><span>${formatMinutes(segment.estimatedTimeMinute)}</span></div>
    `;

    if (segment.type === "WALK") {
      content += `
        <div class="detail-row"><strong>엔진</strong><span>${segment.engine || "-"}</span></div>
        <div class="detail-row"><strong>구간</strong><span>${segment.startName || "-"} -> ${segment.endName || "-"}</span></div>
        <div class="detail-row"><strong>Snap</strong><span>S ${segment.snapStatus?.start || "-"} / E ${segment.snapStatus?.end || "-"}</span></div>
        ${summarizeDetails(segment.detailSummary)}
      `;
    } else if (segment.type === "BUS") {
      content += `
        <div class="detail-row"><strong>노선</strong><span>${segment.routeNo || "-"}</span></div>
        <div class="detail-row"><strong>구간</strong><span>${segment.startName || "-"} -> ${segment.endName || "-"}</span></div>
        <div class="detail-row"><strong>실시간</strong><span>${segment.realtime?.min1 || "-"}분 / ${lowFloorLabel(segment.realtime)}</span></div>
      `;
    } else if (segment.type === "SUBWAY") {
      content += `
        <div class="detail-row"><strong>노선</strong><span>${segment.lineName || "-"}</span></div>
        <div class="detail-row"><strong>구간</strong><span>${segment.startName || "-"} -> ${segment.endName || "-"}</span></div>
        <div class="detail-row"><strong>매칭 상태</strong><span>${segment.matchStatus || "-"}</span></div>
        <div class="detail-row"><strong>매칭 근거</strong><span>${segment.matchReason || "-"}</span></div>
      `;
    }

    content += `</div>`;
    return content;
  }).join("<hr>");
}

function renderMapFromHybrid(payload, requestedPoints) {
  clearOverlays();
  const pointsForBounds = [requestedPoints.start, requestedPoints.end];

  drawMarker(requestedPoints.start, "#1d3557", "입력 출발");
  drawMarker(requestedPoints.end, "#6d213c", "입력 도착");

  (payload.segments || []).forEach((segment, index) => {
    const geometry = Array.isArray(segment.geometry) ? segment.geometry : [];
    const color = SEGMENT_COLORS[segment.type] || "#333333";
    drawPolyline(segment.type, geometry, {
      strokeColor: color,
      strokeStyle: segment.type === "WALK" ? "solid" : "shortdash"
    });
    geometry.forEach(([lng, lat]) => pointsForBounds.push({ lat, lng }));

    if (segment.startPoint) {
      drawMarker(segment.startPoint, color, `${index + 1} 시작`);
      pointsForBounds.push(segment.startPoint);
    }
    if (segment.endPoint) {
      drawMarker(segment.endPoint, color, `${index + 1} 끝`);
      pointsForBounds.push(segment.endPoint);
    }
  });

  fitBounds(pointsForBounds);
}

function summarizeRouteBlock(label, profile, response, requestedPoints) {
  const path = response?.paths?.[0];
  if (!path) {
    return `<div><strong>${label}</strong> ${profile}: 경로 없음</div>`;
  }

  const instructionCount = Array.isArray(path.instructions) ? path.instructions.length : 0;
  const pointCount = Array.isArray(path.points?.coordinates) ? path.points.coordinates.length : 0;
  const snapped = path.snapped_waypoints?.coordinates || [];
  const startSnap = snapped[0] ? `${snapped[0][1].toFixed(7)}, ${snapped[0][0].toFixed(7)}` : "-";
  const endSnap = snapped[1] ? `${snapped[1][1].toFixed(7)}, ${snapped[1][0].toFixed(7)}` : "-";

  return `
    <div>
      <strong>${label}</strong> ${profile}
      <div>입력 출발 ${requestedPoints.start.lat.toFixed(7)}, ${requestedPoints.start.lng.toFixed(7)}</div>
      <div>입력 도착 ${requestedPoints.end.lat.toFixed(7)}, ${requestedPoints.end.lng.toFixed(7)}</div>
      <div>거리 ${formatNumber(path.distance, 3)}m / 시간 ${formatMinutes(path.time / 60000)}</div>
      <div>geometry ${pointCount}개 / instruction ${instructionCount}개</div>
      <div>snapped 출발 ${startSnap}</div>
      <div>snapped 도착 ${endSnap}</div>
    </div>
  `;
}

function renderWalkCompareSummary(results, requestedPoints) {
  const node = el("route-summary");
  const cards = results.map((result) => summarizeRouteBlock("비교", result.profile, result.response, requestedPoints));
  const legend = Object.entries(PROFILE_COLORS).map(([profile, color]) => {
    return `
      <div class="legend-row">
        <span class="legend-chip" style="background:${color}"></span>
        <span>${profile}</span>
      </div>
    `;
  }).join("");

  node.className = "info-card";
  node.innerHTML = `
    <div class="summary-grid">${cards.join("")}</div>
    <div class="legend">${legend}</div>
  `;
}

function renderWalkCompareDetails(results) {
  const node = el("details-summary");
  node.className = "info-card";
  node.innerHTML = results.map((result) => {
    const details = result.response?.paths?.[0]?.details || {};
    return `
      <div class="detail-block">
        <div class="detail-block-header">
          <strong>${result.profile}</strong>
          <span>GraphHopper direct compare</span>
        </div>
        ${summarizeDetails(details)}
      </div>
    `;
  }).join("<hr>");
}

function renderWalkCompareMap(results, requestedPoints) {
  clearOverlays();
  const pointsForBounds = [requestedPoints.start, requestedPoints.end];

  drawMarker(requestedPoints.start, "#1d3557", "입력 출발");
  drawMarker(requestedPoints.end, "#6d213c", "입력 도착");

  results.forEach((result) => {
    const path = result.response?.paths?.[0];
    if (!path) {
      return;
    }
    drawPolyline("WALK", path.points.coordinates, {
      strokeColor: PROFILE_COLORS[result.profile] || "#333333",
      strokeStyle: "solid"
    });
    path.points.coordinates.forEach(([lng, lat]) => pointsForBounds.push({ lat, lng }));
  });

  fitBounds(pointsForBounds);
}

async function executeHybridRoute() {
  const requestedPoints = readRoutePoints();
  const profile = el("profile-select").value;
  const payload = await loadHybridRoute(requestedPoints, profile);
  state.lastPayload = payload;
  renderHybridSummary(payload);
  renderHybridDetails(payload);
  renderMapFromHybrid(payload, requestedPoints);
  return payload;
}

async function onLoadRoute() {
  try {
    const payload = await executeHybridRoute();
    setSelectionHint(`${payload.mode} 조회가 완료되었습니다.`);
  } catch (error) {
    setStatus("error", "경로 조회 실패", error.message);
  }
}

async function onCompareFamily() {
  const points = readRoutePoints();
  const straightDistance = Number(state.lastPayload?.request?.straightDistanceMeter || 0);
  if (straightDistance > Number(state.lastPayload?.thresholdMeter || 1000)) {
    setSelectionHint("하이브리드 모드에서는 family shortest/safe 비교를 지원하지 않습니다.");
    return;
  }

  const profile = el("profile-select").value;
  const family = profile.startsWith("wheelchair") ? "wheelchair" : "visual";
  try {
    const results = [];
    for (const currentProfile of [`${family}_shortest`, `${family}_safe`]) {
      const response = await routeRequest(currentProfile, points);
      results.push({ profile: currentProfile, response });
    }
    renderWalkCompareSummary(results, points);
    renderWalkCompareDetails(results);
    renderWalkCompareMap(results, points);
    setSelectionHint(`${family} family shortest/safe 비교가 완료되었습니다.`);
  } catch (error) {
    setStatus("error", "비교 조회 실패", error.message);
  }
}

function setClickMode(mode) {
  state.clickMode = state.clickMode === mode ? null : mode;
  if (state.clickMode === "start") {
    setSelectionHint("지도에서 한 번 클릭하면 출발지 좌표가 입력됩니다.", true);
  } else if (state.clickMode === "end") {
    setSelectionHint("지도에서 한 번 클릭하면 도착지 좌표가 입력됩니다.", true);
  } else {
    setSelectionHint("지도 클릭 선택 모드가 꺼져 있습니다.");
  }
}

function onMapClick(mouseEvent) {
  if (!state.clickMode) {
    return;
  }
  const latlng = mouseEvent.latLng;
  const point = {
    lat: Number(latlng.getLat().toFixed(7)),
    lng: Number(latlng.getLng().toFixed(7))
  };

  if (state.clickMode === "start") {
    setInputValue("start-lat-input", point.lat);
    setInputValue("start-lng-input", point.lng);
    setSelectionHint("출발지 좌표를 지도에서 반영했습니다.");
  } else {
    setInputValue("end-lat-input", point.lat);
    setInputValue("end-lng-input", point.lng);
    setSelectionHint("도착지 좌표를 지도에서 반영했습니다.");
  }

  state.clickMode = null;
  drawInputMarkers(readRoutePoints());
}

function loadKakaoSdk(key) {
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${key}&autoload=false`;
    script.onload = () => kakao.maps.load(resolve);
    script.onerror = (event) => reject(new Error(`Kakao SDK load failed: ${event.type}`));
    document.head.appendChild(script);
  });
}

function initMap() {
  if (!window.kakao?.maps) {
    return;
  }
  state.map = new kakao.maps.Map(el("map"), {
    center: new kakao.maps.LatLng(
      APP_CONFIG.initialCenter?.lat || 35.157,
      APP_CONFIG.initialCenter?.lng || 129.059
    ),
    level: APP_CONFIG.initialLevel || 5
  });
  kakao.maps.event.addListener(state.map, "click", onMapClick);
  drawInputMarkers(readRoutePoints());
}

async function boot() {
  populatePresets();

  el("preset-select").addEventListener("change", applyPresetCoordinates);
  el("apply-preset-button").addEventListener("click", applyPresetCoordinates);
  el("pick-start-button").addEventListener("click", () => setClickMode("start"));
  el("pick-end-button").addEventListener("click", () => setClickMode("end"));
  el("load-route-button").addEventListener("click", onLoadRoute);
  el("compare-family-button").addEventListener("click", onCompareFamily);

  ["start-lat-input", "start-lng-input", "end-lat-input", "end-lng-input"].forEach((id) => {
    el(id).addEventListener("change", () => {
      try {
        drawInputMarkers(readRoutePoints());
      } catch {
        // ignore invalid intermediate input
      }
    });
  });

  if (!APP_CONFIG.graphhopperBaseUrl) {
    setStatus("warn", "설정 확인 필요", "graphhopperBaseUrl이 없어서 연결 상태를 미리 확인할 수 없습니다.");
  } else {
    try {
      const info = await loadGraphhopperInfo();
      const profiles = (info.profiles || []).map((item) => item.name).join(", ");
      setStatus("ok", "로컬 라우팅 연결 성공", `/info에서 profile ${profiles} 확인`);
    } catch (error) {
      setStatus("warn", "GraphHopper 연결 미확인", error.message);
    }
  }

  if (!APP_CONFIG.kakaoJavascriptKey || APP_CONFIG.kakaoJavascriptKey.includes("REPLACE_WITH")) {
    setStatus("warn", "Kakao key 필요", "config.local.js에 kakaoJavascriptKey를 넣어야 지도가 로드됩니다.");
    return;
  }

  try {
    await loadKakaoSdk(APP_CONFIG.kakaoJavascriptKey);
    initMap();
    setSelectionHint("좌표를 직접 입력하거나 지도를 클릭한 뒤 경로 조회를 실행하세요.");
  } catch (error) {
    setStatus("error", "Kakao SDK 로드 실패", error.message);
  }
}

boot();
