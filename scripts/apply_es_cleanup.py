import json
import os

# Top critical translations covering common, navigation, modules, and status
# Based on analysis of missing_es_strict.json
TRANSLATIONS = {
    # Common
    "common.error": "Error",
    "common.source": "Fuente",
    "common.tests.xray": "Rayos X",
    "common.quotingHelper.workbench.material": "Material",
    "common.status.completed": "Completado",
    "common.status.picked": "Recogido",
    "common.status.packed": "Empaquetado",
    "common.status.shipped": "Enviado",
    "common.status.delivered": "Entregado",
    "common.status.inProgress": "En progreso",
    "common.status.pending": "Pendiente",
    "common.status.error": "Error",
    "common.user": "Usuario",
    "common.priority.normal": "Normal",
    "common.protocol": "Protocolo",
    "common.total": "Total",
    "common.subtotal": "Subtotal",
    "common.abort": "Abortar",
    "common.activity": "Actividad",
    "common.actual": "Real",
    "common.instructor": "Instructor",
    "common.activate": "Activar",
    
    # Navigation
    "navigation.auditor": "Auditor",
    "navigation.obeya": "Obeya",
    "navigation.andon": "Andon",
    
    # Settings
    "settings.general": "General",
    "settings.profile.avatar": "Avatar",
    "settings.roleInsights.roles.auditor.name": "Auditor",
    "settings.roleInsights.roles.supervisor.name": "Supervisor",
    "settings.team.roles.admin": "Administrador",
    "settings.webhooks": "Webhooks",
    
    # Modules - Production
    "modules.production.detail.node": "Nodo",
    "modules.production.detail.tabs.history": "Historial",
    "modules.production.detail.tabs.operations": "Operaciones",
    "modules.production.detail.tabs.quality": "Calidad",
    "modules.production.detail.viewHistory": "Ver historial",
    "modules.production.detail.station": "ESTACIÓN",
    "modules.production.detail.days": "DÍAS",
    
    # Modules - Quality
    "modules.quality.ncr.detail.comment": "Comentario",
    "modules.quality.ncr.detail.noDescription": "Sin descripción",
    "modules.quality.ncr.detail.subtitle": "Subtítulo",
    "modules.quality.ncr.detail.tabs.disposition": "Disposición",
    "modules.quality.ncr.detail.tabs.eventLog": "Registro de eventos",
    "modules.quality.ncr.detail.tabs.evidence": "Evidencia",
    "modules.quality.ncr.detail.tabs.rootCause": "Causa raíz",
    "modules.quality.ncr.detail.viewLogs": "Ver registros",
    "modules.quality.ncr.new.validationError": "Error de validación",
    "modules.quality.ncr.new.titleDescRequired": "El título y la descripción son obligatorios.",
    "modules.quality.ncr.new.ncrCreated": "NCR Creada",
    "modules.quality.ncr.new.recordedSuccess": "La NCR se ha registrado con éxito.",
    "modules.quality.ncr.new.createFailed": "Error al crear NCR",
    "modules.quality.capa.new.capaCreated": "CAPA Creada",
    "modules.quality.capa.new.createFailed": "Error al crear",
    "modules.quality.capa.detail.problemStatement": "Declaración del problema",
    "modules.quality.capa.detail.rootCauseAnalysis": "Análisis de causa raíz",
    "modules.quality.inspection.detail.checklist": "Lista de verificación",
    "modules.quality.inspection.detail.leadInspector": "Inspector principal",
    "modules.quality.inspection.detail.printEvidence": "Imprimir evidencia",
    "modules.quality.inspection.new.inspectionStarted": "Inspección iniciada",
    "modules.quality.inspection.new.initializedSuccess": "Nuevo registro de inspección inicializado.",
    "modules.quality.inspection.new.createFailed": "Error al crear la inspección.",
    
    # Modules - Inventory & Maintenance
    "modules.inventory.stock": "Stock",
    "modules.maintenance.mttr": "TMTR (MTTR)",
    "modules.maintenance.mtbf": "TMEF (MTBF)",
    
    # Modules - Products
    "modules.products.title": "Catálogo de productos",
    "modules.products.subtitle": "Gestionar productos, LdM (BOMs) y rutas de fabricación",
    "modules.products.station": "PRODUCTOS",
    "modules.products.stats.activeProducts": "Productos activos",
    "modules.products.stats.bomsDefined": "LdM Definidas",
    "modules.products.stats.routingsActive": "Rutas activas",
    "modules.products.stats.avgLeadTime": "Tiempo de entrega prom.",
    "modules.products.stats.activeInventoryNodes": "Nodos de inventario activos",
    "modules.products.stats.aggregatedRevenue": "Ingresos totales",
    "modules.products.stats.meanMarginKPI": "Margen promedio",
    "modules.products.stats.stockAbnormalities": "Alertas de stock bajo",
    "modules.products.actions.newProduct": "Nuevo producto",
    "modules.products.tabs.products": "Productos",
    "modules.products.tabs.boms": "LdM (BOMs)",
    "modules.products.tabs.routings": "Rutas",
    "modules.products.details.overview": "Descripción general",
    "modules.products.details.specifications": "Especificaciones",
    "modules.products.details.bom": "Lista de materiales (LdM)",
    "modules.products.details.routing": "Ruta",
    "modules.products.details.inventory": "Inventario",
    "modules.products.details.history": "Historial",
    "modules.products.status.discontinued": "Descontinuado",
    "modules.products.viewBom": "Ver LdM",
    "modules.products.viewAnalytics": "Ver análisis",
    "modules.products.stockLevel": "Nivel de stock",
    "modules.products.allStock": "Todo el stock",
    "modules.products.lowStock": "Stock bajo",
    "modules.products.outOfStock": "Sin stock",
    "modules.products.table.product": "Producto",
    "modules.products.table.standardCost": "Costo estándar",
    "modules.products.table.listPrice": "Precio de lista",
    "modules.products.table.margin": "Margen",
    "modules.products.table.inventory": "Inventario",
    "modules.products.table.leadTime": "Tiempo de entrega",
    "modules.products.table.totalSold": "Total vendido",
    "modules.products.emptyState.description": "Comience agregando su primer producto al catálogo.",
    "modules.products.emptyState.title": "No se encontraron productos",
    "modules.products.exportIntel": "Exportar catálogo",
    "modules.products.import": "Importar",
    "modules.products.initializeNode": "Crear producto",
    "modules.products.new.requiredParams": "Faltan parámetros requeridos",
    "modules.products.new.providePartAndName": "Proporcione al menos un número de parte y un nombre.",
    "modules.products.new.nodeSynchronized": "Nodo sincronizado",
    "modules.products.new.establishedSuccess": "{name} se ha establecido con éxito en el catálogo.",
    "modules.products.new.syncFailed": "Error de sincronización",
    "modules.products.new.failedToEstablish": "Error al establecer el nodo del producto en el registro.",
    "modules.products.detail.meta": "Meta",

    # Pages - Executive & Analytics
    "pages.analytics.statusOptimal": "ÓPTIMO",
    "pages.executive.loading": "Cargando...",
    "pages.executive.kpi.qualityScore": "Puntaje de calidad",
    "pages.executive.kpi.deliveryScore": "Puntaje de entrega",
    "pages.executive.kpi.costEfficiency": "Eficiencia de costos",
    "pages.executive.kpi.workforce": "Fuerza laboral",
    "pages.executive.kpi.overallScore": "Puntaje general",
    "pages.executive.kpi.belowTarget": "Por debajo del objetivo",
    "pages.executive.kpi.awaitingData": "Esperando datos",
    "pages.executive.ops.activeUsers": "Usuarios activos",
    "pages.executive.ops.openWorkOrders": "Órdenes de trabajo abiertas",
    "pages.executive.ops.productionEfficiency": "Eficiencia de producción",
    "pages.executive.ops.pendingApprovals": "Aprobaciones pendientes",
    "pages.executive.sqdcp.safety": "Seguridad",
    "pages.executive.sqdcp.quality": "Calidad",
    "pages.executive.sqdcp.delivery": "Entrega",
    "pages.executive.sqdcp.cost": "Costo",
    "pages.executive.sqdcp.people": "Personas",

    # Pages - Finance
    "pages.finance.sections.accountsReceivable": "Cuentas por cobrar",
    "pages.finance.sections.budgetAnalysis": "Análisis presupuestario",
    "pages.finance.costDrivers.energy": "Energía",
    "pages.finance.costDrivers.impactOnMargin": "Impacto en el margen",
    "pages.finance.costDrivers.logistics": "Logística",
    "pages.finance.costDrivers.overtime": "Horas extra",
    "pages.finance.station": "Estación",

    # Pages - HR
    "pages.hr.unassignedRole": "Rol no asignado",
    "pages.hr.noDepartment": "Sin depto.",
    "pages.hr.remote": "Remoto",
    "pages.hr.unknownPosition": "Posición desconocida",
    "pages.hr.candidateDetails": "Detalles del candidato",
    "pages.hr.searchPersonnel": "Buscar personal...",
    "pages.hr.searchJobs": "Buscar trabajos...",
    "pages.hr.toast.employeeCreated": "Empleado creado con éxito",
    "pages.hr.toast.employeeCreatedTitle": "Éxito",
    "pages.hr.toast.employeeTerminated": "Registro del empleado terminado",
    "pages.hr.toast.jobCreated": "Oferta de trabajo creada",
    "pages.hr.toast.jobDeleted": "Oferta de trabajo eliminada",
    "pages.hr.toast.deletionFailed": "Error al eliminar",
    "pages.hr.toast.applicationSubmitted": "Solicitud enviada",
    "pages.hr.toast.applicationMoved": "Solicitud movida a {status}",
    "pages.hr.toast.updateStatusFailed": "Error al actualizar el estado de la solicitud",
    "pages.hr.toast.leaveSubmitted": "Solicitud de licencia enviada",
    "pages.hr.toast.leaveApproved": "Solicitud de licencia aprobada",
    "pages.hr.toast.leaveApproveFailed": "Error al aprobar la solicitud de licencia",
    "pages.hr.toast.leaveRejected": "Solicitud de licencia rechazada",
    "pages.hr.toast.leaveRejectFailed": "Error al rechazar la solicitud de licencia",
    "pages.hr.confirmTerminate.title": "Terminar registro de empleado",
    "pages.hr.confirmTerminate.description": "¿Está seguro de que desea terminar este registro de empleado? Esta acción no se puede deshacer.",
    "pages.hr.confirmDeleteJob.title": "Eliminar oferta de trabajo",
    "pages.hr.confirmDeleteJob.description": "¿Está seguro de que desea eliminar esta oferta de trabajo?",

    # Pages - Warehouse
    "pages.warehouse.loading": "Cargando datos del almacén...",
    "pages.warehouse.searchDescription": "Buscar y gestionar todo el inventario del almacén",
    "pages.warehouse.searchPlaceholder": "Buscar artículos...",
    "pages.warehouse.itemName": "Nombre del artículo",
    "pages.warehouse.onHand": "Disponible",
    "pages.warehouse.managePO": "Gestionar recibos de órdenes de compra y materiales entrantes",
    "pages.warehouse.poReference": "Ref. OC",
    "pages.warehouse.expectedDate": "Fecha esperada",
    "pages.warehouse.inTransit": "En tránsito",
    "pages.warehouse.manageShipments": "Gestionar envíos y logística de entrega",
    "pages.warehouse.shipDate": "Fecha de envío",
    "pages.warehouse.activePickLists": "Listas de picking activas y cumplimiento de pedidos",
    "pages.warehouse.itemsPicked": "artículos recogidos",

    # Pages - Pipeline & Customers
    "pages.pipeline.views.kanban": "Kanban",
    "pages.pipeline.tableHeaders.triageScore": "Puntaje de triaje",
    "pages.pipeline.tableHeaders.completeness": "Integridad",
    "pages.customers.labels.rfqs": "RFQs",
    "pages.customers.metrics.rfqs": "RFQs",
    "pages.customers.detail.stats.totalRfqs": "Total RFQs",
    "pages.customers.toast.deactivated": "Cliente desactivado",

    # Pages - Quotes & Sales
    "pages.quotes.actions.initiateApproval": "Iniciar aprobación",
    "pages.quotes.detail.subtotal": "Subtotal",
    "pages.quotes.detail.total": "Total",
    "pages.quotes.new.subtotal": "Subtotal",
    "pages.quotes.new.total": "Total",
    "pages.quotes.new.materialCost": "Costo de material",
    "pages.quotes.new.laborCost": "Costo de mano de obra",
    "pages.quotes.new.overheadCost": "Gastos generales",
    "pages.quotes.new.lineItemNotes": "Notas del artículo",
    "pages.quotes.new.noAssumptions": "Sin supuestos definidos",
    "pages.quotes.new.newQuote": "Nueva cotización",
    "pages.quotes.new.viewVersionHistory": "Ver historial de versiones",
    "pages.quotes.new.addProductsPricing": "Agregar productos y precios",
    "pages.quotes.new.toggleCostBreakdown": "Alternar desglose de costos detallado",
    "pages.quotes.new.unitPrice": "Precio unitario",
    "pages.quotes.new.internalCostingAnalysis": "Análisis de costos internos",
    "pages.quotes.new.totalRevenue": "Ingresos totales",
    "pages.quotes.new.grossProfit": "Beneficio bruto",
    "pages.quotes.new.quickActions": "Acciones rápidas",
    "pages.quotes.new.assumptionsVerified": "Supuestos verificados",
    "pages.quotes.new.warningsPresent": "Advertencias presentes",
    "pages.quotes.toast.savedDraft": "Cotización guardada como borrador",
    "pages.quotes.toast.submitted": "Cotización enviada para aprobación",
    "pages.quotes.toast.saveFailed": "Error al guardar la cotización",
    "pages.quotes.toast.tryAgain": "Por favor intente nuevamente.",
    "pages.sales.noBid": "Sin oferta",
    "pages.sales.statusReviewing": "Revisando",
    "pages.sales.statusQuoting": "Cotizando",
    "pages.sales.statusSubmitted": "Enviado",
    "pages.sales.totalRfqs": "Total RFQs",
    "pages.sales.avgResponseTime": "Tiempo de respuesta prom.",
    "pages.sales.conversionRate": "Tasa de conversión",
    "pages.sales.dueDate": "Fecha de vencimiento",
    "pages.sales.receivedDate": "Fecha de recepción",
    "pages.sales.searchRfqs": "Buscar RFQs...",

    # Pages - Others
    "pages.production.views.kanban": "Kanban",
    "pages.production.views.gantt": "Gantt",
    "pages.quality.tabs.ncrs": "NCRs",
    "pages.quality.tabs.capas": "CAPAs",
    "pages.quality.status.capa": "CAPA",
    "pages.quality.table.inspector": "Inspector",
    "pages.maintenance.tabs.loto": "Loto",
    "pages.maintenance.table.actual": "Real",
    "pages.purchase.requisitions": "Solicitudes",
    "pages.purchase.requisitionNew.error": "Error",
    "pages.settings.profile.sections.avatar": "Avatar",
    
    # Obeya & A3 & CTQ
    "pages.obeya.sections.hoshinKanri": "Hoshin Kanri",
    "pages.obeya.toast.itemDeleted": "Elemento eliminado con éxito",
    "pages.obeya.toast.deleteFailed": "Error al eliminar el elemento",
    "pages.obeya.toast.commentAdded": "Comentario agregado",
    "pages.obeya.toast.commentFailed": "Error al agregar comentario",
    "pages.obeya.toast.statusUpdated": "Estado actualizado",
    "pages.obeya.toast.statusFailed": "Error al actualizar el estado",
    "pages.obeya.toast.created": "Tablero Obeya creado",
    "pages.obeya.toast.createdDesc": "Su nuevo tablero digital obeya ha sido inicializado con éxito.",
    "pages.a3.toast.titleRequired": "Por favor ingrese un título para el informe A3.",
    "pages.a3.toast.created": "Informe A3 creado",
    "pages.a3.toast.createdDesc": "El nuevo informe A3 ha sido inicializado con éxito.",
    "pages.a3.toast.createFailed": "Error al crear el informe A3.",
    "pages.a3.toast.loadFailed": "Error al cargar detalles del A3",
    "pages.a3.toast.export": "Exportar",
    "pages.a3.toast.exportDesc": "Iniciando exportación PDF...",
    "pages.a3.toast.updated": "Informe A3 actualizado",
    "pages.a3.toast.updatedDesc": "Los cambios se han guardado con éxito.",
    "pages.a3.toast.updateFailed": "Error al actualizar el informe A3.",
    "pages.ctq.toast.error": "Error",
    "pages.ctq.toast.loadFailed": "Error al cargar detalles de CTQ",
    "pages.ctq.toast.success": "Éxito",
    "pages.ctq.toast.deleteFailed": "Error al eliminar CTQ",
    "pages.ctq.toast.measurementAdded": "Medición agregada con éxito",
    "pages.ctq.toast.measurementFailed": "Error al agregar medición",
    "pages.ctq.toast.exportStarted": "Exportación iniciada",
    "pages.ctq.toast.exportStartedDesc": "Su informe CTQ se está generando",
    "pages.ctq.detail.specificationDetails": "Detalles de especificación",
    "pages.ctq.detail.qualityRequirements": "Requisitos de características de calidad",
    "pages.ctq.detail.nominalValue": "Valor nominal",
    "pages.ctq.detail.upperTolerance": "Tolerancia superior",
    "pages.ctq.detail.lowerTolerance": "Tolerancia inferior",
    "pages.ctq.detail.relatedRfq": "RFQ relacionada",
    "pages.ctq.detail.partNumber": "Número de parte",
    "pages.ctq.detail.measurementInfo": "Información de medición",
    "pages.ctq.detail.howMeasured": "Cómo se mide esta característica",
    "pages.ctq.detail.measurementMethod": "Método de medición",
    "pages.ctq.detail.samplingPlan": "Plan de muestreo",
    "pages.ctq.detail.checkStage": "Etapa de verificación",
    "pages.ctq.detail.evidenceRequired": "Evidencia requerida",
    "pages.ctq.detail.lastUpdated": "Última actualización",
    "pages.ctq.detail.measurementHistory": "Historial de mediciones",
    "pages.ctq.detail.recentResults": "Resultados recientes y tendencias",
    "pages.ctq.detail.measuredBy": "Medido por",
    "pages.ctq.detail.deleteCtq": "Eliminar CTQ",
    "pages.ctq.detail.extractProtocol": "Protocolo de extracción",
    "pages.ctq.detail.addMeasurement": "Agregar medición",
    "pages.ctq.detail.measuredValue": "Valor medido",
    "pages.ctq.detail.notMeasured": "No medido",

    # Project Management
    "pages.projectManagement.detail.backlog": "Backlog",
    "pages.projectManagement.detail.sprints": "Sprints",
    "pages.projectManagement.detail.wiki": "Wiki",
    "pages.projectManagement.types.scrum": "Scrum",
    "pages.projectManagement.types.kanban": "Kanban",
    "pages.projectManagement.types.kaizen": "Kaizen",
}

def apply_cleanup():
    target_file = 'frontend/src/locales/es.json'
    
    if not os.path.exists(target_file):
        print(f"Error: Could not find {target_file}")
        return

    print(f"Loading {target_file}...")
    try:
        with open(target_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading JSON: {e}")
        return

    updated_count = 0
    
    def set_nested_value(d, path, value):
        keys = path.split('.')
        current = d
        for i, k in enumerate(keys[:-1]):
            if k not in current:
                # Path doesn't exist, can't update
                return False
            current = current[k]
            if not isinstance(current, dict):
                 # Structure mismatch
                 return False
        
        last_key = keys[-1]
        if last_key in current:
            if current[last_key] != value:
                # Verify we are overwriting something that looks like English or at least not the target
                # (Optional check, but let's blindly trust the dictionary for now)
                print(f"Updating {path}: '{current[last_key]}' -> '{value}'")
                current[last_key] = value
                return True
        return False

    for key, spanish_val in TRANSLATIONS.items():
        if set_nested_value(data, key, spanish_val):
            updated_count += 1

    if updated_count > 0:
        print(f"Saving {updated_count} updates to {target_file}...")
        with open(target_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("Done.")
    else:
        print("No updates needed.")

if __name__ == "__main__":
    apply_cleanup()
