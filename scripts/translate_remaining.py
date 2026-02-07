import json
import sys

# Arabic Translation Fixes
# Includes RTL specific corrections + Missing English Translations

translations = {
    "ar": {
        # RTL Fixes & Specific Lines mentioned by user
        "pages.today.fallback.priorities.closeRfqBlockers": "إغلاق معوقات RFQ لهذا اليوم",
        "pages.today.fallback.tasks.reviewOpenRfqs": "مراجعة RFQs المفتوحة",
        "pages.today.fallback.tasks.approveDraftQuote": "الموافقة على مسودة العرض",
        "pages.today.fallback.kpis.openRfqs": "RFQs المفتوحة",
        "pages.today.fallback.kpis.pendingQuotes": "عروض الأسعار المعلقة",
        "pages.today.fallback.kpis.onTimeDelivery": "التسليم في الوقت المحدد",
        "pages.today.fallback.kpis.oee": "الفعالية الشاملة للمعدات (OEE)",
        "pages.today.fallback.activity.rfqStatusUpdated": "تم تحديث حالة RFQ-2024-0089",
        "pages.today.fallback.activity.quoteSentToAcme": "تم إرسال العرض إلى Acme Corp",
        
        # Settings - API
        "settings.api.initializedOn": "تمت التهيئة في",
        "settings.api.requestVolume": "حجم الطلبات (24 ساعة)",
        "settings.api.errorRate": "معدل الخطأ",
        "settings.api.protocolStream": "البروتوكول: REST_JSON_STREAM // العقدة: SENSEI_CORE_V3",
        "settings.api.keys.erpSync": "مزامنة ERP",
        "settings.api.keys.shopFloorDisplay": "شاشة أرضية المصنع",
        "settings.api.description": "إدارة مفاتيح التفويض لتيارات المعلومات الخارجية",
        "settings.api.title": "رموز الوصول API",
        "settings.api.activeAuthNodes": "عقد المصادقة النشطة",
        "settings.api.intelligenceThroughput": "إنتاجية المعلومات",
        "settings.api.optimalLoad": "الحمل الأمثل",
        "settings.api.initializeNewKey": "تهيئة مفتاح جديد",
        
        # Settings - Company Defaults & Branding
        "settings.company.defaults.legalEntityIdentity": "Sensei Manufacturing Solutions",
        "settings.company.defaults.taxIdVat": "MA-123456789",
        "settings.company.defaults.registeredOffice": "123 شارع الصناعة، الدار البيضاء، المغرب",
        "settings.company.branding.primaryLogoNode": "عقدة الشعار الرئيسي",
        "settings.company.branding.logoPlaceholder": "الشعار",
        "settings.company.branding.updateStream": "تحديث التيار",
        "settings.company.branding.interfaceAccentSync": "مزامنة تمييز الواجهة",
        "settings.company.branding.activeAccent": "نشط: برتقالي_رامز (#FFBE00)",
        
        # Settings - Integrations items (status connected/disconnected usually exist but checking)
        "settings.integrations.status.connected": "متصل",
        "settings.integrations.status.disconnected": "غير متصل",
        "settings.integrations.items.sap.name": "بروتوكول SAP ERP",
        "settings.integrations.items.sap.desc": "مزامنة ثنائية الاتجاه لدورات الإنتاج وعقد المخزون",
        "settings.integrations.items.teams.name": "قناة Microsoft Teams",
        "settings.integrations.items.teams.desc": "إرسال آلي لإشارات Andon للقنوات التشغيلية",
        "settings.integrations.items.powerbi.name": "ذكاء PowerBI",
        "settings.integrations.items.powerbi.desc": "تصدير تيار البيانات الاستراتيجي للتحليل الزمني العميق",
        "settings.integrations.items.slack.name": "تكامل Slack",
        "settings.integrations.items.slack.desc": "إشعارات القياس عن بعد في الوقت الفعلي ومزامنة القيادة التشغيلية",
        
        # Settings - Localization
        "settings.localization.rtlActive": "تخطيط من اليمين لليسار (RTL) نشط",
        "settings.localization.preview": "معاينة",
        "settings.localization.standardMetric": "مقياس قياسي",
        "settings.localization.efficiencyPercentage": "نسبة الكفاءة",
        
        # Settings - Profile
        "settings.profile.personnelSummaryPlaceholder": "اكتب ملخصاً مهنياً موجزاً",
        "settings.profile.selectDepartment": "اختر القسم",
        "settings.profile.selectTimezone": "اختر المنطقة الزمنية",
        "settings.profile.timezones.africaCasablanca": "(GMT+0) الدار البيضاء",
        "settings.profile.timezones.europeParis": "(GMT+1) باريس",
        "settings.profile.timezones.europeLondon": "(GMT+0) لندن",
        "settings.profile.timezones.americaNewYork": "(GMT-5) نيويورك",
        "settings.profile.timezones.americaLosAngeles": "(GMT-8) لوس أنجلوس",
        
        "settings.profile.departments.engineering": "الهندسة",
        "settings.profile.departments.production": "الإنتاج",
        "settings.profile.departments.quality": "الجودة",
        "settings.profile.departments.sales": "المبيعات",
        "settings.profile.departments.operations": "العمليات",
        "settings.profile.departments.finance": "المالية",
        "settings.profile.departments.humanResources": "الموارد البشرية",
        "settings.profile.departments.it": "تكنولوجيا المعلومات",
        "settings.profile.departments.management": "الإدارة",
        "settings.profile.departments.warehouse": "المستودع",

        "settings.profile.toast.updated.title": "تم تحديث الملف الشخصي",
        "settings.profile.toast.updated.description": "تم حفظ التغييرات بنجاح.",
        "settings.profile.toast.failed.title": "فشل التحديث",
        "settings.profile.toast.failed.description": "حدث خطأ أثناء حفظ التغييرات.",

        # Settings - Security (Password etc)
        "settings.account.changePasswordDesc": "أدخل كلمة المرور الحالية وكلمة المرور الجديدة",
        "settings.security.changePasswordDesc": "أدخل كلمة المرور الحالية وكلمة المرور الجديدة",
        "settings.security.passwordStrengthHint": "يجب أن تتكون كلمة المرور من 8 أحرف على الأقل وتشمل حرفاً كبيراً ورقماً",
        "settings.security.passwordsDoNotMatch": "كلمات المرور غير متطابقة",
        "settings.security.passwordVisibility.show": "عرض",
        "settings.security.passwordVisibility.hide": "إخفاء",
        "settings.security.passwordVisibility.label": "كلمات المرور",
        "settings.security.changingPassword": "جاري التغيير...",
        "settings.security.currentPassword": "كلمة المرور الحالية",
        "settings.security.newPassword": "كلمة المرور الجديدة",
        "settings.security.confirmPassword": "تأكيد كلمة المرور",
        
        # Settings - Sites
        "settings.sites.placeholders.siteCode": "مثال: SITE-NY-01",
        "settings.sites.placeholders.nodeCommonName": "مثال: مصنع نيويورك المتقدم",
        "settings.sites.placeholders.countrySync": "الولايات المتحدة",
        "settings.sites.placeholders.currencyNode": "دولار أمريكي",
        "settings.sites.placeholders.temporalAlignment": "أمريكا/نيويورك",
        "settings.sites.placeholders.physicalAddressNode": "123 شارع الصناعة، نيويورك",
        
        "settings.sites.table.code": "الرمز",
        "settings.sites.table.siteIdentity": "هوية الموقع",
        "settings.sites.table.temporalSync": "المزامنة الزمنية",
        "settings.sites.table.currency": "العملة",
        "settings.sites.table.statusNode": "حالة العقدة",
        
        "settings.sites.addressUnavailable": "موقع غير محدد",
        "settings.sites.valueUnavailable": "—",
        
        # Settings - Team Roles (Previously mostly English)
        "settings.team.roles.admin": "مسؤول",
        "settings.team.roles.adminDesc": "وصول كامل لجميع الميزات والإعدادات",
        "settings.team.roles.manager": "مدير",
        "settings.team.roles.managerDesc": "يمكنه إدارة أعضاء الفريق والموافقة على سير العمل",
        "settings.team.roles.user": "مستخدم",
        "settings.team.roles.userDesc": "وصول قياسي للميزات المعينة",
        "settings.team.roles.viewer": "مشاهد",
        "settings.team.roles.viewerDesc": "وصول للقراءة فقط",
        
        "settings.team.status.active": "نشط",
        "settings.team.status.invited": "مدعو",
        "settings.team.status.disabled": "معطل",
        
        "settings.team.departments.management": "الإدارة",
        "settings.team.departments.engineering": "الهندسة",
        "settings.team.departments.production": "الإنتاج",
        "settings.team.departments.quality": "الجودة",
        "settings.team.departments.sales": "المبيعات",
        "settings.team.departments.warehouse": "المستودع"
    },
    
    # French
    "fr": {
         "settings.api.initializedOn": "INITIALISÉ_LE",
        "settings.api.requestVolume": "VOLUME_REQUÊTES (24H)",
        "settings.api.errorRate": "TAUX_ERREUR",
        "settings.api.protocolStream": "Protocole: REST_JSON_STREAM // NŒUD: SENSEI_CORE_V3",
        "settings.api.keys.erpSync": "Sync ERP",
        "settings.api.keys.shopFloorDisplay": "Affichage Atelier",
        "settings.api.description": "Gérer les clés d'autorisation pour les flux d'intelligence externes",
        "settings.api.title": "Jetons d'Accès API",
        "settings.api.activeAuthNodes": "Nœuds d'Authentification Actifs",
        "settings.api.intelligenceThroughput": "Débit d'Intelligence",
        "settings.api.optimalLoad": "Charge Optimale",
        "settings.api.initializeNewKey": "Initialiser Nouvelle Clé",

        "settings.company.defaults.legalEntityIdentity": "Sensei Manufacturing Solutions",
        "settings.company.defaults.taxIdVat": "MA-123456789",
        "settings.company.defaults.registeredOffice": "123 Av. Industrielle, Casablanca, Maroc",
        "settings.company.branding.primaryLogoNode": "NŒUD_LOGO_PRINCIPAL",
        "settings.company.branding.logoPlaceholder": "LOGO",
        "settings.company.branding.updateStream": "FLUX_MISE_À_JOUR",
        "settings.company.branding.interfaceAccentSync": "SYNC_ACCENT_INTERFACE",
        "settings.company.branding.activeAccent": "Actif: Orange_Rams (#FFBE00)",

        "settings.integrations.items.sap.name": "Protocole SAP ERP",
        "settings.integrations.items.sap.desc": "Sync bidirectionnelle des cycles de production et nœuds d'inventaire",
        "settings.integrations.items.teams.name": "Canal Microsoft Teams",
        "settings.integrations.items.teams.desc": "Envoi automatisé des signaux Andon aux canaux opérationnels",
        "settings.integrations.items.powerbi.name": "Intelligence PowerBI",
        "settings.integrations.items.powerbi.desc": "Export de flux de données stratégiques pour analyse temporelle approfondie",
        "settings.integrations.items.slack.name": "Intégration Slack",
        "settings.integrations.items.slack.desc": "Notifications de télémétrie en temps réel et sync commande opérationnelle",

        "settings.localization.rtlActive": "Mise en page de droite à gauche (RTL) active",
        "settings.localization.preview": "Aperçu",
        "settings.localization.standardMetric": "Métrique standard",
        "settings.localization.efficiencyPercentage": "Pourcentage d'efficacité",

        "settings.profile.personnelSummaryPlaceholder": "Rédigez un bref résumé professionnel",
        "settings.profile.selectDepartment": "Sélectionner un département",
        "settings.profile.selectTimezone": "Sélectionner un fuseau horaire",
        "settings.profile.timezones.africaCasablanca": "(GMT+0) Casablanca",
        "settings.profile.timezones.europeParis": "(GMT+1) Paris",
        "settings.profile.timezones.europeLondon": "(GMT+0) Londres",
        "settings.profile.timezones.americaNewYork": "(GMT-5) New York",
        "settings.profile.timezones.americaLosAngeles": "(GMT-8) Los Angeles",

        "settings.profile.departments.engineering": "Ingénierie",
        "settings.profile.departments.production": "Production",
        "settings.profile.departments.quality": "Qualité",
        "settings.profile.departments.sales": "Ventes",
        "settings.profile.departments.operations": "Opérations",
        "settings.profile.departments.finance": "Finance",
        "settings.profile.departments.humanResources": "Ressources Humaines",
        "settings.profile.departments.it": "IT",
        "settings.profile.departments.management": "Direction",
        "settings.profile.departments.warehouse": "Entrepôt",

        "settings.profile.toast.updated.title": "Profil mis à jour",
        "settings.profile.toast.updated.description": "Vos modifications ont été enregistrées avec succès.",
        "settings.profile.toast.failed.title": "Échec de la mise à jour",
        "settings.profile.toast.failed.description": "Une erreur est survenue lors de l'enregistrement.",

        "settings.account.changePasswordDesc": "Entrez votre mot de passe actuel et un nouveau mot de passe",
        "settings.security.changePasswordDesc": "Entrez votre mot de passe actuel et un nouveau mot de passe",
        "settings.security.passwordStrengthHint": "Le mot de passe doit comporter au moins 8 caractères et inclure une majuscule et un chiffre",
        "settings.security.passwordsDoNotMatch": "Les mots de passe ne correspondent pas",
        "settings.security.passwordVisibility.show": "Afficher",
        "settings.security.passwordVisibility.hide": "Masquer",
        "settings.security.passwordVisibility.label": "mots de passe",
        "settings.security.changingPassword": "Modification...",
        "settings.security.currentPassword": "Mot de passe actuel",
        "settings.security.newPassword": "Nouveau mot de passe",
        "settings.security.confirmPassword": "Confirmer le mot de passe",

        "settings.sites.placeholders.siteCode": "ex. SITE-NY-01",
        "settings.sites.placeholders.nodeCommonName": "ex. Usine Avancée New York",
        "settings.sites.placeholders.countrySync": "USA",
        "settings.sites.placeholders.currencyNode": "USD",
        "settings.sites.placeholders.temporalAlignment": "Amérique/New_York",
        "settings.sites.placeholders.physicalAddressNode": "123 Av. Industrielle, NY",
        
        "settings.sites.table.code": "CODE",
        "settings.sites.table.siteIdentity": "IDENTITÉ_SITE",
        "settings.sites.table.temporalSync": "SYNC_TEMPORELLE",
        "settings.sites.table.currency": "DEVISE",
        "settings.sites.table.statusNode": "NOEUD_STATUT",
        
        "settings.sites.addressUnavailable": "LOC_INDÉTERMINÉE",
        "settings.sites.valueUnavailable": "—",

        "settings.team.roles.admin": "Admin",
        "settings.team.roles.adminDesc": "Accès complet à toutes les fonctionnalités et paramètres",
        "settings.team.roles.manager": "Manager",
        "settings.team.roles.managerDesc": "Peut gérer les membres de l'équipe et approuver les flux",
        "settings.team.roles.user": "Utilisateur",
        "settings.team.roles.userDesc": "Accès standard aux fonctionnalités assignées",
        "settings.team.roles.viewer": "Spectateur",
        "settings.team.roles.viewerDesc": "Accès en lecture seule",
        
        "settings.team.status.active": "Actif",
        "settings.team.status.invited": "Invité",
        "settings.team.status.disabled": "Désactivé",

        "settings.team.departments.management": "Direction",
        "settings.team.departments.engineering": "Ingénierie",
        "settings.team.departments.production": "Production",
        "settings.team.departments.quality": "Qualité",
        "settings.team.departments.sales": "Ventes",
        "settings.team.departments.warehouse": "Entrepôt"
    },

    # Spanish
    "es": {
        "settings.api.initializedOn": "INICIALIZADO_EL",
        "settings.api.requestVolume": "VOLUMEN_SOLICITUDES (24H)",
        "settings.api.errorRate": "TASA_ERROR",
        "settings.api.protocolStream": "Protocolo: REST_JSON_STREAM // NODO: SENSEI_CORE_V3",
        "settings.api.keys.erpSync": "Sincronización ERP",
        "settings.api.keys.shopFloorDisplay": "Pantalla de Planta",
        "settings.api.description": "Administrar claves de autorización para flujos de inteligencia externa",
        "settings.api.title": "Tokens de Acceso API",
        "settings.api.activeAuthNodes": "Nodos de Autenticación Activos",
        "settings.api.intelligenceThroughput": "Rendimiento de Inteligencia",
        "settings.api.optimalLoad": "Carga Óptima",
        "settings.api.initializeNewKey": "Inicializar Nueva Clave",

        "settings.company.defaults.legalEntityIdentity": "Sensei Manufacturing Solutions",
        "settings.company.defaults.taxIdVat": "MA-123456789",
        "settings.company.defaults.registeredOffice": "123 Av. Industrial, Casablanca, Marruecos",
        "settings.company.branding.primaryLogoNode": "NODO_LOGO_PRINCIPAL",
        "settings.company.branding.logoPlaceholder": "LOGO",
        "settings.company.branding.updateStream": "FLUJO_ACTUALIZACIÓN",
        "settings.company.branding.interfaceAccentSync": "SYNC_ACENTO_INTERFAZ",
        "settings.company.branding.activeAccent": "Activo: Naranja_Rams (#FFBE00)",

        "settings.integrations.items.sap.name": "Protocolo SAP ERP",
        "settings.integrations.items.sap.desc": "Sincronización bidireccional de ciclos de producción y nodos de inventario",
        "settings.integrations.items.teams.name": "Canal Microsoft Teams",
        "settings.integrations.items.teams.desc": "Envío automatizado de señales Andon a canales operativos",
        "settings.integrations.items.powerbi.name": "Inteligencia PowerBI",
        "settings.integrations.items.powerbi.desc": "Exportación de flujo de datos estratégicos para análisis temporal profundo",
        "settings.integrations.items.slack.name": "Integración Slack",
        "settings.integrations.items.slack.desc": "Notificaciones de telemetría en tiempo real y sincronización de comando operativo",

        "settings.localization.rtlActive": "Diseño de derecha a izquierda (RTL) activo",
        "settings.localization.preview": "Vista previa",
        "settings.localization.standardMetric": "Métrica estándar",
        "settings.localization.efficiencyPercentage": "Porcentaje de eficiencia",

        "settings.profile.personnelSummaryPlaceholder": "Escriba un breve resumen profesional",
        "settings.profile.selectDepartment": "Seleccionar departamento",
        "settings.profile.selectTimezone": "Seleccionar zona horaria",
        "settings.profile.timezones.africaCasablanca": "(GMT+0) Casablanca",
        "settings.profile.timezones.europeParis": "(GMT+1) París",
        "settings.profile.timezones.europeLondon": "(GMT+0) Londres",
        "settings.profile.timezones.americaNewYork": "(GMT-5) Nueva York",
        "settings.profile.timezones.americaLosAngeles": "(GMT-8) Los Ángeles",

        "settings.profile.departments.engineering": "Ingeniería",
        "settings.profile.departments.production": "Producción",
        "settings.profile.departments.quality": "Calidad",
        "settings.profile.departments.sales": "Ventas",
        "settings.profile.departments.operations": "Operaciones",
        "settings.profile.departments.finance": "Finanzas",
        "settings.profile.departments.humanResources": "Recursos Humanos",
        "settings.profile.departments.it": "IT",
        "settings.profile.departments.management": "Dirección",
        "settings.profile.departments.warehouse": "Almacén",

        "settings.profile.toast.updated.title": "Perfil actualizado",
        "settings.profile.toast.updated.description": "Sus cambios se han guardado exitosamente.",
        "settings.profile.toast.failed.title": "Actualización fallida",
        "settings.profile.toast.failed.description": "Hubo un error al guardar sus cambios.",

        "settings.account.changePasswordDesc": "Ingrese su contraseña actual y una nueva contraseña",
        "settings.security.changePasswordDesc": "Ingrese su contraseña actual y una nueva contraseña",
        "settings.security.passwordStrengthHint": "La contraseña debe tener al menos 8 caracteres e incluir una mayúscula y un número",
        "settings.security.passwordsDoNotMatch": "Las contraseñas no coinciden",
        "settings.security.passwordVisibility.show": "Mostrar",
        "settings.security.passwordVisibility.hide": "Ocultar",
        "settings.security.passwordVisibility.label": "contraseñas",
        "settings.security.changingPassword": "Cambiando...",
        "settings.security.currentPassword": "Contraseña actual",
        "settings.security.newPassword": "Nueva contraseña",
        "settings.security.confirmPassword": "Confirmar contraseña",

        "settings.sites.placeholders.siteCode": "ej. SITE-NY-01",
        "settings.sites.placeholders.nodeCommonName": "ej. Planta Avanzada Nueva York",
        "settings.sites.placeholders.countrySync": "EE. UU.",
        "settings.sites.placeholders.currencyNode": "USD",
        "settings.sites.placeholders.temporalAlignment": "América/Nueva_York",
        "settings.sites.placeholders.physicalAddressNode": "123 Av. Industrial, NY",
        
        "settings.sites.table.code": "CÓDIGO",
        "settings.sites.table.siteIdentity": "IDENTIDAD_SITIO",
        "settings.sites.table.temporalSync": "SYNC_TEMPORAL",
        "settings.sites.table.currency": "MONEDA",
        "settings.sites.table.statusNode": "NODO_ESTADO",
        
        "settings.sites.addressUnavailable": "LOC_INDETERMINADA",
        "settings.sites.valueUnavailable": "—",

        "settings.team.roles.admin": "Admin",
        "settings.team.roles.adminDesc": "Acceso total a todas las funciones y configuraciones",
        "settings.team.roles.manager": "Gerente",
        "settings.team.roles.managerDesc": "Puede gestionar miembros del equipo y aprobar flujos",
        "settings.team.roles.user": "Usuario",
        "settings.team.roles.userDesc": "Acceso estándar a funciones asignadas",
        "settings.team.roles.viewer": "Espectador",
        "settings.team.roles.viewerDesc": "Acceso de solo lectura",
        
        "settings.team.status.active": "Activo",
        "settings.team.status.invited": "Invitado",
        "settings.team.status.disabled": "Deshabilitado",

        "settings.team.departments.management": "Dirección",
        "settings.team.departments.engineering": "Ingeniería",
        "settings.team.departments.production": "Producción",
        "settings.team.departments.quality": "Calidad",
        "settings.team.departments.sales": "Ventas",
        "settings.team.departments.warehouse": "Almacén"
    },

    # German
    "de": {
        "settings.api.initializedOn": "INITIALISIERT_AM",
        "settings.api.requestVolume": "ANFRAGEVOLUMEN (24H)",
        "settings.api.errorRate": "FEHLERRATE",
        "settings.api.protocolStream": "Protokoll: REST_JSON_STREAM // KNOTEN: SENSEI_CORE_V3",
        "settings.api.keys.erpSync": "ERP-Sync",
        "settings.api.keys.shopFloorDisplay": "Shop-Floor-Anzeige",
        "settings.api.description": "Autorisierungsschlüssel für externe Intelligence-Streams verwalten",
        "settings.api.title": "API-Zugriffstoken",
        "settings.api.activeAuthNodes": "Aktive Authentifizierungsknoten",
        "settings.api.intelligenceThroughput": "Intelligence-Durchsatz",
        "settings.api.optimalLoad": "Optimale Last",
        "settings.api.initializeNewKey": "Neuen Schlüssel initialisieren",

        "settings.company.defaults.legalEntityIdentity": "Sensei Manufacturing Solutions",
        "settings.company.defaults.taxIdVat": "MA-123456789",
        "settings.company.defaults.registeredOffice": "123 Industriestraße, Casablanca, Marokko",
        "settings.company.branding.primaryLogoNode": "PRIMÄRER_LOGO_KNOTEN",
        "settings.company.branding.logoPlaceholder": "LOGO",
        "settings.company.branding.updateStream": "UPDATE_STREAM",
        "settings.company.branding.interfaceAccentSync": "INTERFACE_AKZENT_SYNC",
        "settings.company.branding.activeAccent": "Aktiv: Rams_Orange (#FFBE00)",

        "settings.integrations.items.sap.name": "SAP ERP Protokoll",
        "settings.integrations.items.sap.desc": "Bidirektionale Synchronisierung von Produktionszyklen und Bestandsknoten",
        "settings.integrations.items.teams.name": "Microsoft Teams Kanal",
        "settings.integrations.items.teams.desc": "Automatisierter Versand von Andon-Signalen an operative Kanäle",
        "settings.integrations.items.powerbi.name": "PowerBI Intelligence",
        "settings.integrations.items.powerbi.desc": "Strategischer Datenstrom-Export für tiefe zeitliche Analyse",
        "settings.integrations.items.slack.name": "Slack Integration",
        "settings.integrations.items.slack.desc": "Echtzeit-Telemetrie-Benachrichtigungen und operative Befehlssynchronisierung",

        "settings.localization.rtlActive": "Rechts-nach-Links (RTL) Layout aktiv",
        "settings.localization.preview": "Vorschau",
        "settings.localization.standardMetric": "Standardmetrik",
        "settings.localization.efficiencyPercentage": "Effizienzprozentsatz",

        "settings.profile.personnelSummaryPlaceholder": "Schreiben Sie eine kurze berufliche Zusammenfassung",
        "settings.profile.selectDepartment": "Abteilung auswählen",
        "settings.profile.selectTimezone": "Zeitzone auswählen",
        "settings.profile.timezones.africaCasablanca": "(GMT+0) Casablanca",
        "settings.profile.timezones.europeParis": "(GMT+1) Paris",
        "settings.profile.timezones.europeLondon": "(GMT+0) London",
        "settings.profile.timezones.americaNewYork": "(GMT-5) New York",
        "settings.profile.timezones.americaLosAngeles": "(GMT-8) Los Angeles",

        "settings.profile.departments.engineering": "Ingenieurwesen",
        "settings.profile.departments.production": "Produktion",
        "settings.profile.departments.quality": "Qualität",
        "settings.profile.departments.sales": "Vertrieb",
        "settings.profile.departments.operations": "Operationen",
        "settings.profile.departments.finance": "Finanzen",
        "settings.profile.departments.humanResources": "Personalwesen",
        "settings.profile.departments.it": "IT",
        "settings.profile.departments.management": "Management",
        "settings.profile.departments.warehouse": "Lager",

        "settings.profile.toast.updated.title": "Profil aktualisiert",
        "settings.profile.toast.updated.description": "Ihre Änderungen wurden erfolgreich gespeichert.",
        "settings.profile.toast.failed.title": "Aktualisierung fehlgeschlagen",
        "settings.profile.toast.failed.description": "Beim Speichern Ihrer Änderungen ist ein Fehler aufgetreten.",

        "settings.account.changePasswordDesc": "Geben Sie Ihr aktuelles Passwort und ein neues Passwort ein",
        "settings.security.changePasswordDesc": "Geben Sie Ihr aktuelles Passwort und ein neues Passwort ein",
        "settings.security.passwordStrengthHint": "Passwort muss mindestens 8 Zeichen lang sein und einen Großbuchstaben sowie eine Zahl enthalten",
        "settings.security.passwordsDoNotMatch": "Passwörter stimmen nicht überein",
        "settings.security.passwordVisibility.show": "Anzeigen",
        "settings.security.passwordVisibility.hide": "Verbergen",
        "settings.security.passwordVisibility.label": "passwörter",
        "settings.security.changingPassword": "Ändere...",
        "settings.security.currentPassword": "Aktuelles Passwort",
        "settings.security.newPassword": "Neues Passwort",
        "settings.security.confirmPassword": "Passwort bestätigen",

        "settings.sites.placeholders.siteCode": "z.B. SITE-NY-01",
        "settings.sites.placeholders.nodeCommonName": "z.B. New York Advanced Plant",
        "settings.sites.placeholders.countrySync": "USA",
        "settings.sites.placeholders.currencyNode": "USD",
        "settings.sites.placeholders.temporalAlignment": "Amerika/New_York",
        "settings.sites.placeholders.physicalAddressNode": "123 Industriestraße, NY",
        
        "settings.sites.table.code": "CODE",
        "settings.sites.table.siteIdentity": "STANDORT_IDENTITÄT",
        "settings.sites.table.temporalSync": "ZEIT_SYNC",
        "settings.sites.table.currency": "WÄHRUNG",
        "settings.sites.table.statusNode": "STATUS_KNOTEN",

        "settings.sites.addressUnavailable": "ORT_UNBESTIMMT",
        "settings.sites.valueUnavailable": "—",

        "settings.team.roles.admin": "Admin",
        "settings.team.roles.adminDesc": "Vollzugriff auf alle Funktionen und Einstellungen",
        "settings.team.roles.manager": "Manager",
        "settings.team.roles.managerDesc": "Kann Teammitglieder verwalten und Workflows genehmigen",
        "settings.team.roles.user": "Benutzer",
        "settings.team.roles.userDesc": "Standardzugriff auf zugewiesene Funktionen",
        "settings.team.roles.viewer": "Betrachter",
        "settings.team.roles.viewerDesc": "Lesezugriff",
        
        "settings.team.status.active": "Aktiv",
        "settings.team.status.invited": "Eingeladen",
        "settings.team.status.disabled": "Deaktiviert",

        "settings.team.departments.management": "Management",
        "settings.team.departments.engineering": "Ingenieurwesen",
        "settings.team.departments.production": "Produktion",
        "settings.team.departments.quality": "Qualität",
        "settings.team.departments.sales": "Vertrieb",
        "settings.team.departments.warehouse": "Lager"
    }
}

def set_nested(data, key_path, value):
    keys = key_path.split('.')
    curr = data
    for i, k in enumerate(keys[:-1]):
        if k not in curr or not isinstance(curr[k], dict):
            curr[k] = {}
        curr = curr[k]
    curr[keys[-1]] = value

def main():
    for locale, key_map in translations.items():
        file_path = f'frontend/src/locales/{locale}.json'
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for key, val in key_map.items():
                set_nested(data, key, val)
                
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Updated {locale}.json")
            
        except FileNotFoundError:
            print(f"Skipping {locale} (not found)")
        except Exception as e:
            print(f"Error updating {locale}: {e}")

if __name__ == "__main__":
    main()
