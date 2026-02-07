import json
import re

def update_json_file(file_path, updates, language):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return

    # Helper recursive function to update data
    def recursive_update(d, u):
        for k, v in u.items():
            if isinstance(v, dict):
                d[k] = recursive_update(d.get(k, {}), v)
            else:
                d[k] = v
        return d

    data = recursive_update(data, updates)

    # Specific Fixes for Spanish Uppercase
    if language == 'es':
         replacements = {
             "SEÑAL_DE_CONFIANZA": "Señal de confianza",
             "PROMEDIO_HISTÓRICO": "Promedio histórico",
             "SALUD_DEL_MODELO_AUTÓNOMO": "Salud del modelo autónomo",
             "AUDITORÍA": "Auditoría",
             "CRÍTICA": "Crítica",
             "RECEPCIÓN": "Recepción",
             "REVISIÓN": "Revisión",
             "N.º_DE_SERIE": "N.º de serie",
             "N.º_LOTE": "N.º lote",
             "CANTIDAD": "Cantidad",
             "UBICACIÓN": "Ubicación",
             "ESTADO": "Estado",
             "NOTAS": "Notas"
         }
         def fix_values(obj):
             if isinstance(obj, dict):
                 return {k: fix_values(v) for k, v in obj.items()}
             elif isinstance(obj, str):
                 if obj in replacements:
                     return replacements[obj]
                 # Fallback for dynamic containing strings if needed, but mostly exact matches found
                 return obj
             return obj
         data = fix_values(data)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Updated {file_path}")

# Data for Auth Section (top level usually, or under auth key which looks blended in root in provided grep)
# Based on grep, "loading": "Loading authentication..." is at root level or mixed in. 
# Looking at grep output: 
# "termsAgreement": "...",
# "loading": "Loading authentication...",
# "error": { ... }
# It seems these are in a specific section, likely 'auth' or root. 
# However, keys like "loading" are generic.
# Let's assume the grep context was accurate and map correctly. 
# Actually, looking at file reads, `termsAgreement` is around line 317 in fr.json.
# It seems "auth" keys might be flat in the root or in a container I missed.
# I will establish them as top level overrides for simplicity if they exist there, 
# or keys in 'auth' object.
# To be safe, I've seen "loading" generic key in root. 
# BUT the specific "Loading authentication..." text suggests the key `loading` *is* often overloaded or this is a specific `auth.loading`.
# Given the grep showed:
# "loading": "Loading authentication...",
# I will target that specific key/value pair's location if I can, but since I am using dictionary update, I need the path.
# If "termsAgreement" is a sibling, I can check if they are in an "auth" object.
# Common practice: `auth: { ... }`.
# I'll try to update `auth` object structure.

auth_updates = {
    "ar": {
        "auth": {
            "loading": "جارٍ تحميل المصادقة...",
            "error": {
                "title": "خطأ في المصادقة",
                "description": "لم نتمكن من إكمال عملية المصادقة.",
                "tryAgain": "حاول مرة أخرى",
                "backToLogin": "العودة لتسجيل الدخول"
            }
        }
    },
    "fr": {
        "auth": {
            "loading": "Chargement de l'authentification...",
            "error": {
                "title": "Erreur d'authentification",
                "description": "Nous n'avons pas pu terminer le processus d'authentification.",
                "tryAgain": "Réessayer",
                "backToLogin": "Retour à la connexion"
            }
        }
    },
    "es": {
        "auth": {
            "loading": "Cargando autenticación...",
            "error": {
                "title": "Error de autenticación",
                "description": "No pudimos completar el proceso de autenticación.",
                "tryAgain": "Intentar de nuevo",
                "backToLogin": "Volver a iniciar sesión"
            }
        }
    },
    "de": {
        "auth": {
            "loading": "Authentifizierung wird geladen...",
            "error": {
                "title": "Authentifizierungsfehler",
                "description": "Wir konnten den Authentifizierungsprozess nicht abschließen.",
                "tryAgain": "Erneut versuchen",
                "backToLogin": "Zurück zum Login"
            }
        }
    }
}

email_updates = {
    "ar": {
        "emailDrafting": {
            "title": "صياغة البريد الإلكتروني بالذكاء الاصطناعي",
            "aria": {
                "selectPurpose": "اختر الغرض",
                "toneGroup": "اختر النبرة",
                "selectLanguage": "اختر اللغة",
                "recipientEmail": "بريد المستلم",
                "recipientName": "اسم المستلم",
                "addKeyPoint": "أضف نقطة رئيسية",
                "keyPointsList": "قائمة النقاط الرئيسية",
                "removeKeyPoint": "إزالة: {point}",
                "copyToClipboard": "نسخ إلى الحافظة",
                "editSubject": "تعديل الموضوع",
                "close": "إغلاق",
                "draftsList": "مسودات البريد الإلكتروني"
            },
            "placeholders": {
                "selectPurpose": "اختر الغرض...",
                "recipientEmail": "recipient@example.com",
                "recipientNameOptional": "الاسم (اختياري)",
                "keyPoint": "أضف نقطة رئيسية",
                "senderName": "مثال: أحمد محمد",
                "senderEmail": "مثال: ahmed@sensei.com",
                "senderTitle": "مثال: مدير الحساب",
                "companyName": "مثال: شركة سينسي",
                "threadEntityType": "اختر نوع الكيان...",
                "threadEntityId": "أدخل معرف الكيان...",
                "referenceNumber": "مثال: RFQ-2024-001",
                "subjectHint": "مثال: تحديث الأسعار للربع الثاني"
            },
            "purpose": {
                "missingInfoRequest": "طلب معلومات مفقودة",
                "quoteFollowup": "متابعة عرض الأسعار",
                "quoteSubmission": "تقديم عرض السعر",
                "supplierInquiry": "استفسار المورد",
                "meetingRequest": "طلب اجتماع",
                "meetingConfirmation": "تأكيد الاجتماع",
                "meetingReschedule": "إعادة جدولة الاجتماع",
                "issueNotification": "إشعار بمشكلة",
                "statusUpdate": "تحديث الحالة",
                "thankYou": "شكر",
                "introduction": "مقدمة",
                "escalation": "تصعيد",
                "apology": "اعتذار",
                "custom": "بريد مخصص"
            },
            "tone": {
                "formal": "رسمي",
                "professional": "مهني",
                "friendly": "ودي",
                "urgent": "عاجل",
                "apologetic": "اعتذاري",
                "appreciative": "تقديري",
                "concise": "موجز"
            },
            "language": {
                "english": "الإنجليزية",
                "french": "الفرنسية",
                "german": "الألمانية",
                "spanish": "الإسبانية",
                "italian": "الإيطالية",
                "portuguese": "البرتغالية",
                "japanese": "اليابانية",
                "chinese": "الصينية",
                "korean": "الكورية",
                "arabic": "العربية"
            },
            "actions": {
                "add": "أضف",
                "apply": "تطبيق",
                "edit": "تعديل",
                "generating": "جارٍ التوليد...",
                "generateDraft": "توليد مسودة",
                "regenerate": "إعادة التوليد",
                "send": "إرسال"
            },
            "preview": {
                "title": "معاينة المسودة",
                "subjectLabel": "الموضوع",
                "confidence": "الثقة: {score}",
                "generatedIn": "تم التوليد في {time}"
            },
            "units": {
                "milliseconds": "ملي ثانية",
                "seconds": "ثانية"
            },
            "compliance": {
                "none": "لم يتم اكتشاف مشكلات الامتثال",
                "title": "مشكلات الامتثال ({count})"
            },
            "suggestions": {
                "title": "الاقتراحات ({count})"
            },
            "alternatives": {
                "title": "مواضيع بديلة:"
            },
            "thread": {
                "entityType": {
                    "rfq": "RFQ",
                    "quote": "عرض سعر",
                    "workOrder": "أمر عمل",
                    "opportunity": "فرصة",
                    "nonConformance": "عدم مطابقة",
                    "shipment": "شحنة",
                    "invoice": "فاتورة"
                },
                "loadFailed": "فشل تحميل تتبع السلسلة",
                "helper": "اربط هذه المسودة بسلسلة للحفاظ على سياق البيانات.",
                "loading": "جارٍ تحميل تتبع السلسلة...",
                "traceTitle": "تتبع السلسلة",
                "traceStats": "التتبع: {nodes} عقد / {edges} روابط",
                "reasoningId": "معرف المنطق: {id}"
            },
            "defaults": {
                "senderName": "مشغل سينسي",
                "senderEmail": "operator@sensei.com",
                "companyName": "سينسي"
            },
            "sections": {
                "recipient": "المستلم",
                "purpose": "الغرض",
                "sender": "المرسل",
                "threadContext": "سياق السلسلة",
                "tone": "النبرة",
                "language": "اللغة",
                "keyPoints": "النقاط الرئيسية"
            },
            "fields": {
                "senderName": "اسم المرسل",
                "senderEmail": "بريد المرسل",
                "senderTitle": "المسمى الوظيفي للمرسل",
                "companyName": "اسم الشركة",
                "threadEntityType": "نوع كيان السلسلة",
                "threadEntityId": "معرف كيان السلسلة",
                "referenceNumberOptional": "رقم المرجع (اختياري)",
                "subjectHintOptional": "تلميح الموضوع (اختياري)"
            },
            "status": {
                "generating": "جارٍ التوليد...",
                "ready": "جاهز للمراجعة",
                "reviewed": "تمت المراجعة",
                "approved": "تمت الموافقة",
                "sent": "تم الإرسال",
                "discarded": "تم التجاهل",
                "failed": "فشل"
            },
            "notifications": {
                "copied": "تم النسخ إلى الحافظة!"
            },
            "empty": {
                "title": "لا توجد مسودة بعد",
                "description": "أنشئ مسودة لرؤية المعاينة وفحوصات الامتثال.",
                "list": "لا توجد مسودات بعد"
            },
            "drafts": {
                "snippet": "{snippet}..."
            },
            "validation": {
                "emailRequired": "البريد الإلكتروني مطلوب",
                "emailInvalid": "صيغة البريد غير صالحة"
            }
        }
    },
    "fr": {
        "emailDrafting": {
            "title": "Rédacteur d'e-mails IA",
            "aria": {
                "selectPurpose": "Sélectionner l'objectif",
                "toneGroup": "Sélectionner le ton",
                "selectLanguage": "Sélectionner la langue",
                "recipientEmail": "Email du destinataire",
                "recipientName": "Nom du destinataire",
                "addKeyPoint": "Ajouter un point clé",
                "keyPointsList": "Liste des points clés",
                "removeKeyPoint": "Supprimer : {point}",
                "copyToClipboard": "Copier dans le presse-papiers",
                "editSubject": "Modifier l'objet",
                "close": "Fermer",
                "draftsList": "Brouillons d'e-mails"
            },
            "placeholders": {
                "selectPurpose": "Sélectionner l'objectif...",
                "recipientEmail": "destinataire@exemple.com",
                "recipientNameOptional": "Nom (optionnel)",
                "keyPoint": "Ajouter un point clé",
                "senderName": "ex. Alex Durand",
                "senderEmail": "ex. alex@sensei.com",
                "senderTitle": "ex. Responsable de compte",
                "companyName": "ex. Sensei Corp",
                "threadEntityType": "Sélectionner l'entité du fil...",
                "threadEntityId": "Entrer l'ID de l'entité...",
                "referenceNumber": "ex. RFQ-2024-001",
                "subjectHint": "ex. Mise à jour des tarifs T2"
            },
            "purpose": {
                "missingInfoRequest": "Demande d'informations manquantes",
                "quoteFollowup": "Suivi de devis",
                "quoteSubmission": "Soumission de devis",
                "supplierInquiry": "Demande fournisseur",
                "meetingRequest": "Demande de rendez-vous",
                "meetingConfirmation": "Confirmation de rendez-vous",
                "meetingReschedule": "Reprogrammation de rendez-vous",
                "issueNotification": "Signalement de problème",
                "statusUpdate": "Mise à jour de statut",
                "thankYou": "Remerciements",
                "introduction": "Introduction",
                "escalation": "Escalade",
                "apology": "Excuses",
                "custom": "E-mail personnalisé"
            },
             "tone": {
                "formal": "Formel",
                "professional": "Professionnel",
                "friendly": "Amical",
                "urgent": "Urgent",
                "apologetic": "Désolé",
                "appreciative": "Reconnaissant",
                "concise": "Concis"
            },
            "language": {
                "english": "Anglais",
                "french": "Français",
                "german": "Allemand",
                "spanish": "Espagnol",
                "italian": "Italien",
                "portuguese": "Portugais",
                "japanese": "Japonais",
                "chinese": "Chinois",
                "korean": "Coréen",
                "arabic": "Arabe"
            },
            "actions": {
                "add": "Ajouter",
                "apply": "Appliquer",
                "edit": "Modifier",
                "generating": "Génération...",
                "generateDraft": "Générer le brouillon",
                "regenerate": "Régénérer",
                "send": "Envoyer"
            },
            "preview": {
                "title": "Aperçu du brouillon",
                "subjectLabel": "Objet",
                "confidence": "Confiance : {score}",
                "generatedIn": "Généré en {time}"
            },
            "units": {
                "milliseconds": "ms",
                "seconds": "s"
            },
            "compliance": {
                "none": "Aucun problème de conformité détecté",
                "title": "Problèmes de conformité ({count})"
            },
            "suggestions": {
                "title": "Suggestions ({count})"
            },
            "alternatives": {
                "title": "Sujets alternatifs :"
            },
            "thread": {
                "entityType": {
                    "rfq": "Appel d'offres",
                    "quote": "Devis",
                    "workOrder": "Ordre de travail",
                    "opportunity": "Opportunité",
                    "nonConformance": "Non-conformité",
                    "shipment": "Expédition",
                    "invoice": "Facture"
                },
                "loadFailed": "Échec du chargement de la trace du fil",
                "helper": "Connectez ce brouillon à un fil pour maintenir le contexte des données.",
                "loading": "Chargement de la trace du fil...",
                "traceTitle": "Trace du fil",
                "traceStats": "Trace : {nodes} nœuds / {edges} liens",
                "reasoningId": "ID de raisonnement : {id}"
            },
            "defaults": {
                "senderName": "Opérateur Sensei",
                "senderEmail": "operateur@sensei.com",
                "companyName": "Sensei"
            },
            "sections": {
                "recipient": "Destinataire",
                "purpose": "Objectif",
                "sender": "Expéditeur",
                "threadContext": "Contexte du fil",
                "tone": "Ton",
                "language": "Langue",
                "keyPoints": "Points clés"
            },
            "fields": {
                "senderName": "Nom de l'expéditeur",
                "senderEmail": "Email de l'expéditeur",
                "senderTitle": "Titre de l'expéditeur",
                "companyName": "Nom de l'entreprise",
                "threadEntityType": "Type d'entité du fil",
                "threadEntityId": "ID de l'entité du fil",
                "referenceNumberOptional": "Numéro de référence (optionnel)",
                "subjectHintOptional": "Indice de l'objet (optionnel)"
            },
            "status": {
                "generating": "Génération...",
                "ready": "Prêt pour examen",
                "reviewed": "Examiné",
                "approved": "Approuvé",
                "sent": "Envoyé",
                "discarded": "Rejeté",
                "failed": "Échoué"
            },
            "notifications": {
                "copied": "Copié dans le presse-papiers !"
            },
            "empty": {
                "title": "Pas encore de brouillon",
                "description": "Générez un brouillon pour voir l'aperçu et les contrôles de conformité.",
                "list": "Aucun brouillon pour le moment"
            },
            "drafts": {
                "snippet": "{snippet}…"
            },
            "validation": {
                "emailRequired": "L'e-mail est requis",
                "emailInvalid": "Format d'e-mail invalide"
            }
        }
    },
    "es": {
         "emailDrafting": {
            "title": "Redactor de correos IA",
            "aria": {
                "selectPurpose": "Seleccionar propósito",
                "toneGroup": "Seleccionar tono",
                "selectLanguage": "Seleccionar idioma",
                "recipientEmail": "Correo del destinatario",
                "recipientName": "Nombre del destinatario",
                "addKeyPoint": "Añadir punto clave",
                "keyPointsList": "Lista de puntos clave",
                "removeKeyPoint": "Eliminar: {point}",
                "copyToClipboard": "Copiar al portapapeles",
                "editSubject": "Editar asunto",
                "close": "Cerrar",
                "draftsList": "Borradores de correo"
            },
            "placeholders": {
                "selectPurpose": "Seleccionar propósito...",
                "recipientEmail": "destinatario@ejemplo.com",
                "recipientNameOptional": "Nombre (opcional)",
                "keyPoint": "Añadir punto clave",
                "senderName": "ej. Alex Morgan",
                "senderEmail": "ej. alex@sensei.com",
                "senderTitle": "ej. Gerente de Cuenta",
                "companyName": "ej. Sensei Corp",
                "threadEntityType": "Seleccionar entidad del hilo...",
                "threadEntityId": "Introducir ID de entidad...",
                "referenceNumber": "ej. RFQ-2024-001",
                "subjectHint": "ej. Actualización de precios T2"
            },
            "purpose": {
                "missingInfoRequest": "Solicitud de información faltante",
                "quoteFollowup": "Seguimiento de cotización",
                "quoteSubmission": "Envío de cotización",
                "supplierInquiry": "Consulta a proveedor",
                "meetingRequest": "Solicitud de reunión",
                "meetingConfirmation": "Confirmación de reunión",
                "meetingReschedule": "Reprogramación de reunión",
                "issueNotification": "Notificación de problema",
                "statusUpdate": "Actualización de estado",
                "thankYou": "Agradecimiento",
                "introduction": "Introducción",
                "escalation": "Escalamiento",
                "apology": "Disculpa",
                "custom": "Correo personalizado"
            },
            "tone": {
                "formal": "Formal",
                "professional": "Profesional",
                "friendly": "Amigable",
                "urgent": "Urgente",
                "apologetic": "Disculpa",
                "appreciative": "Agradecido",
                "concise": "Conciso"
            },
            "language": {
                "english": "Inglés",
                "french": "Francés",
                "german": "Alemán",
                "spanish": "Español",
                "italian": "Italiano",
                "portuguese": "Portugués",
                "japanese": "Japonés",
                "chinese": "Chino",
                "korean": "Coreano",
                "arabic": "Árabe"
            },
            "actions": {
                "add": "Añadir",
                "apply": "Aplicar",
                "edit": "Editar",
                "generating": "Generando...",
                "generateDraft": "Generar borrador",
                "regenerate": "Regenerar",
                "send": "Enviar"
            },
            "preview": {
                "title": "Vista previa del borrador",
                "subjectLabel": "Asunto",
                "confidence": "Confianza: {score}",
                "generatedIn": "Generado en {time}"
            },
            "units": {
                "milliseconds": "ms",
                "seconds": "s"
            },
            "compliance": {
                "none": "No se detectaron problemas de cumplimiento",
                "title": "Problemas de cumplimiento ({count})"
            },
            "suggestions": {
                "title": "Sugerencias ({count})"
            },
            "alternatives": {
                "title": "Asuntos alternativos:"
            },
            "thread": {
                "entityType": {
                    "rfq": "RFQ",
                    "quote": "Cotización",
                    "workOrder": "Orden de trabajo",
                    "opportunity": "Oportunidad",
                    "nonConformance": "No conformidad",
                    "shipment": "Envío",
                    "invoice": "Factura"
                },
                "loadFailed": "Error al cargar el rastro del hilo",
                "helper": "Conecta este borrador a un hilo para mantener intacto el contexto de los datos.",
                "loading": "Cargando rastro del hilo...",
                "traceTitle": "Rastro del hilo",
                "traceStats": "Rastro: {nodes} nodos / {edges} enlaces",
                "reasoningId": "ID de razonamiento: {id}"
            },
            "defaults": {
                "senderName": "Operador Sensei",
                "senderEmail": "operador@sensei.com",
                "companyName": "Sensei"
            },
            "sections": {
                "recipient": "Destinatario",
                "purpose": "Propósito",
                "sender": "Remitente",
                "threadContext": "Contexto del hilo",
                "tone": "Tono",
                "language": "Idioma",
                "keyPoints": "Puntos clave"
            },
            "fields": {
                "senderName": "Nombre del remitente",
                "senderEmail": "Correo del remitente",
                "senderTitle": "Título del remitente",
                "companyName": "Nombre de la empresa",
                "threadEntityType": "Tipo de entidad del hilo",
                "threadEntityId": "ID de entidad del hilo",
                "referenceNumberOptional": "Número de referencia (opcional)",
                "subjectHintOptional": "Sugerencia de asunto (opcional)"
            },
            "status": {
                "generating": "Generando...",
                "ready": "Listo para revisión",
                "reviewed": "Revisado",
                "approved": "Aprobado",
                "sent": "Enviado",
                "discarded": "Descartado",
                "failed": "Fallido"
            },
            "notifications": {
                "copied": "¡Copiado al portapapeles!"
            },
            "empty": {
                "title": "Aún no hay borrador",
                "description": "Genera un borrador para ver la vista previa y las comprobaciones de cumplimiento.",
                "list": "Aún no hay borradores"
            },
            "drafts": {
                "snippet": "{snippet}..."
            },
            "validation": {
                "emailRequired": "El correo es obligatorio",
                "emailInvalid": "Formato de correo inválido"
            }
        }
    },
    "de": {
        "emailDrafting": {
            "title": "KI-E-Mail-Verfasser",
            "aria": {
                "selectPurpose": "Zweck auswählen",
                "toneGroup": "Tonfall auswählen",
                "selectLanguage": "Sprache auswählen",
                "recipientEmail": "Empfänger-E-Mail",
                "recipientName": "Empfängername",
                "addKeyPoint": "Hauptpunkt hinzufügen",
                "keyPointsList": "Liste der Hauptpunkte",
                "removeKeyPoint": "Entfernen: {point}",
                "copyToClipboard": "In die Zwischenablage kopieren",
                "editSubject": "Betreff bearbeiten",
                "close": "Schließen",
                "draftsList": "E-Mail-Entwürfe"
            },
            "placeholders": {
                "selectPurpose": "Zweck auswählen...",
                "recipientEmail": "empfaenger@beispiel.de",
                "recipientNameOptional": "Name (optional)",
                "keyPoint": "Hauptpunkt hinzufügen",
                "senderName": "z.B. Max Mustermann",
                "senderEmail": "z.B. max@sensei.com",
                "senderTitle": "z.B. Account Manager",
                "companyName": "z.B. Sensei GmbH",
                "threadEntityType": "Thread-Entität auswählen...",
                "threadEntityId": "Entitäts-ID eingeben...",
                "referenceNumber": "z.B. RFQ-2024-001",
                "subjectHint": "z.B. Preisupdate für Q2"
            },
            "purpose": {
                "missingInfoRequest": "Anfrage fehlender Informationen",
                "quoteFollowup": "Angebotsnachverfolgung",
                "quoteSubmission": "Angebotsabgabe",
                "supplierInquiry": "Lieferantenanfrage",
                "meetingRequest": "Terminanfrage",
                "meetingConfirmation": "Terminbestätigung",
                "meetingReschedule": "Terminverschiebung",
                "issueNotification": "Problembenachrichtigung",
                "statusUpdate": "Statusaktualisierung",
                "thankYou": "Danksagung",
                "introduction": "Vorstellung",
                "escalation": "Eskalation",
                "apology": "Entschuldigung",
                "custom": "Benutzerdefinierte E-Mail"
            },
             "tone": {
                "formal": "Formell",
                "professional": "Professionell",
                "friendly": "Freundlich",
                "urgent": "Dringend",
                "apologetic": "Entschuldigend",
                "appreciative": "Wertschätzend",
                "concise": "Prägnant"
            },
            "language": {
                "english": "Englisch",
                "french": "Französisch",
                "german": "Deutsch",
                "spanish": "Spanisch",
                "italian": "Italienisch",
                "portuguese": "Portugiesisch",
                "japanese": "Japanisch",
                "chinese": "Chinesisch",
                "korean": "Koreanisch",
                "arabic": "Arabisch"
            },
            "actions": {
                "add": "Hinzufügen",
                "apply": "Anwenden",
                "edit": "Bearbeiten",
                "generating": "Wird generiert...",
                "generateDraft": "Entwurf generieren",
                "regenerate": "Neu generieren",
                "send": "Senden"
            },
            "preview": {
                "title": "Entwurfsvorschau",
                "subjectLabel": "Betreff",
                "confidence": "Konfidenz: {score}",
                "generatedIn": "Generiert in {time}"
            },
            "units": {
                "milliseconds": "ms",
                "seconds": "s"
            },
            "compliance": {
                "none": "Keine Compliance-Probleme erkannt",
                "title": "Compliance-Probleme ({count})"
            },
            "suggestions": {
                "title": "Vorschläge ({count})"
            },
            "alternatives": {
                "title": "Alternative Betreffzeilen:"
            },
            "thread": {
                "entityType": {
                    "rfq": "Anfrage (RFQ)",
                    "quote": "Angebot",
                    "workOrder": "Arbeitsauftrag",
                    "opportunity": "Verkaufschance",
                    "nonConformance": "Nichtkonformität",
                    "shipment": "Sendung",
                    "invoice": "Rechnung"
                },
                "loadFailed": "Laden der Thread-Verfolgung fehlgeschlagen",
                "helper": "Verbinden Sie diesen Entwurf mit einem Thread, um den Datenkontext beizubehalten.",
                "loading": "Thread-Verfolgung wird geladen...",
                "traceTitle": "Thread-Verfolgung",
                "traceStats": "Trace: {nodes} Knoten / {edges} Kanten",
                "reasoningId": "Reasoning-ID: {id}"
            },
            "defaults": {
                "senderName": "Sensei Operator",
                "senderEmail": "operator@sensei.com",
                "companyName": "Sensei"
            },
            "sections": {
                "recipient": "Empfänger",
                "purpose": "Zweck",
                "sender": "Absender",
                "threadContext": "Thread-Kontext",
                "tone": "Tonfall",
                "language": "Sprache",
                "keyPoints": "Wichtige Punkte"
            },
            "fields": {
                "senderName": "Absendername",
                "senderEmail": "Absender-E-Mail",
                "senderTitle": "Absendertitel",
                "companyName": "Firmenname",
                "threadEntityType": "Thread-Entitätstyp",
                "threadEntityId": "Thread-Entitäts-ID",
                "referenceNumberOptional": "Referenznummer (optional)",
                "subjectHintOptional": "Betreff-Hinweis (optional)"
            },
            "status": {
                "generating": "Wird generiert...",
                "ready": "Bereit zur Überprüfung",
                "reviewed": "Überprüft",
                "approved": "Genehmigt",
                "sent": "Gesendet",
                "discarded": "Verworfen",
                "failed": "Fehlgeschlagen"
            },
            "notifications": {
                "copied": "In die Zwischenablage kopiert!"
            },
            "empty": {
                "title": "Noch kein Entwurf",
                "description": "Erstellen Sie einen Entwurf, um die Vorschau und die Compliance-Prüfungen zu sehen.",
                "list": "Noch keine Entwürfe"
            },
            "drafts": {
                "snippet": "{snippet}..."
            },
            "validation": {
                "emailRequired": "E-Mail ist erforderlich",
                "emailInvalid": "Ungültiges E-Mail-Format"
            }
        }
    }
}

def main():
    languages = ['ar', 'fr', 'es', 'de']
    for lang in languages:
        updates = {}
        # Merge updates
        if lang in auth_updates:
            updates.update(auth_updates[lang])
        if lang in email_updates:
            updates.update(email_updates[lang])
            
        update_json_file(f'frontend/src/locales/{lang}.json', updates, lang)

if __name__ == "__main__":
    main()
