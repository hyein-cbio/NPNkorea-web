const DEFAULT_API_URL = "http://127.0.0.1:8000";
const DEFAULT_POINT = { lon: 126.978422, lat: 37.566742 };

const elements = {
  mapMode: document.getElementById("map-mode"),
  codeMode: document.getElementById("code-mode"),
  commandForm: document.getElementById("command-form"),
  commandInput: document.getElementById("command-input"),
  commandSubmit: document.getElementById("command-submit"),
  connectionState: document.getElementById("connection-state"),
  connectionLabel: document.getElementById("connection-label"),
  settingsToggle: document.getElementById("settings-toggle"),
  settingsPanel: document.getElementById("settings-panel"),
  settingsClose: document.getElementById("settings-close"),
  baseUrl: document.getElementById("base-url"),
  healthButton: document.getElementById("health-button"),
  selectionCard: document.getElementById("selection-card"),
  selectionLon: document.getElementById("selection-lon"),
  selectionLat: document.getElementById("selection-lat"),
  toast: document.getElementById("toast"),
  resultDock: document.getElementById("result-dock"),
  resultLon: document.getElementById("result-lon"),
  resultLat: document.getElementById("result-lat"),
  resultCode: document.getElementById("result-code"),
  copyButton: document.getElementById("copy-button"),
  clearButton: document.getElementById("clear-button"),
};

const state = {
  mode: "map",
  busy: false,
  code: "",
  point: null,
  cellCorner: null,
  locateButton: null,
  locating: false,
  toastTimer: null,
};

const map = L.map("map", {
  zoomControl: false,
  minZoom: 6,
  maxZoom: 19,
}).setView([37.6, 126.978422], 11);

L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
}).addTo(map);

map.attributionControl.setPrefix(false);
L.control.scale({ position: "bottomleft", imperial: false, maxWidth: 120 }).addTo(map);

const selectionLayers = L.layerGroup().addTo(map);
const locationLayers = L.layerGroup().addTo(map);

const LocateControl = L.Control.extend({
  options: { position: "topright" },
  onAdd() {
    const button = L.DomUtil.create("button", "map-location-control");
    const icon = L.DomUtil.create("span", "material-symbols-outlined", button);
    const label = L.DomUtil.create("span", "map-location-label", button);
    button.type = "button";
    icon.textContent = "my_location";
    label.textContent = "현재 위치";
    button.title = "브라우저에서 현재 위치 확인";
    button.setAttribute("aria-label", "브라우저에서 현재 위치 확인");
    L.DomEvent.disableClickPropagation(button);
    L.DomEvent.on(button, "click", locateUser);
    state.locateButton = button;
    return button;
  },
});

new LocateControl().addTo(map);
L.control.zoom({ position: "topright" }).addTo(map);

function getApiUrl() {
  const rawUrl = elements.baseUrl.value.trim() || DEFAULT_API_URL;
  let url;
  try {
    url = new URL(rawUrl);
  } catch {
    throw new Error("API URL을 올바르게 입력해 주세요.");
  }

  if (!/^https?:$/.test(url.protocol)) {
    throw new Error("API URL은 http 또는 https 주소여야 합니다.");
  }
  url.search = "";
  url.hash = "";
  return url.toString().replace(/\/$/, "");
}

function persistApiUrl() {
  try {
    localStorage.setItem("npnkorea-api-url", getApiUrl());
  } catch {
    // Storage is optional; the editable field remains the source of truth.
  }
}

function restoreApiUrl() {
  try {
    elements.baseUrl.value = localStorage.getItem("npnkorea-api-url") || DEFAULT_API_URL;
  } catch {
    elements.baseUrl.value = DEFAULT_API_URL;
  }
}

async function requestJson(path, options = {}, apiUrl = getApiUrl()) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), 15000);

  try {
    const response = await fetch(`${apiUrl}${path}`, {
      ...options,
      signal: controller.signal,
    });
    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("application/json")
      ? await response.json()
      : await response.text();

    if (!response.ok) {
      const detail = typeof payload === "object" && payload !== null ? payload.detail : payload;
      throw new Error(detail || `요청에 실패했습니다 (${response.status})`);
    }

    return payload;
  } catch (error) {
    if (error.name === "AbortError") {
      const timeoutError = new Error("API 응답 시간이 초과되었습니다.");
      timeoutError.name = "TimeoutError";
      throw timeoutError;
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

function setConnection(status) {
  elements.connectionState.classList.toggle("is-online", status === "online");
  elements.connectionState.classList.toggle("is-offline", status === "offline");
  elements.connectionLabel.textContent = {
    online: "API 연결됨",
    offline: "API 오프라인",
    checking: "확인 중",
  }[status];
}

async function checkHealth({ announce = false } = {}) {
  setConnection("checking");

  try {
    const apiUrl = getApiUrl();
    persistApiUrl();
    await requestJson("/health", {}, apiUrl);
    setConnection("online");
    if (announce) showToast("API 연결을 확인했습니다.");
    return true;
  } catch (error) {
    setConnection("offline");
    if (announce) showToast(error.message, { error: true });
    return false;
  }
}

function setBusy(busy) {
  state.busy = busy;
  elements.commandInput.disabled = busy;
  elements.commandSubmit.disabled = busy;
  elements.mapMode.disabled = busy;
  elements.codeMode.disabled = busy;
  elements.settingsToggle.disabled = busy;
  elements.settingsClose.disabled = busy;
  elements.baseUrl.disabled = busy;
  elements.healthButton.disabled = busy;
  elements.copyButton.disabled = busy || !state.code;
  elements.clearButton.disabled = busy || !state.code;
  if (state.locateButton) state.locateButton.disabled = busy || state.locating;
  elements.commandSubmit.classList.toggle("is-loading", busy);
  const icon = elements.commandSubmit.querySelector(".material-symbols-outlined");
  icon.textContent = busy ? "progress_activity" : "arrow_forward";
  elements.commandForm.setAttribute("aria-busy", String(busy));
}

function setLocating(locating) {
  state.locating = locating;
  if (!state.locateButton) return;

  const icon = state.locateButton.querySelector(".material-symbols-outlined");
  const label = state.locateButton.querySelector(".map-location-label");
  state.locateButton.disabled = locating || state.busy;
  state.locateButton.classList.toggle("is-locating", locating);
  state.locateButton.setAttribute("aria-busy", String(locating));
  icon.textContent = locating ? "progress_activity" : "my_location";
  label.textContent = locating ? "확인 중" : "현재 위치";
}

function showToast(message, { error = false } = {}) {
  window.clearTimeout(state.toastTimer);
  elements.toast.textContent = message;
  elements.toast.classList.toggle("is-error", error);
  elements.toast.hidden = false;
  state.toastTimer = window.setTimeout(() => {
    elements.toast.hidden = true;
  }, 3600);
}

function setInputError(isError) {
  elements.commandForm.classList.toggle("has-error", isError);
  elements.commandInput.setAttribute("aria-invalid", String(isError));
}

function isConnectionError(error) {
  return error instanceof TypeError || error.name === "TimeoutError";
}

function formatCoordinate(value) {
  return Number(value).toFixed(6);
}

function offsetMeters(point, eastMeters, northMeters) {
  const latitudeRadians = (point.lat * Math.PI) / 180;
  return {
    lat: point.lat + northMeters / 111320,
    lon: point.lon + eastMeters / (111320 * Math.cos(latitudeRadians)),
  };
}

function renderSelection() {
  selectionLayers.clearLayers();
  if (!state.point || !state.cellCorner) return;

  const northEast = offsetMeters(state.cellCorner, 10, 10);
  const bounds = map.getBounds();
  const crosshairStyle = {
    color: "#e53b42",
    weight: 1,
    opacity: 0.78,
    interactive: false,
  };

  L.polyline(
    [
      [state.point.lat, bounds.getWest()],
      [state.point.lat, bounds.getEast()],
    ],
    crosshairStyle,
  ).addTo(selectionLayers);

  L.polyline(
    [
      [bounds.getSouth(), state.point.lon],
      [bounds.getNorth(), state.point.lon],
    ],
    crosshairStyle,
  ).addTo(selectionLayers);

  L.rectangle(
    [
      [state.cellCorner.lat, state.cellCorner.lon],
      [northEast.lat, northEast.lon],
    ],
    {
      color: "#e53b42",
      weight: 2,
      fillColor: "#ffd84d",
      fillOpacity: 0.72,
      interactive: false,
    },
  ).addTo(selectionLayers);

  L.circleMarker([state.point.lat, state.point.lon], {
    radius: 7,
    color: "#e53b42",
    weight: 3,
    fillColor: "#ffffff",
    fillOpacity: 1,
    interactive: false,
  }).addTo(selectionLayers);
}

function renderResultCode(code) {
  const match = code.match(/^([^\s]+)\s+(.+)$/);
  if (!match) {
    elements.resultCode.textContent = code;
    return;
  }

  const prefix = document.createElement("span");
  const digits = document.createElement("span");
  prefix.className = "code-prefix";
  digits.className = "code-digits";
  prefix.textContent = match[1];
  digits.textContent = match[2];
  elements.resultCode.replaceChildren(prefix, document.createTextNode(" "), digits);
}

function updateResult(point, code, cellCorner) {
  state.point = point;
  state.cellCorner = cellCorner;
  state.code = code;

  const lon = formatCoordinate(point.lon);
  const lat = formatCoordinate(point.lat);
  elements.resultLon.textContent = lon;
  elements.resultLat.textContent = lat;
  renderResultCode(code);
  elements.selectionLon.textContent = lon;
  elements.selectionLat.textContent = lat;
  elements.selectionCard.hidden = false;
  elements.resultDock.classList.add("has-result");
  elements.copyButton.disabled = false;
  elements.clearButton.disabled = false;
  renderSelection();
}

function clearResult({ clearInput = true } = {}) {
  state.code = "";
  state.point = null;
  state.cellCorner = null;
  selectionLayers.clearLayers();
  locationLayers.clearLayers();
  elements.resultLon.textContent = "—";
  elements.resultLat.textContent = "—";
  elements.resultCode.textContent = "지도를 클릭해 위치를 선택하세요";
  elements.selectionCard.hidden = true;
  elements.resultDock.classList.remove("has-result");
  elements.copyButton.disabled = true;
  elements.clearButton.disabled = true;
  setInputError(false);
  if (clearInput) elements.commandInput.value = "";
}

function requireConversion(payload) {
  const corner = payload?.cell_corner;
  if (
    typeof payload?.code !== "string" ||
    !corner ||
    !Number.isFinite(corner.lon) ||
    !Number.isFinite(corner.lat)
  ) {
    throw new Error("변환 API 응답 형식이 올바르지 않습니다.");
  }
  return { code: payload.code, cellCorner: corner };
}

async function postConvert(input, apiUrl) {
  const payload = await requestJson("/convert", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...input, output: "han" }),
  }, apiUrl);
  return requireConversion(payload);
}

async function convertCoordinates(point, { moveMap = false } = {}) {
  if (state.busy) return;
  setBusy(true);
  setInputError(false);

  try {
    const apiUrl = getApiUrl();
    const { code, cellCorner } = await postConvert({ point }, apiUrl);
    updateResult(point, code, cellCorner);
    elements.commandInput.value = `${formatCoordinate(point.lon)}, ${formatCoordinate(point.lat)}`;
    if (moveMap) map.flyTo([point.lat, point.lon], Math.max(map.getZoom(), 15));
    setConnection("online");
  } catch (error) {
    setInputError(true);
    setConnection(isConnectionError(error) ? "offline" : "online");
    showToast(error.message, { error: true });
    return false;
  } finally {
    setBusy(false);
  }
  return true;
}

async function convertCode(code) {
  if (state.busy) return;
  setBusy(true);
  setInputError(false);

  try {
    const apiUrl = getApiUrl();
    const conversion = await postConvert({ code }, apiUrl);
    const cellCenter = offsetMeters(conversion.cellCorner, 5, 5);
    updateResult(cellCenter, conversion.code, conversion.cellCorner);
    elements.commandInput.value = conversion.code;
    map.flyTo([cellCenter.lat, cellCenter.lon], 17);
    setConnection("online");
  } catch (error) {
    setInputError(true);
    setConnection(isConnectionError(error) ? "offline" : "online");
    showToast(error.message, { error: true });
  } finally {
    setBusy(false);
  }
}

function parseCoordinateInput(value) {
  const parts = value
    .trim()
    .split(/[\s,]+/)
    .filter(Boolean)
    .map(Number);

  if (parts.length !== 2 || parts.some((part) => !Number.isFinite(part))) {
    throw new Error("경도와 위도를 쉼표로 구분해 입력해 주세요.");
  }

  return { lon: parts[0], lat: parts[1] };
}

function setMode(mode, { focus = true } = {}) {
  state.mode = mode;
  const isMapMode = mode === "map";
  elements.mapMode.classList.toggle("is-active", isMapMode);
  elements.codeMode.classList.toggle("is-active", !isMapMode);
  elements.mapMode.setAttribute("aria-selected", String(isMapMode));
  elements.codeMode.setAttribute("aria-selected", String(!isMapMode));
  elements.commandInput.placeholder = isMapMode
    ? "경도, 위도 입력 또는 지도 클릭"
    : "국가지점번호 입력 (예: 다사 5393 5205)";
  elements.commandInput.inputMode = isMapMode ? "decimal" : "text";
  setInputError(false);
  if (focus) elements.commandInput.focus();
}

function toggleSettings(forceOpen) {
  const shouldOpen = forceOpen ?? elements.settingsPanel.hidden;
  elements.settingsPanel.hidden = !shouldOpen;
  elements.settingsToggle.setAttribute("aria-expanded", String(shouldOpen));
  if (shouldOpen) elements.baseUrl.focus();
}

async function copyResult() {
  if (!state.code) return;
  try {
    await navigator.clipboard.writeText(state.code);
    showToast("국가지점번호를 복사했습니다.");
  } catch {
    showToast("클립보드에 복사하지 못했습니다.", { error: true });
  }
}

function locateUser() {
  if (state.locating) return;

  if (!window.isSecureContext) {
    showToast("현재 위치는 HTTPS 또는 localhost에서만 사용할 수 있습니다.", { error: true });
    return;
  }

  if (!navigator.geolocation) {
    showToast("이 브라우저에서는 현재 위치를 사용할 수 없습니다.", { error: true });
    return;
  }

  setLocating(true);
  showToast("브라우저에서 현재 위치를 확인하고 있습니다.");
  navigator.geolocation.getCurrentPosition(
    async ({ coords }) => {
      const point = { lon: coords.longitude, lat: coords.latitude };
      const accuracy = Math.max(coords.accuracy, 5);
      locationLayers.clearLayers();
      L.circle([point.lat, point.lon], {
        radius: accuracy,
        color: "#1459f5",
        weight: 1,
        fillColor: "#1459f5",
        fillOpacity: 0.1,
        interactive: false,
      }).addTo(locationLayers);
      setLocating(false);
      setMode("map", { focus: false });
      map.flyTo([point.lat, point.lon], 16);
      const converted = await convertCoordinates(point);
      if (converted) showToast(`현재 위치를 확인했습니다 (정확도 약 ${Math.round(accuracy)} m).`);
    },
    (error) => {
      setLocating(false);
      const message = {
        1: "위치 권한이 거부되었습니다. 브라우저 설정에서 권한을 허용해 주세요.",
        2: "현재 위치를 확인할 수 없습니다.",
        3: "현재 위치 확인 시간이 초과되었습니다.",
      }[error.code] || error.message;
      showToast(message, { error: true });
    },
    { enableHighAccuracy: true, timeout: 8000 },
  );
}

elements.mapMode.addEventListener("click", () => setMode("map"));
elements.codeMode.addEventListener("click", () => setMode("code"));

elements.commandForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const value = elements.commandInput.value.trim();
  if (!value) {
    showToast(state.mode === "map" ? "지도를 클릭하거나 좌표를 입력해 주세요." : "국가지점번호를 입력해 주세요.");
    elements.commandInput.focus();
    return;
  }

  if (state.mode === "code") {
    locationLayers.clearLayers();
    convertCode(value);
    return;
  }

  try {
    locationLayers.clearLayers();
    convertCoordinates(parseCoordinateInput(value), { moveMap: true });
  } catch (error) {
    setInputError(true);
    showToast(error.message, { error: true });
  }
});

map.on("click", ({ latlng }) => {
  locationLayers.clearLayers();
  setMode("map", { focus: false });
  convertCoordinates({ lon: latlng.lng, lat: latlng.lat });
});

map.on("moveend", renderSelection);
elements.copyButton.addEventListener("click", copyResult);
elements.clearButton.addEventListener("click", () => clearResult());
elements.settingsToggle.addEventListener("click", () => toggleSettings());
elements.settingsClose.addEventListener("click", () => toggleSettings(false));
elements.healthButton.addEventListener("click", () => checkHealth({ announce: true }));
elements.baseUrl.addEventListener("change", () => checkHealth({ announce: true }));

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !elements.settingsPanel.hidden) toggleSettings(false);
});

document.addEventListener("click", (event) => {
  if (
    !elements.settingsPanel.hidden &&
    !elements.settingsPanel.contains(event.target) &&
    !elements.settingsToggle.contains(event.target)
  ) {
    toggleSettings(false);
  }
});

async function initialize() {
  restoreApiUrl();
  setMode("map", { focus: false });
  clearResult({ clearInput: false });
  await convertCoordinates(DEFAULT_POINT);
}

initialize();
