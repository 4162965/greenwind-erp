export const DEFAULT_POSITIONS = [
  '经理',
  '主管',
  '客服',
  '养护员',
  '司机',
  '跟车配送',
  '采购',
  '仓管',
  '财务',
  '市场',
]

const STORAGE_KEY = 'greenwind_position_options'

export function getPositionOptions() {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
    const positions = Array.isArray(parsed) ? parsed.map((item) => String(item).trim()).filter(Boolean) : []
    return positions.length ? Array.from(new Set(positions)) : [...DEFAULT_POSITIONS]
  } catch {
    return [...DEFAULT_POSITIONS]
  }
}

export function savePositionOptions(positions: string[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(new Set(positions.map((item) => item.trim()).filter(Boolean)))))
}
