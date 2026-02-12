import json
import os

# Path to the files
AR_JSON_PATH = os.path.join("frontend", "src", "locales", "ar.json")
# MISSING_KEYS_PATH is not strictly needed if we hardcode the translations based on it,
# but can be useful for verification.
MISSING_KEYS_PATH = os.path.join("scripts", "missing_ar_strict.json")

# The massive dictionary of fix translations
# Mapped from the Key in missing_ar_strict.json to the Correct Arabic Value
TRANSLATIONS = {
    # Meta / Common
    "meta.locale": "ar",
    "meta.direction": "rtl",
    "common.source": "المصدر",
    "common.tests.aoi": "الفحص البصري الآلي (AOI)\u200f",
    "common.tests.xray": "فحص الأشعة السينية (X-Ray)\u200f",
    "common.tests.ict": "الفحص داخل الدائرة (ICT)\u200f",
    "common.tests.fct": "فحص الوظائف (FCT)\u200f",
    "common.status.completed": "مكتمل",
    "common.status.picked": "تم الالتقاط",
    "common.status.packed": "تم التغليف",
    "common.status.shipped": "تم الشحن",
    "common.status.delivered": "تم التوصيل",
    "common.status.inProgress": "قيد التنفيذ",
    "common.status.pending": "معلق",
    "common.user": "المستخدم",
    "common.protocol": "بروتوكول",
    "common.cat": "فحص بمساعدة الحاسوب (CAT)",

    # Layout / System
    "layout.systemInitialization": "تهيئة النظام...",
    "layout.bootProtocol": "البروتوكول: Sensei_OS_V3 // تسلسل التمهيد",
    "layout.systemMetadata.station": "المحطة: {station}",
    "layout.systemMetadata.osVer": "إصدار النظام: {version}",
    "layout.systemMetadata.integrity": "النزاهة: {state}",
    "layout.systemMetadata.latency": "زمن الانتقال: {latency}",

    # Email Drafting
    "emailDrafting.placeholders.recipientEmail": "recipient@example.com",
    "emailDrafting.thread.entityType.rfq": "طلب عرض سعر (RFQ)",
    "emailDrafting.defaults.senderEmail": "operator@sensei.com",
    "emailDrafting.drafts.snippet": "{snippet}...",

    # Settings
    "settings.shell.toastTitle": "تمت مزامنة الإعدادات",
    "settings.shell.toastDescription": "تم تحديث معلمات {title} المستهدفة في السجل.",
    "settings.shell.synchronizing": "جاري المزامنة...",
    "settings.shell.saveConfiguration": "حفظ_التكوين",
    "settings.appearance.preview.title": "وحدة الاستخبارات 04\u200f",
    "settings.appearance.preview.subtitle": "تدفق العمليات المباشر متزامن\u200f",
    "settings.appearance.preview.primaryAction": "تنفيذ_الأمر\u200f",
    "settings.appearance.preview.secondaryAction": "عرض_الاستخبارات\u200f",
    "settings.appearance.preview.tertiaryAction": "إنهاء\u200f",
    "settings.team.inviteDialog.emailPlaceholder": "colleague@example.com",
    "settings.sites.status.active": "نشط\u200f",
    "settings.sites.status.inactive": "غير نشط\u200f",
    "settings.company.defaults.legalEntityIdentity": "Sensei حلول التصنيع",
    "settings.company.defaults.taxIdVat": "الرقم الضريبي: MA-123456789",
    "settings.email.defaults.dispatchIdentity": "أمر_نظام_Sensei\u200f",
    "settings.email.defaults.relayReplyTo": "no-reply@sensei-manuf.com\u200f",
    "settings.email.smtpStatus": "مرحل SMTP: متزامن\u200f",
    "settings.email.smtpDetails": "المضيف: mail.sensei-infra.com // المنفذ: 587 (TLS)\u200f",
    
    # Generic Errors
    "errors.boundaryFallback": "حدث خطأ ما. يرجى التحديث أو المحاولة مرة أخرى.",

    # Modules: Production
    "modules.production.detail.aggregationPulse": "نبض التجميع",
    "modules.production.detail.escalateAnomaly": "تصعيد الشذوذ",
    "modules.production.detail.executionVelocity": "سرعة التنفيذ",
    "modules.production.detail.exportSpec": "تصدير المواصفات",
    "modules.production.detail.gateVerified": "تم التحقق من البوابة",
    "modules.production.detail.initiateExecution": "بدء التنفيذ",
    "modules.production.detail.node": "العقدة",
    "modules.production.detail.scrapDeviation": "انحراف الخردة",
    "modules.production.detail.suspendProtocol": "تعليق البروتوكول",
    "modules.production.detail.tabs.bom": "قائمة المواد (BOM)",
    "modules.production.detail.tabs.history": "السجل",
    "modules.production.detail.tabs.operations": "العمليات",
    "modules.production.detail.tabs.quality": "الجودة",
    "modules.production.detail.targetMagnitude": "الحجم المستهدف",
    "modules.production.detail.unknownProduct": "منتج غير معروف",
    "modules.production.detail.viewHistory": "عرض السجل",
    "modules.production.detail.loadingBom": "جاري استرداد عقد بروتوكول قائمة المواد...",
    "modules.production.detail.temporalSchedule": "الجدول الزمني",
    "modules.production.detail.startHorizon": "أفق البدء",
    "modules.production.detail.targetTerminal": "المحطة المستهدفة",
    "modules.production.detail.standardLeadTime": "وقت التسليم القياسي",
    "modules.production.detail.days": "أيام",
    "modules.production.detail.station": "المحطة",

    # Modules: Quality - NCR
    "modules.quality.ncr.detail.assignCapa": "تعيين إجراء تصحيحي/وقائي",
    "modules.quality.ncr.detail.comment": "تعليق",
    "modules.quality.ncr.detail.discrepancyIntelligence": "استخبارات التناقض",
    "modules.quality.ncr.detail.investigationProtocol": "بروتوكول التحقيق",
    "modules.quality.ncr.detail.noDescription": "لا يوجد وصف",
    "modules.quality.ncr.detail.refineProtocol": "تحسين البروتوكول",
    "modules.quality.ncr.detail.subjectiveData": "بيانات ذاتية",
    "modules.quality.ncr.detail.subtitle": "العنوان الفرعي",
    "modules.quality.ncr.detail.tabs.disposition": "التصرف",
    "modules.quality.ncr.detail.tabs.eventLog": "سجل الأحداث",
    "modules.quality.ncr.detail.tabs.evidence": "الأدلة",
    "modules.quality.ncr.detail.tabs.rootCause": "السبب الجذري",
    "modules.quality.ncr.detail.terminateNode": "إنهاء العقدة",
    "modules.quality.ncr.detail.viewLogs": "عرض السجلات",
    "modules.quality.ncr.new.validationError": "خطأ في التحقق",
    "modules.quality.ncr.new.titleDescRequired": "العنوان والوصف مطلوبان.",
    "modules.quality.ncr.new.ncrCreated": "تم إنشاء NCR",
    "modules.quality.ncr.new.recordedSuccess": "تم تسجيل تقرير عدم المطابقة (NCR) بنجاح.",
    "modules.quality.ncr.new.createFailed": "فشل إنشاء NCR",
    "modules.quality.ncr.new.placeholders.title": "مثال: انحراف الأبعاد في ثقوب الحامل",
    "modules.quality.ncr.new.placeholders.location": "مثال: خط التجميع 2",
    "modules.quality.ncr.new.placeholders.partNumber": "رقم_القطعة",
    "modules.quality.ncr.new.placeholders.woNumber": "رقم_أمر_العمل",
    "modules.quality.ncr.new.placeholders.description": "قدم أدلة مفصلة بخصوص بروتوكول التناقض...",

    # Modules: Quality - CAPA
    "modules.quality.capa.new.capaCreated": "تم إنشاء CAPA",
    "modules.quality.capa.new.createFailed": "فشل الإنشاء",
    "modules.quality.capa.new.initiatedSuccess": "تم البدء بنجاح",
    "modules.quality.capa.detail.addNode": "إضافة عقدة",
    "modules.quality.capa.detail.commitAction": "تنفيذ الإجراء",
    "modules.quality.capa.detail.countermeasureNodes": "عقد التدابير المضادة",
    "modules.quality.capa.detail.exportProtocol": "تصدير البروتوكول",
    "modules.quality.capa.detail.implementationMagnitude": "حجم التنفيذ",
    "modules.quality.capa.detail.problemStatement": "بيان المشكلة",
    "modules.quality.capa.detail.refineCapa": "تحسين CAPA",
    "modules.quality.capa.detail.rootCauseAnalysis": "تحليل السبب الجذري",
    "modules.quality.capa.detail.subtitle": "العنوان الفرعي",
    "modules.quality.capa.detail.syncPulse": "نبض المزامنة",
    "modules.quality.capa.detail.tabs.actionProtocol": "بروتوكول العمل",
    "modules.quality.capa.detail.tabs.effectivenessSync": "مزامنة الفعالية",
    "modules.quality.capa.detail.tabs.relatedAnomalies": "الشذوذات ذات الصلة",
    "modules.quality.capa.detail.terminateNode": "إنهاء العقدة",
    "modules.quality.capa.detail.verifyEffectiveness": "التحقق من الفعالية",

    # Modules: Quality - Inspection
    "modules.quality.inspection.detail.assignmentTelemetry": "قياسات التعيين عن بعد",
    "modules.quality.inspection.detail.checklist": "قائمة التحقق",
    "modules.quality.inspection.detail.commitSync": "تأكيد المزامنة",
    "modules.quality.inspection.detail.inspectionIntelligence": "استخبارات التفتيش",
    "modules.quality.inspection.detail.leadInspector": "كبير المفتشين",
    "modules.quality.inspection.detail.printEvidence": "طباعة الأدلة",
    "modules.quality.inspection.detail.resultsAnalytics": "تحليلات النتائج",
    "modules.quality.inspection.detail.scheduledSync": "مزامنة مجدولة",
    "modules.quality.inspection.new.inspectionStarted": "بدأ التفتيش",
    "modules.quality.inspection.new.initializedSuccess": "تمت تهيئة سجل تفتيش جديد.",
    "modules.quality.inspection.new.createFailed": "فشل إنشاء التفتيش.",
    "modules.quality.inspection.new.associatedWoSync": "مزامنة أمر العمل المرتبط",
    "modules.quality.inspection.new.initialObservation": "معلومات الملاحظة الأولية",
    "modules.quality.inspection.new.placeholders.protocolIdentity": "مثال: بروتوكول التفتيش النهائي - BRK-2024",
    "modules.quality.inspection.new.placeholders.operatorIdentity": "هوية_المشغل",
    "modules.quality.inspection.new.placeholders.partNumber": "رقم_القطعة",
    "modules.quality.inspection.new.placeholders.woNumber": "رقم_أمر_العمل",
    "modules.quality.inspection.new.placeholders.notes": "تضمين النتائج الأولية والبيانات السياقية...",

    # Modules: Products
    "modules.products.title": "كتالوج المنتجات",
    "modules.products.subtitle": "إدارة المنتجات، قوائم المواد، ومسارات التصنيع",
    "modules.products.station": "المنتجات",
    "modules.products.stats.activeProducts": "المنتجات النشطة",
    "modules.products.stats.bomsDefined": "قوائم المواد المعرفة",
    "modules.products.stats.routingsActive": "المسارات النشطة",
    "modules.products.stats.avgLeadTime": "متوسط وقت التسليم",
    "modules.products.stats.activeInventoryNodes": "عقد المخزون النشطة",
    "modules.products.stats.aggregatedRevenue": "إجمالي الإيرادات",
    "modules.products.stats.meanMarginKPI": "متوسط الهامش",
    "modules.products.stats.stockAbnormalities": "تنبيهات المخزون المنخفض",
    "modules.products.actions.newProduct": "منتج جديد",
    "modules.products.tabs.products": "المنتجات",
    "modules.products.tabs.boms": "قوائم المواد",
    "modules.products.tabs.routings": "المسارات",
    "modules.products.details.overview": "نظرة عامة",
    "modules.products.details.specifications": "المواصفات",
    "modules.products.details.bom": "قائمة المواد",
    "modules.products.details.routing": "المسار",
    "modules.products.details.inventory": "المخزون",
    "modules.products.details.history": "السجل",
    "modules.products.status.discontinued": "متوقف",
    "modules.products.viewBom": "عرض قائمة المواد",
    "modules.products.viewAnalytics": "عرض التحليلات",
    "modules.products.stockLevel": "مستوى المخزون",
    "modules.products.allStock": "كل المخزون",
    "modules.products.lowStock": "مخزون منخفض",
    "modules.products.outOfStock": "نفد المخزون",
    "modules.products.table.product": "المنتج",
    "modules.products.table.standardCost": "التكلفة القياسية",
    "modules.products.table.listPrice": "سعر القائمة",
    "modules.products.table.margin": "الهامش",
    "modules.products.table.inventory": "المخزون",
    "modules.products.table.leadTime": "وقت التسليم",
    "modules.products.table.totalSold": "إجمالي المباع",
    "modules.products.emptyState.description": "ابدأ بإضافة منتجك الأول إلى الكتالوج.",
    "modules.products.emptyState.title": "لم يتم العثور على منتجات",
    "modules.products.exportIntel": "تصدير الكتالوج",
    "modules.products.import": "استيراد",
    "modules.products.initializeNode": "إنشاء منتج",
    "modules.products.new.requiredParams": "المعلمات المطلوبة مفقودة",
    "modules.products.new.providePartAndName": "يرجى تقديم رقم القطعة واسم للعقدة على الأقل.",
    "modules.products.new.nodeSynchronized": "تمت مزامنة العقدة",
    "modules.products.new.establishedSuccess": "تم تأسيس {name} بنجاح في الكتالوج.",
    "modules.products.new.syncFailed": "فشل المزامنة",
    "modules.products.new.failedToEstablish": "فشل في إنشاء عقدة المنتج في السجل.",
    "modules.products.new.placeholders.nomenclature": "اسم_المنتج",
    "modules.products.new.placeholders.description": "وصف موجز للمنتج أو مواصفات المكونات...",
    "modules.products.new.placeholders.uom": "ISO_CODE",
    "modules.products.new.placeholders.minStock": "الحد_الأدنى",
    "modules.products.new.placeholders.maxStock": "الحد_الأقصى",
    "modules.products.new.placeholders.leadTime": "أيام",
    "modules.products.new.placeholders.location": "المنطقة-الصندوق-الرف",
    "modules.products.new.placeholders.supplier": "معرف_المورد",

    # Pages: Analytics / Executive
    "pages.analytics.statusOptimal": "مثالي",
    "pages.executive.tabs.northStar": "نجم الشمال (North Star)",
    "pages.executive.tabs.sqdcp": "SQDCP",
    "pages.executive.tabs.senseiAi": "ذكاء Sensei",
    "pages.executive.tabs.riskPrediction": "تنبؤ المخاطر",
    "pages.executive.loading": "جاري التحميل...",
    "pages.executive.kpi.qualityScore": "نقاط الجودة",
    "pages.executive.kpi.deliveryScore": "نقاط التسليم",
    "pages.executive.kpi.costEfficiency": "كفاءة التكلفة",
    "pages.executive.kpi.workforce": "القوى العاملة",
    "pages.executive.kpi.overallScore": "النتيجة الإجمالية",
    "pages.executive.kpi.belowTarget": "أقل من الهدف",
    "pages.executive.kpi.awaitingData": "بانتظار البيانات",
    "pages.executive.ops.activeUsers": "المستخدمون النشطون",
    "pages.executive.ops.openWorkOrders": "أوامر العمل المفتوحة",
    "pages.executive.ops.productionEfficiency": "كفاءة الإنتاج",
    "pages.executive.ops.pendingApprovals": "موافقات معلقة",
    "pages.executive.sqdcp.safety": "السلامة",
    "pages.executive.sqdcp.quality": "الجودة",
    "pages.executive.sqdcp.delivery": "التسليم",
    "pages.executive.sqdcp.cost": "التكلفة",
    "pages.executive.sqdcp.people": "الأفراد",

    # Pages: Finance (Spanish contaminated?)
    "pages.finance.sections.delete": "حذف العقدة",
    "pages.finance.sections.edit": "تحرير المعلمات",
    "pages.finance.sections.view": "عرض المواصفات",

    # Pages: HR
    "pages.hr.unassignedRole": "دور غير معين",
    "pages.hr.noDepartment": "بدون قسم",
    "pages.hr.remote": "عن بعد",
    "pages.hr.unknownPosition": "منصب غير معروف",
    "pages.hr.candidateDetails": "تفاصيل المرشح",
    "pages.hr.searchPersonnel": "البحث عن الموظفين...",
    "pages.hr.searchJobs": "البحث عن وظائف...",
    "pages.hr.toast.employeeCreated": "تم إنشاء الموظف بنجاح",
    "pages.hr.toast.employeeCreatedTitle": "نجاح",
    "pages.hr.toast.employeeTerminated": "تم إنهاء سجل الموظف",
    "pages.hr.toast.jobCreated": "تم إنشاء فرصة عمل",
    "pages.hr.toast.jobDeleted": "تم حذف فرصة العمل",
    "pages.hr.toast.deletionFailed": "فشل في إجراء الحذف",
    "pages.hr.toast.applicationSubmitted": "تم تقديم الطلب",
    "pages.hr.toast.applicationMoved": "تم نقل الطلب إلى {status}",
    "pages.hr.toast.updateStatusFailed": "فشل تحديث حالة الطلب",
    "pages.hr.toast.leaveSubmitted": "تم تقديم طلب الإجازة",
    "pages.hr.toast.leaveApproved": "تمت الموافقة على طلب الإجازة",
    "pages.hr.toast.leaveApproveFailed": "فشل الموافقة على طلب الإجازة",
    "pages.hr.toast.leaveRejected": "تم رفض طلب الإجازة",
    "pages.hr.toast.leaveRejectFailed": "فشل رفض طلب الإجازة",
    "pages.hr.confirmTerminate.title": "إنهاء سجل الموظف",
    "pages.hr.confirmTerminate.description": "هل أنت متأكد أنك تريد إنهاء سجل هذا الموظف؟ لا يمكن التراجع عن هذا الإجراء.",
    "pages.hr.confirmDeleteJob.title": "حذف فرصة العمل",
    "pages.hr.confirmDeleteJob.description": "هل أنت متأكد أنك تريد حذف فرصة العمل هذه؟",
    "pages.hr.placeholders.email": "user@company.com",
    "pages.hr.placeholders.selectRegion": "اختر المنطقة",
    "pages.hr.placeholders.selectStatus": "اختر الحالة",
    "pages.hr.placeholders.jobDescription": "وصف الوظيفة...",
    "pages.hr.placeholders.requiredSkills": "المهارات المطلوبة...",
    "pages.hr.placeholders.selectPosition": "اختر المنصب",
    "pages.hr.placeholders.firstName": "الاسم الأول",
    "pages.hr.placeholders.lastName": "اسم العائلة",
    "pages.hr.placeholders.personalEmail": "email@example.com",
    "pages.hr.placeholders.portfolioUrl": "https://...",
    "pages.hr.placeholders.additionalNotes": "ملاحظات إضافية...",
    "pages.hr.placeholders.selectEmployee": "اختر الموظف",
    "pages.hr.placeholders.leaveReason": "سبب الإجازة...",

    # Pages: Warehouse
    "pages.warehouse.loading": "جاري تحميل بيانات المستودع...",
    "pages.warehouse.searchDescription": "بحث وإدارة جميع مخزون المستودع",
    "pages.warehouse.searchPlaceholder": "البحث في الأصناف...",
    "pages.warehouse.itemName": "اسم الصنف",
    "pages.warehouse.onHand": "متاح",
    "pages.warehouse.managePO": "إدارة إيصالات أوامر الشراء والمواد الواردة",
    "pages.warehouse.poReference": "مرجع أمر الشراء",
    "pages.warehouse.expectedDate": "التاريخ المتوقع",
    "pages.warehouse.inTransit": "في النقل",
    "pages.warehouse.manageShipments": "إدارة الشحنات ولوجستيات التسليم",
    "pages.warehouse.shipDate": "تاريخ الشحن",
    "pages.warehouse.activePickLists": "قوائم الالتقاط النشطة وتلبية الطلبات",
    "pages.warehouse.itemsPicked": "أصناف تم التقاطها",

    # Pages: Pipeline
    "pages.pipeline.tableHeaders.triageScore": "درجة الفرز\u200f",
    "pages.pipeline.tableHeaders.completeness": "الاكتمال\u200f",
    "pages.pipeline.new.placeholders.partNumber": "PN-XXXX\u200f",
    "pages.pipeline.new.placeholders.itemDescription": "وصف الصنف...\u200f",
    "pages.pipeline.new.placeholders.unit": "قطعة، كجم، إلخ.\u200f",

    # Pages: Customers (Old Fix)
    "pages.customers.detail.stats.pipelineMagnitude": "حجم مسار المبيعات",
    "pages.customers.toast.deactivated": "تم تعطيل العميل",

    # Pages: Quotes
    "pages.quotes.new.materialCost": "تكلفة المواد",
    "pages.quotes.new.laborCost": "تكلفة العمل",
    "pages.quotes.new.overheadCost": "التكاليف العامة",
    "pages.quotes.new.lineItemNotes": "ملاحظات البند",
    "pages.quotes.new.noAssumptions": "لا توجد افتراضات محددة",
    "pages.quotes.new.newQuote": "عرض سعر جديد",
    "pages.quotes.new.viewVersionHistory": "عرض سجل الإصدارات",
    "pages.quotes.new.addProductsPricing": "إضافة المنتجات والأسعار",
    "pages.quotes.new.toggleCostBreakdown": "تبديل تفاصيل التكلفة",
    "pages.quotes.new.unitPrice": "سعر الوحدة",
    "pages.quotes.new.internalCostingAnalysis": "تحليل التكاليف الداخلي",
    "pages.quotes.new.totalRevenue": "إجمالي الإيرادات",
    "pages.quotes.new.grossProfit": "إجمالي الربح",
    "pages.quotes.new.quickActions": "إجراءات سريعة",
    "pages.quotes.new.assumptionsVerified": "تم التحقق من الافتراضات",
    "pages.quotes.new.warningsPresent": "توجد تحذيرات",
    "pages.quotes.toast.savedDraft": "تم حفظ عرض السعر كمسودة",
    "pages.quotes.toast.submitted": "تم تقديم عرض السعر للموافقة",
    "pages.quotes.toast.saveFailed": "خطأ في حفظ عرض السعر",
    "pages.quotes.toast.tryAgain": "يرجى المحاولة مرة أخرى.",

    # Pages: Sales
    "pages.sales.noBid": "لا يوجد عطاء",
    "pages.sales.statusNew": "جديد",
    "pages.sales.statusReviewing": "قيد المراجعة",
    "pages.sales.statusQuoting": "قيد التسعير",
    "pages.sales.statusSubmitted": "تم التقديم",
    "pages.sales.totalRfqs": "إجمالي طلبات الأسعار",
    "pages.sales.avgResponseTime": "متوسط وقت الاستجابة",
    "pages.sales.conversionRate": "معدل التحويل",
    "pages.sales.dueDate": "تاريخ الاستحقاق",
    "pages.sales.receivedDate": "تاريخ الاستلام",
    "pages.sales.searchRfqs": "البحث في طلبات الأسعار...",

    # Andon / Obeya
    "pages.andon.toast.settingsSaved": "تم تحديث تفضيلات إشعارات الإشارة.",
    "pages.obeya.toast.loadFailed": "فشل تحميل بيانات عنصر Obeya"
}

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def update_nested_key(data, dotted_key, value):
    keys = dotted_key.split(".")
    current = data
    for i, key in enumerate(keys[:-1]):
        if key not in current:
            # If a key is missing in the path, create it (shouldn't happen often for cleanup but good for safety)
            current[key] = {}
        
        # If we hit a string too early (structure mismatch), we might need to handle it.
        # But assuming ar.json structure matches existing keys.
        if not isinstance(current[key], dict):
             # Force it to be a dict if it was a string? No, that breaks other things. 
             # Just warn and skip if structure is wildly different
             print(f"Skipping {dotted_key}: {key} is basic type but expected dict container.")
             return
        current = current[key]
    
    current[keys[-1]] = value

def main():
    print(f"Loading {AR_JSON_PATH}...")
    ar_data = load_json(AR_JSON_PATH)

    print(f"Loading {MISSING_KEYS_PATH}...")
    try:
        missing_keys_map = load_json(MISSING_KEYS_PATH)
    except FileNotFoundError:
        print("Missing keys file not found. Assuming we just rely on the hardcoded map.")
        missing_keys_map = {}

    count = 0
    # Iterate through our manually prepared translations
    for dotted_key, arabic_text in TRANSLATIONS.items():
        # Check if the key existed in the missing list? 
        # (Optional, but good to know we are actually fixing things mentioned)
        # We'll just apply blindly because we want to fix them.
        
        # Apply the fix
        update_nested_key(ar_data, dotted_key, arabic_text)
        count += 1

    print(f"Applied {count} translations.")
    
    print(f"Saving to {AR_JSON_PATH}...")
    save_json(AR_JSON_PATH, ar_data)
    print("Done.")

if __name__ == "__main__":
    main()
