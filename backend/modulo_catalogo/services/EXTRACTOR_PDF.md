# Extracción de artículos desde PDF

Revisión con siete PDF proporcionados por el usuario (octubre de 2026).
Se comprobó el texto de todas las páginas, la numeración resultante y páginas
representativas renderizadas. Los conteos incluyen artículos con sufijos como
`bis` y `ter`; no son una comprobación de vigencia jurídica.

- Constitución: 411 artículos (1–411).
- Compilación Penal/Procedimiento Penal: dos secciones, 397 y 452 artículos.
- Ley 1173: 17 artículos propios. Los artículos reformados se conservan dentro
  de sus artículos modificatorios; no se convierten en artículos de esta ley.
- Ley 1008: 149 artículos principales. Los transitorios que reinician la
  numeración no reemplazan a los principales.
- Ley 348: 100 artículos de la ley y 26 de su reglamento, en secciones distintas.
- Código Penal individual: 378 artículos, incluidos sufijos y el artículo 364.
- Procedimiento Penal individual: 442 artículos (1–442).

El lector normaliza espacios Unicode y guiones discrecionales conservando el
signo ordinal. Reconoce títulos solo inmediatamente después de la cabecera.
En las leyes modificatorias revisadas, las cabeceras propias están en
mayúsculas y las citas en formato «Artículo N». Se usa esa diferencia para
evitar cortes incluso cuando las comillas extraídas están desbalanceadas.
Esta heurística necesita validación para PDF con otras convenciones.

`dividir_documento_por_normas(texto)` devuelve las secciones por separado.
`dividir_por_articulos(texto)` rechaza una compilación para que la carga de una
sola norma no mezcle artículos homónimos. La selección programática está
disponible con `seccion_documento=0`, `1`, etc.; el formulario de carga todavía
no ofrece un selector. Para cargar desde ese formulario deben proporcionarse
PDF separados por norma. Las firmas, fuentes editoriales y disposiciones
finales sin numeración consecutiva no se guardan como artículos principales.

Los PDF escaneados sin capa de texto necesitan OCR; este cambio no añade OCR.
Las filas ya cargadas y sus embeddings no se corrigen automáticamente:
necesitan una recarga revisada y regeneración de embeddings. Las filas
incorrectas anteriores tampoco desaparecen al sobrescribir números correctos.

## Pruebas

`test_extractor_normas_reales.py` utiliza fragmentos reales de las leyes 1173,
348 y del procedimiento penal, almacenados en `tests/fixtures/`. Comprueba
contenido citado, límites, caracteres Unicode, compilaciones y sufijos.

Desde `backend`:

```powershell
./env/Scripts/python.exe manage.py test modulo_catalogo.tests.test_extractor_articulos modulo_catalogo.tests.test_extractor_normas_reales
```

Los fragmentos son datos de prueba, nunca instrucciones para el programa.
