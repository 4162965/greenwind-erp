import type { App } from 'vue'

const BAR_CLASS = 'global-status-tabs'
const ACTIVE_CLASS = 'is-active'
const HIDDEN_CLASS = 'global-status-hidden'

function isInsideDialog(element: Element) {
  return Boolean(element.closest('.el-dialog, .el-drawer, .el-message-box'))
}

function getStatusColumnIndex(table: HTMLElement) {
  const headers = Array.from(table.querySelectorAll<HTMLElement>('.el-table__header-wrapper th.el-table__cell'))
  return headers.findIndex((header) => {
    const label = header.querySelector('.cell')?.textContent?.trim() || header.textContent?.trim() || ''
    return label === '状态' || label === '鐘舵€?'
  })
}

function readStatus(cell: Element | undefined) {
  return (cell?.textContent || '').trim()
}

function getBodyRows(table: HTMLElement) {
  return Array.from(table.querySelectorAll<HTMLTableRowElement>('.el-table__body-wrapper tbody tr'))
}

function getStatusValues(table: HTMLElement, index: number) {
  const values = new Set<string>()
  for (const row of getBodyRows(table)) {
    const value = readStatus(row.children[index])
    if (value) values.add(value)
  }
  return Array.from(values)
}

function applyStatus(table: HTMLElement, index: number, status: string) {
  for (const row of getBodyRows(table)) {
    const visible = !status || readStatus(row.children[index]) === status
    row.classList.toggle(HIDDEN_CLASS, !visible)
  }
}

function renderBar(table: HTMLElement, statuses: string[]) {
  let bar = table.previousElementSibling as HTMLElement | null
  if (!bar || !bar.classList.contains(BAR_CLASS)) {
    bar = document.createElement('div')
    bar.className = BAR_CLASS
    table.parentElement?.insertBefore(bar, table)
  }

  const active = bar.dataset.active || ''
  const finalActive = active && statuses.includes(active) ? active : ''
  bar.dataset.active = finalActive
  bar.innerHTML = ''

  const allButton = document.createElement('button')
  allButton.type = 'button'
  allButton.textContent = `全部 ${getBodyRows(table).length}`
  allButton.classList.toggle(ACTIVE_CLASS, !finalActive)
  allButton.addEventListener('click', () => {
    bar!.dataset.active = ''
    refreshTable(table)
  })
  bar.appendChild(allButton)

  for (const status of statuses) {
    const count = getBodyRows(table).filter((row) => readStatus(row.children[getStatusColumnIndex(table)]) === status).length
    const button = document.createElement('button')
    button.type = 'button'
    button.textContent = `${status} ${count}`
    button.classList.toggle(ACTIVE_CLASS, finalActive === status)
    button.addEventListener('click', () => {
      bar!.dataset.active = status
      refreshTable(table)
    })
    bar.appendChild(button)
  }
}

function refreshTable(table: HTMLElement) {
  if (isInsideDialog(table)) return
  const index = getStatusColumnIndex(table)
  if (index < 0) return
  const statuses = getStatusValues(table, index)
  if (!statuses.length) return
  renderBar(table, statuses)
  const bar = table.previousElementSibling as HTMLElement | null
  applyStatus(table, index, bar?.dataset.active || '')
}

function refreshAll() {
  for (const table of Array.from(document.querySelectorAll<HTMLElement>('.el-table'))) {
    refreshTable(table)
  }
}

export function installTableStatusTabs(app: App) {
  app.mixin({
    mounted() {
      setTimeout(refreshAll, 80)
    },
    updated() {
      setTimeout(refreshAll, 80)
    },
  })

  window.addEventListener('popstate', () => setTimeout(refreshAll, 120))
}
