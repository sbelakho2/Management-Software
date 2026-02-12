import json
import os
import sys

# Path to the files
AR_JSON_PATH = os.path.join(os.getcwd(), "frontend", "src", "locales", "ar.json")
MISSING_KEYS_PATH = os.path.join(os.getcwd(), "scripts", "missing_ar_strict.json")

# The dictionary of fix translations for Part 2
TRANSLATIONS = {
    # Pages: Obeya
    "pages.obeya.toast.itemDeleted": "تم حذف العنصر بنجاح",
    "pages.obeya.toast.deleteFailed": "فشل حذف العنصر",
    "pages.obeya.toast.commentAdded": "تمت إضافة التعليق",
    "pages.obeya.toast.commentFailed": "فشل إضافة التعليق",
    "pages.obeya.toast.statusUpdated": "تم تحديث الحالة",
    "pages.obeya.toast.statusFailed": "فشل تحديث الحالة",
    "pages.obeya.toast.created": "تم إنشاء لوحة Obeya",
    "pages.obeya.toast.createdDesc": "تمت تهيئة لوحة Obeya الرقمية الجديدة بنجاح.",

    # Pages: A3
    "pages.a3.toast.titleRequired": "يرجى إدخال عنوان لتقرير A3.",
    "pages.a3.toast.created": "تم إنشاء تقرير A3",
    "pages.a3.toast.createdDesc": "تمت تهيئة تقرير A3 الجديد بنجاح.",
    "pages.a3.toast.createFailed": "فشل إنشاء تقرير A3.",
    "pages.a3.toast.loadFailed": "فشل تحميل تفاصيل A3",
    "pages.a3.toast.export": "تصدير",
    "pages.a3.toast.exportDesc": "جاري بدء تصدير PDF...",
    "pages.a3.toast.updated": "تم تحديث تقرير A3",
    "pages.a3.toast.updatedDesc": "تم حفظ التغييرات بنجاح.",
    "pages.a3.toast.updateFailed": "فشل تحديث تقرير A3.",
    
    # Pages: CTQ
    "pages.ctq.toast.error": "خطأ",
    "pages.ctq.toast.loadFailed": "فشل تحميل تفاصيل CTQ",
    "pages.ctq.toast.success": "ناجح",
    "pages.ctq.toast.deleteFailed": "فشل حذف CTQ",
    "pages.ctq.toast.measurementAdded": "تمت إضافة القياس بنجاح",
    "pages.ctq.toast.measurementFailed": "فشل إضافة القياس",
    "pages.ctq.toast.exportStarted": "بدأ التصدير",
    "pages.ctq.toast.exportStartedDesc": "جاري إنشاء تقرير CTQ الخاص بك",
    "pages.ctq.detail.specificationDetails": "تفاصيل المواصفات",
    "pages.ctq.detail.qualityRequirements": "متطلبات خصائص الجودة",
    "pages.ctq.detail.nominalValue": "القيمة الاسمية",
    "pages.ctq.detail.upperTolerance": "الحد الأعلى للتفاوت",
    "pages.ctq.detail.lowerTolerance": "الحد الأدنى للتفاوت",
    "pages.ctq.detail.relatedRfq": "RFQ ذي الصلة",
    "pages.ctq.detail.partNumber": "رقم القطعة",
    "pages.ctq.detail.measurementInfo": "معلومات القياس",
    "pages.ctq.detail.howMeasured": "كيفية قياس هذه الخاصية",
    "pages.ctq.detail.measurementMethod": "طريقة القياس",
    "pages.ctq.detail.samplingPlan": "خطة أخذ العينات",
    "pages.ctq.detail.checkStage": "مرحلة الفحص",
    "pages.ctq.detail.evidenceRequired": "الأدلة المطلوبة",
    "pages.ctq.detail.lastUpdated": "آخر تحديث",
    "pages.ctq.detail.measurementHistory": "سجل القياسات",
    "pages.ctq.detail.recentResults": "نتائج القياس والاتجاهات الحديثة",
    "pages.ctq.detail.measuredBy": "تم القياس بواسطة",
    "pages.ctq.detail.deleteCtq": "حذف CTQ",
    "pages.ctq.detail.addMeasurement": "إضافة قياس",
    "pages.ctq.detail.measuredValue": "قيمة القياس",
    "pages.ctq.detail.notMeasured": "لم يتم القياس",
    "pages.ctq.measurementNotesPlaceholder": "أضف أي ملاحظات ذات صلة حول هذا القياس",

    # Pages: Exceptions
    "pages.exceptions.synchronizing": "مزامنة الاستثناءات التشغيلية",
    "pages.exceptions.zeroHighUrgency": "تم تحديد صفر عقد عالية الاستعجال",

    # Pages: Project Management
    "pages.projectManagement.toast.settingsSaved": "تم حفظ الإعدادات",
    "pages.projectManagement.toast.settingsSavedDesc": "تم تحديث إعدادات المشروع.",
    "pages.projectManagement.toast.saveFailed": "فشل الحفظ",
    "pages.projectManagement.toast.saveFailedDesc": "حدث خطأ أثناء حفظ التغييرات.",
    "pages.projectManagement.kanban.columns.new": "جديد",
    "pages.projectManagement.kanban.columns.ready": "جاهز",
    "pages.projectManagement.kanban.columns.inProgress": "قيد التنفيذ",
    "pages.projectManagement.kanban.columns.readyForTest": "جاهز للاختبار",
    "pages.projectManagement.kanban.columns.done": "تم",
    "pages.projectManagement.milestones.namePlaceholder": "اكتملت المرحلة 1",
    "pages.projectManagement.milestones.detailsPlaceholder": "التفاصيل...",
    "pages.projectManagement.wiki.searchPlaceholder": "بحث...",
    "pages.projectManagement.wiki.titlePlaceholder": "عنوان الصفحة",

    # Pages: Admin Import (Prefix matching pages.* caught these)
    "pages.admin.import.conflictResolution": "حل النزاع",
    "pages.admin.import.skipExisting": "تجاوز الموجود",
    "pages.admin.import.updateExisting": "تحديث الموجود",
    
    # Pages: Quoting Helper (Prefix matching pages.* caught these)
    "pages.quotingHelper.noQuoteFound": "لم يتم العثور على عرض سعر",
    "pages.quotingHelper.toast.handoffSuccess": "نجاح تسليم NPI",
    "pages.quotingHelper.toast.handoffFailed": "فشل التسليم",

    # Pages: Pipeline (Prefix matching pages.* caught these)
    "pages.pipeline.new.placeholders.partNumber": "PN-XXXX\u200f",

    # Pages: Executive
    "pages.executive.tabs.sqdcp": "SQDCP",
    "executive.title": "لوحة المعلومات التنفيذية",
    "executive.kpis": "مؤشرات الأداء الرئيسية (KPIs)",
    "executive.northStar": "نجم الشمال (North Star)",
    "executive.riskDashboard": "لوحة معلومات المخاطر",
    "executive.strategicDirectives.title": "التوجيهات الاستراتيجية",
    "executive.strategicDirectives.addDirective": "إضافة توجيه",
    "executive.strategicDirectives.status": "الحالة",
    "executive.strategicDirectives.progress": "التقدم",
    "executive.strategicDirectives.active": "نشط\u200f",
    "executive.strategicDirectives.completed": "مكتمل",
    "executive.strategicDirectives.onHold": "معلق",
    "executive.nl2sql.title": "استعلام اللغة الطبيعية",
    "executive.nl2sql.placeholder": "اطرح سؤالاً حول بياناتك...",
    "executive.nl2sql.execute": "تنفيد الاستعلام",

    # Maintenance
    "maintenance.title": "الصيانة",
    "maintenance.assets.title": "الأصول",
    "maintenance.assets.addAsset": "إضافة أصل",
    "maintenance.assets.name": "اسم الأصل",
    "maintenance.assets.serialNumber": "الرقم التسلسلي",
    "maintenance.assets.location": "الموقع",
    "maintenance.assets.status": "الحالة",
    "maintenance.assets.operational": "تشغيلي",
    "maintenance.assets.needsRepair": "يحتاج إصلاح",
    "maintenance.assets.outOfService": "خارج الخدمة",
    "maintenance.assets.searchPlaceholder": "بحث في الأصول...",
    "maintenance.workOrders.title": "أوامر العمل",
    "maintenance.workOrders.addWorkOrder": "إنشاء أمر عمل",
    "maintenance.workOrders.title_field": "العنوان",
    "maintenance.workOrders.priority": "الأولوية",
    "maintenance.workOrders.status": "الحالة",
    "maintenance.workOrders.assignee": "المكلف",
    "maintenance.workOrders.dueDate": "تاريخ الاستحقاق",
    "maintenance.workOrders.open": "مفتوح",
    "maintenance.workOrders.inProgress": "قيد التنفيذ",
    "maintenance.workOrders.completed": "مكتمل",
    "maintenance.workOrders.cancelled": "ملغي",
    "maintenance.preventiveMaintenance.title": "الصيانة الوقائية",
    "maintenance.preventiveMaintenance.schedule": "الجدول",
    "maintenance.preventiveMaintenance.frequency": "التكرار",
    "maintenance.preventiveMaintenance.lastCompleted": "آخر إكمال",
    "maintenance.preventiveMaintenance.nextDue": "الاستحقاق القادم",
    "maintenance.tabs.assets": "الأصول",
    "maintenance.tabs.workOrders": "أوامر العمل",
    "maintenance.tabs.pmSchedules": "جداول الصيانة الوقائية",
    "maintenance.tabs.tools": "الأدوات",
    "maintenance.tabs.warranties": "الضمانات",
    "maintenance.tabs.loto": "تأمين/توسيم (LOTO)",
    "maintenance.tabs.fieldReturns": "مرتجعات ميدانية",
    "maintenance.tabs.budgets": "الميزانيات",

    # Tour
    "tour.back": "سابق",
    "tour.next": "تال",
    "tour.finish": "إنهاء",
    "tour.closeTour": "إغلاق الجولة",
    "tour.productTour": "جولة في المنتج",
    "tour.stepOf": "{current} \u0645\u0646 {total}\u200f",

    # Components: Empty State
    "components.emptyState.noResultsFound": "لم يتم العثور على نتائج",
    "components.emptyState.noItemsYet": "لا توجد عناصر بعد",
    "components.emptyState.noRfqsInQueue": "لا توجد طلبات عروض أسعار في قائمة الانتظار",
    "components.emptyState.noQuotesCreated": "لم يتم إنشاء عروض أسعار",
    "components.emptyState.noActiveJobs": "لا توجد وظائف نشطة",

    # Components: Error State
    "components.errorState.connectionError": "خطأ في الاتصال",
    "components.errorState.connectionErrorDesc": "تعذر الوصول إلى الخادم. يرجى التحقق من اتصالك والمحاولة مرة أخرى.",
    "components.errorState.serverError": "خطأ في الخادم",
    "components.errorState.serverErrorDesc": "حدث خطأ ما من جانبنا. يرجى المحاولة مرة أخرى لاحقًا.",
    "components.errorState.noData": "لا توجد بيانات",
    "components.errorState.noDataDesc": "لم يتم العثور على سجلات تطابق معاييرك.",
    "components.errorState.accessDenied": "تم رفض الوصول",
    "components.errorState.accessDeniedDesc": "ليس لديك إذن للوصول إلى هذا المورد.",
    "components.errorState.notFound": "غير موجود",
    "components.errorState.notFoundDesc": "تعذر العثور على المورد المطلوب.",
    "components.errorState.error": "خطأ",
    "components.errorState.errorDesc": "حدث خطأ غير متوقع.",
    "components.errorState.tryAgain": "حاول مرة أخرى",

    # Components: Gantt Chart
    "components.ganttChart.noTasks": "لا توجد مهام لتصورها في غانت",
    "components.ganttChart.taskName": "اسم المهمة",

    # Components: Table
    "components.table.noData": "لا توجد بيانات",
    "components.table.rowsPerPage": "صفوف لكل صفحة:",

    # Modules: Production (Rest of them)
    "production.title": "الإنتاج",
    "production.workOrders.title": "أوامر العمل",
    "production.workOrders.addWorkOrder": "إنشاء أمر عمل",
    "production.workOrders.woNumber": "رقم أمر العمل",
    "production.workOrders.product": "المنتج",
    "production.workOrders.quantity": "الكمية",
    "production.workOrders.status": "الحالة",
    "production.workOrders.planned": "مخطط",
    "production.workOrders.released": "صدر",
    "production.workOrders.inProgress": "قيد التنفيذ",
    "production.workOrders.completed": "مكتمل",
    "production.workOrders.priority": "الأولوية",
    "production.workOrders.startDate": "تاريخ البدء",
    "production.workOrders.dueDate": "تاريخ الاستحقاق",
    "production.scheduling.title": "الجدولة",
    "production.scheduling.gantt": "مخطط غانت",
    "production.scheduling.calendar": "التقويم",
    "production.tabs.workOrders": "أوامر العمل",
    "production.tabs.scheduling": "الجدولة",

    # Modules: Quality (Rest of them)
    "quality.title": "الجودة",
    "quality.inspections.title": "عمليات التفتيش",
    "quality.inspections.addInspection": "تفتيش جديد",
    "quality.inspections.workOrder": "أمر العمل",
    "quality.inspections.product": "المنتج",
    "quality.inspections.type": "النوع",
    "quality.inspections.date": "تاريخ التفتيش",
    "quality.inspections.status": "الحالة",
    "quality.inspections.passed": "نجح",
    "quality.inspections.failed": "فشل",
    "quality.inspections.pending": "معلق",
    "quality.inspections.quantityInspected": "الكمية التي تم فحصها",
    "quality.inspections.quantityPassed": "الكمية المقبولة",
    "quality.inspections.quantityFailed": "الكمية المرفوضة",
    "quality.inspections.searchPlaceholder": "بحث في عمليات التفتيش...",
    "quality.ncrs.title": "تقارير عدم المطابقة (NCRs)",
    "quality.ncrs.addNCR": "إنشاء NCR",
    "quality.ncrs.severity": "الشدة",
    "quality.ncrs.critical": "حرج",
    "quality.ncrs.major": "كبير",
    "quality.ncrs.minor": "طفيف",
    "quality.ncrs.rootCause": "السبب الجذري",
    "quality.ncrs.containmentAction": "إجراء الاحتواء",
    "quality.capas.title": "CAPA",
    "quality.capas.addCAPA": "إنشاء CAPA",
    "quality.capas.correctiveAction": "إجراء تصحيحي",
    "quality.capas.preventiveAction": "إجراء وقائي",
    "quality.capas.effectiveness": "الفعالية",
    "quality.msa.title": "دراسات MSA",
    "quality.msa.gageRR": "Gage R&R",
    "quality.msa.compute": "حساب GRR",
    "quality.msa.repeatability": "التكرارية (Repeatability)",
    "quality.msa.reproducibility": "إعادة الإنتاج (Reproducibility)",
    "quality.capability.title": "قدرة العملية (Process Capability)",
    "quality.capability.compute": "حساب Cp/Cpk",
    "quality.capability.cpk": "Cpk",
    "quality.capability.cp": "Cp",
    "quality.capability.pp": "Pp",
    "quality.capability.ppk": "Ppk",
    "quality.tabs.inspections": "عمليات التفتيش",
    "quality.tabs.ncrs": "NCRs",
    "quality.tabs.capas": "CAPAs",
    "quality.tabs.msa": "MSA",
    "quality.tabs.capability": "القدرة",
    "quality.tabs.complaints": "الشكاوى",
    "quality.tabs.surveys": "الاستطلاعات",
    "quality.tabs.fai": "FAI",
    "quality.tabs.selfInspection": "التفتيش الذاتي",
    "quality.tabs.labTesting": "الاختبار المعملي",
    "quality.tabs.aql": "أخذ العينات AQL",
    "quality.tabs.traceability": "التتبع",
    "quality.tabs.changePoint": "نقطة التغيير",
    
    # Quality: Grr
    "quality.grr.analysisResults": "نتائج تحليل GRR",
    "quality.grr.gauge": "المقياس: {name}",
    "quality.grr.totalGageRR": "إجمالي Gage R&R",
    "quality.grr.excellent": "ممتاز",
    "quality.grr.acceptable": "مقبول",
    "quality.grr.unacceptable": "غير مقبول",
    "quality.grr.msgExcellent": "نظام القياس مقبول",
    "quality.grr.msgAcceptable": "قد يكون مقبولاً حسب التطبيق",
    "quality.grr.msgUnacceptable": "نظام القياس يحتاج إلى تحسين",
    "quality.grr.variationBreakdown": "تفصيل التباين",
    "quality.grr.variationTooltip": "يوضح مساهمة كل مصدر في التباين الكلي. انخفاض EV + AV (GRR) يعني نظام قياس أفضل.",
    "quality.grr.equipmentVariation": "تباين المعدات (EV): {value}%",
    "quality.grr.repeatability": "التكرارية",
    "quality.grr.appraiserVariation": "تباين المقيّم (AV): {value}%",
    "quality.grr.reproducibility": "إعادة الإنتاج",
    "quality.grr.partVariationPct": "تباين القطعة (PV): {value}%",
    "quality.grr.actualPartVariation": "التباين الفعلي من قطعة إلى قطعة",
    "quality.grr.legendEV": "EV (التكرارية)",
    "quality.grr.legendAV": "AV (إعادة الإنتاج)",
    "quality.grr.legendPV": "PV (تباين القطعة)",
    "quality.grr.repeatabilityEV": "التكرارية (EV)",
    "quality.grr.reproducibilityAV": "إعادة الإنتاج (AV)",
    "quality.grr.partVariation": "تباين القطعة (PV)",
    "quality.grr.totalVariation": "التباين الكلي (TV)",
    "quality.grr.ndcTitle": "عدد الفئات المتميزة (NDC)",
    "quality.grr.ndcAcceptable": "\u2265 5 (مقبول)",
    "quality.grr.ndcNeedsImprovement": "< 5 (يحتاج تحسين)",
    "quality.grr.ndcDescription": "يمثل NDC عدد فئات الأجزاء المتميزة التي يمكن لنظام القياس تمييزها بشكل موثوق. توصي AIAG بحد أدنى 5 فئات متميزة.",
    "quality.grr.aiagGuidelines": "إرشادات AIAG MSA:",
    "quality.grr.aiagExcellent": "< 10% GRR: نظام القياس مقبول",
    "quality.grr.aiagAcceptable": "10-30% GRR: قد يكون مقبولاً بناءً على أهمية التطبيق",
    "quality.grr.aiagUnacceptable": "> 30% GRR: نظام القياس يحتاج إلى تحسين",

    # HR (Found mixed in previous analysis)
    "pages.hr.placeholders.email": "user@company.com",
    "pages.hr.placeholders.personalEmail": "email@example.com",
    "pages.hr.placeholders.portfolioUrl": "https://...",
    "hr.title": "الموارد البشرية",
    "hr.employees.title": "الموظفين",
    "hr.employees.addEmployee": "إضافة موظف",
    "hr.employees.editEmployee": "تعديل موظف",
    "hr.employees.firstName": "الاسم الأول",
    "hr.employees.lastName": "اسم العائلة",
    "hr.employees.email": "البريد الإلكتروني",
    "hr.employees.department": "القسم",
    "hr.employees.position": "المنصب",
    "hr.employees.status": "الحالة",
    "hr.employees.active": "نشط\u200f",
    "hr.employees.inactive": "غير نشط\u200f",
    "hr.employees.onLeave": "في إجازة",
    "hr.employees.hireDate": "تاريخ التوظيف",
    "hr.employees.searchPlaceholder": "بحث في الموظفين...",
    "hr.employees.noEmployees": "لم يتم العثور على موظفين",
    "hr.employees.createSuccess": "تم إنشاء الموظف بنجاح",
    "hr.employees.updateSuccess": "تم تحديث الموظف بنجاح",
    "hr.employees.deleteSuccess": "تمت إزالة الموظف بنجاح",
    "hr.employees.deleteConfirm": "هل أنت متأكد أنك تريد حذف هذا الموظف؟",
    "hr.employees.requiredField": "هذا الحقل مطلوب",
    "hr.employees.invalidEmail": "يرجى إدخال عنوان بريد إلكتروني صالح",
    "hr.jobOpenings.title": "الفرص الوظيفية",
    "hr.jobOpenings.addOpening": "إضافة فرصة عمل",
    "hr.jobOpenings.jobTitle": "المسمى الوظيفي",
    "hr.jobOpenings.department": "القسم",
    "hr.jobOpenings.location": "الموقع",
    "hr.jobOpenings.type": "نوع التوظيف",
    "hr.jobOpenings.status": "الحالة",
    "hr.jobOpenings.open": "مفتوح",
    "hr.jobOpenings.closed": "مغلق",
    "hr.jobOpenings.filled": "مشغول",
    "hr.jobOpenings.postedDate": "تاريخ النشر",
    "hr.jobOpenings.closingDate": "تاريخ الإغلاق",
    "hr.jobOpenings.applications": "الطلبات",
    "hr.jobOpenings.noOpenings": "لا توجد فرص وظيفية",
    "hr.leaveRequests.title": "طلبات الإجازة",
    "hr.leaveRequests.addRequest": "طلب إجازة جديد",
    "hr.leaveRequests.employee": "الموظف",
    "hr.leaveRequests.leaveType": "نوع الإجازة",
    "hr.leaveRequests.startDate": "تاريخ البدء",
    "hr.leaveRequests.endDate": "تاريخ الانتهاء",
    "hr.leaveRequests.status": "الحالة",
    "hr.leaveRequests.pending": "معلق",
    "hr.leaveRequests.approved": "موافق عليه",
    "hr.leaveRequests.rejected": "مرفوض",
    "hr.leaveRequests.reason": "السبب",
    "hr.leaveRequests.noRequests": "لا توجد طلبات إجازة",
    "hr.leaveRequests.approve": "موافقة",
    "hr.leaveRequests.reject": "رفض",
    "hr.applicationsPipeline.title": "خط أنابيب الطلبات",
    "hr.applicationsPipeline.applied": "متقدم",
    "hr.applicationsPipeline.screening": "فحص",
    "hr.applicationsPipeline.interview": "مقابلة",
    "hr.applicationsPipeline.offered": "عرض عمل",
    "hr.applicationsPipeline.hired": "تم التعيين",
    "hr.tabs.employees": "الموظفين",
    "hr.tabs.jobOpenings": "الفرص الوظيفية",
    "hr.tabs.leaveRequests": "طلبات الإجازة",
    "hr.tabs.applicationsPipeline": "خط أنابيب الطلبات",
    "hr.toasts.employeeCreated": "تم إنشاء الموظف بنجاح",
    "hr.toasts.employeeUpdated": "تم تحديث الموظف بنجاح",
    "hr.toasts.leaveApproved": "تمت الموافقة على طلب الإجازة",
    "hr.toasts.leaveRejected": "تم رفض طلب الإجازة",
    "hr.toasts.openingCreated": "تم إنشاء فرصة العمل",

    # Training
    "training.title": "تدريب",
    "training.certifications.title": "الشهادات",
    "training.certifications.name": "اسم الشهادة",
    "training.certifications.status": "الحالة",
    "training.certifications.enrolled": "مسجل",
    "training.certifications.inProgress": "قيد التقدم",
    "training.certifications.completed": "مكتمل",
    "training.certifications.expired": "منتهي الصلاحية",
    "training.certifications.expiryDate": "تاريخ انتهاء الصلاحية",
    "training.programs.title": "برامج التدريب",
    "training.programs.addProgram": "إضافة برنامج",
    "training.programs.name": "اسم البرنامج",
    "training.programs.duration": "المدة",
    "training.programs.participants": "المشاركون",
    "training.records.title": "سجلات التدريب",
    "training.records.employee": "الموظف",
    "training.records.course": "الدورة",
    "training.records.completedDate": "تاريخ الإكمال",
    "training.records.score": "النتيجة",
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
            current[key] = {}
        
        if not isinstance(current[key], dict):
             print(f"Skipping {dotted_key}: {key} is basic type but expected dict container.")
             return
        current = current[key]
    
    current[keys[-1]] = value

def main():
    print(f"Loading {AR_JSON_PATH}...")
    try:
        ar_data = load_json(AR_JSON_PATH)
    except Exception as e:
        print(f"Error loading {AR_JSON_PATH}: {e}")
        return

    count = 0
    # Iterate through our manually prepared translations
    for dotted_key, arabic_text in TRANSLATIONS.items():
        update_nested_key(ar_data, dotted_key, arabic_text)
        count += 1

    print(f"Applied {count} translations.")
    
    print(f"Saving to {AR_JSON_PATH}...")
    save_json(AR_JSON_PATH, ar_data)
    print("Done.")

if __name__ == "__main__":
    main()
