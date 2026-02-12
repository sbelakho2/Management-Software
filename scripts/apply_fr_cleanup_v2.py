import json
import os

# 1. PATH-BASED dictionary
TRANSLATIONS = {
    # Common
    "common.source": "Source",
    "common.tests.xray": "Rayons X",
    "common.quotingHelper.workbench.variance": "Écart",
    "common.quotingHelper.packet.sla": "SLA : {date}",
    "common.status.completed": "Terminé",
    "common.status.picked": "Prélevé",
    "common.status.packed": "Emballé",
    "common.status.shipped": "Expédié",
    "common.status.delivered": "Livré",
    "common.status.inProgress": "En cours",
    "common.status.pending": "En attente",
    "common.date": "Date",
    "common.user": "Utilisateur",
    "common.description": "Description",
    "common.type": "Type",
    "common.protocol": "Protocole",
    "common.total": "Total",
    "common.expert": "Expert",
    "common.received": "Reçu",
    "common.version": "Version",
    "common.private": "Privé",
    "common.public": "Public",

    # Navigation
    "navigation.pipeline": "Pipeline",
    "navigation.production": "Production",
    "navigation.obeya": "Obeya",
    "navigation.exceptions": "Exceptions",
    "navigation.andon": "Andon",
    "navigation.maintenance": "Maintenance",
    "navigation.finance": "Finance",
    "navigation.notifications": "Notifications",
    "navigation.menu": "Menu",

    # Layout
    "layout.systemInitialization": "INITIALISATION_SYSTÈME...",
    "layout.bootProtocol": "PROTOCOLE : SENSEI_OS_V3 // SÉQUENCE_DÉMARRAGE",
    "layout.systemMetadata.station": "STATION : {station}",
    "layout.systemMetadata.osVer": "VER_OS : {version}",
    "layout.systemMetadata.integrity": "INTÉGRITÉ : {state}",
    "layout.systemMetadata.latency": "LATENCE : {latency}",

    # Email Drafting
    "emailDrafting.purpose.introduction": "Introduction",
    "emailDrafting.tone.urgent": "Urgent",
    "emailDrafting.suggestions.title": "Suggestions ({count})",
    "emailDrafting.defaults.companyName": "Sensei",
    "emailDrafting.drafts.snippet": "{snippet}...",

    # Settings
    "settings.shell.toastTitle": "Paramètres synchronisés",
    "settings.shell.toastDescription": "Paramètres cibles {title} mis à jour dans le registre.",
    "settings.shell.synchronizing": "SYNCHRONISATION...",
    "settings.shell.saveConfiguration": "ENREGISTRER_CONFIGURATION",
    "settings.profile.avatar": "Avatar",
    "settings.profile.timezones.africaCasablanca": "(GMT+0) Casablanca",
    "settings.profile.timezones.europeParis": "(GMT+1) Paris",
    "settings.profile.timezones.americaNewYork": "(GMT-5) New York",
    "settings.profile.timezones.americaLosAngeles": "(GMT-8) Los Angeles",
    "settings.profile.departments.production": "Production",
    "settings.profile.departments.finance": "Finance",
    "settings.notifications.title": "Notifications",
    "settings.roleInsights.table.insightHeader": "Aperçu",
    "settings.roleInsights.audit.headers.action": "Action",
    "settings.roleInsights.audit.headers.insight": "Aperçu",
    "settings.roleInsights.roles.finance.name": "Finance",
    "settings.roleInsights.roles.maintenance.name": "Maintenance",
    "settings.appearance.fontSizeSmallDesc": "Base 14px",
    "settings.appearance.fontSizeLargeDesc": "Base 18px",
    "settings.appearance.compact": "Compact",
    "settings.appearance.preview.title": "Module Intelligence 04",
    "settings.appearance.preview.subtitle": "Flux opérationnel en direct synchronisé",
    "settings.team.roles.admin": "Admin",
    "settings.team.roles.manager": "Manager",
    "settings.team.departments.production": "Production",
    "settings.permissions": "Permissions",
    "settings.webhooks": "Webhooks",
    "settings.company.defaults.legalEntityIdentity": "Sensei Manufacturing Solutions",
    "settings.company.defaults.taxIdVat": "MA-123456789",
    "settings.email.defaults.relayReplyTo": "no-reply@sensei-manuf.com",
    "settings.email.smtpStatus": "RELAIS_SMTP : SYNCHRONISÉ",
    "settings.email.smtpDetails": "Hôte : mail.sensei-infra.com // Port : 587 (TLS)",
    
    # Errors
    "errors.boundaryFallback": "Une erreur s'est produite. Veuillez actualiser ou réessayer.",
    
    # Time
    "time.minute": "minute",
    
    # Tables
    "tables.page": "Page",
    
    # Notifications
    "notifications.title": "Notifications",

    # Modules - Production
    "modules.production.title": "Production",
    "modules.production.detail.documentation": "Documentation",
    "modules.production.detail.aggregationPulse": "Impulsion d'agrégation",
    "modules.production.detail.escalateAnomaly": "Escalader anomalie",
    "modules.production.detail.executionVelocity": "Vitesse d'exécution",
    "modules.production.detail.exportSpec": "Exporter spécification",
    "modules.production.detail.gateVerified": "Porte vérifiée",
    "modules.production.detail.initiateExecution": "Initier exécution",
    "modules.production.detail.node": "Nœud",
    "modules.production.detail.scrapDeviation": "Écart de rebut",
    "modules.production.detail.suspendProtocol": "Suspendre protocole",
    "modules.production.detail.tabs.history": "Historique",
    "modules.production.detail.tabs.operations": "Opérations",
    "modules.production.detail.tabs.quality": "Qualité",
    "modules.production.detail.targetMagnitude": "Magnitude cible",
    "modules.production.detail.unknownProduct": "Produit inconnu",
    "modules.production.detail.viewHistory": "Voir historique",
    "modules.production.detail.loadingBom": "Récupération des nœuds du protocole de nomenclature...",
    "modules.production.detail.temporalSchedule": "Calendrier temporel",
    "modules.production.detail.startHorizon": "Horizon de début",
    "modules.production.detail.targetTerminal": "Terminal cible",
    "modules.production.detail.standardLeadTime": "Délai standard",
    "modules.production.detail.days": "JOURS",
    "modules.production.detail.station": "STATION",

    # Modules - Sales
    "modules.sales.pipeline": "Pipeline",
    "modules.sales.quota": "Quota",

    # Modules - Quality
    "modules.quality.title": "Qualité",
    "modules.quality.inspections": "Inspections",
    "modules.quality.ncr.detail.assignCapa": "Assigner CAPA",
    "modules.quality.ncr.detail.comment": "Commentaire",
    "modules.quality.ncr.detail.discrepancyIntelligence": "Intelligence des divergences",
    "modules.quality.ncr.detail.investigationProtocol": "Protocole d'investigation",
    "modules.quality.ncr.detail.noDescription": "Pas de description",
    "modules.quality.ncr.detail.refineProtocol": "Affiner protocole",
    "modules.quality.ncr.detail.subjectiveData": "Données subjectives",
    "modules.quality.ncr.detail.subtitle": "Sous-titre",
    "modules.quality.ncr.detail.tabs.disposition": "Disposition",
    "modules.quality.ncr.detail.tabs.eventLog": "Journal des événements",
    "modules.quality.ncr.detail.tabs.evidence": "Preuve",
    "modules.quality.ncr.detail.tabs.rootCause": "Cause racine",
    "modules.quality.ncr.detail.terminateNode": "Terminer nœud",
    "modules.quality.ncr.detail.viewLogs": "Voir journaux",
    "modules.quality.ncr.new.validationError": "Erreur de validation",
    "modules.quality.ncr.new.titleDescRequired": "Le titre et la description sont requis.",
    "modules.quality.ncr.new.ncrCreated": "NCR Créée",
    "modules.quality.ncr.new.recordedSuccess": "NCR enregistrée avec succès.",
    "modules.quality.ncr.new.createFailed": "Échec de création NCR",
    "modules.quality.ncr.new.placeholders.title": "ex: Écart dimensionnel dans les trous du support",
    "modules.quality.ncr.new.placeholders.location": "ex: Ligne d'assemblage 2",
    "modules.quality.ncr.new.placeholders.partNumber": "NUMÉRO_PIÈCE",
    "modules.quality.ncr.new.placeholders.woNumber": "NUMÉRO_OF",
    "modules.quality.ncr.new.placeholders.description": "Fournir des preuves détaillées concernant le protocole de divergence...",
    "modules.quality.capa.new.capaCreated": "CAPA Créée",
    "modules.quality.capa.new.createFailed": "Échec de création",
    "modules.quality.capa.new.initiatedSuccess": "Initié avec succès",
    "modules.quality.capa.detail.addNode": "Ajouter nœud",
    "modules.quality.capa.detail.commitAction": "Valider action",
    "modules.quality.capa.detail.countermeasureNodes": "Nœuds de contre-mesure",
    "modules.quality.capa.detail.exportProtocol": "Exporter protocole",
    "modules.quality.capa.detail.implementationMagnitude": "Magnitude de mise en œuvre",
    "modules.quality.capa.detail.problemStatement": "Énoncé du problème",
    "modules.quality.capa.detail.refineCapa": "Affiner CAPA",
    "modules.quality.capa.detail.rootCauseAnalysis": "Analyse cause racine",
    "modules.quality.capa.detail.subtitle": "Sous-titre",
    "modules.quality.capa.detail.syncPulse": "Impulsion de synchro",
    "modules.quality.capa.detail.tabs.actionProtocol": "Protocole d'action",
    "modules.quality.capa.detail.tabs.effectivenessSync": "Synchro d'efficacité",
    "modules.quality.capa.detail.tabs.relatedAnomalies": "Anomalies liées",
    "modules.quality.capa.detail.terminateNode": "Terminer nœud",
    "modules.quality.capa.detail.verifyEffectiveness": "Vérifier efficacité",
    "modules.quality.certifications": "Certifications",
    "modules.quality.audit": "Audit",
    "modules.quality.inspection.detail.assignmentTelemetry": "Télémesure d'assignation",
    "modules.quality.inspection.detail.checklist": "Liste de contrôle",
    "modules.quality.inspection.detail.commitSync": "Valider synchro",
    "modules.quality.inspection.detail.inspectionIntelligence": "Intelligence d'inspection",
    "modules.quality.inspection.detail.leadInspector": "Inspecteur principal",
    "modules.quality.inspection.detail.printEvidence": "Imprimer preuve",
    "modules.quality.inspection.detail.resultsAnalytics": "Analytique des résultats",
    "modules.quality.inspection.detail.scheduledSync": "Synchro planifiée",
    "modules.quality.inspection.new.inspectionStarted": "Inspection commencée",
    "modules.quality.inspection.new.initializedSuccess": "Nouvel enregistrement d'inspection initialisé.",
    "modules.quality.inspection.new.createFailed": "Échec de création d'inspection.",
    "modules.quality.inspection.new.associatedWoSync": "Synchro OF associé",
    "modules.quality.inspection.new.initialObservation": "Intel observation initiale",
    "modules.quality.inspection.new.placeholders.protocolIdentity": "ex: Protocole d'inspection final - BRK-2024",
    "modules.quality.inspection.new.placeholders.operatorIdentity": "IDENTITÉ_OPÉRATIF",
    "modules.quality.inspection.new.placeholders.partNumber": "NUMÉRO_PIÈCE",
    "modules.quality.inspection.new.placeholders.woNumber": "NUMÉRO_OF",
    "modules.quality.inspection.new.placeholders.notes": "Intégrer les constatations initiales et données contextuelles...",

    # Modules - Inventory
    "modules.inventory.stock": "Stock",

    # Modules - Maintenance
    "modules.maintenance.title": "Maintenance",
    "modules.maintenance.corrective": "Correctif",
    "modules.maintenance.mttr": "MTTR",
    "modules.maintenance.mtbf": "MTBF",

    # Modules - HR
    "modules.hr.performance": "Performance",

    # Modules - Finance
    "modules.finance.title": "Finance",
    "modules.finance.budgets": "Budgets",

    # Modules - Products
    "modules.products.title": "Catalogue Produits",
    "modules.products.subtitle": "Gérer les produits, nomenclatures et gammes de fabrication",
    "modules.products.station": "PRODUITS",
    "modules.products.stats.activeProducts": "Produits actifs",
    "modules.products.stats.bomsDefined": "Nomenclatures définies",
    "modules.products.stats.routingsActive": "Gammes actives",
    "modules.products.stats.avgLeadTime": "Délai moyen",
    "modules.products.stats.activeInventoryNodes": "Produits actifs",
    "modules.products.stats.aggregatedRevenue": "Revenu total",
    "modules.products.stats.meanMarginKPI": "Marge moyenne",
    "modules.products.stats.stockAbnormalities": "Alertes stock bas",
    "modules.products.actions.newProduct": "Nouveau produit",
    "modules.products.tabs.products": "Produits",
    "modules.products.tabs.boms": "Nomenclatures",
    "modules.products.tabs.routings": "Gammes",
    "modules.products.details.overview": "Aperçu",
    "modules.products.details.specifications": "Spécifications",
    "modules.products.details.bom": "Nomenclature",
    "modules.products.details.routing": "Gamme",
    "modules.products.details.inventory": "Inventaire",
    "modules.products.details.history": "Historique",
    "modules.products.status.discontinued": "Discontinué",
    "modules.products.viewBom": "Voir Nomenclature",
    "modules.products.viewAnalytics": "Voir Analytique",
    "modules.products.stockLevel": "Niveau Stock",
    "modules.products.allStock": "Tout Stock",
    "modules.products.lowStock": "Stock Bas",
    "modules.products.outOfStock": "Rupture de Stock",
    "modules.products.table.product": "Produit",
    "modules.products.table.standardCost": "Coût Standard",
    "modules.products.table.listPrice": "Prix Liste",
    "modules.products.table.margin": "Marge",
    "modules.products.table.inventory": "Inventaire",
    "modules.products.table.leadTime": "Délai",
    "modules.products.table.totalSold": "Total Vendu",
    "modules.products.emptyState.description": "Commencez par ajouter votre premier produit au catalogue.",
    "modules.products.emptyState.title": "Aucun produit trouvé",
    "modules.products.exportIntel": "Exporter Catalogue",
    "modules.products.import": "Importer",
    "modules.products.initializeNode": "Créer Produit",
    "modules.products.new.requiredParams": "Paramètres requis manquants",
    "modules.products.new.providePartAndName": "Veuillez fournir au moins un numéro de pièce et un nom pour le nœud.",
    "modules.products.new.nodeSynchronized": "Nœud synchronisé",
    "modules.products.new.establishedSuccess": "{name} a été établi avec succès dans le catalogue.",
    "modules.products.new.syncFailed": "Échec synchronisation",
    "modules.products.new.failedToEstablish": "Échec de l'établissement du nœud produit dans le registre.",
    "modules.products.new.placeholders.nomenclature": "NOM_PRODUIT_STR",
    "modules.products.new.placeholders.description": "Brève description du produit ou spécifications des composants...",
    "modules.products.new.placeholders.uom": "CODE_ISO",
    "modules.products.new.placeholders.unitCost": "0.00",
    "modules.products.new.placeholders.minStock": "QTE_MIN",
    "modules.products.new.placeholders.maxStock": "QTE_MAX",
    "modules.products.new.placeholders.leadTime": "JOURS",
    "modules.products.new.placeholders.location": "ZONE-BAC-ÉTAGÈRE",
    "modules.products.new.placeholders.supplier": "ID_FOURNISSEUR",

    # Pages - Analytics
    "pages.analytics.mlInsights.impact": "Impact",
    "pages.analytics.models.intelligence": "Intelligence",
    "pages.analytics.statusOptimal": "OPTIMAL",

    # Pages - Auditor
    "pages.auditor.tabs.audits": "Audits",
    "pages.auditor.optimal": "Optimal",

    # Pages - Executive
    "pages.executive.tabs.finance": "Finance",
    "pages.executive.tabs.northStar": "ÉTOILE_NORD",
    "pages.executive.tabs.sqdcp": "SQDCP",
    "pages.executive.tabs.senseiAi": "SENSEI_AI",
    "pages.executive.tabs.riskPrediction": "PRÉDICTION_RISQUE",
    "pages.executive.loading": "Chargement...",
    "pages.executive.kpi.qualityScore": "Score Qualité",
    "pages.executive.kpi.deliveryScore": "Score Livraison",
    "pages.executive.kpi.costEfficiency": "Efficacité Coût",
    "pages.executive.kpi.workforce": "Main d'œuvre",
    "pages.executive.kpi.overallScore": "Score Global",
    "pages.executive.kpi.belowTarget": "Sous la cible",
    "pages.executive.kpi.awaitingData": "En attente de données",
    "pages.executive.station": "Station",
    "pages.executive.ops.activeUsers": "Utilisateurs Actifs",
    "pages.executive.ops.openWorkOrders": "OF Ouverts",
    "pages.executive.ops.productionEfficiency": "Efficacité Production",
    "pages.executive.ops.pendingApprovals": "Approbations En Attente",
    "pages.executive.sqdcp.safety": "Sécurité",
    "pages.executive.sqdcp.quality": "Qualité",
    "pages.executive.sqdcp.delivery": "Livraison",
    "pages.executive.sqdcp.cost": "Coût",
    "pages.executive.sqdcp.people": "Personnel",

    # Pages - Finance
    "pages.finance.sections.delete": "Supprimer le nœud",
    "pages.finance.sections.edit": "Modifier les paramètres",
    "pages.finance.sections.view": "Voir la spécification",
    "pages.finance.tabs.budgets": "Budgets",
    "pages.finance.costing.variance": "Écart",
    "pages.finance.ledger.balance": "Solde",
    "pages.finance.ledger.code": "Code",
    "pages.finance.ledger.type": "Type",
    "pages.finance.tax.code": "Code",
    "pages.finance.tax.taxable": "Imposable",
    "pages.finance.tax.type": "Type",
    "pages.finance.kpi.alpha": "Alpha",
    "pages.finance.kpi.delta": "Delta",
    "pages.finance.kpi.opex": "Opex",
    "pages.finance.station": "Station",

    # Pages - HR
    "pages.hr.sections.performance": "Performance",
    "pages.hr.tabs.performance": "Performance",
    "pages.hr.unassignedRole": "Rôle non assigné",
    "pages.hr.noDepartment": "Aucun Dép.",
    "pages.hr.remote": "Télétravail",
    "pages.hr.unknownPosition": "Poste inconnu",
    "pages.hr.candidateDetails": "Détails candidat",
    "pages.hr.searchPersonnel": "Rechercher personnel...",
    "pages.hr.searchJobs": "Rechercher emplois...",
    "pages.hr.toast.employeeCreated": "Employé créé avec succès",
    "pages.hr.toast.employeeCreatedTitle": "Succès",
    "pages.hr.toast.employeeTerminated": "Dossier employé terminé",
    "pages.hr.toast.jobCreated": "Offre d'emploi créée",
    "pages.hr.toast.jobDeleted": "Offre d'emploi supprimée",
    "pages.hr.toast.deletionFailed": "Échec de suppression",
    "pages.hr.toast.applicationSubmitted": "Candidature soumise",
    "pages.hr.toast.applicationMoved": "Candidature déplacée vers {status}",
    "pages.hr.toast.updateStatusFailed": "Échec mise à jour statut",
    "pages.hr.toast.leaveSubmitted": "Demande de congé soumise",
    "pages.hr.toast.leaveApproved": "Demande de congé approuvée",
    "pages.hr.toast.leaveApproveFailed": "Échec approbation congé",
    "pages.hr.toast.leaveRejected": "Demande de congé rejetée",
    "pages.hr.toast.leaveRejectFailed": "Échec rejet congé",
    "pages.hr.confirmTerminate.title": "Terminer dossier employé",
    "pages.hr.confirmTerminate.description": "Êtes-vous sûr de vouloir terminer ce dossier employé ? Cette action est irréversible.",
    "pages.hr.confirmDeleteJob.title": "Supprimer offre d'emploi",
    "pages.hr.confirmDeleteJob.description": "Êtes-vous sûr de vouloir supprimer cette offre d'emploi ?",
    "pages.hr.placeholders.email": "jean.dupont@entreprise.com",
    "pages.hr.placeholders.selectRegion": "Sélectionner région",
    "pages.hr.placeholders.selectStatus": "Sélectionner statut",
    "pages.hr.placeholders.jobDescription": "Description du poste...",
    "pages.hr.placeholders.requiredSkills": "Compétences requises...",
    "pages.hr.placeholders.selectPosition": "Sélectionner poste",
    "pages.hr.placeholders.firstName": "Jean",
    "pages.hr.placeholders.personalEmail": "jean.dupont@email.com",
    "pages.hr.placeholders.portfolioUrl": "https://...",
    "pages.hr.placeholders.additionalNotes": "Notes additionnelles...",
    "pages.hr.placeholders.selectEmployee": "Sélectionner employé",
    "pages.hr.placeholders.leaveReason": "Motif du congé...",

    # Pages - IT
    "pages.it.sections.infrastructure": "Infrastructure",
    "pages.it.sections.tickets": "Tickets",
    "pages.it.tabs.incidents": "Incidents",

    # Pages - Today
    "pages.today.severity.info": "Info",
    "pages.today.handover.station": "Station {id}",
    "pages.today.handover.note": "Note",
    "pages.today.handover.notes": "Notes",

    # Pages - Tasks
    "pages.tasks.status.backlog": "Backlog",

    # Pages - Warehouse
    "pages.warehouse.loading": "Chargement données entrepôt...",
    "pages.warehouse.searchDescription": "Rechercher et gérer tout l'inventaire entrepôt",
    "pages.warehouse.searchPlaceholder": "Rechercher articles...",
    "pages.warehouse.itemName": "Nom d'article",
    "pages.warehouse.onHand": "En main",
    "pages.warehouse.managePO": "Gérer réceptions de commandes et matériaux entrants",
    "pages.warehouse.poReference": "Réf. PO",
    "pages.warehouse.expectedDate": "Date prévue",
    "pages.warehouse.inTransit": "En transit",
    "pages.warehouse.manageShipments": "Gérer expéditions et logistique de livraison",
    "pages.warehouse.shipDate": "Date expédition",
    "pages.warehouse.activePickLists": "Listes de prélèvement actives et exécution des commandes",
    "pages.warehouse.itemsPicked": "articles prélevés",

    # Pages - Pipeline
    "pages.pipeline.views.kanban": "Kanban",
    "pages.pipeline.tableHeaders.triageScore": "Score de triage",
    "pages.pipeline.tableHeaders.completeness": "Complétude",
    "pages.pipeline.new.labels.detailedContext": "Description",
    "pages.pipeline.new.labels.specification": "Description",
    "pages.pipeline.new.labels.protocolNotes": "Notes",
    "pages.pipeline.new.priority.urgent": "Urgent",

    # Pages - Customers
    "pages.customers.status.prospect": "Prospect",
    "pages.customers.detail.contacts": "Contacts",
    "pages.customers.detail.notes": "Notes",
    "pages.customers.detail.stats.pipelineMagnitude": "Magnitude du pipeline",
    "pages.customers.filters.prospect": "Prospect",
    "pages.customers.new.contact": "Contact",
    "pages.customers.new.contacts": "Contacts",
    "pages.customers.viewModes.table": "Tableau",
    "pages.customers.toast.deactivated": "Client désactivé",

    # Pages - Quotes
    "pages.quotes.detail.table.description": "Description",
    "pages.quotes.detail.total": "Total",
    "pages.quotes.new.total": "Total",
    "pages.quotes.new.materialCost": "Coût Matériel",
    "pages.quotes.new.laborCost": "Coût Main d'œuvre",
    "pages.quotes.new.overheadCost": "Frais Généraux",
    "pages.quotes.new.lineItemNotes": "Notes de ligne",
    "pages.quotes.new.noAssumptions": "Aucune hypothèse définie",
    "pages.quotes.new.newQuote": "Nouveau Devis",
    "pages.quotes.new.viewVersionHistory": "Voir Historique Versions",
    "pages.quotes.new.addProductsPricing": "Ajouter produits et prix",
    "pages.quotes.new.toggleCostBreakdown": "Basculer détail coûts",
    "pages.quotes.new.unitPrice": "Prix Unitaire",
    "pages.quotes.new.internalCostingAnalysis": "Analyse Coûts Interne",
    "pages.quotes.new.totalRevenue": "Revenu Total",
    "pages.quotes.new.grossProfit": "Marge Brute",
    "pages.quotes.new.quickActions": "Actions Rapides",
    "pages.quotes.new.assumptionsVerified": "Hypothèses Vérifiées",
    "pages.quotes.new.warningsPresent": "Avertissements Présents",
    "pages.quotes.table.version": "Version",
    "pages.quotes.toast.savedDraft": "Devis enregistré comme brouillon",
    "pages.quotes.toast.submitted": "Devis soumis pour approbation",
    "pages.quotes.toast.saveFailed": "Erreur enregistrement devis",
    "pages.quotes.toast.tryAgain": "Veuillez réessayer.",

    # Pages - Sales
    "pages.sales.noBid": "Pas d'offre",
    "pages.sales.statusReviewing": "En revu",
    "pages.sales.statusQuoting": "En devis",
    "pages.sales.statusSubmitted": "Soumis",
    "pages.sales.totalRfqs": "Total RFQs",
    "pages.sales.avgResponseTime": "Temps réponse moy.",
    "pages.sales.conversionRate": "Taux conversion",
    "pages.sales.dueDate": "Date d'échéance",
    "pages.sales.receivedDate": "Date réception",
    "pages.sales.searchRfqs": "Rechercher RFQs...",

    # Pages - Production
    "pages.production.views.kanban": "Kanban",
    "pages.production.views.gantt": "Gantt",

    # Pages - Quality
    "pages.quality.tabs.inspections": "Inspections",
    "pages.quality.tabs.capas": "CAPAs",
    "pages.quality.status.disposition": "Disposition",
    "pages.quality.status.capa": "CAPA",
    "pages.quality.table.inspection": "Inspection",
    "pages.quality.msa.notes": "Notes",
    "pages.quality.msa.grrPercent": "% R&R",
    "pages.quality.capability.notes": "Notes",

    # Pages - Maintenance
    "pages.maintenance.tabs.budget": "Budget",
    "pages.maintenance.tabs.loto": "Loto",
    "pages.maintenance.lotoProcedures": "Procédures Loto",
    "pages.maintenance.table.budget": "Budget",
    "pages.maintenance.table.variance": "Écart",

    # Pages - Training
    "pages.training.tabs.certifications": "Certifications",
    "pages.training.certifications.title": "Certifications",
    "pages.training.programs.table.dates": "Dates",
    "pages.training.records.table.score": "Score",

    # Pages - Andon
    "pages.andon.toast.settingsSaved": "Préférences de notification de signal mises à jour.",

    # Pages - Supply Chain
    "pages.supplyChain.tabs.disruptions": "Perturbations",
    "pages.supplyChain.scenarios.probability": "Prob",

    # Pages - Settings
    "pages.settings.links.notifications": "Notifications",
    "pages.settings.profile.sections.avatar": "Avatar",

    # Pages - Obeya
    "pages.obeya.tabs.actions": "Actions",
    "pages.obeya.tabs.exceptions": "Exceptions",
    "pages.obeya.sections.hoshinKanri": "Hoshin Kanri",
    "pages.obeya.toast.loadFailed": "Échec chargement données Obeya",
    "pages.obeya.toast.itemDeleted": "Article supprimé avec succès",
    "pages.obeya.toast.deleteFailed": "Échec suppression article",
    "pages.obeya.toast.commentAdded": "Commentaire ajouté",
    "pages.obeya.toast.commentFailed": "Échec ajout commentaire",
    "pages.obeya.toast.statusUpdated": "Statut mis à jour",
    "pages.obeya.toast.statusFailed": "Échec mise à jour statut",
    "pages.obeya.toast.created": "Tableau Obeya créé",
    "pages.obeya.toast.createdDesc": "Votre nouveau tableau obeya numérique a été initialisé avec succès.",

    # Pages - A3
    "pages.a3.toast.titleRequired": "Veuillez entrer un titre pour le rapport A3.",
    "pages.a3.toast.created": "Rapport A3 créé",
    "pages.a3.toast.createdDesc": "Le nouveau rapport A3 a été initialisé avec succès.",
    "pages.a3.toast.createFailed": "Échec création rapport A3.",
    "pages.a3.toast.loadFailed": "Échec chargement détails A3",
    "pages.a3.toast.export": "Exporter",
    "pages.a3.toast.exportDesc": "Démarrage export PDF...",
    "pages.a3.toast.updated": "Rapport A3 mis à jour",
    "pages.a3.toast.updatedDesc": "Modifications enregistrées avec succès.",
    "pages.a3.toast.updateFailed": "Échec mise à jour rapport A3.",

    # Pages - CTQ
    "pages.ctq.toast.error": "Erreur",
    "pages.ctq.toast.loadFailed": "Échec chargement détails CTQ",
    "pages.ctq.toast.success": "Succès",
    "pages.ctq.toast.deleteFailed": "Échec suppression CTQ",
    "pages.ctq.toast.measurementAdded": "Mesure ajoutée avec succès",
    "pages.ctq.toast.measurementFailed": "Échec ajout mesure",
    "pages.ctq.toast.exportStarted": "Export démarré",
    "pages.ctq.toast.exportStartedDesc": "Votre rapport CTQ est en cours de génération",
    "pages.ctq.detail.specificationDetails": "Détails Spécification",
    "pages.ctq.detail.qualityRequirements": "Exigences caractéristiques qualité",
    "pages.ctq.detail.nominalValue": "Valeur Nominale",
    "pages.ctq.detail.upperTolerance": "Tolérance Supérieure",
    "pages.ctq.detail.lowerTolerance": "Tolérance Inférieure",
    "pages.ctq.detail.relatedRfq": "RFQ Lié",
    "pages.ctq.detail.partNumber": "Numéro Pièce",
    "pages.ctq.detail.measurementInfo": "Info Mesure",
    "pages.ctq.detail.howMeasured": "Comment cette caractéristique est mesurée",
    "pages.ctq.detail.measurementMethod": "Méthode Mesure",
    "pages.ctq.detail.samplingPlan": "Plan Échantillonnage",
    "pages.ctq.detail.checkStage": "Étape Contrôle",
    "pages.ctq.detail.evidenceRequired": "Preuve Requise",
    "pages.ctq.detail.lastUpdated": "Dernière MAJ",
    "pages.ctq.detail.measurementHistory": "Historique Mesures",
    "pages.ctq.detail.recentResults": "Résultats de mesure récents et tendances",
    "pages.ctq.detail.measuredBy": "Mesuré Par",
    "pages.ctq.detail.deleteCtq": "Supprimer CTQ",
    "pages.ctq.detail.addMeasurement": "Ajouter Mesure",
    "pages.ctq.detail.measuredValue": "Valeur Mesurée",
    "pages.ctq.detail.notMeasured": "Non Mesuré",
    "pages.ctq.measurementNotesPlaceholder": "Ajouter notes pertinentes sur cette mesure",

    # Pages - Exceptions
    "pages.exceptions.synchronizing": "Synchronisation exceptions opérationnelles",
    "pages.exceptions.zeroHighUrgency": "Zéro nœuds haute urgence identifiés",

    # Pages - Project Management
    "pages.projectManagement.detail.backlog": "Backlog",
    "pages.projectManagement.detail.sprints": "Sprints",
    "pages.projectManagement.detail.wiki": "Wiki",
    "pages.projectManagement.portfolio": "Portefeuille",
    "pages.projectManagement.types.standard": "Standard",
    "pages.projectManagement.types.scrum": "Scrum",
    "pages.projectManagement.types.kanban": "Kanban",
    "pages.projectManagement.types.kaizen": "Kaizen",
    "pages.projectManagement.types.maintenance": "Maintenance",
    "pages.projectManagement.toast.settingsSaved": "Paramètres enregistrés",
    "pages.projectManagement.toast.settingsSavedDesc": "Paramètres projet mis à jour.",
    "pages.projectManagement.toast.saveFailed": "Échec enregistrement",
    "pages.projectManagement.toast.saveFailedDesc": "Erreur lors de l'enregistrement de vos modifications.",
    "pages.projectManagement.kanban.columns.ready": "Prêt",
    "pages.projectManagement.kanban.columns.inProgress": "En Cours",
    "pages.projectManagement.kanban.columns.readyForTest": "Prêt pour Test",
    "pages.projectManagement.kanban.columns.done": "Fait",
    "pages.projectManagement.milestones.namePlaceholder": "Phase 1 Terminée",
    "pages.projectManagement.milestones.detailsPlaceholder": "Détails...",
    "pages.projectManagement.wiki.searchPlaceholder": "Rechercher...",
    "pages.projectManagement.wiki.titlePlaceholder": "Titre Page",

    # Pages - Admin
    "pages.admin.title": "Administration",
    "pages.admin.import.conflictResolution": "Résolution Conflit",
    "pages.admin.import.skipExisting": "Ignorer Existant",
    "pages.admin.import.updateExisting": "Mettre à jour Existant",

    # Pages - Obeya New
    "pages.obeyaNew.description": "Description",

    # Pages - Quoting Helper
    "pages.quotingHelper.noQuoteFound": "Aucun Devis Trouvé",
    "pages.quotingHelper.toast.handoffSuccess": "Transfert NPI Réussi",
    "pages.quotingHelper.toast.handoffFailed": "Échec Transfert",

    # A3
    "a3.new.basicInformation.description": "Description",
    "a3.sections.background.description": "Description",
    "a3.sections.countermeasures.description": "Description",
    "a3.sections.currentCondition.description": "Description",
    "a3.sections.goal.description": "Description",
    "a3.sections.implementation.description": "Description",
    "a3.sections.rootCause.description": "Description",
    "a3.stats.emailDrafting.title": "Assistant E-mail IA",
    "a3.stats.emailDrafting.aria.selectPurpose": "Sélectionner objectif",
}

def set_nested_value(d, path, value):
    keys = path.split('.')
    current = d
    for i, k in enumerate(keys[:-1]):
        if k not in current: return False
        current = current[k]
        if not isinstance(current, dict): return False
    
    last_key = keys[-1]
    if last_key in current:
        if current[last_key] != value:
            print(f"Updating {path}...")
            # print(f"  Old: {current[last_key]}")
            # print(f"  New: {value}")
            current[last_key] = value
            return True
    return False

def main():
    target_file = 'frontend/src/locales/fr.json'
    
    if not os.path.exists(target_file):
        print(f"Error: {target_file} not found.")
        return

    with open(target_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    updated_count = 0
    for path, value in TRANSLATIONS.items():
        if set_nested_value(data, path, value):
            updated_count += 1

    if updated_count > 0:
        with open(target_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\nSuccessfully updated {updated_count} translations in {target_file}")
    else:
        print("\nNo changes needed.")

if __name__ == "__main__":
    main()
