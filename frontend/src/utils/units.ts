export const DEFAULT_UNITS = ['盆', '个', '棵', '箱', '瓶', '袋', '斤', '公斤', '套', '件']

const STORAGE_KEY = 'greenwind_unit_options'

export function getUnitOptions(): string[] {
  const raw = localStorage.getItem(STORAGE_KEY)
  if (!raw) return [...DEFAULT_UNITS]
  try {
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return [...DEFAULT_UNITS]
    const units = parsed.map((item) => String(item).trim()).filter(Boolean)
    return units.length ? Array.from(new Set(units)) : [...DEFAULT_UNITS]
  } catch {
    return [...DEFAULT_UNITS]
  }
}

export function saveUnitOptions(units: string[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(new Set(units.map((item) => item.trim()).filter(Boolean)))))
}
