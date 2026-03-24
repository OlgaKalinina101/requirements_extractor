/**
 * usePageHighlight — composable for PDF text-block highlighting.
 *
 * Responsibilities:
 *  - Fetch per-page text blocks from the backend (with local cache).
 *  - Find blocks that match an active requirement using a 3-stage algorithm.
 *  - Draw / clear a highlight overlay on a canvas element.
 *
 * Usage:
 *  const { loadPageBlocks, findMatchingBlocks, syncOverlaySize, drawOverlay, clearOverlay } =
 *    usePageHighlight(documentId, pdfCanvasRef, overlayCanvasRef, getCurrentPageObj)
 */

import api from '@/services/api'

// ── Text normalisation ──────────────────────────────────────────────────────
const normalize = (s) =>
  s.toLowerCase().replace(/[^\w\u0400-\u04ff\d]/g, ' ').replace(/\s+/g, ' ').trim()

// ── Page index ──────────────────────────────────────────────────────────────

function buildPageIndex(blocks) {
  const sorted = [...blocks].sort((a, b) => {
    if (Math.abs(a.y0 - b.y0) > 5) return a.y0 - b.y0
    return a.x0 - b.x0
  })
  let normConcat = ''
  const charToBlock = []
  for (let i = 0; i < sorted.length; i++) {
    const nt = normalize(sorted[i].text || '')
    if (!nt) continue
    for (const ch of nt) {
      charToBlock.push(i)
      normConcat += ch
    }
    charToBlock.push(-1)
    normConcat += ' '
  }
  return { sorted, normConcat, charToBlock }
}

function blocksInRange(sorted, charToBlock, start, end) {
  const indices = new Set()
  for (let i = start; i < end && i < charToBlock.length; i++) {
    if (charToBlock[i] >= 0) indices.add(charToBlock[i])
  }
  return [...indices].map(i => sorted[i])
}

// ── Fuzzy gram search ───────────────────────────────────────────────────────

function fuzzyGramSearch(sorted, charToBlock, haystack, needle) {
  if (needle.length < 8 || haystack.length < 8) return []

  const GRAM = 4
  const needleGrams = new Set()
  for (let i = 0; i <= needle.length - GRAM; i++) {
    needleGrams.add(needle.substring(i, i + GRAM))
  }
  if (needleGrams.size < 3) return []

  const winLen = needle.length
  const minWin = Math.floor(winLen * 0.6)
  const maxWin = Math.floor(winLen * 1.6)

  let bestScore = 0, bestStart = -1, bestEnd = -1

  for (let start = 0; start <= haystack.length - minWin; start++) {
    const end = Math.min(start + maxWin, haystack.length)
    const window = haystack.substring(start, end)
    let hits = 0
    for (let i = 0; i <= window.length - GRAM; i++) {
      if (needleGrams.has(window.substring(i, i + GRAM))) hits++
    }
    const score = hits / needleGrams.size
    if (score > bestScore) { bestScore = score; bestStart = start; bestEnd = end }
  }

  if (bestScore < 0.25 || bestStart === -1) return []

  const tightEnd = Math.min(bestStart + Math.floor(winLen * 1.3), bestEnd)
  return blocksInRange(sorted, charToBlock, bestStart, tightEnd)
}

// ── Public matching algorithm ───────────────────────────────────────────────

export function findMatchingBlocks(blocks, req) {
  if (!req || !blocks || !blocks.length) return []

  let needle = (req.source_quote || '').trim()
  if (!needle || needle.length < 10) {
    const full = (req.text || '').trim()
    const sentenceEnd = full.search(/[.!?\n]/)
    needle = sentenceEnd > 20 ? full.substring(0, sentenceEnd + 1) : full.substring(0, 200)
  }
  if (needle.length < 5) return []

  const { sorted, normConcat, charToBlock } = buildPageIndex(blocks)
  const normNeedle = normalize(needle)
  if (!normNeedle || normNeedle.length < 3) return []

  // Step 1: exact substring
  const exactPos = normConcat.indexOf(normNeedle)
  if (exactPos !== -1) {
    return blocksInRange(sorted, charToBlock, exactPos, exactPos + normNeedle.length)
  }

  // Step 2: progressive word sequences (first N, then last N words)
  const needleWords = normNeedle.split(' ').filter(w => w.length >= 3)
  for (const slice of [needleWords.slice(0), needleWords.slice().reverse()]) {
    for (let len = Math.min(needleWords.length, 7); len >= 3; len--) {
      const sub = (slice === needleWords ? slice.slice(0, len) : needleWords.slice(-len)).join(' ')
      const pos = normConcat.indexOf(sub)
      if (pos !== -1) return blocksInRange(sorted, charToBlock, pos, pos + sub.length)
    }
  }

  // Step 3: character 4-gram fuzzy
  return fuzzyGramSearch(sorted, charToBlock, normConcat, normNeedle)
}

// ── Composable factory ──────────────────────────────────────────────────────

/**
 * @param {import('vue').Ref<string|number>} documentId
 * @param {import('vue').Ref<HTMLCanvasElement|null>} pdfCanvasRef
 * @param {import('vue').Ref<HTMLCanvasElement|null>} overlayCanvasRef
 * @param {() => any} getCurrentPageObj  — returns the current pdf.js page object
 */
export function usePageHighlight(documentId, pdfCanvasRef, overlayCanvasRef, getCurrentPageObj) {
  const cache = {}

  async function loadPageBlocks(pageNum) {
    if (cache[pageNum] !== undefined) return cache[pageNum]
    try {
      const { data } = await api.get(`/api/documents/${documentId.value}/pages/${pageNum}`)
      cache[pageNum] = data
      return data
    } catch {
      cache[pageNum] = { text_blocks: [], is_ocr: false }
      return cache[pageNum]
    }
  }

  function clearCache() {
    Object.keys(cache).forEach(k => delete cache[k])
  }

  function syncOverlaySize() {
    const pdf = pdfCanvasRef.value
    const ov  = overlayCanvasRef.value
    if (!pdf || !ov) return
    ov.width  = pdf.width
    ov.height = pdf.height
  }

  function clearOverlay() {
    const ov = overlayCanvasRef.value
    if (!ov) return
    ov.getContext('2d').clearRect(0, 0, ov.width, ov.height)
  }

  function drawOverlay(matchingBlocks) {
    const ov  = overlayCanvasRef.value
    const pdf = pdfCanvasRef.value
    if (!ov || !pdf) return

    syncOverlaySize()
    const ctx = ov.getContext('2d')
    ctx.clearRect(0, 0, ov.width, ov.height)
    if (!matchingBlocks?.length) return

    const pageObj  = getCurrentPageObj()
    if (!pageObj) return
    const viewport = pageObj.getViewport({ scale: 1.0 })
    const pxPerPt  = pdf.width / viewport.width

    for (const block of matchingBlocks) {
      const x = block.x0 * pxPerPt
      const y = block.y0 * pxPerPt
      const w = (block.x1 - block.x0) * pxPerPt
      const h = (block.y1 - block.y0) * pxPerPt
      ctx.fillStyle   = 'rgba(255, 180, 0, 0.40)'
      ctx.fillRect(x, y, w, h)
      ctx.strokeStyle = 'rgba(220, 120, 0, 0.7)'
      ctx.lineWidth   = 1.5
      ctx.strokeRect(x, y, w, h)
    }
  }

  return { loadPageBlocks, clearCache, findMatchingBlocks, syncOverlaySize, clearOverlay, drawOverlay }
}
