// api/tokenManager.js
//
// Fuente única del access token: vive SOLO en una variable en memoria,
// nunca en localStorage ni sessionStorage. Un script inyectado por XSS
// puede leer localStorage con una línea (`localStorage.getItem(...)`),
// pero no tiene forma de leer una variable de módulo de otro chunk de JS
// a menos que ya tenga ejecución arbitraria en la página (en cuyo punto
// ya perdiste de cualquier forma). El refresh token ni siquiera pasa por
// acá: vive en una cookie httpOnly que el JS del navegador no puede leer.
//
// Se pierde al recargar la página a propósito — authStore.bootstrap()
// lo repone pidiendo uno nuevo con la cookie httpOnly del refresh token.

let accessToken = null

export function getAccessToken() {
  return accessToken
}

export function setAccessToken(token) {
  accessToken = token
}

export function clearAccessToken() {
  accessToken = null
}
