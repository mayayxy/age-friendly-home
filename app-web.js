const STABLE_FRAMES = 3
const STABLE_THRESHOLD = 14
const AUTO_COOLDOWN_MS = 5000
const CAPTURE_MAX_SIDE = 720
const JPEG_QUALITY = 0.68

const MODE_META = {
  elder: { label: '适老化' },
  baby: { label: '婴儿安全' },
  pet: { label: '宠物安全' }
}

const state = {
  stream: null,
  analyzing: false,
  sheetOpen: false,
  autoEnabled: true,
  lastAnalyzeAt: 0,
  prevFrame: null,
  stableCount: 0,
  watchTimer: null,
  analyzeStartedAt: 0,
  mode: 'elder'
}

const els = {
  camera: document.getElementById('camera'),
  frameCanvas: document.getElementById('frameCanvas'),
  statusText: document.getElementById('statusText'),
  scanTip: document.getElementById('scanTip'),
  scanBtn: document.getElementById('scanBtn'),
  scanLabel: document.getElementById('scanLabel'),
  permissionCard: document.getElementById('permissionCard'),
  startCamBtn: document.getElementById('startCamBtn'),
  modelHint: document.getElementById('modelHint'),
  sheetMask: document.getElementById('sheetMask'),
  resultSheet: document.getElementById('resultSheet'),
  detectedScene: document.getElementById('detectedScene'),
  modeLabel: document.getElementById('modeLabel'),
  modeSwitch: document.getElementById('modeSwitch'),
  resultTitle: document.getElementById('resultTitle'),
  resultSummary: document.getElementById('resultSummary'),
  scoreNum: document.getElementById('scoreNum'),
  scoreBadge: document.getElementById('scoreBadge'),
  riskList: document.getElementById('riskList'),
  unjudgableBlock: document.getElementById('unjudgableBlock'),
  unjudgableList: document.getElementById('unjudgableList'),
  rescanBtn: document.getElementById('rescanBtn'),
  closeSheetBtn: document.getElementById('closeSheetBtn'),
  toast: document.getElementById('toast')
}

const motionCanvas = document.createElement('canvas')

function showToast(message) {
  els.toast.hidden = false
  els.toast.textContent = message
  clearTimeout(showToast.timer)
  showToast.timer = setTimeout(() => {
    els.toast.hidden = true
  }, 2600)
}

function setStatus(text) {
  els.statusText.textContent = text
}

function setScanBusy(busy, label) {
  state.analyzing = busy
  els.scanBtn.disabled = busy || !state.stream
  els.scanBtn.classList.toggle('busy', busy)
  els.scanLabel.textContent = label
}

function openSheet() {
  state.sheetOpen = true
  state.autoEnabled = false
  els.sheetMask.hidden = false
  els.resultSheet.hidden = false
}

function closeSheet(resumeAuto = true) {
  state.sheetOpen = false
  els.sheetMask.hidden = true
  els.resultSheet.hidden = true
  if (resumeAuto) {
    state.autoEnabled = true
    state.stableCount = 0
    state.prevFrame = null
    state.lastAnalyzeAt = Date.now()
    setStatus('继续对准')
    els.scanTip.textContent = '对准后点识别'
  }
}

function setMode(mode) {
  if (!MODE_META[mode]) return
  state.mode = mode
  document.querySelectorAll('.mode-btn').forEach((btn) => {
    const active = btn.dataset.mode === mode
    btn.classList.toggle('active', active)
    btn.setAttribute('aria-selected', active ? 'true' : 'false')
  })
  els.scanTip.textContent = '对准后点识别'
  if (!state.analyzing && !state.sheetOpen) {
    setStatus(`当前：${MODE_META[mode].label}`)
  }
}

function renderReport(report) {
  const modeName = report.mode || MODE_META[state.mode].label
  const risks = report.risks || []
  const hasRisks = risks.length > 0

  if (els.modeLabel) els.modeLabel.textContent = modeName
  els.detectedScene.textContent = report.sceneLabel
  els.resultTitle.textContent = hasRisks
    ? `${report.sceneLabel}安全评分`
    : `${report.sceneLabel}`
  els.resultSummary.textContent = hasRisks
    ? report.summary
    : (report.summary || '相机范围内未识别到风险')
  els.scoreNum.textContent = String(report.score)
  els.scoreBadge.hidden = true
  els.scoreBadge.textContent = ''
  els.scoreBadge.classList.remove('danger', 'ok')

  els.riskList.innerHTML = hasRisks
    ? risks
      .map((risk) => {
        const levelClass =
          risk.level === '高风险' ? 'high' : risk.level === '低风险' ? 'low' : ''
        const suggestions = (risk.suggestions || (risk.advice ? [risk.advice] : []))
          .map((item) => `<li>${item}</li>`)
          .join('')
        return `
        <article class="risk-item ${levelClass}">
          <div class="risk-top">
            <span>${risk.title}</span>
            <span class="risk-level">${risk.level}</span>
          </div>
          <p class="risk-advice">${risk.description || risk.advice || ''}</p>
          <div class="risk-section">
            <p class="risk-label">改造建议</p>
            <ul class="risk-suggestions">${suggestions}</ul>
          </div>
          <p class="risk-benefit"><span>预期收益</span>${risk.benefit || ''}</p>
        </article>
      `
      })
      .join('')
    : '<p class="empty-risk">相机范围内未识别到风险</p>'

  const unjudgable = report.unjudgable || []
  if (unjudgable.length) {
    els.unjudgableBlock.hidden = false
    els.unjudgableList.innerHTML = unjudgable.map((item) => `<li>${item}</li>`).join('')
  } else {
    els.unjudgableBlock.hidden = true
    els.unjudgableList.innerHTML = ''
  }

  openSheet()
}

function captureFrameBlob() {
  const video = els.camera
  if (!video.videoWidth || !video.videoHeight) {
    return Promise.reject(new Error('相机尚未就绪'))
  }

  const canvas = els.frameCanvas
  const scale = Math.min(1, CAPTURE_MAX_SIDE / Math.max(video.videoWidth, video.videoHeight))
  canvas.width = Math.max(1, Math.round(video.videoWidth * scale))
  canvas.height = Math.max(1, Math.round(video.videoHeight * scale))

  const ctx = canvas.getContext('2d', { alpha: false })
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height)

  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (!blob) reject(new Error('截图失败'))
        else resolve(blob)
      },
      'image/jpeg',
      JPEG_QUALITY
    )
  })
}

function sampleMotionVector() {
  const video = els.camera
  if (!video.videoWidth) return null

  const size = 32
  motionCanvas.width = size
  motionCanvas.height = size
  const ctx = motionCanvas.getContext('2d', { willReadFrequently: true, alpha: false })
  ctx.drawImage(video, 0, 0, size, size)
  const { data } = ctx.getImageData(0, 0, size, size)
  const gray = new Float32Array(size * size)

  for (let i = 0, j = 0; i < data.length; i += 4, j += 1) {
    gray[j] = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2]
  }
  return gray
}

function frameDiff(a, b) {
  if (!a || !b || a.length !== b.length) return 999
  let sum = 0
  for (let i = 0; i < a.length; i += 1) {
    sum += Math.abs(a[i] - b[i])
  }
  return sum / a.length
}

async function analyzeWithModel(blob) {
  const form = new FormData()
  form.append('image', blob, 'scene.jpg')
  form.append('mode', state.mode)

  const response = await fetch('/api/analyze', {
    method: 'POST',
    body: form
  })

  let payload = null
  try {
    payload = await response.json()
  } catch {
    payload = null
  }

  if (!response.ok) {
    const detail = payload && payload.detail ? payload.detail : `请求失败（${response.status}）`
    const text = typeof detail === 'string' ? detail : JSON.stringify(detail)
    throw new Error(text.slice(0, 180))
  }

  return payload
}

function tickAnalyzeStatus() {
  if (!state.analyzing) return
  setStatus('识别中…')
}

async function analyzeCurrentView(fromAuto = false) {
  if (state.analyzing || state.sheetOpen) return
  if (!state.stream) {
    showToast('请先开启相机')
    return
  }

  state.analyzeStartedAt = Date.now()
  setScanBusy(true, '识别中')
  setStatus('识别中…')
  els.scanTip.textContent = '对准后点识别'
  const statusTimer = setInterval(tickAnalyzeStatus, 500)

  try {
    const blob = await captureFrameBlob()
    const report = await analyzeWithModel(blob)
    state.lastAnalyzeAt = Date.now()
    setStatus('识别完成')
    renderReport(report)
  } catch (error) {
    const message = error && error.message ? error.message : '识别失败，请稍后重试'
    if (message.includes('Failed to fetch') || message.includes('NetworkError')) {
      showToast('服务未连接')
      setStatus('服务未连接')
    } else {
      showToast(message)
      setStatus('识别失败')
    }
    state.autoEnabled = true
    state.stableCount = 0
    state.prevFrame = null
  } finally {
    clearInterval(statusTimer)
    setScanBusy(false, '识别')
    els.scanTip.textContent = '对准后点识别'
  }
}

function watchStability() {
  clearInterval(state.watchTimer)
  state.watchTimer = setInterval(() => {
    if (!state.autoEnabled || state.analyzing || state.sheetOpen || !state.stream) return
    if (Date.now() - state.lastAnalyzeAt < AUTO_COOLDOWN_MS) return

    const current = sampleMotionVector()
    if (!current) return

    const diff = frameDiff(state.prevFrame, current)
    state.prevFrame = current

    if (diff < STABLE_THRESHOLD) {
      state.stableCount += 1
      if (state.stableCount === 2) {
        setStatus('已对准…')
      }
      if (state.stableCount >= STABLE_FRAMES) {
        state.stableCount = 0
        analyzeCurrentView(true)
      }
    } else {
      state.stableCount = 0
    }
  }, 180)
}

async function startCamera() {
  setStatus('正在请求相机权限...')
  els.permissionCard.hidden = true

  try {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error('当前浏览器不支持相机')
    }

    const stream = await navigator.mediaDevices.getUserMedia({
      audio: false,
      video: {
        facingMode: { ideal: 'environment' },
        width: { ideal: 720, max: 960 },
        height: { ideal: 960, max: 1280 },
        frameRate: { ideal: 24, max: 30 }
      }
    })

    state.stream = stream
    els.camera.srcObject = stream
    els.camera.setAttribute('playsinline', 'true')
    els.camera.muted = true
    await els.camera.play()

    els.scanBtn.disabled = false
    // 允许马上自动识别，不再空等冷却
    state.lastAnalyzeAt = 0
    setStatus('对准空间')
    els.scanTip.textContent = '对准后点识别'
    watchStability()
  } catch (error) {
    els.permissionCard.hidden = false
    setStatus('未获得相机权限')
    const message = error && error.name === 'NotAllowedError'
      ? '请允许相机权限'
      : (error && error.message) || '无法打开相机'
    showToast(message)
  }
}

async function checkHealth() {
  if (!els.modelHint) return
  try {
    const response = await fetch('/api/health')
    if (!response.ok) throw new Error('health failed')
    const data = await response.json()
    els.modelHint.textContent = data.configured ? '服务已就绪' : '请先配置密钥'
  } catch {
    els.modelHint.textContent = '服务未连接'
  }
}

function bindEvents() {
  els.startCamBtn.addEventListener('click', startCamera)
  els.scanBtn.addEventListener('click', () => analyzeCurrentView(false))
  els.closeSheetBtn.addEventListener('click', () => closeSheet(true))
  els.rescanBtn.addEventListener('click', () => {
    closeSheet(true)
  })
  els.sheetMask.addEventListener('click', () => closeSheet(true))

  if (els.modeSwitch) {
    els.modeSwitch.addEventListener('click', (e) => {
      const btn = e.target.closest('.mode-btn')
      if (!btn || !btn.dataset.mode) return
      if (state.analyzing) {
        showToast('识别进行中，请稍后再切换')
        return
      }
      setMode(btn.dataset.mode)
    })
  }
}

bindEvents()
setMode('elder')
checkHealth()

if (window.isSecureContext || location.hostname === 'localhost' || location.hostname === '127.0.0.1') {
  startCamera()
} else {
  els.permissionCard.hidden = false
  setStatus('请通过本地服务打开页面')
  showToast('请使用 http://127.0.0.1:8000 打开')
}
