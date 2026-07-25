// modules/catalogo/hooks/useArchivoPdf.js
import { useCallback, useRef, useState } from 'react'
import { validarArchivo } from '../utils/validation'

/**
 * Encapsula toda la lógica de selección de archivo: input file,
 * drag & drop, validación y limpieza. Mantiene el componente de
 * página libre de este detalle de implementación.
 */
export function useArchivoPdf() {
  const fileInputRef = useRef(null)
  const [archivo, setArchivo] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState(null)

  const seleccionar = useCallback((file) => {
    if (!file) return
    const err = validarArchivo(file)
    if (err) {
      setError(err)
      return
    }
    setError(null)
    setArchivo(file)
  }, [])

  const remover = useCallback(() => {
    setArchivo(null)
    setError(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }, [])

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files?.[0]
    if (file) seleccionar(file)
  }, [seleccionar])

  const handleDragOver = useCallback((e) => {
    e.preventDefault()
    setDragOver(true)
  }, [])

  const handleDragLeave = useCallback(() => setDragOver(false), [])

  const abrirSelector = useCallback(() => {
    fileInputRef.current?.click()
  }, [])

  return {
    fileInputRef,
    archivo,
    dragOver,
    error,
    seleccionar,
    remover,
    handleDrop,
    handleDragOver,
    handleDragLeave,
    abrirSelector,
  }
}