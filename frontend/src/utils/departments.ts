export const DEFAULT_DEPARTMENTS = [
  '市场部',
  '绿化部',
  '财务部',
  '采购部',
  '仓管部',
  '配送部',
  '客服部',
  '管理层',
  '其他',
]

const STORAGE_KEY = 'greenwind_department_options'

export function getDepartmentOptions() {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
    const departments = Array.isArray(parsed) ? parsed.map((item) => String(item).trim()).filter(Boolean) : []
    return departments.length ? Array.from(new Set(departments)) : [...DEFAULT_DEPARTMENTS]
  } catch {
    return [...DEFAULT_DEPARTMENTS]
  }
}

export function saveDepartmentOptions(departments: string[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(new Set(departments.map((item) => item.trim()).filter(Boolean)))))
}
