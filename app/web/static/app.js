const form = document.getElementById("jobForm");
const apiSettingsForm = document.getElementById("apiSettingsForm");
const fileInput = document.getElementById("videoFile");
const subtitleFileInput = document.getElementById("subtitleFile");
const importSubtitleBtn = document.getElementById("importSubtitleBtn");
const videoPreview = document.getElementById("videoPreview");
const canvasFrame = document.getElementById("canvasFrame");
const canvasControls = document.getElementById("canvasControls");
const canvasControlsToggle = document.getElementById("canvasControlsToggle");
const canvasResizeHandle = document.getElementById("canvasResizeHandle");
const videoZoomRange = document.getElementById("videoZoomRange");
const videoZoomValue = document.getElementById("videoZoomValue");
const videoFitBtn = document.getElementById("videoFitBtn");
const subtitleSizeRange = document.getElementById("subtitleSizeRange");
const subtitleSizeValue = document.getElementById("subtitleSizeValue");
const subtitleXRange = document.getElementById("subtitleXRange");
const subtitleXValue = document.getElementById("subtitleXValue");
const subtitleYRange = document.getElementById("subtitleYRange");
const subtitleYValue = document.getElementById("subtitleYValue");
const subtitleCoverRange = document.getElementById("subtitleCoverRange");
const subtitleCoverValue = document.getElementById("subtitleCoverValue");
const subtitleCoverModeSelect = document.getElementById("subtitleCoverModeSelect");
const subtitleCoverHeightRange = document.getElementById("subtitleCoverHeightRange");
const subtitleCoverHeightValue = document.getElementById("subtitleCoverHeightValue");
const subtitleOverlay = document.getElementById("subtitleOverlay");
const originalSubtitleCover = document.getElementById("originalSubtitleCover");
const emptyState = document.getElementById("emptyState");
const videoName = document.getElementById("videoName");
const statusPill = document.getElementById("statusPill");
const dirtyBadge = document.getElementById("dirtyBadge");
const languageBadge = document.getElementById("languageBadge");
const progressBadge = document.getElementById("progressBadge");
const renderProgress = document.getElementById("renderProgress");
const renderProgressLabel = document.getElementById("renderProgressLabel");
const renderProgressFill = document.getElementById("renderProgressFill");
const timelineTrack = document.getElementById("timelineTrack");
const timelineLane = document.getElementById("timelineLane");
const timelineRuler = document.getElementById("timelineRuler");
const timelineZoomRange = document.getElementById("timelineZoomRange");
const timelineZoomValue = document.getElementById("timelineZoomValue");
const timelineMeta = document.getElementById("timelineMeta");
const jobList = document.getElementById("jobList");
const scriptList = document.getElementById("scriptList");
const sourceSrtLink = document.getElementById("sourceSrtLink");
const srtLink = document.getElementById("srtLink");
const vttLink = document.getElementById("vttLink");
const jsonLink = document.getElementById("jsonLink");
const hardsubLink = document.getElementById("hardsubLink");
const voiceoverLink = document.getElementById("voiceoverLink");
const previewSourceBtn = document.getElementById("previewSourceBtn");
const previewHardsubBtn = document.getElementById("previewHardsubBtn");
const previewVoiceoverBtn = document.getElementById("previewVoiceoverBtn");
const saveTimelineBtn = document.getElementById("saveTimelineBtn");
const translateSubtitleBtn = document.getElementById("translateSubtitleBtn");
const burnSubtitleBtn = document.getElementById("burnSubtitleBtn");
const voiceoverRenderBtn = document.getElementById("voiceoverRenderBtn");
const selectedClipTitle = document.getElementById("selectedClipTitle");
const selectedClipRange = document.getElementById("selectedClipRange");
const segmentStartInput = document.getElementById("segmentStart");
const segmentEndInput = document.getElementById("segmentEnd");
const segmentSourceInput = document.getElementById("segmentSource");
const segmentTranslatedInput = document.getElementById("segmentTranslated");
const segmentSubtitleInput = document.getElementById("segmentSubtitle");
const nudgeBackBtn = document.getElementById("nudgeBackBtn");
const nudgeForwardBtn = document.getElementById("nudgeForwardBtn");
const useTranslatedBtn = document.getElementById("useTranslatedBtn");
const splitSegmentBtn = document.getElementById("splitSegmentBtn");
const mergePreviousBtn = document.getElementById("mergePreviousBtn");
const mergeNextBtn = document.getElementById("mergeNextBtn");
const resumeJobsBtn = document.getElementById("resumeJobsBtn");
const apiSettingsToggle = document.getElementById("apiSettingsToggle");
const apiSettingsPanel = document.getElementById("apiSettingsPanel");
const apiSettingsClose = document.getElementById("apiSettingsClose");
const saveApiSettingsBtn = document.getElementById("saveApiSettingsBtn");
const apiSettingsStatus = document.getElementById("apiSettingsStatus");
const savePrompt = document.getElementById("savePrompt");
const savePromptMessage = document.getElementById("savePromptMessage");
const savePromptSaveBtn = document.getElementById("savePromptSaveBtn");
const savePromptDiscardBtn = document.getElementById("savePromptDiscardBtn");
const savePromptCancelBtn = document.getElementById("savePromptCancelBtn");
const toast = document.getElementById("toast");
const voiceNameInput = document.getElementById("voiceNameInput");
const voiceGainInput = document.getElementById("voiceGainInput");
const bedGainInput = document.getElementById("bedGainInput");

const MIN_SEGMENT_DURATION = 0.2;
const DEFAULT_TIMELINE_PIXELS_PER_SECOND = 72;
const MIN_VIDEO_ZOOM = 60;
const MAX_VIDEO_ZOOM = 180;
const DEFAULT_VIDEO_ASPECT_RATIO = 16 / 9;
const SUBTITLE_PREVIEW_REFERENCE_WIDTH = 1090;
const MIN_PREVIEW_SUBTITLE_FONT_SIZE = 4;
const MAX_PREVIEW_SUBTITLE_FONT_SIZE = 128;
const API_SETTINGS_STORAGE_KEY = "autoTranslateVideo.apiSettings.v1";
const SUBTITLE_STYLE_STORAGE_KEY = "autoTranslateVideo.subtitleStyle.v1";
const API_SETTING_FIELDS = [
  "openai_api_key",
  "openai_model",
  "openai_base_url",
  "gemini_api_key",
  "gemini_model",
  "gemini_base_url",
  "llm_base_url",
  "llm_api_key",
  "llm_model",
  "libretranslate_url",
  "libretranslate_api_key",
];

const STATUS_LABELS = {
  queued: "Đang chờ",
  running: "Đang chạy",
  completed: "Hoàn tất",
  failed: "Thất bại",
  completed_with_errors: "Hoàn tất có lỗi",
};

const ERROR_TRANSLATIONS = [
  ["Save failed", "Lưu thất bại"],
  ["Render failed", "Xuất video thất bại"],
  ["Could not create job.", "Không thể tạo tác vụ."],
  ["Could not resume jobs.", "Không thể chạy tiếp tác vụ."],
  ["Job failed", "Tác vụ thất bại"],
];

const STAGE_LABELS = {
  queued: "Đang chờ",
  probing: "Đọc thông tin video",
  extracting_audio: "Tách âm thanh",
  transcribing: "Nhận diện giọng nói / tải model lần đầu",
  translating: "Dịch phụ đề",
  writing_subtitles: "Ghi file phụ đề",
  rendering_hardsub: "Xuất video có phụ đề",
  rendering_voiceover: "Xuất video thuyết minh",
  subtitle_saved: "Đã lưu phụ đề",
  subtitle_translated: "Đã dịch lại phụ đề",
  translation_failed: "Dịch phụ đề thất bại",
  completed: "Hoàn tất",
  completed_with_errors: "Hoàn tất có lỗi",
  failed: "Thất bại",
  render_hardsub_failed: "Xuất phụ đề thất bại",
  render_voiceover_failed: "Xuất thuyết minh thất bại",
};

const EXPORT_ARTIFACTS = {
  video_hardsub: {
    label: "video phụ đề",
    suffix: "phu-de",
  },
  video_voiceover: {
    label: "video thuyết minh",
    suffix: "thuyet-minh",
  },
};
const ACTIVE_PROGRESS_STAGES = new Set(["translating", "rendering_hardsub", "rendering_voiceover"]);

const state = {
  jobId: null,
  job: null,
  segments: [],
  selectedSegmentId: null,
  dirty: false,
  pollTimer: null,
  queuePollTimer: null,
  laneWidth: 1400,
  timelinePixelsPerSecond: DEFAULT_TIMELINE_PIXELS_PER_SECOND,
  videoZoom: 100,
  subtitleStyle: {
    size: 32,
    x: 50,
    y: 8,
    coverMode: "blur",
    coverOpacity: 72,
    coverHeight: 18,
  },
  previewMode: "source",
  previewSourceMode: "source",
  drag: null,
  canvasResize: null,
  subtitleDrag: null,
  liveSegmentId: null,
  savePromptResolver: null,
  pendingExportSave: null,
};

function setDownloadLink(element, url) {
  if (!url) {
    element.href = "#";
    element.classList.add("disabled");
    return;
  }
  element.href = url;
  element.classList.remove("disabled");
}

function setSubtitleDownloadAction(element, enabled, title) {
  if (!element) {
    return;
  }
  element.href = "#";
  element.classList.toggle("disabled", !enabled);
  element.title = enabled ? title : "Chưa có phụ đề để lưu.";
}

function setRenderActionLink(element, enabled, title) {
  element.href = "#";
  element.classList.toggle("disabled", !enabled);
  element.title = enabled ? title : "Cần có phụ đề trước khi xuất video.";
}

function setDirty(value) {
  state.dirty = value;
  dirtyBadge.textContent = value ? "Chưa lưu" : "Đã lưu";
  dirtyBadge.classList.toggle("dirty", value);
  if (state.previewMode === "hardsub") {
    state.previewSourceMode = preferredPreviewSourceMode("hardsub");
    setPreviewButtons();
    applyPlaybackHighlight(videoPreview.currentTime || 0);
  }
}

function setStatus(text, tone = "neutral") {
  statusPill.textContent = text;
  statusPill.dataset.tone = tone;
  statusPill.title = text;
}

function filenameStem(value) {
  return String(value || "video")
    .split(/[\\/]/)
    .pop()
    .replace(/\.[^.]+$/, "")
    .replace(/[<>:"/\\|?*\x00-\x1F]/g, "_")
    .trim() || "video";
}

function defaultExportFilename(artifact) {
  const config = exportArtifactConfig(artifact);
  return `${filenameStem(state.job?.input_video || state.jobId)}.${config.suffix}.mp4`;
}

function exportArtifactConfig(artifact) {
  return EXPORT_ARTIFACTS[artifact] || EXPORT_ARTIFACTS.video_hardsub;
}

function supportsFileSavePicker() {
  return typeof window.showSaveFilePicker === "function" && window.isSecureContext;
}

async function pickExportDestination(artifact) {
  if (!supportsFileSavePicker()) {
    return { mode: "browser-download", artifact };
  }
  const config = exportArtifactConfig(artifact);
  const handle = await window.showSaveFilePicker({
    suggestedName: defaultExportFilename(artifact),
    types: [
      {
        description: `MP4 ${config.label}`,
        accept: { "video/mp4": [".mp4"] },
      },
    ],
  });
  return { mode: "file-picker", artifact, handle };
}

async function saveBlobToDestination(blob, destination, fallbackFilename) {
  if (destination?.mode === "file-picker" && destination.handle) {
    const writable = await destination.handle.createWritable();
    await writable.write(blob);
    await writable.close();
    return true;
  }
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fallbackFilename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  return false;
}

async function saveRenderedArtifact(job, destination) {
  if (!destination?.artifact || !job?.downloads?.[destination.artifact]) {
    return false;
  }
  const config = exportArtifactConfig(destination.artifact);
  setStatus(`Đang lưu ${config.label}...`, "neutral");
  const response = await fetch(job.downloads[destination.artifact]);
  if (!response.ok) {
    throw new Error(`Không tải được ${config.label} sau khi xuất.`);
  }
  const blob = await response.blob();
  const savedDirectly = await saveBlobToDestination(blob, destination, defaultExportFilename(destination.artifact));
  setStatus(savedDirectly ? `Đã lưu ${config.label} vào nơi đã chọn` : `Đã tải ${config.label}`, "ok");
  showToast(savedDirectly ? `Đã lưu ${config.label}.` : `Đã tải ${config.label}.`, "ok");
  return true;
}

function updateRenderProgress(job = null) {
  const isActiveProgress = Boolean(job && job.status === "running" && ACTIVE_PROGRESS_STAGES.has(job.stage));
  if (!renderProgress || !renderProgressFill || !renderProgressLabel) {
    return;
  }
  renderProgress.classList.toggle("hidden", !isActiveProgress);
  if (!isActiveProgress) {
    renderProgressFill.style.width = "0%";
    renderProgressLabel.textContent = "Đang xử lý 0%";
    renderProgress.setAttribute("aria-valuenow", "0");
    return;
  }
  const percent = Math.max(0, Math.min(100, Math.round((job.progress || 0) * 100)));
  renderProgressFill.style.width = `${percent}%`;
  renderProgressLabel.textContent = `${stageLabel(job.stage)} ${percent}%`;
  renderProgress.setAttribute("aria-valuenow", String(percent));
}

function showToast(text, tone = "neutral") {
  if (!toast) {
    return;
  }
  toast.textContent = text;
  toast.dataset.tone = tone;
  toast.classList.remove("hidden");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => {
    toast.classList.add("hidden");
  }, 3200);
}

function setApiSettingsStatus(text, tone = "neutral") {
  if (!apiSettingsStatus) {
    return;
  }
  apiSettingsStatus.textContent = text;
  apiSettingsStatus.dataset.tone = tone;
}

function setApiSettingsPanelOpen(open) {
  if (!apiSettingsPanel || !apiSettingsToggle) {
    return;
  }
  apiSettingsPanel.classList.toggle("hidden", !open);
  apiSettingsToggle.classList.toggle("active", open);
  apiSettingsToggle.setAttribute("aria-expanded", String(open));
}

function clampNumber(value, min, max, fallback) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return fallback;
  }
  return Math.max(min, Math.min(max, parsed));
}

function showSubtitleOverlayInCurrentMode() {
  return state.previewMode === "hardsub";
}

function preferredPreviewSourceMode(mode) {
  if (mode === "hardsub") {
    return "source";
  }
  return mode;
}

function persistSubtitleStyle() {
  try {
    window.localStorage.setItem(SUBTITLE_STYLE_STORAGE_KEY, JSON.stringify(state.subtitleStyle));
  } catch (error) {
  }
}

function subtitlePreviewScale() {
  const rect = canvasFrame?.getBoundingClientRect();
  const width = rect?.width || parseFloat(canvasFrame?.style.width) || SUBTITLE_PREVIEW_REFERENCE_WIDTH;
  return Math.max(0.25, Math.min(2.5, width / SUBTITLE_PREVIEW_REFERENCE_WIDTH));
}

function applySubtitleOverlayScale() {
  const scale = subtitlePreviewScale();
  const fontSize = clampNumber(
    state.subtitleStyle.size * scale,
    MIN_PREVIEW_SUBTITLE_FONT_SIZE,
    MAX_PREVIEW_SUBTITLE_FONT_SIZE,
    state.subtitleStyle.size,
  );
  const paddingY = Math.max(3, Math.round(10 * scale));
  const paddingX = Math.max(5, Math.round(16 * scale));
  const shadowY = Math.max(1, 3 * scale).toFixed(1);
  const shadowBlur = Math.max(2, 8 * scale).toFixed(1);
  const strokeBlur = Math.max(1, 2 * scale).toFixed(1);
  subtitleOverlay.style.fontSize = `${fontSize.toFixed(1)}px`;
  subtitleOverlay.style.padding = `${paddingY}px ${paddingX}px`;
  subtitleOverlay.style.textShadow = `0 ${shadowY}px ${shadowBlur}px #000, 0 0 ${strokeBlur}px #000`;
}

function applySubtitleStyle(nextStyle = {}) {
  const coverMode = ["blur", "box"].includes(nextStyle.coverMode)
    ? nextStyle.coverMode
    : state.subtitleStyle.coverMode;
  state.subtitleStyle = {
    size: clampNumber(nextStyle.size ?? state.subtitleStyle.size, 8, 64, 32),
    x: clampNumber(nextStyle.x ?? state.subtitleStyle.x, 10, 90, 50),
    y: clampNumber(nextStyle.y ?? state.subtitleStyle.y, 3, 45, 8),
    coverMode: coverMode || "blur",
    coverOpacity: clampNumber(nextStyle.coverOpacity ?? state.subtitleStyle.coverOpacity, 0, 100, 72),
    coverHeight: clampNumber(nextStyle.coverHeight ?? state.subtitleStyle.coverHeight, 8, 35, 18),
  };
  applySubtitleOverlayScale();
  subtitleOverlay.style.left = `${state.subtitleStyle.x}%`;
  subtitleOverlay.style.right = "auto";
  subtitleOverlay.style.bottom = `${state.subtitleStyle.y}%`;
  subtitleOverlay.style.transform = "translateX(-50%)";
  subtitleOverlay.style.width = "max-content";
  subtitleOverlay.style.maxWidth = "84%";
  const blurCoverWidth = 76;
  const blurCoverCenter = clampNumber(
    state.subtitleStyle.x,
    blurCoverWidth / 2,
    100 - blurCoverWidth / 2,
    50,
  );
  originalSubtitleCover.style.height = `${state.subtitleStyle.coverHeight}%`;
  originalSubtitleCover.style.opacity = state.subtitleStyle.coverMode === "blur"
    ? "1"
    : String(state.subtitleStyle.coverOpacity / 100);
  originalSubtitleCover.style.left = state.subtitleStyle.coverMode === "blur" ? `${blurCoverCenter}%` : "0";
  originalSubtitleCover.style.right = state.subtitleStyle.coverMode === "blur" ? "auto" : "0";
  originalSubtitleCover.style.width = state.subtitleStyle.coverMode === "blur" ? `${blurCoverWidth}%` : "auto";
  originalSubtitleCover.style.transform = state.subtitleStyle.coverMode === "blur" ? "translateX(-50%)" : "none";
  originalSubtitleCover.style.backdropFilter = state.subtitleStyle.coverMode === "blur"
    ? `blur(${Math.max(2, Math.round(state.subtitleStyle.coverOpacity / 8))}px)`
    : "none";
  originalSubtitleCover.style.background = state.subtitleStyle.coverMode === "blur"
    ? "transparent"
    : "#000";
  originalSubtitleCover.classList.toggle("blur-cover", state.subtitleStyle.coverMode === "blur");
  originalSubtitleCover.classList.toggle("box-cover", state.subtitleStyle.coverMode !== "blur");

  subtitleSizeRange.value = String(state.subtitleStyle.size);
  subtitleXRange.value = String(state.subtitleStyle.x);
  subtitleYRange.value = String(state.subtitleStyle.y);
  subtitleCoverModeSelect.value = state.subtitleStyle.coverMode;
  subtitleCoverRange.value = String(state.subtitleStyle.coverOpacity);
  subtitleCoverHeightRange.value = String(state.subtitleStyle.coverHeight);
  subtitleSizeValue.textContent = `${state.subtitleStyle.size}px`;
  subtitleXValue.textContent = `${state.subtitleStyle.x}%`;
  subtitleYValue.textContent = `${state.subtitleStyle.y}%`;
  subtitleCoverValue.textContent = `${state.subtitleStyle.coverOpacity}%`;
  subtitleCoverHeightValue.textContent = `${state.subtitleStyle.coverHeight}%`;
}

function loadSubtitleStyle() {
  try {
    const saved = JSON.parse(window.localStorage.getItem(SUBTITLE_STYLE_STORAGE_KEY) || "{}");
    applySubtitleStyle(saved);
  } catch (error) {
    applySubtitleStyle();
  }
}

function subtitleStylePayload() {
  return {
    subtitle_font_size: state.subtitleStyle.size,
    subtitle_position_x: state.subtitleStyle.x,
    subtitle_position_y: state.subtitleStyle.y,
    subtitle_cover_mode: state.subtitleStyle.coverMode,
    subtitle_cover_opacity: state.subtitleStyle.coverOpacity / 100,
    subtitle_cover_height_ratio: state.subtitleStyle.coverHeight / 100,
  };
}

function statusLabel(status) {
  return STATUS_LABELS[status] || status || "--";
}

function stageLabel(stage) {
  return STAGE_LABELS[stage] || stage || "--";
}

function escapeHtml(value) {
  return String(value || "").replace(/[&<>"]/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
  })[character]);
}

function userMessage(message) {
  let text = String(message || "Có lỗi xảy ra.");
  ERROR_TRANSLATIONS.forEach(([source, target]) => {
    text = text.replaceAll(source, target);
  });
  return text;
}

function getApiSettings() {
  const values = {};
  API_SETTING_FIELDS.forEach((fieldName) => {
    const input = apiSettingsForm?.elements[fieldName];
    const value = String(input?.value || "").trim();
    if (value) {
      values[fieldName] = value;
    }
  });
  return values;
}

function applyApiSettings(settings) {
  API_SETTING_FIELDS.forEach((fieldName) => {
    const input = apiSettingsForm?.elements[fieldName];
    if (input && Object.prototype.hasOwnProperty.call(settings, fieldName)) {
      input.value = settings[fieldName] || "";
    }
  });
}

function loadApiSettings() {
  try {
    const saved = JSON.parse(window.localStorage.getItem(API_SETTINGS_STORAGE_KEY) || "{}");
    applyApiSettings(saved);
    if (Object.keys(saved).length) {
      setApiSettingsStatus(`Đã nạp ${Object.keys(saved).length} mục cài đặt API từ trình duyệt này.`, "ok");
    }
  } catch (error) {
    setApiSettingsStatus("Không thể nạp cài đặt API đã lưu.", "error");
  }
}

function saveApiSettings() {
  const settings = getApiSettings();
  const total = Object.keys(settings).length;
  window.localStorage.setItem(API_SETTINGS_STORAGE_KEY, JSON.stringify(settings));
  const message = total
    ? `Đã lưu ${total} mục cài đặt API trên trình duyệt này.`
    : "Chưa có cài đặt API nào để lưu.";
  setApiSettingsStatus(message, total ? "ok" : "warn");
  showToast(message, total ? "ok" : "neutral");
}

function persistApiSettingsQuietly() {
  try {
    window.localStorage.setItem(API_SETTINGS_STORAGE_KEY, JSON.stringify(getApiSettings()));
    setApiSettingsStatus("Đã tự lưu thay đổi cài đặt API.", "ok");
  } catch (error) {
    setApiSettingsStatus("Không thể tự lưu cài đặt API.", "error");
  }
}

function appendApiSettings(payload) {
  const settings = getApiSettings();
  Object.entries(settings).forEach(([key, value]) => {
    payload.set(key, value);
  });
  if (payload.get("translator_backend") === "echo") {
    if (settings.gemini_api_key) {
      payload.set("translator_backend", "gemini");
    } else if (settings.openai_api_key) {
      payload.set("translator_backend", "gpt");
    }
  }
}

function appendSubtitleStyle(payload) {
  Object.entries(subtitleStylePayload()).forEach(([key, value]) => {
    payload.set(key, String(value));
  });
}

function closeSavePrompt(choice = "cancel") {
  savePrompt.classList.add("hidden");
  if (state.savePromptResolver) {
    state.savePromptResolver(choice);
    state.savePromptResolver = null;
  }
}

function askSaveChanges(message = "Bạn muốn lưu thay đổi trước khi tiếp tục không?") {
  if (!state.dirty) {
    return Promise.resolve("discard");
  }
  savePromptMessage.textContent = message;
  savePrompt.classList.remove("hidden");
  savePromptSaveBtn.focus();
  return new Promise((resolve) => {
    state.savePromptResolver = resolve;
  });
}

async function confirmUnsavedChanges(message) {
  if (!state.dirty) {
    return true;
  }

  const choice = await askSaveChanges(message);
  if (choice === "cancel") {
    return false;
  }
  if (choice === "save") {
    await saveTimeline();
  }
  if (choice === "discard") {
    setDirty(false);
  }
  return true;
}

function formatSeconds(value) {
  const seconds = Number(value || 0);
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

function formatPreciseSeconds(value) {
  return Number(value || 0).toFixed(2);
}

function parseSubtitleTimestamp(value) {
  const text = String(value || "").trim().replace(",", ".");
  const match = text.match(/(?:(\d+):)?(\d{1,2}):(\d{1,2})(?:\.(\d{1,3}))?/);
  if (!match) {
    return null;
  }
  const hours = Number(match[1] || 0);
  const minutes = Number(match[2] || 0);
  const seconds = Number(match[3] || 0);
  const milliseconds = Number((match[4] || "0").padEnd(3, "0"));
  return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000;
}

function normalizeImportedSegments(segments, duration = 0) {
  const normalized = [];
  segments
    .map((segment) => ({
      start: Number(segment.start ?? segment.start_sec ?? segment.from ?? 0),
      end: Number(segment.end ?? segment.end_sec ?? segment.to ?? 0),
      text: String(segment.subtitle_text || segment.translated_text || segment.text || "").trim(),
      translated_text: String(segment.translated_text || segment.subtitle_text || segment.text || "").trim(),
      subtitle_text: String(segment.subtitle_text || segment.translated_text || segment.text || "").trim(),
    }))
    .filter((segment) => Number.isFinite(segment.start) && Number.isFinite(segment.end) && segment.end > segment.start)
    .sort((first, second) => first.start - second.start || first.end - second.end)
    .forEach((segment, index) => {
      let start = Math.max(0, segment.start);
      let end = Math.max(start + MIN_SEGMENT_DURATION, segment.end);
      if (duration > 0) {
        start = Math.min(start, Math.max(duration - MIN_SEGMENT_DURATION, 0));
        end = Math.min(duration, Math.max(start + MIN_SEGMENT_DURATION, end));
      }
      normalized.push({
        id: index + 1,
        start: Number(start.toFixed(3)),
        end: Number(end.toFixed(3)),
        text: segment.text || segment.subtitle_text || segment.translated_text || "",
        translated_text: segment.translated_text || segment.subtitle_text || segment.text || "",
        subtitle_text: segment.subtitle_text || segment.translated_text || segment.text || "",
      });
    });
  return normalized;
}

function parseJsonSubtitle(text) {
  const payload = JSON.parse(text);
  const segments = Array.isArray(payload) ? payload : payload.segments;
  if (!Array.isArray(segments)) {
    throw new Error("File JSON không có danh sách segments.");
  }
  return segments;
}

function parseTimedTextSubtitle(text) {
  const blocks = String(text || "")
    .replace(/^\uFEFF/, "")
    .replace(/\r/g, "")
    .split(/\n{2,}/);
  const segments = [];

  blocks.forEach((block) => {
    const lines = block
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .filter((line) => !/^WEBVTT(?:\s|$)/i.test(line) && !/^NOTE(?:\s|$)/i.test(line));
    const timeLineIndex = lines.findIndex((line) => line.includes("-->"));
    if (timeLineIndex < 0) {
      return;
    }

    const [startRaw, endAndSettingsRaw] = lines[timeLineIndex].split("-->");
    const start = parseSubtitleTimestamp(startRaw);
    const end = parseSubtitleTimestamp(String(endAndSettingsRaw || "").trim().split(/\s+/)[0]);
    const subtitleText = lines.slice(timeLineIndex + 1).join("\n").trim();
    if (start === null || end === null || !subtitleText) {
      return;
    }
    segments.push({
      start,
      end,
      text: subtitleText,
      translated_text: subtitleText,
      subtitle_text: subtitleText,
    });
  });

  return segments;
}

function parseSubtitleFileText(text, fileName = "") {
  const isJson = fileName.toLowerCase().endsWith(".json") || String(text || "").trim().startsWith("{") || String(text || "").trim().startsWith("[");
  return isJson ? parseJsonSubtitle(text) : parseTimedTextSubtitle(text);
}

function editorDurationForImport(rawSegments = []) {
  const currentDuration = Number(state.job?.duration_sec || 0);
  if (currentDuration > 0) {
    return currentDuration;
  }
  const videoDuration = Number(videoPreview.duration || 0);
  if (Number.isFinite(videoDuration) && videoDuration > 0) {
    return videoDuration;
  }
  return Math.max(0, ...rawSegments.map((segment) => Number(segment.end ?? segment.end_sec ?? segment.to ?? 0)).filter(Number.isFinite));
}

function applyImportedSegments(segments, fileName) {
  if (!segments.length) {
    throw new Error("Không tìm thấy dòng phụ đề hợp lệ trong file này.");
  }
  const duration = Math.max(editorDurationForImport(segments), ...segments.map((segment) => Number(segment.end ?? segment.end_sec ?? segment.to ?? 0)).filter(Number.isFinite));
  const normalized = normalizeImportedSegments(segments, duration);
  if (!normalized.length) {
    throw new Error("Không tìm thấy mốc thời gian hợp lệ trong file phụ đề.");
  }

  if (!state.job) {
    state.job = {
      job_id: null,
      duration_sec: duration,
      downloads: {},
      preview_urls: {},
    };
  } else {
    state.job.duration_sec = Math.max(Number(state.job.duration_sec || 0), duration);
  }

  state.segments = normalized;
  state.selectedSegmentId = normalized[0].id;
  setDirty(true);
  renderAll();
  applyPlaybackHighlight(videoPreview.currentTime || 0);
  const saveHint = state.jobId ? "Bấm Lưu phụ đề để ghi vào tác vụ." : "Chọn/tạo tác vụ video nếu muốn lưu lại.";
  setStatus(`Đã import ${normalized.length} dòng từ ${fileName}. ${saveHint}`, state.jobId ? "warn" : "neutral");
  showToast(`Đã import ${normalized.length} dòng phụ đề.`, "ok");
}

async function importSubtitleFile(file) {
  if (!file) {
    return;
  }
  const shouldContinue = await confirmUnsavedChanges("Bạn đang có phụ đề chưa lưu. Lưu trước khi import file mới không?");
  if (!shouldContinue) {
    subtitleFileInput.value = "";
    return;
  }
  const text = await file.text();
  const parsedSegments = parseSubtitleFileText(text, file.name);
  applyImportedSegments(parsedSegments, file.name);
  subtitleFileInput.value = "";
}

function cloneSegments(segments) {
  return (segments || []).map((segment) => ({
    ...segment,
    translated_text: segment.translated_text || segment.text || "",
    subtitle_text: segmentSubtitleText(segment),
  }));
}

function orderedSegments() {
  return [...state.segments].sort((a, b) => a.start - b.start || a.end - b.end || a.id - b.id);
}

function getSegmentById(segmentId) {
  return state.segments.find((segment) => Number(segment.id) === Number(segmentId)) || null;
}

function getSelectedSegment() {
  return getSegmentById(state.selectedSegmentId);
}

function getSelectedOrderedIndex() {
  return orderedSegments().findIndex((segment) => Number(segment.id) === Number(state.selectedSegmentId));
}

function renumberSegments() {
  state.segments = orderedSegments().map((segment, index) => ({
    ...segment,
    id: index + 1,
  }));
}

function findSegmentByRange(start, end) {
  return state.segments.find(
    (segment) => Math.abs(Number(segment.start) - start) < 0.002 && Math.abs(Number(segment.end) - end) < 0.002,
  );
}

function splitTextValue(value) {
  const text = String(value || "").trim();
  if (!text) {
    return ["", ""];
  }

  const lines = text.split("\n").map((line) => line.trim()).filter(Boolean);
  if (lines.length > 1) {
    const midpoint = Math.ceil(lines.length / 2);
    return [lines.slice(0, midpoint).join("\n"), lines.slice(midpoint).join("\n")];
  }

  const words = text.split(/\s+/).filter(Boolean);
  if (words.length <= 1) {
    return [text, text];
  }

  const midpoint = Math.ceil(words.length / 2);
  return [words.slice(0, midpoint).join(" "), words.slice(midpoint).join(" ")];
}

function joinTextValues(first, second, separator = " ") {
  return [first, second]
    .map((value) => String(value || "").trim())
    .filter(Boolean)
    .join(separator);
}

function compactText(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function sameCompactText(first, second) {
  const firstText = compactText(first);
  const secondText = compactText(second);
  return !!firstText && !!secondText && firstText === secondText;
}

function segmentSubtitleText(segment) {
  const sourceText = compactText(segment?.text);
  const translatedText = compactText(segment?.translated_text);
  const subtitleText = compactText(segment?.subtitle_text);
  if (translatedText && translatedText !== sourceText && (!subtitleText || sameCompactText(subtitleText, sourceText))) {
    return translatedText;
  }
  return subtitleText || translatedText || sourceText;
}

function setPreviewButtons() {
  const previewUrls = state.job?.preview_urls || {};
  previewSourceBtn.classList.toggle("active", state.previewMode === "source");
  previewHardsubBtn.classList.toggle("active", state.previewMode === "hardsub");
  previewVoiceoverBtn.classList.toggle("active", state.previewMode === "voiceover");
  previewVoiceoverBtn.disabled = !previewUrls.voiceover;
  document.body.classList.toggle("subtitle-style-mode", showSubtitleOverlayInCurrentMode());
  originalSubtitleCover.classList.toggle("hidden", !showSubtitleOverlayInCurrentMode() || state.subtitleStyle.coverOpacity <= 0);
}

function currentVideoAspectRatio() {
  if (videoPreview.videoWidth > 0 && videoPreview.videoHeight > 0) {
    return videoPreview.videoWidth / videoPreview.videoHeight;
  }
  return DEFAULT_VIDEO_ASPECT_RATIO;
}

function availableCanvasSize() {
  const canvasArea = canvasFrame.parentElement;
  const areaRect = canvasArea?.getBoundingClientRect();
  if (!areaRect) {
    return { width: 1090, height: 613 };
  }
  const areaStyle = window.getComputedStyle(canvasArea);
  const paddingX = parseFloat(areaStyle.paddingLeft) + parseFloat(areaStyle.paddingRight);
  const paddingY = parseFloat(areaStyle.paddingTop) + parseFloat(areaStyle.paddingBottom);
  const gap = parseFloat(areaStyle.rowGap || areaStyle.gap) || 0;
  return {
    width: Math.max(240, areaRect.width - paddingX),
    height: Math.max(140, areaRect.height - paddingY),
  };
}

function applyVideoZoom(value = state.videoZoom) {
  const nextZoom = Math.max(MIN_VIDEO_ZOOM, Math.min(MAX_VIDEO_ZOOM, Number(value) || 100));
  const { width: availableWidth, height: availableHeight } = availableCanvasSize();
  const aspectRatio = currentVideoAspectRatio();
  const fitWidth = Math.min(1090, availableWidth);
  const fitHeight = Math.min(availableHeight, fitWidth / aspectRatio);
  const zoomScale = nextZoom / 100;
  const targetWidth = Math.min(availableWidth, fitHeight * aspectRatio * zoomScale);
  const targetHeight = Math.min(availableHeight, targetWidth / aspectRatio);
  state.videoZoom = nextZoom;
  canvasFrame.style.width = `${Math.round(targetWidth)}px`;
  canvasFrame.style.height = `${Math.round(targetHeight)}px`;
  canvasFrame.style.aspectRatio = `${aspectRatio}`;
  if (videoZoomRange) {
    videoZoomRange.value = String(nextZoom);
  }
  if (videoZoomValue) {
    videoZoomValue.textContent = `${nextZoom}%`;
  }
  applySubtitleOverlayScale();
}

function resetVideoZoom() {
  applyVideoZoom(100);
}

function setCanvasControlsOpen(open) {
  if (!canvasControls || !canvasControlsToggle) {
    return;
  }
  canvasControls.classList.toggle("collapsed", !open);
  canvasControlsToggle.setAttribute("aria-expanded", String(open));
  canvasControlsToggle.textContent = open ? "✕ Đóng chỉnh" : "⚙ Chỉnh";
  applyVideoZoom();
}

function applyTimelineZoom(value = state.timelinePixelsPerSecond, preserveCenter = true) {
  const duration = Number(state.job?.duration_sec || 0);
  const previousWidth = state.laneWidth || timelineTrack.clientWidth || 1;
  const centerRatio = preserveCenter && previousWidth > 0
    ? (timelineTrack.scrollLeft + timelineTrack.clientWidth / 2) / previousWidth
    : 0;
  const nextPixelsPerSecond = Math.max(32, Math.min(180, Number(value) || DEFAULT_TIMELINE_PIXELS_PER_SECOND));
  state.timelinePixelsPerSecond = nextPixelsPerSecond;
  if (timelineZoomRange) {
    timelineZoomRange.value = String(nextPixelsPerSecond);
  }
  if (timelineZoomValue) {
    timelineZoomValue.textContent = `${nextPixelsPerSecond} px/s`;
  }
  renderTimeline();
  if (preserveCenter && duration > 0) {
    const nextScrollLeft = centerRatio * state.laneWidth - timelineTrack.clientWidth / 2;
    timelineTrack.scrollLeft = Math.max(0, nextScrollLeft);
  }
}

function updatePreviewSource(url) {
  if (!url) {
    return;
  }
  if (videoPreview.dataset.previewUrl === url) {
    return;
  }
  const currentTime = Number(videoPreview.currentTime || 0);
  videoPreview.dataset.previewUrl = url;
  videoPreview.src = url;
  if (currentTime > 0) {
    videoPreview.addEventListener("loadedmetadata", () => {
      seekVideoToTime(currentTime);
    }, { once: true });
  }
}

function setPreviewMode(mode) {
  const previewUrls = state.job?.preview_urls || {};
  const sourceMode = preferredPreviewSourceMode(mode);
  const targetUrl = previewUrls[sourceMode];
  if (!targetUrl) {
    if (["source", "hardsub"].includes(mode) && (videoPreview.currentSrc || videoPreview.src)) {
      state.previewMode = mode;
      state.previewSourceMode = sourceMode;
      videoPreview.style.display = "block";
      emptyState.style.display = "none";
      setPreviewButtons();
      applyPlaybackHighlight(videoPreview.currentTime || 0);
    }
    return;
  }
  state.previewMode = mode;
  state.previewSourceMode = sourceMode;
  updatePreviewSource(targetUrl);
  videoPreview.style.display = "block";
  emptyState.style.display = "none";
  setPreviewButtons();
  applyPlaybackHighlight(videoPreview.currentTime || 0);
}

function renderArtifactLinks(job) {
  const canRenderVideo = Boolean(job.downloads?.transcript_json && !["queued", "running"].includes(job.status));
  setSubtitleDownloadAction(sourceSrtLink, Boolean(state.segments.length), "Lưu phụ đề gốc đang hiển thị");
  setSubtitleDownloadAction(srtLink, Boolean(state.segments.length), "Lưu phụ đề dịch/đã sửa đang hiển thị");
  setDownloadLink(vttLink, job.downloads?.subtitle_vtt);
  setDownloadLink(jsonLink, job.downloads?.transcript_json);
  setRenderActionLink(hardsubLink, canRenderVideo, "Xuất lại MP4 phụ đề từ nội dung đang sửa");
  setRenderActionLink(voiceoverLink, canRenderVideo, "Xuất lại MP4 thuyết minh từ phụ đề đang sửa");
}

function renderJobList(jobs) {
  jobList.innerHTML = "";
  if (!jobs?.length) {
    jobList.innerHTML = '<div class="script-empty">Tác vụ đang chờ sẽ hiện ở đây.</div>';
    return;
  }

  jobs.slice(0, 12).forEach((job) => {
    const item = document.createElement("div");
    item.className = "job-item";
    item.dataset.id = job.job_id;
    if (job.job_id === state.jobId) {
      item.classList.add("selected");
    }
    const filename = String(job.input_video || job.job_id).split(/[\\/]/).pop();
    item.innerHTML = `
      <button class="job-select" type="button" data-job-action="select">
        <div>
          <strong>${escapeHtml(filename)}</strong>
          <span>${escapeHtml(stageLabel(job.stage || job.status))} | ${Math.round((job.progress || 0) * 100)}%</span>
        </div>
        <small class="job-status">${escapeHtml(statusLabel(job.status))}</small>
      </button>
      <button class="job-delete" type="button" data-job-action="delete" title="Xoá tác vụ này">Xoá</button>
    `;
    jobList.appendChild(item);
  });
}

function renderTimeline() {
  timelineLane.innerHTML = "";
  timelineRuler.innerHTML = "";

  const duration = Number(state.job?.duration_sec || 0);
  const segments = orderedSegments();
  if (!segments.length || !duration) {
    timelineMeta.textContent = "Chưa có bản nhận diện.";
    timelineLane.style.width = "100%";
    timelineRuler.style.width = "100%";
    return;
  }

  const roundedDuration = Math.max(1, Math.ceil(duration));
  state.laneWidth = Math.max(timelineTrack.clientWidth || 0, roundedDuration * state.timelinePixelsPerSecond);
  timelineLane.style.width = `${state.laneWidth}px`;
  timelineRuler.style.width = `${state.laneWidth}px`;
  timelineMeta.textContent = `${segments.length} đoạn | ${formatSeconds(duration)} | ${state.timelinePixelsPerSecond} px/s`;

  const minMarkerGap = 92;
  const markerStep = Math.max(1, Math.ceil(minMarkerGap / state.timelinePixelsPerSecond));
  for (let point = 0; point <= roundedDuration; point += markerStep) {
    const marker = document.createElement("div");
    marker.className = "timeline-marker";
    marker.style.left = `${Math.min((point / duration) * state.laneWidth, state.laneWidth)}px`;
    marker.innerHTML = `<span>${formatSeconds(point)}</span>`;
    timelineRuler.appendChild(marker);
  }
  if (roundedDuration % markerStep !== 0) {
    const marker = document.createElement("div");
    marker.className = "timeline-marker";
    marker.style.left = `${state.laneWidth}px`;
    marker.innerHTML = `<span>${formatSeconds(duration)}</span>`;
    timelineRuler.appendChild(marker);
  }

  segments.forEach((segment) => {
    const block = document.createElement("button");
    block.type = "button";
    block.className = "timeline-block";
    block.dataset.id = segment.id;
    block.style.left = `${(segment.start / duration) * state.laneWidth}px`;
    block.style.width = `${Math.max(((segment.end - segment.start) / duration) * state.laneWidth, 54)}px`;
    if (Number(segment.id) === Number(state.selectedSegmentId)) {
      block.classList.add("selected");
    }
    if (Number(segment.id) === Number(state.liveSegmentId)) {
      block.classList.add("live");
    }
    block.innerHTML = `
      <span class="timeline-handle left" data-edge="left"></span>
      <span class="timeline-stamp">${formatSeconds(segment.start)} - ${formatSeconds(segment.end)}</span>
      <strong>${escapeHtml(segmentSubtitleText(segment))}</strong>
      <span class="timeline-handle right" data-edge="right"></span>
    `;
    timelineLane.appendChild(block);
  });
}

function renderScriptList() {
  const segments = orderedSegments();
  scriptList.innerHTML = "";

  if (!segments.length) {
    scriptList.innerHTML = '<div class="script-empty">Các dòng phụ đề sẽ hiện ở đây sau khi xử lý.</div>';
    return;
  }

  segments.forEach((segment) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "script-item";
    item.dataset.id = segment.id;
    if (Number(segment.id) === Number(state.selectedSegmentId)) {
      item.classList.add("selected");
    }
    if (Number(segment.id) === Number(state.liveSegmentId)) {
      item.classList.add("live");
    }
    item.innerHTML = `
      <div class="script-time">${formatSeconds(segment.start)} - ${formatSeconds(segment.end)}</div>
      <div class="script-copy">
        <strong>${escapeHtml(segmentSubtitleText(segment))}</strong>
      </div>
    `;
    scriptList.appendChild(item);
  });
}

function renderInspector() {
  const segment = getSelectedSegment();
  const disabled = !segment;
  [segmentStartInput, segmentEndInput, segmentSourceInput, segmentTranslatedInput, segmentSubtitleInput].forEach((input) => {
    input.disabled = disabled;
  });
  [nudgeBackBtn, nudgeForwardBtn, useTranslatedBtn, splitSegmentBtn, mergePreviousBtn, mergeNextBtn].forEach((button) => {
    button.disabled = disabled;
  });

  if (!segment) {
    selectedClipTitle.textContent = "Chưa chọn đoạn";
    selectedClipRange.textContent = "--";
    segmentStartInput.value = "";
    segmentEndInput.value = "";
    segmentSourceInput.value = "";
    segmentTranslatedInput.value = "";
    segmentSubtitleInput.value = "";
    return;
  }

  const selectedIndex = getSelectedOrderedIndex();
  splitSegmentBtn.disabled = Number(segment.end) - Number(segment.start) < MIN_SEGMENT_DURATION * 2;
  mergePreviousBtn.disabled = selectedIndex <= 0;
  mergeNextBtn.disabled = selectedIndex < 0 || selectedIndex >= state.segments.length - 1;

  selectedClipTitle.textContent = `Đoạn ${segment.id}`;
  selectedClipRange.textContent = `${formatSeconds(segment.start)} - ${formatSeconds(segment.end)}`;
  segmentStartInput.value = formatPreciseSeconds(segment.start);
  segmentEndInput.value = formatPreciseSeconds(segment.end);
  segmentSourceInput.value = segment.text || "";
  segmentTranslatedInput.value = segment.translated_text || "";
  segmentSubtitleInput.value = segmentSubtitleText(segment);
}

function renderAll() {
  renderTimeline();
  renderScriptList();
  renderInspector();
  setPreviewButtons();
  applyPlaybackHighlight(videoPreview.currentTime || 0);
}

function focusSubtitleEditor() {
  if (!segmentSubtitleInput || segmentSubtitleInput.disabled) {
    return;
  }
  segmentSubtitleInput.focus({ preventScroll: true });
  segmentSubtitleInput.select();
}

function seekVideoToTime(time) {
  const duration = Number(state.job?.duration_sec || videoPreview.duration || 0);
  const nextTime = duration > 0 ? Math.max(0, Math.min(Number(time) || 0, duration)) : Math.max(0, Number(time) || 0);
  if (Number.isFinite(videoPreview.currentTime)) {
    videoPreview.currentTime = nextTime;
  }
  applyPlaybackHighlight(nextTime);
}

function timelineTimeFromPointer(event) {
  const duration = Number(state.job?.duration_sec || 0);
  if (!duration || !state.laneWidth) {
    return null;
  }
  const rect = timelineLane.getBoundingClientRect();
  const x = Math.max(0, Math.min(event.clientX - rect.left, state.laneWidth));
  return (x / state.laneWidth) * duration;
}

function segmentContainingTime(time) {
  return orderedSegments().find(
    (segment) => time >= Number(segment.start) && time <= Number(segment.end),
  ) || null;
}

function selectSegmentAtTime(time, focusEditor = false) {
  const segment = segmentContainingTime(time);
  if (segment) {
    selectSegment(Number(segment.id), false, focusEditor);
  }
  seekVideoToTime(time);
}

function selectSegment(segmentId, seekVideo = false, focusEditor = false) {
  if (!getSegmentById(segmentId)) {
    return;
  }
  state.selectedSegmentId = Number(segmentId);
  renderAll();
  if (seekVideo && Number.isFinite(videoPreview.currentTime)) {
    const segment = getSelectedSegment();
    if (segment) {
      seekVideoToTime(segment.start);
    }
  }
  const selectedSegment = getSelectedSegment();
  if (selectedSegment) {
    const selectedText = segmentSubtitleText(selectedSegment);
    subtitleOverlay.textContent = selectedText;
    subtitleOverlay.classList.toggle("hidden", !selectedText || !showSubtitleOverlayInCurrentMode());
  }
  if (focusEditor) {
    focusSubtitleEditor();
  }
}

function applyPlaybackHighlight(currentTime) {
  const activeSegment = orderedSegments().find(
    (segment) => currentTime >= Number(segment.start) && currentTime <= Number(segment.end),
  );
  state.liveSegmentId = activeSegment ? Number(activeSegment.id) : null;
  const overlayText = activeSegment ? segmentSubtitleText(activeSegment) : "";
  subtitleOverlay.textContent = overlayText;
  subtitleOverlay.classList.toggle("hidden", !overlayText || !showSubtitleOverlayInCurrentMode());

  document.querySelectorAll(".timeline-block").forEach((block) => {
    block.classList.toggle("live", Number(block.dataset.id) === Number(state.liveSegmentId));
  });
  document.querySelectorAll(".script-item").forEach((item) => {
    item.classList.toggle("live", Number(item.dataset.id) === Number(state.liveSegmentId));
  });
}

function applyJobState(job) {
  state.job = job;
  state.jobId = job.job_id;
  if (!state.dirty || !state.segments.length) {
    state.segments = cloneSegments(job.segments);
  }

  if (!getSegmentById(state.selectedSegmentId) && state.segments.length) {
    state.selectedSegmentId = Number(state.segments[0].id);
  }
  if (!state.segments.length) {
    state.selectedSegmentId = null;
  }

  languageBadge.textContent = `ngôn ngữ gốc: ${job.detected_language || "--"}`;
  const jobPercent = Math.round((job.progress || 0) * 100);
  progressBadge.textContent = `${jobPercent}%`;
  updateRenderProgress(job);
  translateSubtitleBtn.disabled = !job.downloads?.transcript_json;
  translateSubtitleBtn.title = translateSubtitleBtn.disabled
    ? "Cần xử lý/nhận dạng video xong trước khi dịch lại"
    : "Dịch lại phụ đề sang tiếng Việt";
  renderArtifactLinks(job);

  const sourceMode = preferredPreviewSourceMode(state.previewMode);
  if (job.preview_urls?.[sourceMode]) {
    state.previewSourceMode = sourceMode;
    updatePreviewSource(job.preview_urls[sourceMode]);
  } else if (job.preview_urls?.source) {
    state.previewMode = "source";
    state.previewSourceMode = "source";
    updatePreviewSource(job.preview_urls.source);
  }
  if (videoPreview.src) {
    videoPreview.style.display = "block";
    emptyState.style.display = "none";
  }

  setStatus(`${stageLabel(job.stage)} | ${jobPercent}%`, job.status === "completed_with_errors" ? "warn" : "neutral");
  renderAll();

  if (job.status === "completed") {
    if (state.pendingExportSave?.jobId === job.job_id) {
      const pendingExport = state.pendingExportSave;
      state.pendingExportSave = null;
      saveRenderedArtifact(job, pendingExport.destination).catch((error) => {
        setStatus(userMessage(error.message), "error");
      });
    } else {
      setStatus("Hoàn tất", "ok");
    }
    stopPolling();
    pollJobs();
  }

  if (job.status === "completed_with_errors") {
    const message = job.errors?.[0] || "Xuất video hoàn tất nhưng có cảnh báo";
    if (state.pendingExportSave?.jobId === job.job_id && job.downloads?.[state.pendingExportSave.destination.artifact]) {
      const pendingExport = state.pendingExportSave;
      state.pendingExportSave = null;
      saveRenderedArtifact(job, pendingExport.destination)
        .then(() => setStatus(`${message} | đã lưu file`, "warn"))
        .catch((error) => setStatus(userMessage(error.message), "error"));
    } else {
      state.pendingExportSave = null;
      setStatus(message, "warn");
    }
    stopPolling();
    pollJobs();
  }

  if (job.status === "failed") {
    state.pendingExportSave = null;
    const message = job.errors?.[0] || "Tác vụ thất bại";
    setStatus(userMessage(message), "error");
    stopPolling();
    pollJobs();
  }
}

async function pollJob(jobId) {
  const response = await fetch(`/api/jobs/${jobId}`);
  if (!response.ok) {
    return;
  }
  const job = await response.json();
  applyJobState(job);
}

async function loadJob(jobId) {
  const shouldContinue = await confirmUnsavedChanges("Bạn đang có phụ đề chưa lưu. Lưu trước khi chuyển tác vụ không?");
  if (!shouldContinue) {
    return;
  }
  stopPolling();
  state.jobId = jobId;
  state.selectedSegmentId = null;
  state.segments = [];
  setDirty(false);
  await pollJob(jobId);
  if (["queued", "running"].includes(state.job?.status)) {
    startPolling();
  }
}

function clearSelectedJob() {
  state.jobId = null;
  state.job = null;
  state.segments = [];
  state.selectedSegmentId = null;
  state.previewMode = "source";
  subtitleOverlay.textContent = "";
  subtitleOverlay.classList.add("hidden");
  originalSubtitleCover.classList.add("hidden");
  videoPreview.removeAttribute("src");
  videoPreview.dataset.previewUrl = "";
  videoPreview.load();
  videoPreview.style.display = "none";
  emptyState.style.display = "grid";
  videoName.textContent = "Chưa chọn video";
  languageBadge.textContent = "ngôn ngữ gốc: --";
  progressBadge.textContent = "0%";
  updateRenderProgress(null);
  translateSubtitleBtn.disabled = true;
  translateSubtitleBtn.title = "Cần xử lý video xong trước khi dịch lại";
  renderArtifactLinks({ downloads: {} });
  setDirty(false);
  renderAll();
}

async function deleteJob(jobId) {
  const shouldContinue = await confirmUnsavedChanges("Bạn đang có phụ đề chưa lưu. Lưu trước khi xoá tác vụ không?");
  if (!shouldContinue) {
    return;
  }
  const accepted = window.confirm("Xoá tác vụ này khỏi danh sách gần đây? Các file phụ đề/video đã tạo trong tác vụ cũng sẽ bị xoá.");
  if (!accepted) {
    return;
  }
  const response = await fetch(`/api/jobs/${jobId}`, { method: "DELETE" });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Không thể xoá tác vụ." }));
    throw new Error(userMessage(error.detail || "Không thể xoá tác vụ."));
  }
  if (jobId === state.jobId) {
    stopPolling();
    clearSelectedJob();
  }
  showToast("Đã xoá tác vụ.", "ok");
  await pollJobs();
}

async function pollJobs() {
  const response = await fetch("/api/jobs");
  if (!response.ok) {
    return;
  }
  const payload = await response.json();
  renderJobList(payload.jobs || []);
}

function startPolling() {
  if (!state.jobId) {
    return;
  }
  stopPolling();
  state.pollTimer = window.setInterval(() => pollJob(state.jobId), 2500);
}

function startQueuePolling() {
  if (state.queuePollTimer) {
    window.clearInterval(state.queuePollTimer);
  }
  state.queuePollTimer = window.setInterval(() => pollJobs(), 5000);
}

function stopPolling() {
  if (state.pollTimer) {
    window.clearInterval(state.pollTimer);
    state.pollTimer = null;
  }
}

function sanitizeSegmentsForSave() {
  return state.segments.map((segment) => ({
    id: Number(segment.id),
    start: Number(segment.start),
    end: Number(segment.end),
    text: String(segment.text || "").trim(),
    translated_text: String(segment.translated_text || segment.text || "").trim(),
    subtitle_text: segmentSubtitleText(segment),
  }));
}

function srtTimestamp(value) {
  const totalMilliseconds = Math.max(0, Math.round(Number(value || 0) * 1000));
  const hours = Math.floor(totalMilliseconds / 3600000);
  const minutes = Math.floor((totalMilliseconds % 3600000) / 60000);
  const seconds = Math.floor((totalMilliseconds % 60000) / 1000);
  const milliseconds = totalMilliseconds % 1000;
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")},${String(milliseconds).padStart(3, "0")}`;
}

function buildSrtFromSegments(textGetter) {
  return `${orderedSegments()
    .map((segment, index) => {
      const text = String(textGetter(segment) || "").trim();
      return [String(index + 1), `${srtTimestamp(segment.start)} --> ${srtTimestamp(segment.end)}`, text].join("\n");
    })
    .join("\n\n")}\n`;
}

function downloadTextFile(filename, content, mimeType = "text/plain;charset=utf-8") {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function downloadCurrentSubtitle(kind) {
  if (!state.segments.length) {
    setStatus("Chưa có phụ đề để lưu.", "warn");
    return;
  }
  const isSource = kind === "source";
  const content = buildSrtFromSegments((segment) => (isSource ? segment.text : segmentSubtitleText(segment)));
  const suffix = isSource ? "phu-de-goc" : "phu-de-dich";
  downloadTextFile(`${filenameStem(state.job?.input_video || state.jobId)}.${suffix}.srt`, content, "application/x-subrip;charset=utf-8");
  setStatus(isSource ? "Đã lưu phụ đề gốc." : "Đã lưu phụ đề dịch.", "ok");
}

async function saveTimeline() {
  if (!state.jobId) {
    return;
  }
  const response = await fetch(`/api/jobs/${state.jobId}/segments`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ segments: sanitizeSegmentsForSave() }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Lưu thất bại" }));
    throw new Error(userMessage(error.detail || "Lưu thất bại"));
  }
  const job = await response.json();
  setDirty(false);
  applyJobState(job);
}

async function runRender(endpoint, body = null, options = {}) {
  if (!state.jobId) {
    return;
  }
  if (!options.skipConfirm) {
    const shouldContinue = await confirmUnsavedChanges("Bạn đang có phụ đề chưa lưu. Lưu trước khi xuất video không?");
    if (!shouldContinue) {
      return false;
    }
  }
  const response = await fetch(endpoint, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Xuất video thất bại" }));
    throw new Error(userMessage(error.detail || "Xuất video thất bại"));
  }
  const job = await response.json().catch(() => null);
  if (job?.job_id) {
    applyJobState(job);
  }
  setStatus("Đã đưa lệnh xuất video vào hàng đợi...", "neutral");
  startPolling();
  return true;
}

async function runRenderWithDestination(endpoint, artifact, body = null) {
  const shouldContinue = await confirmUnsavedChanges("Bạn đang có phụ đề chưa lưu. Lưu trước khi xuất video không?");
  if (!shouldContinue) {
    return false;
  }
  let destination;
  try {
    destination = await pickExportDestination(artifact);
  } catch (error) {
    if (error?.name === "AbortError") {
      setStatus("Đã huỷ chọn nơi lưu video", "neutral");
      return false;
    }
    throw error;
  }
  state.pendingExportSave = { jobId: state.jobId, destination };
  try {
    return await runRender(endpoint, body, { skipConfirm: true });
  } catch (error) {
    state.pendingExportSave = null;
    throw error;
  }
}

function voiceoverRenderPayload() {
  return {
    ...subtitleStylePayload(),
    voice_name: voiceNameInput.value || null,
    voiceover_gain: parseNumberOrCurrent(voiceGainInput.value, null),
    background_audio_gain: parseNumberOrCurrent(bedGainInput.value, null),
  };
}

async function renderHardsubFromCurrentSubtitles() {
  if (!state.jobId || hardsubLink.classList.contains("disabled")) {
    return;
  }
  setStatus("Đang xuất MP4 phụ đề từ nội dung đã sửa...", "neutral");
  await runRenderWithDestination(
    `/api/jobs/${state.jobId}/render/hardsub`,
    "video_hardsub",
    subtitleStylePayload(),
  );
}

async function renderVoiceoverFromCurrentSubtitles() {
  if (!state.jobId || voiceoverLink.classList.contains("disabled")) {
    return;
  }
  setStatus("Đang xuất MP4 thuyết minh từ phụ đề đã sửa...", "neutral");
  await runRenderWithDestination(
    `/api/jobs/${state.jobId}/render/voiceover`,
    "video_voiceover",
    voiceoverRenderPayload(),
  );
}

async function runTranslate() {
  if (!state.jobId) {
    return;
  }
  if (!state.job?.downloads?.transcript_json) {
    throw new Error("Chưa có bản nhận dạng giọng nói. Hãy xử lý video xong trước rồi mới dịch lại.");
  }
  const shouldContinue = await confirmUnsavedChanges("Bạn đang có phụ đề chưa lưu. Lưu trước khi dịch lại không?");
  if (!shouldContinue) {
    return false;
  }
  const settings = getApiSettings();
  const backend = form.elements.translator_backend?.value || "gemini";
  const payload = {
    translator_backend: backend,
    target_language: "vi",
    ...settings,
  };
  const response = await fetch(`/api/jobs/${state.jobId}/translate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Dịch phụ đề thất bại" }));
    throw new Error(userMessage(error.detail || "Dịch phụ đề thất bại"));
  }
  const job = await response.json().catch(() => null);
  if (job?.job_id) {
    applyJobState(job);
  }
  setStatus("Đã đưa lệnh dịch lại phụ đề vào hàng đợi...", "neutral");
  startPolling();
  return true;
}

function updateSelectedSegment(updater) {
  const segment = getSelectedSegment();
  const duration = Number(state.job?.duration_sec || 0);
  if (!segment) {
    return;
  }

  updater(segment);

  if (duration > 0) {
    segment.start = Math.max(0, Math.min(segment.start, duration - MIN_SEGMENT_DURATION));
    segment.end = Math.max(segment.start + MIN_SEGMENT_DURATION, Math.min(segment.end, duration));
    if (segment.end <= segment.start) {
      segment.end = Math.min(duration, segment.start + MIN_SEGMENT_DURATION);
    }
  } else {
    segment.start = Math.max(0, segment.start);
    segment.end = Math.max(segment.start + MIN_SEGMENT_DURATION, segment.end);
  }

  segment.start = Number(segment.start.toFixed(3));
  segment.end = Number(segment.end.toFixed(3));
  setDirty(true);
  renderAll();
}

function updateSelectedTextField(fieldName, value) {
  const segment = getSelectedSegment();
  if (!segment) {
    return;
  }
  segment[fieldName] = value;
  setDirty(true);
  renderTimeline();
  renderScriptList();
  applyPlaybackHighlight(videoPreview.currentTime || 0);
}

function splitSelectedSegment() {
  const segment = getSelectedSegment();
  if (!segment) {
    return;
  }

  const start = Number(segment.start);
  const end = Number(segment.end);
  const segmentDuration = end - start;
  if (segmentDuration < MIN_SEGMENT_DURATION * 2) {
    setStatus("Đoạn này quá ngắn để tách.", "error");
    return;
  }

  const playhead = Number(videoPreview.currentTime);
  const canSplitAtPlayhead = playhead > start + MIN_SEGMENT_DURATION && playhead < end - MIN_SEGMENT_DURATION;
  const splitAt = Number((canSplitAtPlayhead ? playhead : start + segmentDuration / 2).toFixed(3));
  const [firstSource, secondSource] = splitTextValue(segment.text);
  const [firstTranslated, secondTranslated] = splitTextValue(segment.translated_text || segment.text);
  const [firstSubtitle, secondSubtitle] = splitTextValue(segment.subtitle_text || segment.translated_text || segment.text);

  const firstSegment = {
    ...segment,
    start,
    end: splitAt,
    text: firstSource || segment.text || "",
    translated_text: firstTranslated || segment.translated_text || firstSource || segment.text || "",
    subtitle_text: firstSubtitle || firstTranslated || segmentSubtitleText(segment) || firstSource || "",
  };
  const secondSegment = {
    ...segment,
    start: splitAt,
    end,
    text: secondSource || firstSource || segment.text || "",
    translated_text: secondTranslated || secondSource || segment.translated_text || segment.text || "",
    subtitle_text: secondSubtitle || secondTranslated || segmentSubtitleText(segment) || secondSource || "",
  };

  state.segments = state.segments
    .filter((candidate) => Number(candidate.id) !== Number(segment.id))
    .concat(firstSegment, secondSegment);
  renumberSegments();

  const selectedSegment = findSegmentByRange(start, splitAt) || orderedSegments()[0];
  state.selectedSegmentId = selectedSegment ? Number(selectedSegment.id) : null;
  setDirty(true);
  renderAll();
  setStatus(canSplitAtPlayhead ? "Đã tách đoạn tại vị trí phát." : "Đã tách đoạn ở giữa.", "warn");
}

function mergeSelectedSegment(direction) {
  const segments = orderedSegments();
  const selectedIndex = getSelectedOrderedIndex();
  if (selectedIndex < 0) {
    return;
  }

  const neighborIndex = direction === "previous" ? selectedIndex - 1 : selectedIndex + 1;
  if (neighborIndex < 0 || neighborIndex >= segments.length) {
    setStatus("Không có đoạn kế bên để gộp.", "error");
    return;
  }

  const selectedSegment = segments[selectedIndex];
  const neighborSegment = segments[neighborIndex];
  const firstSegment = neighborIndex < selectedIndex ? neighborSegment : selectedSegment;
  const secondSegment = neighborIndex < selectedIndex ? selectedSegment : neighborSegment;
  const mergedStart = Math.min(Number(firstSegment.start), Number(secondSegment.start));
  const mergedEnd = Math.max(Number(firstSegment.end), Number(secondSegment.end));
  const mergedSegment = {
    ...firstSegment,
    start: Number(mergedStart.toFixed(3)),
    end: Number(mergedEnd.toFixed(3)),
    text: joinTextValues(firstSegment.text, secondSegment.text),
    translated_text: joinTextValues(
      firstSegment.translated_text || firstSegment.text,
      secondSegment.translated_text || secondSegment.text,
    ),
    subtitle_text: joinTextValues(
      segmentSubtitleText(firstSegment),
      segmentSubtitleText(secondSegment),
      "\n",
    ),
  };

  state.segments = segments
    .filter(
      (candidate) =>
        Number(candidate.id) !== Number(firstSegment.id) && Number(candidate.id) !== Number(secondSegment.id),
    )
    .concat(mergedSegment);
  renumberSegments();

  const mergedSelection = findSegmentByRange(mergedSegment.start, mergedSegment.end) || orderedSegments()[selectedIndex - 1] || orderedSegments()[0];
  state.selectedSegmentId = mergedSelection ? Number(mergedSelection.id) : null;
  setDirty(true);
  renderAll();
  setStatus("Đã gộp đoạn. Hãy lưu dòng thời gian để giữ thay đổi.", "warn");
}

function parseNumberOrCurrent(value, fallback) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

fileInput.addEventListener("change", () => {
  const files = Array.from(fileInput.files || []);
  if (!files.length) {
    return;
  }
  videoName.textContent = files.length === 1 ? files[0].name : `Đã chọn ${files.length} video`;
  videoPreview.src = URL.createObjectURL(files[0]);
  videoPreview.style.display = "block";
  emptyState.style.display = "none";
  state.previewMode = "source";
  setPreviewButtons();
});

importSubtitleBtn.addEventListener("click", () => {
  subtitleFileInput.click();
});

subtitleFileInput.addEventListener("change", async () => {
  const [file] = Array.from(subtitleFileInput.files || []);
  try {
    await importSubtitleFile(file);
  } catch (error) {
    subtitleFileInput.value = "";
    setStatus(userMessage(error.message), "error");
    showToast(userMessage(error.message), "error");
  }
});

videoZoomRange.addEventListener("input", () => {
  applyVideoZoom(videoZoomRange.value);
});

videoFitBtn.addEventListener("click", () => {
  resetVideoZoom();
  setCanvasControlsOpen(false);
});

if (canvasControlsToggle && canvasControls) {
  canvasControlsToggle.addEventListener("click", () => {
    setCanvasControlsOpen(canvasControls.classList.contains("collapsed"));
  });
}

subtitleSizeRange.addEventListener("input", () => {
  applySubtitleStyle({ size: subtitleSizeRange.value });
  persistSubtitleStyle();
  setPreviewButtons();
});

subtitleXRange.addEventListener("input", () => {
  applySubtitleStyle({ x: subtitleXRange.value });
  persistSubtitleStyle();
  setPreviewButtons();
});

subtitleYRange.addEventListener("input", () => {
  applySubtitleStyle({ y: subtitleYRange.value });
  persistSubtitleStyle();
  setPreviewButtons();
});

subtitleCoverRange.addEventListener("input", () => {
  applySubtitleStyle({ coverOpacity: subtitleCoverRange.value });
  persistSubtitleStyle();
  setPreviewButtons();
});

subtitleCoverModeSelect.addEventListener("change", () => {
  applySubtitleStyle({ coverMode: subtitleCoverModeSelect.value });
  persistSubtitleStyle();
  setPreviewButtons();
});

subtitleCoverHeightRange.addEventListener("input", () => {
  applySubtitleStyle({ coverHeight: subtitleCoverHeightRange.value });
  persistSubtitleStyle();
  setPreviewButtons();
});

canvasResizeHandle.addEventListener("mousedown", (event) => {
  event.preventDefault();
  state.canvasResize = {
    startX: event.clientX,
    startZoom: state.videoZoom,
  };
  document.body.classList.add("resizing-canvas");
});

subtitleOverlay.addEventListener("mousedown", (event) => {
  if (!showSubtitleOverlayInCurrentMode()) {
    return;
  }
  event.preventDefault();
  state.subtitleDrag = {
    startX: event.clientX,
    startY: event.clientY,
    initialX: state.subtitleStyle.x,
    initialY: state.subtitleStyle.y,
  };
  document.body.classList.add("dragging-subtitle");
});

timelineZoomRange.addEventListener("input", () => {
  applyTimelineZoom(timelineZoomRange.value);
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const shouldContinue = await confirmUnsavedChanges("Bạn đang có phụ đề chưa lưu. Lưu trước khi tạo tác vụ mới không?");
  if (!shouldContinue) {
    return;
  }
  const files = Array.from(fileInput.files || []);
  if (!files.length) {
    setStatus("Hãy chọn một hoặc nhiều video trước.", "error");
    return;
  }

  setStatus(files.length === 1 ? "Đang tải lên và đưa tác vụ vào hàng đợi..." : `Đang tải lên và đưa ${files.length} tác vụ vào hàng đợi...`, "neutral");
  const payload = new FormData(form);
  appendApiSettings(payload);
  appendSubtitleStyle(payload);
  const endpoint = files.length === 1 ? "/api/jobs" : "/api/jobs/batch";
  if (files.length > 1) {
    payload.delete("file");
    files.forEach((file) => payload.append("files", file));
  }
  const response = await fetch(endpoint, {
    method: "POST",
    body: payload,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Không thể tạo tác vụ." }));
    setStatus(userMessage(error.detail || "Không thể tạo tác vụ."), "error");
    return;
  }

  const data = await response.json();
  const queuedJobs = data.jobs || [data];
  state.jobId = queuedJobs[0].job_id;
  state.previewMode = "source";
  setDirty(false);
  progressBadge.textContent = "0%";
  updateRenderProgress(null);
  languageBadge.textContent = "ngôn ngữ gốc: --";
  startPolling();
  await pollJobs();
  await pollJob(state.jobId);
});

previewSourceBtn.addEventListener("click", () => setPreviewMode("source"));
previewHardsubBtn.addEventListener("click", () => setPreviewMode("hardsub"));
previewVoiceoverBtn.addEventListener("click", () => setPreviewMode("voiceover"));

if (apiSettingsToggle) {
  apiSettingsToggle.addEventListener("click", () => {
    setApiSettingsPanelOpen(apiSettingsPanel?.classList.contains("hidden"));
  });
}

if (apiSettingsClose) {
  apiSettingsClose.addEventListener("click", () => setApiSettingsPanelOpen(false));
}

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    setApiSettingsPanelOpen(false);
  }
});

document.addEventListener("click", (event) => {
  if (!apiSettingsPanel || apiSettingsPanel.classList.contains("hidden")) {
    return;
  }
  const target = event.target;
  if (!(target instanceof Node)) {
    return;
  }
  if (apiSettingsPanel.contains(target) || apiSettingsToggle?.contains(target)) {
    return;
  }
  setApiSettingsPanelOpen(false);
});

if (saveApiSettingsBtn) {
  saveApiSettingsBtn.addEventListener("click", () => {
    try {
      saveApiSettings();
      setApiSettingsPanelOpen(false);
    } catch (error) {
      setApiSettingsStatus("Không thể lưu cài đặt API.", "error");
      showToast("Không thể lưu cài đặt API.", "error");
    }
  });
}

if (apiSettingsForm) {
  apiSettingsForm.addEventListener("change", () => {
    persistApiSettingsQuietly();
  });
}

savePromptSaveBtn.addEventListener("click", () => closeSavePrompt("save"));
savePromptDiscardBtn.addEventListener("click", () => closeSavePrompt("discard"));
savePromptCancelBtn.addEventListener("click", () => closeSavePrompt("cancel"));

savePrompt.addEventListener("click", (event) => {
  if (event.target === savePrompt) {
    closeSavePrompt("cancel");
  }
});

saveTimelineBtn.addEventListener("click", async () => {
  if (!state.jobId) {
    return;
  }
  setStatus("Đang lưu phụ đề đã sửa...", "neutral");
  try {
    await saveTimeline();
    setStatus("Đã lưu phụ đề.", "ok");
  } catch (error) {
    setStatus(userMessage(error.message), "error");
  }
});

if (sourceSrtLink) {
  sourceSrtLink.addEventListener("click", (event) => {
    event.preventDefault();
    if (sourceSrtLink.classList.contains("disabled")) {
      return;
    }
    downloadCurrentSubtitle("source");
  });
}

if (srtLink) {
  srtLink.addEventListener("click", (event) => {
    event.preventDefault();
    if (srtLink.classList.contains("disabled")) {
      return;
    }
    downloadCurrentSubtitle("translated");
  });
}

translateSubtitleBtn.addEventListener("click", async () => {
  if (!state.jobId) {
    return;
  }
  setStatus("Đang dịch lại phụ đề sang tiếng Việt...", "neutral");
  try {
    await runTranslate();
  } catch (error) {
    setStatus(userMessage(error.message), "error");
  }
});

if (burnSubtitleBtn) {
  burnSubtitleBtn.addEventListener("click", async () => {
    if (!state.jobId) {
      return;
    }
    setStatus("Đang đưa lệnh xuất video có phụ đề vào hàng đợi...", "neutral");
    try {
      await runRenderWithDestination(
        `/api/jobs/${state.jobId}/render/hardsub`,
        "video_hardsub",
        subtitleStylePayload(),
      );
    } catch (error) {
      setStatus(userMessage(error.message), "error");
    }
  });
}

if (voiceoverRenderBtn) {
  voiceoverRenderBtn.addEventListener("click", async () => {
    if (!state.jobId) {
      return;
    }
    setStatus("Đang đưa lệnh xuất video thuyết minh vào hàng đợi...", "neutral");
    try {
      await runRenderWithDestination(
        `/api/jobs/${state.jobId}/render/voiceover`,
        "video_voiceover",
        voiceoverRenderPayload(),
      );
    } catch (error) {
      setStatus(userMessage(error.message), "error");
    }
  });
}

hardsubLink.addEventListener("click", async (event) => {
  event.preventDefault();
  try {
    await renderHardsubFromCurrentSubtitles();
  } catch (error) {
    setStatus(userMessage(error.message), "error");
  }
});

voiceoverLink.addEventListener("click", async (event) => {
  event.preventDefault();
  try {
    await renderVoiceoverFromCurrentSubtitles();
  } catch (error) {
    setStatus(userMessage(error.message), "error");
  }
});

segmentStartInput.addEventListener("change", () => {
  updateSelectedSegment((segment) => {
    segment.start = parseNumberOrCurrent(segmentStartInput.value, segment.start);
  });
});

segmentEndInput.addEventListener("change", () => {
  updateSelectedSegment((segment) => {
    segment.end = parseNumberOrCurrent(segmentEndInput.value, segment.end);
  });
});

segmentSourceInput.addEventListener("input", () => {
  updateSelectedTextField("text", segmentSourceInput.value);
});

segmentTranslatedInput.addEventListener("input", () => {
  updateSelectedTextField("translated_text", segmentTranslatedInput.value);
});

segmentSubtitleInput.addEventListener("input", () => {
  updateSelectedTextField("subtitle_text", segmentSubtitleInput.value);
});

nudgeBackBtn.addEventListener("click", () => {
  updateSelectedSegment((segment) => {
    segment.start -= 0.1;
    segment.end -= 0.1;
  });
});

nudgeForwardBtn.addEventListener("click", () => {
  updateSelectedSegment((segment) => {
    segment.start += 0.1;
    segment.end += 0.1;
  });
});

useTranslatedBtn.addEventListener("click", () => {
  updateSelectedSegment((segment) => {
    segment.subtitle_text = segment.translated_text || segmentSubtitleText(segment) || "";
  });
});

splitSegmentBtn.addEventListener("click", () => {
  splitSelectedSegment();
});

mergePreviousBtn.addEventListener("click", () => {
  mergeSelectedSegment("previous");
});

mergeNextBtn.addEventListener("click", () => {
  mergeSelectedSegment("next");
});

timelineLane.addEventListener("click", (event) => {
  const block = event.target.closest(".timeline-block");
  if (!block) {
    const clickedTime = timelineTimeFromPointer(event);
    if (clickedTime !== null) {
      selectSegmentAtTime(clickedTime, true);
    }
    return;
  }
  selectSegment(Number(block.dataset.id), true, true);
});

timelineLane.addEventListener("mousedown", (event) => {
  const block = event.target.closest(".timeline-block");
  if (!block || !state.job?.duration_sec) {
    return;
  }

  const segment = getSegmentById(Number(block.dataset.id));
  if (!segment) {
    return;
  }

  const handle = event.target.closest(".timeline-handle");
  const mode = handle?.dataset.edge === "left" ? "resize-left" : handle?.dataset.edge === "right" ? "resize-right" : "move";

  state.drag = {
    id: Number(block.dataset.id),
    mode,
    startX: event.clientX,
    startY: event.clientY,
    initialStart: Number(segment.start),
    initialEnd: Number(segment.end),
  };
  selectSegment(Number(block.dataset.id), false);
  if (mode === "move") {
    seekVideoToTime(segment.start);
    focusSubtitleEditor();
  }
  document.body.classList.add("dragging");
});

document.addEventListener("mousemove", (event) => {
  if (state.canvasResize) {
    const deltaZoom = ((event.clientX - state.canvasResize.startX) / Math.max(canvasFrame.clientWidth, 1)) * 100;
    applyVideoZoom(state.canvasResize.startZoom + deltaZoom);
    return;
  }

  if (state.subtitleDrag) {
    const rect = canvasFrame.getBoundingClientRect();
    const deltaX = ((event.clientX - state.subtitleDrag.startX) / Math.max(rect.width, 1)) * 100;
    const deltaY = ((event.clientY - state.subtitleDrag.startY) / Math.max(rect.height, 1)) * 100;
    applySubtitleStyle({
      x: state.subtitleDrag.initialX + deltaX,
      y: state.subtitleDrag.initialY - deltaY,
    });
    return;
  }

  if (!state.drag || !state.job?.duration_sec) {
    return;
  }

  const duration = Number(state.job.duration_sec);
  const deltaSeconds = ((event.clientX - state.drag.startX) / state.laneWidth) * duration;
  const segment = getSegmentById(state.drag.id);
  if (!segment) {
    return;
  }

  if (state.drag.mode === "move") {
    const segmentDuration = state.drag.initialEnd - state.drag.initialStart;
    let nextStart = state.drag.initialStart + deltaSeconds;
    nextStart = Math.max(0, Math.min(nextStart, duration - segmentDuration));
    segment.start = nextStart;
    segment.end = nextStart + segmentDuration;
  }

  if (state.drag.mode === "resize-left") {
    segment.start = Math.max(0, Math.min(state.drag.initialStart + deltaSeconds, segment.end - MIN_SEGMENT_DURATION));
  }

  if (state.drag.mode === "resize-right") {
    segment.end = Math.min(duration, Math.max(state.drag.initialEnd + deltaSeconds, segment.start + MIN_SEGMENT_DURATION));
  }

  segment.start = Number(segment.start.toFixed(3));
  segment.end = Number(segment.end.toFixed(3));
  setDirty(true);
  renderTimeline();
  renderInspector();
});

document.addEventListener("mouseup", () => {
  if (state.canvasResize) {
    state.canvasResize = null;
    document.body.classList.remove("resizing-canvas");
  }

  if (state.subtitleDrag) {
    state.subtitleDrag = null;
    document.body.classList.remove("dragging-subtitle");
    persistSubtitleStyle();
  }

  if (!state.drag) {
    return;
  }
  const finishedDrag = state.drag;
  state.drag = null;
  document.body.classList.remove("dragging");
  renderAll();
  if (finishedDrag.mode === "move") {
    const segment = getSegmentById(finishedDrag.id);
    if (segment) {
      seekVideoToTime(segment.start);
    }
  }
});

scriptList.addEventListener("click", (event) => {
  const item = event.target.closest(".script-item");
  if (!item) {
    return;
  }
  selectSegment(Number(item.dataset.id), true, true);
});

jobList.addEventListener("click", async (event) => {
  const item = event.target.closest(".job-item");
  if (!item) {
    return;
  }
  try {
    const action = event.target.closest("[data-job-action]")?.dataset.jobAction || "select";
    if (action === "delete") {
      await deleteJob(item.dataset.id);
      return;
    }
    await loadJob(item.dataset.id);
    await pollJobs();
  } catch (error) {
    setStatus(userMessage(error.message), "error");
    showToast(userMessage(error.message), "error");
  }
});

resumeJobsBtn.addEventListener("click", async () => {
  setStatus("Đang chạy tiếp các tác vụ đang chờ...", "neutral");
  const response = await fetch("/api/jobs/resume", { method: "POST" });
  if (!response.ok) {
    setStatus("Không thể chạy tiếp tác vụ.", "error");
    return;
  }
  const payload = await response.json();
  setStatus(`Đã chạy tiếp ${payload.resumed || 0} tác vụ.`, "ok");
  await pollJobs();
  if (state.jobId) {
    startPolling();
  }
});

videoPreview.addEventListener("timeupdate", () => {
  applyPlaybackHighlight(videoPreview.currentTime || 0);
});

videoPreview.addEventListener("loadeddata", () => {
  emptyState.style.display = "none";
  videoPreview.style.display = "block";
  applyVideoZoom();
});

window.addEventListener("resize", () => {
  applyVideoZoom();
});

if (typeof ResizeObserver !== "undefined") {
  const canvasFrameObserver = new ResizeObserver(() => applySubtitleOverlayScale());
  canvasFrameObserver.observe(canvasFrame);
}

window.addEventListener("beforeunload", (event) => {
  if (!state.dirty) {
    return;
  }
  event.preventDefault();
  event.returnValue = "";
});

setPreviewButtons();
renderInspector();
clearSelectedJob();
applyVideoZoom();
loadSubtitleStyle();
applyTimelineZoom(DEFAULT_TIMELINE_PIXELS_PER_SECOND, false);
loadApiSettings();
pollJobs();
startQueuePolling();
