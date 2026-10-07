# Componentes compartidos

Antes de añadir otra tabla o barra de listado, revisar estos componentes:

- `ui/DataTable`: columnas, filas, carga, error, vacío y acciones sin propagar el clic a la fila.
- `ui/ListState`: estados vacíos y errores de tablas, listados y tarjetas.
- `ui/Pagination`: navegación numerada o `variant="simple"`, rango y selector opcional de tamaño de página.
- `ui/SearchField`: búsqueda accesible y limpieza opcional; entrega texto a `onChange`. El módulo conserva el debounce y las peticiones.
- `ui/FilterTabs`: filtros por estado con `aria-pressed` y botones que no envían formularios.
- `ui/PageHeader`: título, descripción y acciones. Los permisos y navegación siguen en la pantalla.
- `ui/NameDescriptionForm`: formulario de nombre y descripción con errores, cancelación y estado de guardado. Cada adaptador define textos y normalización.

Los controles aceptan `classes` para conservar los estilos de la pantalla; no deben contener llamadas a la API ni reglas de vigencia jurídica.

En Catálogo, `CatalogoEntityTable` comparte la tabla de ramas y entidades. `DisposicionesList` comparte la presentación de disposiciones extraídas y guardadas.

La navegación animada del catálogo y las filas expandibles de artículos conservan sus componentes especializados. Sus interacciones son distintas de los filtros y tablas simples.
