# ============================================================
# FRONTEND — React
# ============================================================
$front = "frontend\src"

$fdirs = @(
  # Módulos principales
  "$front\modules\auth\components",
  "$front\modules\auth\pages",
  "$front\modules\auth\hooks",
  "$front\modules\auth\services",
  "$front\modules\auth\store",

  "$front\modules\usuarios\components",
  "$front\modules\usuarios\pages",
  "$front\modules\usuarios\hooks",
  "$front\modules\usuarios\services",

  "$front\modules\clientes\components",
  "$front\modules\clientes\pages",
  "$front\modules\clientes\services",

  "$front\modules\casos\components",
  "$front\modules\casos\pages",
  "$front\modules\casos\hooks",
  "$front\modules\casos\services",

  "$front\modules\documentos\components",
  "$front\modules\documentos\pages",
  "$front\modules\documentos\services",

  "$front\modules\resultados\components",
  "$front\modules\resultados\pages",
  "$front\modules\resultados\services",

  "$front\modules\catalogo\components",
  "$front\modules\catalogo\pages",
  "$front\modules\catalogo\services",

  # Componentes compartidos
  "$front\components\ui",
  "$front\components\layout",
  "$front\components\forms",
  "$front\components\tables",
  "$front\components\charts",

  # Core
  "$front\api",
  "$front\store",
  "$front\hooks",
  "$front\utils",
  "$front\routes",
  "$front\config"
)

foreach ($dir in $fdirs) {
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

$ffiles = @(
  # API layer
  "$front\api\axiosInstance.js",
  "$front\api\authApi.js",
  "$front\api\usuariosApi.js",
  "$front\api\clientesApi.js",
  "$front\api\casosApi.js",
  "$front\api\documentosApi.js",
  "$front\api\iaApi.js",
  "$front\api\catalogoApi.js",

  # Auth
  "$front\modules\auth\pages\LoginPage.jsx",
  "$front\modules\auth\components\LoginForm.jsx",
  "$front\modules\auth\hooks\useAuth.js",
  "$front\modules\auth\services\authService.js",
  "$front\modules\auth\store\authStore.js",

  # Usuarios
  "$front\modules\usuarios\pages\UsuariosPage.jsx",
  "$front\modules\usuarios\components\UsuarioTable.jsx",
  "$front\modules\usuarios\components\UsuarioForm.jsx",
  "$front\modules\usuarios\services\usuariosService.js",

  # Clientes
  "$front\modules\clientes\pages\ClientesPage.jsx",
  "$front\modules\clientes\components\ClienteForm.jsx",
  "$front\modules\clientes\services\clientesService.js",

  # Casos
  "$front\modules\casos\pages\CasosPage.jsx",
  "$front\modules\casos\pages\CasoDetailPage.jsx",
  "$front\modules\casos\pages\NuevoCasoPage.jsx",
  "$front\modules\casos\components\CasoCard.jsx",
  "$front\modules\casos\components\CasoForm.jsx",
  "$front\modules\casos\components\CasoFiltros.jsx",
  "$front\modules\casos\components\TextoCasoInput.jsx",
  "$front\modules\casos\components\PDFUploader.jsx",
  "$front\modules\casos\hooks\useCaso.js",
  "$front\modules\casos\services\casosService.js",

  # Documentos
  "$front\modules\documentos\pages\DocumentosPage.jsx",
  "$front\modules\documentos\components\DocumentoViewer.jsx",
  "$front\modules\documentos\components\PlantillaUploader.jsx",
  "$front\modules\documentos\services\documentosService.js",

  # Resultados
  "$front\modules\resultados\pages\ResultadosPage.jsx",
  "$front\modules\resultados\components\ResumenCard.jsx",
  "$front\modules\resultados\components\ArticulosAplicables.jsx",
  "$front\modules\resultados\components\FortalezasDebilidades.jsx",
  "$front\modules\resultados\components\EstrategiasCard.jsx",
  "$front\modules\resultados\services\resultadosService.js",

  # Catálogo
  "$front\modules\catalogo\pages\CatalogoPage.jsx",
  "$front\modules\catalogo\components\ArticuloTable.jsx",
  "$front\modules\catalogo\services\catalogoService.js",

  # Componentes UI
  "$front\components\ui\Button.jsx",
  "$front\components\ui\Modal.jsx",
  "$front\components\ui\Badge.jsx",
  "$front\components\ui\Spinner.jsx",
  "$front\components\layout\Sidebar.jsx",
  "$front\components\layout\Navbar.jsx",
  "$front\components\layout\PrivateRoute.jsx",
  "$front\components\tables\DataTable.jsx",
  "$front\components\forms\FileDropzone.jsx",

  # Core
  "$front\store\index.js",
  "$front\hooks\usePermissions.js",
  "$front\utils\formatters.js",
  "$front\utils\validators.js",
  "$front\routes\AppRouter.jsx",
  "$front\config\constants.js",

  # Entry points
  "$front\main.jsx",
  "$front\App.jsx",
  "frontend\.env.example",
  "frontend\vite.config.js"
)

foreach ($f in $ffiles) {
  New-Item -ItemType File -Force -Path $f | Out-Null
}

Write-Host "Frontend creado correctamente." -ForegroundColor Green
Write-Host "Estructura completa generada." -ForegroundColor Cyan