# Modelo local e5_base

El modelo activo es `backend/modelos/e5_base`, una adaptación de multilingual-e5-base.
Se identifica en la base de datos como `e5_base`. Genera vectores normalizados de
768 dimensiones y admite hasta 512 tokens por entrada.

La vectorización añade `query: ` a los fragmentos de casos y `passage: ` a los
artículos y fragmentos de jurisprudencia, de acuerdo con el entrenamiento guardado.
Los vectores anteriores conservan su propia versión.

Desde `backend`, con el entorno virtual activado:

```powershell
python manage.py regenerar_embeddings_articulos --solo-faltantes --batch-size 16
python manage.py regenerar_embeddings_jurisprudencia --batch-size 16
```

Ambos comandos permiten reanudar sin recalcular los registros ya indexados.
La búsqueda de jurisprudencia comunica `sin_embeddings` mientras falten fragmentos
del modelo activo, para evitar presentar una búsqueda parcial como completa.
Los resultados guardados de casos no cambian automáticamente: deben reanalizarse
una vez terminada la indexación.

La configuración local está en `backend/.env`; Docker utiliza `/app/modelos/e5_base`
mediante el montaje de `backend/modelos` definido en `compose.yaml`.
