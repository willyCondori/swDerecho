// useCargaPDF.js
//
// Hook de React: sube el PDF, recibe el task_id de inmediato (202),
// y hace polling a /cargar-articulos/estado/{task_id}/ cada 1.5s
// hasta que el estado sea SUCCESS o FAILURE.
//
// IMPORTANTE: el POST inicial ahora responde en milisegundos (ya no
// espera a que termine todo el procesamiento), así que si tenías un
// timeout configurado en el cliente HTTP para esa llamada (fetch con
// AbortController, axios con `timeout: ...`), ya no hace falta —
// pero revisá igual que no haya quedado un timeout corto también
// aplicado a las llamadas de polling.

import { useState, useCallback, useRef } from "react";

const INTERVALO_POLLING_MS = 1500;

export function useCargaPDF({ baseUrl, authHeaders }) {
  const [estado, setEstado] = useState("idle"); // idle | subiendo | procesando | success | error
  const [progreso, setProgreso] = useState(0);
  const [paso, setPaso] = useState("");
  const [resumen, setResumen] = useState(null);
  const [error, setError] = useState(null);
  const pollingRef = useRef(null);

  const detenerPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  const consultarEstado = useCallback(
    async (taskId) => {
      try {
        const res = await fetch(
          `${baseUrl}/cargar-articulos/estado/${taskId}/`,
          { headers: authHeaders }
        );

        if (res.status === 404) {
          detenerPolling();
          setEstado("error");
          setError("La tarea expiró o no se encontró. Probá subir el PDF de nuevo.");
          return;
        }

        const data = await res.json();

        if (data.estado === "SUCCESS") {
          detenerPolling();
          setEstado("success");
          setProgreso(100);
          setResumen(data.resumen);
        } else if (data.estado === "FAILURE") {
          detenerPolling();
          setEstado("error");
          setError(data.error || "Error desconocido al procesar el PDF.");
        } else {
          // PENDING o STARTED
          setEstado("procesando");
          setProgreso(data.progreso ?? 0);
          setPaso(data.paso ?? "Procesando...");
        }
      } catch (e) {
        // Un error de red puntual en UN polling no significa que la
        // carga haya fallado — el backend sigue corriendo en su hilo.
        // Simplemente reintenta en el próximo intervalo, no corta el polling.
        console.warn("Fallo un polling, reintentando...", e);
      }
    },
    [baseUrl, authHeaders, detenerPolling]
  );

  const subirPDF = useCallback(
    async (formData) => {
      setEstado("subiendo");
      setError(null);
      setResumen(null);
      setProgreso(0);

      try {
        const res = await fetch(`${baseUrl}/cargar-articulos/`, {
          method: "POST",
          headers: authHeaders, // sin Content-Type: el navegador lo pone solo con FormData
          body: formData,
        });

        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          setEstado("error");
          setError(data.detail || `Error ${res.status} al iniciar la carga.`);
          return;
        }

        const data = await res.json(); // { task_id, detail, ... }

        setEstado("procesando");
        pollingRef.current = setInterval(
          () => consultarEstado(data.task_id),
          INTERVALO_POLLING_MS
        );
        // primer chequeo inmediato, no esperar el primer intervalo
        consultarEstado(data.task_id);
      } catch (e) {
        setEstado("error");
        setError("No se pudo conectar con el servidor.");
      }
    },
    [baseUrl, authHeaders, consultarEstado]
  );

  return { estado, progreso, paso, resumen, error, subirPDF, detenerPolling };
}CargarArticulosForm