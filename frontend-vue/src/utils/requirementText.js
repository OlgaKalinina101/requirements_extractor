/**
 * Parse requirement text that may contain bullet subitems.
 * Returns { intro: string, subitems: string[] }
 */
export function parseRequirementWithSubitems(text) {
  if (!text || typeof text !== 'string') return { intro: '', subitems: [] }
  const lines = text.trim().split(/\r?\n/).map(l => l.trim()).filter(Boolean)
  const bulletRe = /^[-•*]\s+/
  const subitems = []
  let introLines = []
  for (const line of lines) {
    if (bulletRe.test(line)) {
      subitems.push(line.replace(bulletRe, '').trim())
    } else {
      if (subitems.length > 0) break // bullets already started, rest is flat
      introLines.push(line)
    }
  }
  return {
    intro: introLines.join('\n'),
    subitems
  }
}
