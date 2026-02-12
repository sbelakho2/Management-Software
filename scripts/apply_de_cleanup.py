import json
import os

# Define the dictionary of translations (dotted_key -> German Value)
TRANSLATIONS = {
    # Common
    "common.info": "Info",
    "common.source": "Quelle",
    "common.details": "Details",
    "common.tests.xray": "Röntgen",
    "common.disciplines.embedded.title": "Embedded/Firmware",
    "common.quotingHelper.workbench.material": "Material",
    "common.quotingHelper.packet.sla": "SLA: {date}",
    "common.status._label": "Status",
    "common.status.completed": "Abgeschlossen",
    "common.status.picked": "Kommissioniert",
    "common.status.packed": "Verpackt",
    "common.status.shipped": "Versendet",
    "common.status.delivered": "Geliefert",
    "common.status.inProgress": "In Bearbeitung",
    "common.status.pending": "Ausstehend",
    "common.status._value": "Status",
    "common.name": "Name",
    "common.user": "Benutzer",
    "common.priority.normal": "Normal",
    "common.protocol": "Protokoll",
    "common.optional": "Optional",
    "common.board": "Board",
    "common.dashboard": "Dashboard",
    "common.trend": "Trend",
    "common.version": "Version",

    # Navigation
    "navigation.dashboard": "Dashboard",
    "navigation.dashboards": "Dashboards",
    "navigation.pipeline": "Pipeline",
    "navigation.obeya": "Obeya",
    "navigation.andon": "Andon",

    # Layout/System
    "layout.systemInitialization": "SYSTEM_INITIALISIERUNG...",
    "layout.bootProtocol": "PROTOKOLL: SENSEI_OS_V3 // BOOT_SEQUENZ",
    "layout.systemMetadata.station": "STATION: {station}",
    "layout.systemMetadata.osVer": "OS_VER: {version}",
    "layout.systemMetadata.integrity": "INTEGRITÄT: {state}",
    "layout.systemMetadata.latency": "LATENZ: {latency}",

    # Settings
    "settings.shell.toastTitle": "Einstellungen synchronisiert",
    "settings.shell.toastDescription": "Zielparameter {title} im Register aktualisiert.",
    "settings.shell.synchronizing": "SYNCHRONISIERUNG...",
    "settings.shell.saveConfiguration": "KONFIGURATION_SPEICHERN",
    "settings.profile.avatar": "Avatar",
    "settings.profile.timezones.africaCasablanca": "(GMT+0) Casablanca",
    "settings.profile.timezones.europeParis": "(GMT+1) Paris",
    "settings.profile.timezones.europeLondon": "(GMT+0) London",
    "settings.profile.timezones.americaNewYork": "(GMT-5) New York",
    "settings.profile.timezones.americaLosAngeles": "(GMT-8) Los Angeles",
    "settings.roleInsights.table.insightHeader": "Einblick",
    "settings.roleInsights.tooltip.level": "Stufe: {level}",
    "settings.roleInsights.roleCard.levelBadge": "Stufe {level}",
    "settings.roleInsights.audit.headers.insight": "Einblick",
    "settings.roleInsights.roles.admin.name": "Administrator",
    "settings.roleInsights.roles.auditor.name": "Auditor",
    "settings.appearance.senseiOrange": "Sensei Orange",
    "settings.system": "System",
    "settings.integrations.items.powerbi.name": "PowerBI Intelligence",
    "settings.integrations.items.slack.name": "Slack Integration",
    "settings.team._value": "Team",
    "settings.team.roles.admin": "Admin",
    "settings.team.roles.manager": "Manager",
    "settings.team.departments.management": "Management",
    "settings.webhooks": "Webhooks",
    "settings.sites.station": "STATION: GLOBAL-OPS-01",
    "settings.company.defaults.legalEntityIdentity": "Sensei Manufacturing Solutions",
    
    # Errors
    "errors.boundaryFallback": "Etwas ist schief gelaufen. Bitte aktualisieren oder erneut versuchen.",

    # Modules - Sales
    "modules.sales.leads": "Leads",
    "modules.sales.pipeline": "Pipeline",
    
    # Modules - Production
    "modules.production.detail.aggregationPulse": "Aggregations-Puls",
    "modules.production.detail.escalateAnomaly": "Anomalie eskalieren",
    "modules.production.detail.executionVelocity": "Ausführungsgeschwindigkeit",
    "modules.production.detail.exportSpec": "Spezifikation exportieren",
    "modules.production.detail.gateVerified": "Gate verifiziert",
    "modules.production.detail.initiateExecution": "Ausführung initiieren",
    "modules.production.detail.node": "Knoten",
    "modules.production.detail.scrapDeviation": "Ausschussabweichung",
    "modules.production.detail.suspendProtocol": "Protokoll aussetzen",
    "modules.production.detail.tabs.history": "Historie",
    "modules.production.detail.tabs.operations": "Operationen",
    "modules.production.detail.tabs.quality": "Qualität",
    "modules.production.detail.targetMagnitude": "Zielgröße",
    "modules.production.detail.unknownProduct": "Unbekanntes Produkt",
    "modules.production.detail.viewHistory": "Historie anzeigen",
    "modules.production.detail.loadingBom": "Stücklisten-Protokollknoten abrufen...",
    "modules.production.detail.temporalSchedule": "Zeitplan",
    "modules.production.detail.startHorizon": "Start-Horizont",
    "modules.production.detail.targetTerminal": "Ziel-Terminal",
    "modules.production.detail.standardLeadTime": "Standard-Vorlaufzeit",
    "modules.production.detail.days": "TAGE",
    "modules.production.detail.station": "STATION",

    # Modules - Quality NCR
    "modules.quality.ncr.detail.assignCapa": "CAPA zuweisen",
    "modules.quality.ncr.detail.comment": "Kommentar",
    "modules.quality.ncr.detail.discrepancyIntelligence": "Abweichungs-Intelligenz",
    "modules.quality.ncr.detail.investigationProtocol": "Untersuchungsprotokoll",
    "modules.quality.ncr.detail.noDescription": "Keine Beschreibung",
    "modules.quality.ncr.detail.refineProtocol": "Protokoll verfeinern",
    "modules.quality.ncr.detail.subjectiveData": "Subjektive Daten",
    "modules.quality.ncr.detail.subtitle": "Untertitel",
    "modules.quality.ncr.detail.tabs.disposition": "Disposition",
    "modules.quality.ncr.detail.tabs.eventLog": "Ereignisprotokoll",
    "modules.quality.ncr.detail.tabs.evidence": "Beweise",
    "modules.quality.ncr.detail.tabs.rootCause": "Ursachenanalyse",
    "modules.quality.ncr.detail.terminateNode": "Knoten beenden",
    "modules.quality.ncr.detail.viewLogs": "Protokolle anzeigen",
    "modules.quality.ncr.new.validationError": "Validierungsfehler",
    "modules.quality.ncr.new.titleDescRequired": "Titel und Beschreibung sind erforderlich.",
    "modules.quality.ncr.new.ncrCreated": "NCR erstellt",
    "modules.quality.ncr.new.recordedSuccess": "NCR wurde erfolgreich aufgezeichnet.",
    "modules.quality.ncr.new.createFailed": "Fehler beim Erstellen der NCR",
    "modules.quality.ncr.new.placeholders.title": "z. B. Maßabweichung in Halterungslöchern",
    "modules.quality.ncr.new.placeholders.location": "z. B. Montagelinie 2",
    "modules.quality.ncr.new.placeholders.description": "Geben Sie detaillierte Beweise bezüglich des Abweichungsprotokolls an...",

    # Modules - Quality CAPA
    "modules.quality.capa.new.capaCreated": "CAPA erstellt",
    "modules.quality.capa.new.createFailed": "Erstellung fehlgeschlagen",
    "modules.quality.capa.new.initiatedSuccess": "Erfolgreich initiiert",
    "modules.quality.capa.detail.addNode": "Knoten hinzufügen",
    "modules.quality.capa.detail.commitAction": "Aktion festschreiben",
    "modules.quality.capa.detail.countermeasureNodes": "Gegenmaßnahme-Knoten",
    "modules.quality.capa.detail.exportProtocol": "Protokoll exportieren",
    "modules.quality.capa.detail.implementationMagnitude": "Implementierungsgröße",
    "modules.quality.capa.detail.problemStatement": "Problemstellung",
    "modules.quality.capa.detail.refineCapa": "CAPA verfeinern",
    "modules.quality.capa.detail.rootCauseAnalysis": "Ursachenanalyse",
    "modules.quality.capa.detail.subtitle": "Untertitel",
    "modules.quality.capa.detail.syncPulse": "Sync-Puls",
    "modules.quality.capa.detail.tabs.actionProtocol": "Aktionsprotokoll",
    "modules.quality.capa.detail.tabs.effectivenessSync": "Wirksamkeits-Sync",
    "modules.quality.capa.detail.tabs.relatedAnomalies": "Verwandte Anomalien",
    "modules.quality.capa.detail.terminateNode": "Knoten beenden",
    "modules.quality.capa.detail.verifyEffectiveness": "Wirksamkeit überprüfen",
    "modules.quality.audit": "Audit",

    # Modules - Quality Inspection
    "modules.quality.inspection.detail.assignmentTelemetry": "Zuweisungs-Telemetrie",
    "modules.quality.inspection.detail.checklist": "Checkliste",
    "modules.quality.inspection.detail.commitSync": "Übermittlungs-Sync",
    "modules.quality.inspection.detail.inspectionIntelligence": "Inspektions-Intelligenz",
    "modules.quality.inspection.detail.leadInspector": "Leitender Inspektor",
    "modules.quality.inspection.detail.printEvidence": "Beweise drucken",
    "modules.quality.inspection.detail.resultsAnalytics": "Ergebnis-Analyse",
    "modules.quality.inspection.detail.scheduledSync": "Geplanter Sync",
    "modules.quality.inspection.new.inspectionStarted": "Inspektion gestartet",
    "modules.quality.inspection.new.initializedSuccess": "Neuer Inspektionsdatensatz wurde initialisiert.",
    "modules.quality.inspection.new.createFailed": "Fehler beim Erstellen der Inspektion.",
    "modules.quality.inspection.new.associatedWoSync": "Zugehöriger Arbeitsauftrags-Sync",
    "modules.quality.inspection.new.initialObservation": "Erste Beobachtungsdaten",
    "modules.quality.inspection.new.placeholders.protocolIdentity": "z. B. Endkontrollprotokoll - BRK-2024",
    "modules.quality.inspection.new.placeholders.notes": "Erste Ergebnisse und Kontextdaten einbeziehen...",

    # Maintenance
    "modules.maintenance.mttr": "MTTR",
    "modules.maintenance.mtbf": "MTBF",

    # Finance
    "modules.finance.budgets": "Budgets",

    # Modules - Products
    "modules.products.title": "Produktkatalog",
    "modules.products.subtitle": "Produkte, Stücklisten und Arbeitspläne verwalten",
    "modules.products.station": "PRODUKTE",
    "modules.products.stats.activeProducts": "Aktive Produkte",
    "modules.products.stats.bomsDefined": "Definierte Stücklisten",
    "modules.products.stats.routingsActive": "Aktive Arbeitspläne",
    "modules.products.stats.avgLeadTime": "Durchschnittl. Vorlaufzeit",
    "modules.products.stats.activeInventoryNodes": "Aktive Bestände",
    "modules.products.stats.aggregatedRevenue": "Gesamteinnahmen",
    "modules.products.stats.meanMarginKPI": "Durchschnittliche Marge",
    "modules.products.stats.stockAbnormalities": "Bestandsanomalien",
    "modules.products.actions.newProduct": "Neues Produkt",
    "modules.products.tabs.products": "Produkte",
    "modules.products.tabs.boms": "Stücklisten",
    "modules.products.tabs.routings": "Arbeitspläne",
    "modules.products.details.overview": "Übersicht",
    "modules.products.details.specifications": "Spezifikationen",
    "modules.products.details.bom": "Stückliste",
    "modules.products.details.routing": "Arbeitsplan",
    "modules.products.details.inventory": "Inventar",
    "modules.products.details.history": "Historie",
    "modules.products.status.discontinued": "Eingestellt",
    "modules.products.viewBom": "Stückliste anzeigen",
    "modules.products.viewAnalytics": "Analyse anzeigen",
    "modules.products.stockLevel": "Lagerbestand",
    "modules.products.allStock": "Gesamtbestand",
    "modules.products.lowStock": "Niedriger Bestand",
    "modules.products.outOfStock": "Nicht vorrätig",
    "modules.products.table.product": "Produkt",
    "modules.products.table.standardCost": "Standardkosten",
    "modules.products.table.listPrice": "Listenpreis",
    "modules.products.table.margin": "Marge",
    "modules.products.table.inventory": "Inventar",
    "modules.products.table.leadTime": "Vorlaufzeit",
    "modules.products.table.totalSold": "Gesamt Verkauft",
    "modules.products.emptyState.description": "Beginnen Sie, indem Sie Ihr erstes Produkt zum Katalog hinzufügen.",
    "modules.products.emptyState.title": "Keine Produkte gefunden",
    "modules.products.exportIntel": "Katalog exportieren",
    "modules.products.import": "Importieren",
    "modules.products.initializeNode": "Produkt erstellen",
    "modules.products.new.requiredParams": "Erforderliche Parameter fehlen",
    "modules.products.new.providePartAndName": "Bitte geben Sie mindestens eine Teilenummer und einen Namen für den Knoten an.",
    "modules.products.new.nodeSynchronized": "Knoten synchronisiert",
    "modules.products.new.establishedSuccess": "{name} wurde erfolgreich im Katalog eingerichtet.",
    "modules.products.new.syncFailed": "Synchronisierung fehlgeschlagen",
    "modules.products.new.failedToEstablish": "Fehler beim Einrichten des Produktknotens im Register.",
    "modules.products.new.placeholders.description": "Kurze Beschreibung des Produkts oder der Komponentenspezifikationen...",
    "modules.products.detail.meta": "Meta",

    # Pages - Analytics
    "pages.analytics.systemHealth.status": "Status",
    "pages.analytics.models.recall": "Abruf",
    "pages.analytics.statusOptimal": "OPTIMAL",

    # Pages - Auditor
    "pages.auditor.station": "STATION: AUDIT-01",
    "pages.auditor.tabs.dashboard": "Dashboard",
    "pages.auditor.tabs.audits": "Audits",
    "pages.auditor.optimal": "Optimal",

    # Pages - Executive
    "pages.executive.tabs.northStar": "NORDSTERN",
    "pages.executive.tabs.sqdcp": "SQDCP",
    "pages.executive.tabs.senseiAi": "SENSEI_AI",
    "pages.executive.tabs.riskPrediction": "RISIKOVORHERSAGE",
    "pages.executive.loading": "Wird geladen...",
    "pages.executive.kpi.qualityScore": "Qualitätsfaktor",
    "pages.executive.kpi.deliveryScore": "Lieferfaktor",
    "pages.executive.kpi.costEfficiency": "Kosteneffizienz",
    "pages.executive.kpi.workforce": "Belegschaft",
    "pages.executive.kpi.overallScore": "Gesamtwertung",
    "pages.executive.kpi.belowTarget": "Unter Ziel",
    "pages.executive.kpi.awaitingData": "Warte auf Daten",
    "pages.executive.station": "Station",
    "pages.executive.ops.activeUsers": "Aktive Benutzer",
    "pages.executive.ops.openWorkOrders": "Offene Arbeitsaufträge",
    "pages.executive.ops.productionEfficiency": "Produktionseffizienz",
    "pages.executive.ops.pendingApprovals": "Ausstehende Genehmigungen",
    "pages.executive.sqdcp.safety": "Sicherheit",
    "pages.executive.sqdcp.quality": "Qualität",
    "pages.executive.sqdcp.delivery": "Lieferung",
    "pages.executive.sqdcp.cost": "Kosten",
    "pages.executive.sqdcp.people": "Mitarbeiter",

    # Pages - Finance (Fixing weird spanish/mixed errors if any)
    "pages.finance.sections.delete": "Knoten löschen",
    "pages.finance.sections.edit": "Parameter bearbeiten",
    "pages.finance.sections.view": "Spezifikation anzeigen",
    "pages.finance.tabs.budgets": "Budgets",
    "pages.finance.ledger.code": "Code",
    "pages.finance.tax.code": "Code",
    "pages.finance.tax.name": "Name",
    "pages.finance.tax.region": "Region",
    "pages.finance.kpi.alpha": "Alpha",
    "pages.finance.kpi.delta": "Delta",
    "pages.finance.kpi.opex": "Opex",
    "pages.finance.station": "Station",

    # Pages - HR
    "pages.hr.unassignedRole": "Nicht zugewiesene Rolle",
    "pages.hr.noDepartment": "Keine Abt.",
    "pages.hr.remote": "Remote",
    "pages.hr.unknownPosition": "Unbekannte Position",
    "pages.hr.candidateDetails": "Kandidatendetails",
    "pages.hr.searchPersonnel": "Personal suchen...",
    "pages.hr.searchJobs": "Stellen suchen...",
    "pages.hr.toast.employeeCreated": "Mitarbeiter erfolgreich erstellt",
    "pages.hr.toast.employeeCreatedTitle": "Erfolg",
    "pages.hr.toast.employeeTerminated": "Mitarbeiterakte beendet",
    "pages.hr.toast.jobCreated": "Stellenanzeige erstellt",
    "pages.hr.toast.jobDeleted": "Stellenanzeige gelöscht",
    "pages.hr.toast.deletionFailed": "Löschen fehlgeschlagen",
    "pages.hr.toast.applicationSubmitted": "Bewerbung eingereicht",
    "pages.hr.toast.applicationMoved": "Bewerbung verschoben nach {status}",
    "pages.hr.toast.updateStatusFailed": "Statusaktualisierung fehlgeschlagen",
    "pages.hr.toast.leaveSubmitted": "Urlaubsantrag eingereicht",
    "pages.hr.toast.leaveApproved": "Urlaubsantrag genehmigt",
    "pages.hr.toast.leaveApproveFailed": "Genehmigung fehlgeschlagen",
    "pages.hr.toast.leaveRejected": "Urlaubsantrag abgelehnt",
    "pages.hr.toast.leaveRejectFailed": "Ablehnung fehlgeschlagen",
    "pages.hr.confirmTerminate.title": "Mitarbeiterakte beenden",
    "pages.hr.confirmTerminate.description": "Sind Sie sicher, dass Sie diese Mitarbeiterakte beenden wollen? Dies kann nicht rückgängig gemacht werden.",
    "pages.hr.confirmDeleteJob.title": "Stellenanzeige löschen",
    "pages.hr.confirmDeleteJob.description": "Sind Sie sicher, dass Sie diese Stellenanzeige löschen möchten?",
    "pages.hr.placeholders.selectRegion": "Region auswählen",
    "pages.hr.placeholders.selectStatus": "Status auswählen",
    "pages.hr.placeholders.jobDescription": "Stellenbeschreibung...",
    "pages.hr.placeholders.requiredSkills": "Erforderliche Fähigkeiten...",
    "pages.hr.placeholders.selectPosition": "Position auswählen",
    "pages.hr.placeholders.additionalNotes": "Zusätzliche Notizen...",
    "pages.hr.placeholders.selectEmployee": "Mitarbeiter auswählen",
    "pages.hr.placeholders.leaveReason": "Grund für Abwesenheit...",

    # Pages - IT
    "pages.it.sections.tickets": "Tickets",

    # Pages - Today
    "pages.today.subtitle": "Intelligence Command Center",
    "pages.today.stationStatus": "STATION_STATUS: OPTIMAL",
    "pages.today.severity.info": "Info",
    "pages.today.handover.station": "Station {id}",
    "pages.today.lsw.title": "Leader Standard Work",

    # Pages - Warehouse
    "pages.tasks.status.backlog": "Rückstand",
    "pages.warehouse.loading": "Lade Lagerdaten...",
    "pages.warehouse.searchDescription": "Gesamtes Lagerinventar suchen und verwalten",
    "pages.warehouse.searchPlaceholder": "Artikel suchen...",
    "pages.warehouse.itemName": "Artikelname",
    "pages.warehouse.onHand": "Vorrätig",
    "pages.warehouse.managePO": "Bestellungen und Wareneingänge verwalten",
    "pages.warehouse.poReference": "Bestell-Ref",
    "pages.warehouse.expectedDate": "Erwartetes Datum",
    "pages.warehouse.inTransit": "Auf dem Transportweg",
    "pages.warehouse.manageShipments": "Sendungen und Lieferlogistik verwalten",
    "pages.warehouse.shipDate": "Versanddatum",
    "pages.warehouse.activePickLists": "Aktive kommissionierlisten",
    "pages.warehouse.itemsPicked": "Artikel kommissioniert",

    # Pages - Pipeline
    "pages.pipeline.views.kanban": "Kanban",
    "pages.pipeline.views.board": "Board",
    "pages.pipeline.tableHeaders.triageScore": "Triage-Score",
    "pages.pipeline.tableHeaders.completeness": "Vollständigkeit",
    "pages.pipeline.new.placeholders.itemDescription": "Artikelbeschreibung...",

    # Pages - Customers
    "pages.customers.labels.rfqs": "Anfragen (RFQs)",
    "pages.customers.metrics.rfqs": "Anfragen (RFQs)",
    "pages.customers.detail.stats.pipelineMagnitude": "Pipeline-Größe",
    "pages.customers.detail.website": "Webseite",
    "pages.customers.new.status": "Status",
    "pages.customers.new.website": "Webseite",
    "pages.customers.toast.deactivated": "Kunde deaktiviert",

    # Quotes
    "pages.quotes.new.materialCost": "Materialkosten",
    "pages.quotes.new.laborCost": "Arbeitskosten",
    "pages.quotes.new.overheadCost": "Gemeinkosten",
    "pages.quotes.new.lineItemNotes": "Positionsnotizen",
    "pages.quotes.new.noAssumptions": "Keine Annahmen definiert",
    "pages.quotes.new.newQuote": "Neues Angebot",
    "pages.quotes.new.viewVersionHistory": "Versionsverlauf anzeigen",
    "pages.quotes.new.addProductsPricing": "Produkte und Preise hinzufügen",
    "pages.quotes.new.toggleCostBreakdown": "Detaillierte Kostenaufschlüsselung umschalten",
    "pages.quotes.new.unitPrice": "Einzelpreis",
    "pages.quotes.new.internalCostingAnalysis": "Interne Kostenanalyse",
    "pages.quotes.new.totalRevenue": "Gesamtumsatz",
    "pages.quotes.new.grossProfit": "Bruttogewinn",
    "pages.quotes.new.quickActions": "Schnellaktionen",
    "pages.quotes.new.assumptionsVerified": "Annahmen verifiziert",
    "pages.quotes.new.warningsPresent": "Warnungen vorhanden",
    "pages.quotes.table.version": "Version",
    "pages.quotes.toast.savedDraft": "Angebot als Entwurf gespeichert",
    "pages.quotes.toast.submitted": "Angebot zur Genehmigung eingereicht",
    "pages.quotes.toast.saveFailed": "Fehler beim Speichern des Angebots",
    "pages.quotes.toast.tryAgain": "Bitte versuchen Sie es erneut.",

    # Sales
    "pages.sales.table.status": "Status",
    "pages.sales.noBid": "Kein Angebot",
    "pages.sales.statusReviewing": "Prüfung",
    "pages.sales.statusQuoting": "Angebotserstellung",
    "pages.sales.statusSubmitted": "Eingereicht",
    "pages.sales.totalRfqs": "Gesamt Anfragen",
    "pages.sales.avgResponseTime": "Ø Antwortzeit",
    "pages.sales.conversionRate": "Konversionsrate",
    "pages.sales.dueDate": "Fälligkeitsdatum",
    "pages.sales.receivedDate": "Empfangsdatum",
    "pages.sales.searchRfqs": "Anfragen suchen...",

    # Production
    "pages.production.views.kanban": "Kanban",
    "pages.production.views.gantt": "Gantt",
    "pages.production.table.operator": "Operator",

    # Quality
    "pages.quality.tabs.ncrs": "NCRs",
    "pages.quality.tabs.capas": "CAPAs",
    "pages.quality.status.disposition": "Disposition",
    "pages.quality.status.capa": "CAPA",
    "pages.quality.msa.design": "Design",
    "pages.quality.msa.grrPercent": "GRR %",

    # Maintenance
    "pages.maintenance.tabs.budget": "Budget",
    "pages.maintenance.tabs.loto": "Loto",
    "pages.maintenance.table.budget": "Budget",

    # Andon
    "pages.andon.tabs.live": "Live",
    "pages.andon.toast.settingsSaved": "Signalbenachrichtigungs-Einstellungen wurden aktualisiert.",

    # Purchase
    "pages.purchase.requisitionNew.station": "STATION: REQ-EINGABE-01",
    "pages.purchase.requisitionNew.priorityLayer": "Prioritätsebene",

    # Settings Profile
    "pages.settings.profile.sections.avatar": "Avatar",

    # Obeya
    "pages.obeya.sections.hoshinKanri": "Hoshin Kanri",
    "pages.obeya.toast.loadFailed": "Laden der Obeya-Daten fehlgeschlagen",
    "pages.obeya.toast.itemDeleted": "Element erfolgreich gelöscht",
    "pages.obeya.toast.deleteFailed": "Fehler beim Löschen des Elements",
    "pages.obeya.toast.commentAdded": "Kommentar hinzugefügt",
    "pages.obeya.toast.commentFailed": "Fehler beim Hinzufügen des Kommentars",
    "pages.obeya.toast.statusUpdated": "Status aktualisiert",
    "pages.obeya.toast.statusFailed": "Fehler beim Aktualisieren des Status",
    "pages.obeya.toast.created": "Obeya Board erstellt",
    "pages.obeya.toast.createdDesc": "Ihr neues digitales Obeya-Board wurde erfolgreich initialisiert.",

    # A3
    "pages.a3.toast.titleRequired": "Bitte geben Sie einen Titel für den A3-Bericht ein.",
    "pages.a3.toast.created": "A3-Bericht erstellt",
    "pages.a3.toast.createdDesc": "Der neue A3-Bericht wurde erfolgreich initialisiert.",
    "pages.a3.toast.createFailed": "Fehler beim Erstellen des A3-Berichts.",
    "pages.a3.toast.loadFailed": "Laden der A3-Details fehlgeschlagen",
    "pages.a3.toast.export": "Exportieren",
    "pages.a3.toast.exportDesc": "Starte PDF-Export...",
    "pages.a3.toast.updated": "A3-Bericht aktualisiert",
    "pages.a3.toast.updatedDesc": "Änderungen wurden erfolgreich gespeichert.",
    "pages.a3.toast.updateFailed": "Fehler beim Aktualisieren des A3-Berichts.",

    # CTQ
    "pages.ctq.toast.error": "Fehler",
    "pages.ctq.toast.loadFailed": "Laden der CTQ-Details fehlgeschlagen",
    "pages.ctq.toast.success": "Erfolg",
}

def set_nested_value(data, dotted_key, value):
    """
    Sets a value in a nested dictionary using a dotted key.
    Creates intermediate dictionaries if they don't exist.
    """
    keys = dotted_key.split('.')
    current = data
    for i, key in enumerate(keys[:-1]):
        if key not in current:
            # If we need to create a path, we can matches the existing structure 
            # or creates a new dict. Here we assume structure mostly exists 
            # or matches the translation file intent.
            current[key] = {}
        
        # If the key exists but is a string (leaf) instead of a dict, 
        # and we need to go deeper, we have a conflict.
        # But usually i18n keys are consistent.
        if not isinstance(current[key], dict):
             # This might happen if a key was a leaf node and is now a parent.
             # In i18n it's rare to change structure like that without migration.
             # We'll skip or warn.
             print(f"Warning: Key '{key}' in path '{dotted_key}' is not a dictionary. Skipping.")
             return False
        
        current = current[key]
    
    last_key = keys[-1]
    current[last_key] = value
    return True

def main():
    file_path = "frontend/src/locales/de.json"
    
    # 1. Load existing German locale
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            return

    # 2. Apply translations
    updated_count = 0
    for key, value in TRANSLATIONS.items():
        if set_nested_value(data, key, value):
            updated_count += 1
            # print(f"Updated: {key} -> {value}")

    # 3. Save the file
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"Successfully updated {updated_count} keys in {file_path}.")

if __name__ == "__main__":
    main()
