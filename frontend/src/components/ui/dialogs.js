let requests = []
const listeners = new Set()
const emit = () => listeners.forEach((listener) => listener())
function request(kind, message, options = {}) {
  return new Promise((resolve) => {
    requests = [...requests, { kind, message, ...options, resolve }]
    emit()
  })
}
export const dialogs = {
  confirm: (message, options) => request('confirm', message, options),
  alert: (message, options) => request('alert', message, options),
}
export const dialogStore = {
  subscribe: (listener) => { listeners.add(listener); return () => listeners.delete(listener) },
  snapshot: () => requests[0] || null,
  close: (accepted = false) => {
    const current = requests[0]
    requests = requests.slice(1)
    current?.resolve(accepted)
    emit()
  },
}
