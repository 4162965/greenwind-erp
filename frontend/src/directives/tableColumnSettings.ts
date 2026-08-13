import type { App } from 'vue'

type ColumnItem = {
  id: string
  label: string
  column: HTMLElement
}

const BUTTON_CLASS = 'global-column-setting-button'
const DIALOG_CLASS = 'global-column-setting-dialog'
const MASK_CLASS = 'global-column-setting-mask'

function safeJson<T>(value: string | null, fallback: T): T {
  if (!value) return fallback
  try {
    return JSON.parse(value) as T
  } catch {
    return fallback
  }
}

function currentAccountKey() {
  const user = safeJson<Record<string, any>>(localStorage.getItem('greenwind_user'), {})
  return String(user.username || user.id || user.phone || 'guest')
}

function pageKey() {
  const path = window.location.pathname.replace(/\/+/g, '_').replace(/^_+|_+$/g, '') || 'home'
  return `${currentAccountKey()}_${path}`
}

function isInsideDialog(element: Element) {
  return Boolean(element.closest('.el-dialog, .el-drawer, .el-message-box'))
}

function columnId(column: HTMLElement, index: number) {
  if (column.classList.contains('el-table-column--selection')) return `__selection_${index}`
  const prop = column.getAttribute('data-prop') || ''
  const label = column.getAttribute('data-label') || column.textContent?.trim() || `字段${index + 1}`
  return prop || label || `column_${index}`
}

function getColumns(table: HTMLElement): ColumnItem[] {
  const columns = Array.from(table.querySelectorAll<HTMLElement>('.el-table__header-wrapper th.el-table__cell'))
  return columns
    .map((column, index) => ({
      id: columnId(column, index),
      label: column.querySelector('.cell')?.textContent?.trim() || column.textContent?.trim() || `字段${index + 1}`,
      column,
    }))
    .filter((item) => item.label && item.label !== '操作' && !item.column.classList.contains('is-hidden') && !item.column.classList.contains('el-table-column--selection'))
}

function applyTableColumns(table: HTMLElement, columns: ColumnItem[], visibleIds: string[]) {
  const usableIds = new Set(columns.map((item) => item.id))
  const normalizedIds = visibleIds.filter((id) => usableIds.has(id))
  const visible = new Set(normalizedIds.length ? normalizedIds : columns.map((item) => item.id))
  const bodyTables = Array.from(table.querySelectorAll<HTMLElement>('.el-table__body-wrapper table'))
  const footerTables = Array.from(table.querySelectorAll<HTMLElement>('.el-table__footer-wrapper table'))
  const headerColumns = Array.from(table.querySelectorAll<HTMLElement>('.el-table__header-wrapper colgroup col'))

  columns.forEach((item) => {
    const index = Array.from(item.column.parentElement?.children || []).indexOf(item.column)
    const display = visible.has(item.id) ? '' : 'none'
    item.column.style.display = display
    if (headerColumns[index]) headerColumns[index].style.display = display
    for (const bodyTable of bodyTables) {
      const cols = Array.from(bodyTable.querySelectorAll<HTMLElement>('colgroup col'))
      if (cols[index]) cols[index].style.display = display
      for (const row of Array.from(bodyTable.querySelectorAll<HTMLTableRowElement>('tbody tr'))) {
        const cell = row.children[index] as HTMLElement | undefined
        if (cell) cell.style.display = display
      }
    }
    for (const footerTable of footerTables) {
      const cols = Array.from(footerTable.querySelectorAll<HTMLElement>('colgroup col'))
      if (cols[index]) cols[index].style.display = display
      for (const row of Array.from(footerTable.querySelectorAll<HTMLTableRowElement>('tbody tr'))) {
        const cell = row.children[index] as HTMLElement | undefined
        if (cell) cell.style.display = display
      }
    }
  })
}

function openDialog(options: {
  title: string
  columns: ColumnItem[]
  storageKey: string
  table: HTMLElement
}) {
  document.querySelector(`.${MASK_CLASS}`)?.remove()
  const saved = safeJson<string[]>(localStorage.getItem(options.storageKey), options.columns.map((item) => item.id))
  const mask = document.createElement('div')
  mask.className = MASK_CLASS
  const dialog = document.createElement('div')
  dialog.className = DIALOG_CLASS
  dialog.innerHTML = `
    <div class="global-column-setting-head">
      <strong>${options.title}</strong>
      <button type="button" class="global-column-close">×</button>
    </div>
    <p>勾选当前账号需要显示的表头，不会影响其他账号。</p>
    <div class="global-column-setting-list"></div>
    <div class="global-column-setting-actions">
      <button type="button" class="global-column-reset">恢复默认</button>
      <button type="button" class="global-column-cancel">取消</button>
      <button type="button" class="global-column-save">保存</button>
    </div>
  `
  const list = dialog.querySelector('.global-column-setting-list') as HTMLElement
  for (const item of options.columns) {
    const label = document.createElement('label')
    label.innerHTML = `<input type="checkbox" value="${item.id}" ${saved.includes(item.id) ? 'checked' : ''}> <span>${item.label}</span>`
    list.appendChild(label)
  }
  const close = () => mask.remove()
  dialog.querySelector('.global-column-close')?.addEventListener('click', close)
  dialog.querySelector('.global-column-cancel')?.addEventListener('click', close)
  dialog.querySelector('.global-column-reset')?.addEventListener('click', () => {
    for (const input of Array.from(list.querySelectorAll<HTMLInputElement>('input'))) input.checked = true
  })
  dialog.querySelector('.global-column-save')?.addEventListener('click', () => {
    const selected = Array.from(list.querySelectorAll<HTMLInputElement>('input:checked')).map((input) => input.value)
    const visible = selected.length ? selected : options.columns.map((item) => item.id)
    localStorage.setItem(options.storageKey, JSON.stringify(visible))
    applyTableColumns(options.table, options.columns, visible)
    close()
  })
  mask.addEventListener('click', (event) => {
    if (event.target === mask) close()
  })
  mask.appendChild(dialog)
  document.body.appendChild(mask)
}

function enhanceTable(table: HTMLElement, tableIndex: number) {
  if (isInsideDialog(table)) return
  const currentPage = pageKey()
  const columns = getColumns(table)
  if (columns.length < 2) return
  const panel = table.closest<HTMLElement>('.table-panel, .panel, .entity-page, .page')
  const toolbar = panel?.querySelector<HTMLElement>('.table-toolbar, .crud-toolbar, .report-toolbar, .schedule-toolbar')
  if (!toolbar) return

  if (table.dataset.columnSettingReady === '1') {
    if (table.dataset.columnSettingPage !== currentPage) {
      table.dataset.columnSettingPage = currentPage
      const storageKey = `greenwind_table_columns_${currentPage}_${tableIndex}`
      const visible = safeJson<string[]>(localStorage.getItem(storageKey), columns.map((item) => item.id))
      applyTableColumns(table, columns, visible)
    }
    return
  }

  table.dataset.columnSettingReady = '1'
  table.dataset.columnSettingPage = currentPage
  const storageKey = `greenwind_table_columns_${currentPage}_${tableIndex}`
  const visible = safeJson<string[]>(localStorage.getItem(storageKey), columns.map((item) => item.id))
  applyTableColumns(table, columns, visible)

  if (toolbar.querySelector(`.${BUTTON_CLASS}[data-table-index="${tableIndex}"]`)) return
  const spacer = document.createElement('span')
  spacer.className = 'global-column-setting-spacer'
  const button = document.createElement('button')
  button.type = 'button'
  button.className = BUTTON_CLASS
  button.dataset.tableIndex = String(tableIndex)
  button.textContent = '表头设置'
  button.addEventListener('click', () => {
    const freshColumns = getColumns(table)
    const freshStorageKey = `greenwind_table_columns_${pageKey()}_${tableIndex}`
    openDialog({
      title: '表头显示设置',
      columns: freshColumns,
      storageKey: freshStorageKey,
      table,
    })
  })
  toolbar.appendChild(spacer)
  toolbar.appendChild(button)
}

function scanTables(root: ParentNode = document) {
  const tables = Array.from(root.querySelectorAll<HTMLElement>('.el-table'))
  tables.forEach((table, index) => enhanceTable(table, index))
}

export function installTableColumnSettings(app: App) {
  app.mixin({
    mounted() {
      window.setTimeout(() => scanTables(), 80)
    },
    updated() {
      window.setTimeout(() => scanTables(), 80)
    },
  })
}
