# ============================================================
# BACKEND — Django
# ============================================================
$base = "backend"

$dirs = @(
  # Config principal
  "$base\config",

  # Módulo usuarios
  "$base\modulo_usuarios\models",
  "$base\modulo_usuarios\serializers",
  "$base\modulo_usuarios\views",
  "$base\modulo_usuarios\services",
  "$base\modulo_usuarios\urls",

  # Módulo clientes
  "$base\modulo_clientes\models",
  "$base\modulo_clientes\serializers",
  "$base\modulo_clientes\views",
  "$base\modulo_clientes\services",
  "$base\modulo_clientes\urls",

  # Módulo catálogo jurídico
  "$base\modulo_catalogo\models",
  "$base\modulo_catalogo\serializers",
  "$base\modulo_catalogo\views",
  "$base\modulo_catalogo\services",
  "$base\modulo_catalogo\urls",

  # Módulo casos
  "$base\modulo_casos\models",
  "$base\modulo_casos\serializers",
  "$base\modulo_casos\views",
  "$base\modulo_casos\services",
  "$base\modulo_casos\urls",

  # Módulo documentos
  "$base\modulo_documentos\models",
  "$base\modulo_documentos\serializers",
  "$base\modulo_documentos\views",
  "$base\modulo_documentos\services",
  "$base\modulo_documentos\urls",

  # Módulo IA
  "$base\modulo_ia\models",
  "$base\modulo_ia\serializers",
  "$base\modulo_ia\views",
  "$base\modulo_ia\services",
  "$base\modulo_ia\urls",
  "$base\modulo_ia\tasks",
  "$base\modulo_ia\utils",

  # Módulo auditoría
  "$base\modulo_auditoria\models",
  "$base\modulo_auditoria\serializers",
  "$base\modulo_auditoria\views",
  "$base\modulo_auditoria\urls",

  # Core compartido
  "$base\core\permissions",
  "$base\core\encryption",
  "$base\core\pagination",
  "$base\core\middleware",
  "$base\core\exceptions",

  # Archivos de media
  "$base\media\documentos_caso",
  "$base\media\documentos_generados",
  "$base\media\plantillas"
)

foreach ($dir in $dirs) {
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

# Archivos clave del backend
$files = @(
  "$base\config\settings\base.py",
  "$base\config\settings\development.py",
  "$base\config\settings\production.py",
  "$base\config\urls.py",
  "$base\config\celery.py",

  "$base\modulo_usuarios\models\usuario.py",
  "$base\modulo_usuarios\models\rol.py",
  "$base\modulo_usuarios\models\perfil.py",
  "$base\modulo_usuarios\serializers\auth_serializer.py",
  "$base\modulo_usuarios\serializers\usuario_serializer.py",
  "$base\modulo_usuarios\views\auth_view.py",
  "$base\modulo_usuarios\views\usuario_view.py",
  "$base\modulo_usuarios\services\auth_service.py",
  "$base\modulo_usuarios\services\encryption_service.py",
  "$base\modulo_usuarios\urls\auth_urls.py",
  "$base\modulo_usuarios\urls\usuario_urls.py",

  "$base\modulo_clientes\models\cliente.py",
  "$base\modulo_clientes\serializers\cliente_serializer.py",
  "$base\modulo_clientes\views\cliente_view.py",
  "$base\modulo_clientes\services\cliente_service.py",
  "$base\modulo_clientes\urls\cliente_urls.py",

  "$base\modulo_catalogo\models\rama.py",
  "$base\modulo_catalogo\models\norma.py",
  "$base\modulo_catalogo\models\articulo.py",
  "$base\modulo_catalogo\models\entidad.py",
  "$base\modulo_catalogo\serializers\articulo_serializer.py",
  "$base\modulo_catalogo\views\articulo_view.py",
  "$base\modulo_catalogo\services\catalogo_service.py",
  "$base\modulo_catalogo\urls\catalogo_urls.py",

  "$base\modulo_casos\models\caso.py",
  "$base\modulo_casos\models\hecho.py",
  "$base\modulo_casos\models\petitorio.py",
  "$base\modulo_casos\serializers\caso_serializer.py",
  "$base\modulo_casos\serializers\hecho_serializer.py",
  "$base\modulo_casos\views\caso_view.py",
  "$base\modulo_casos\views\resultado_view.py",
  "$base\modulo_casos\services\caso_service.py",
  "$base\modulo_casos\urls\caso_urls.py",

  "$base\modulo_documentos\models\documento.py",
  "$base\modulo_documentos\models\plantilla.py",
  "$base\modulo_documentos\models\generado.py",
  "$base\modulo_documentos\serializers\documento_serializer.py",
  "$base\modulo_documentos\views\documento_view.py",
  "$base\modulo_documentos\views\plantilla_view.py",
  "$base\modulo_documentos\services\documento_service.py",
  "$base\modulo_documentos\services\generador_docx_service.py",
  "$base\modulo_documentos\urls\documento_urls.py",

  "$base\modulo_ia\models\embedding.py",
  "$base\modulo_ia\models\resultado.py",
  "$base\modulo_ia\models\chunk.py",
  "$base\modulo_ia\serializers\resultado_serializer.py",
  "$base\modulo_ia\views\analisis_view.py",
  "$base\modulo_ia\services\chunking_service.py",
  "$base\modulo_ia\services\embedding_service.py",
  "$base\modulo_ia\services\ranking_service.py",
  "$base\modulo_ia\services\llm_service.py",
  "$base\modulo_ia\tasks\analisis_task.py",
  "$base\modulo_ia\utils\pdf_extractor.py",
  "$base\modulo_ia\urls\ia_urls.py",

  "$base\modulo_auditoria\models\auditoria.py",
  "$base\modulo_auditoria\serializers\auditoria_serializer.py",
  "$base\modulo_auditoria\views\auditoria_view.py",
  "$base\modulo_auditoria\urls\auditoria_urls.py",

  "$base\core\permissions\roles_permission.py",
  "$base\core\encryption\aes_encryption.py",
  "$base\core\pagination\custom_pagination.py",
  "$base\core\middleware\auditoria_middleware.py",
  "$base\core\exceptions\custom_exceptions.py",

  "$base\requirements.txt",
  "$base\.env.example",
  "$base\manage.py"
)

foreach ($f in $files) {
  New-Item -ItemType File -Force -Path $f | Out-Null
}

Write-Host "Backend creado correctamente." -ForegroundColor Green
