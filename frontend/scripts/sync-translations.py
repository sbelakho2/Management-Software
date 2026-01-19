#!/usr/bin/env python3
"""
Sync translations across all locale files.
This script ensures all locale files have the same keys as en.json.

For missing keys in other locales, it provides vernacular translations
rather than machine-translated text, using a curated translation dictionary.
"""

import json
import os
from pathlib import Path
from typing import Any

# Path to locales directory
LOCALES_DIR = Path(__file__).parent.parent / "src" / "locales"

# Supported locales
LOCALES = ["en", "fr", "de", "es", "ar"]

# Vernacular translations dictionary
# These are carefully crafted translations that sound natural in each language
VERNACULAR_TRANSLATIONS = {
    # Common terms
    "common.abort": {
        "fr": "Abandonner",
        "de": "Abbrechen",
        "es": "Abortar",
        "ar": "إلغاء"
    },
    "common.abortProtocol": {
        "fr": "Abandonner le protocole",
        "de": "Protokoll abbrechen",
        "es": "Abortar protocolo",
        "ar": "إلغاء البروتوكول"
    },
    "common.activeUsers": {
        "fr": "Utilisateurs actifs",
        "de": "Aktive Benutzer",
        "es": "Usuarios activos",
        "ar": "المستخدمون النشطون"
    },
    "common.activity": {
        "fr": "Activité",
        "de": "Aktivität",
        "es": "Actividad",
        "ar": "النشاط"
    },
    "common.actual": {
        "fr": "Réel",
        "de": "Tatsächlich",
        "es": "Real",
        "ar": "فعلي"
    },
    "common.advanced": {
        "fr": "Avancé",
        "de": "Fortgeschritten",
        "es": "Avanzado",
        "ar": "متقدم"
    },
    "common.allDepartments": {
        "fr": "Tous les départements",
        "de": "Alle Abteilungen",
        "es": "Todos los departamentos",
        "ar": "جميع الأقسام"
    },
    "common.asset": {
        "fr": "Équipement",
        "de": "Anlage",
        "es": "Activo",
        "ar": "أصل"
    },
    "common.assigned": {
        "fr": "Assigné",
        "de": "Zugewiesen",
        "es": "Asignado",
        "ar": "مُعيَّن"
    },
    "common.assignedTo": {
        "fr": "Assigné à",
        "de": "Zugewiesen an",
        "es": "Asignado a",
        "ar": "مُعيَّن إلى"
    },
    "common.attachments": {
        "fr": "Pièces jointes",
        "de": "Anhänge",
        "es": "Archivos adjuntos",
        "ar": "المرفقات"
    },
    "common.beginner": {
        "fr": "Débutant",
        "de": "Anfänger",
        "es": "Principiante",
        "ar": "مبتدئ"
    },
    "common.blocked": {
        "fr": "Bloqué",
        "de": "Blockiert",
        "es": "Bloqueado",
        "ar": "محظور"
    },
    "common.board": {
        "fr": "Tableau",
        "de": "Tafel",
        "es": "Tablero",
        "ar": "لوحة"
    },
    "common.created": {
        "fr": "Créé",
        "de": "Erstellt",
        "es": "Creado",
        "ar": "تم الإنشاء"
    },
    "common.creating": {
        "fr": "Création en cours...",
        "de": "Wird erstellt...",
        "es": "Creando...",
        "ar": "جاري الإنشاء..."
    },
    "common.customer": {
        "fr": "Client",
        "de": "Kunde",
        "es": "Cliente",
        "ar": "عميل"
    },
    "common.dashboard": {
        "fr": "Tableau de bord",
        "de": "Dashboard",
        "es": "Panel de control",
        "ar": "لوحة التحكم"
    },
    "common.days": {
        "fr": "Jours",
        "de": "Tage",
        "es": "Días",
        "ar": "أيام"
    },
    "common.detailedIntelligence": {
        "fr": "Informations détaillées",
        "de": "Detaillierte Informationen",
        "es": "Información detallada",
        "ar": "معلومات تفصيلية"
    },
    "common.discard": {
        "fr": "Abandonner",
        "de": "Verwerfen",
        "es": "Descartar",
        "ar": "تجاهل"
    },
    "common.due": {
        "fr": "Échéance",
        "de": "Fällig",
        "es": "Vencimiento",
        "ar": "مستحق"
    },
    "common.dueDate": {
        "fr": "Date d'échéance",
        "de": "Fälligkeitsdatum",
        "es": "Fecha de vencimiento",
        "ar": "تاريخ الاستحقاق"
    },
    "common.duration": {
        "fr": "Durée",
        "de": "Dauer",
        "es": "Duración",
        "ar": "المدة"
    },
    "common.enrolled": {
        "fr": "Inscrit",
        "de": "Eingeschrieben",
        "es": "Inscrito",
        "ar": "مُسجَّل"
    },
    "common.escalated": {
        "fr": "Escaladé",
        "de": "Eskaliert",
        "es": "Escalado",
        "ar": "مُصعَّد"
    },
    "common.execute": {
        "fr": "Exécuter",
        "de": "Ausführen",
        "es": "Ejecutar",
        "ar": "تنفيذ"
    },
    "common.expert": {
        "fr": "Expert",
        "de": "Experte",
        "es": "Experto",
        "ar": "خبير"
    },
    "common.exportIntel": {
        "fr": "Exporter les données",
        "de": "Daten exportieren",
        "es": "Exportar datos",
        "ar": "تصدير البيانات"
    },
    "common.filters": {
        "fr": "Filtres",
        "de": "Filter",
        "es": "Filtros",
        "ar": "الفلاتر"
    },
    "common.grid": {
        "fr": "Grille",
        "de": "Raster",
        "es": "Cuadrícula",
        "ar": "شبكة"
    },
    "common.history": {
        "fr": "Historique",
        "de": "Verlauf",
        "es": "Historial",
        "ar": "السجل"
    },
    "common.initializing": {
        "fr": "Initialisation...",
        "de": "Wird initialisiert...",
        "es": "Inicializando...",
        "ar": "جاري التهيئة..."
    },
    "common.instructor": {
        "fr": "Instructeur",
        "de": "Ausbilder",
        "es": "Instructor",
        "ar": "المدرب"
    },
    "common.intermediate": {
        "fr": "Intermédiaire",
        "de": "Mittelstufe",
        "es": "Intermedio",
        "ar": "متوسط"
    },
    "common.list": {
        "fr": "Liste",
        "de": "Liste",
        "es": "Lista",
        "ar": "قائمة"
    },
    "common.notSpecified": {
        "fr": "Non spécifié",
        "de": "Nicht angegeben",
        "es": "No especificado",
        "ar": "غير محدد"
    },
    "common.operations": {
        "fr": "Opérations",
        "de": "Betrieb",
        "es": "Operaciones",
        "ar": "العمليات"
    },
    "common.overdue": {
        "fr": "En retard",
        "de": "Überfällig",
        "es": "Vencido",
        "ar": "متأخر"
    },
    "common.priorityLayer": {
        "fr": "Niveau de priorité",
        "de": "Prioritätsstufe",
        "es": "Nivel de prioridad",
        "ar": "مستوى الأولوية"
    },
    "common.qty": {
        "fr": "Qté",
        "de": "Menge",
        "es": "Cant.",
        "ar": "الكمية"
    },
    "common.quality": {
        "fr": "Qualité",
        "de": "Qualität",
        "es": "Calidad",
        "ar": "الجودة"
    },
    "common.received": {
        "fr": "Reçu",
        "de": "Empfangen",
        "es": "Recibido",
        "ar": "مستلم"
    },
    "common.saving": {
        "fr": "Enregistrement...",
        "de": "Wird gespeichert...",
        "es": "Guardando...",
        "ar": "جاري الحفظ..."
    },
    "common.scheduled": {
        "fr": "Planifié",
        "de": "Geplant",
        "es": "Programado",
        "ar": "مجدول"
    },
    "common.settings": {
        "fr": "Paramètres",
        "de": "Einstellungen",
        "es": "Configuración",
        "ar": "الإعدادات"
    },
    "common.synchronizing": {
        "fr": "Synchronisation...",
        "de": "Synchronisierung...",
        "es": "Sincronizando...",
        "ar": "جاري المزامنة..."
    },
    "common.target": {
        "fr": "Objectif",
        "de": "Ziel",
        "es": "Objetivo",
        "ar": "هدف"
    },
    "common.task": {
        "fr": "Tâche",
        "de": "Aufgabe",
        "es": "Tarea",
        "ar": "مهمة"
    },
    "common.temporalHorizon": {
        "fr": "Horizon temporel",
        "de": "Zeithorizont",
        "es": "Horizonte temporal",
        "ar": "الأفق الزمني"
    },
    "common.title": {
        "fr": "Titre",
        "de": "Titel",
        "es": "Título",
        "ar": "العنوان"
    },
    "common.trend": {
        "fr": "Tendance",
        "de": "Trend",
        "es": "Tendencia",
        "ar": "الاتجاه"
    },
    "common.tryAgain": {
        "fr": "Réessayer",
        "de": "Erneut versuchen",
        "es": "Intentar de nuevo",
        "ar": "حاول مرة أخرى"
    },
    "common.unassigned": {
        "fr": "Non assigné",
        "de": "Nicht zugewiesen",
        "es": "Sin asignar",
        "ar": "غير مُعيَّن"
    },
    "common.version": {
        "fr": "Version",
        "de": "Version",
        "es": "Versión",
        "ar": "الإصدار"
    },
    "common.viewAll": {
        "fr": "Voir tout",
        "de": "Alle anzeigen",
        "es": "Ver todo",
        "ar": "عرض الكل"
    },
    "common.projectCreated": {
        "fr": "Projet créé",
        "de": "Projekt erstellt",
        "es": "Proyecto creado",
        "ar": "تم إنشاء المشروع"
    },
    "common.private": {
        "fr": "Privé",
        "de": "Privat",
        "es": "Privado",
        "ar": "خاص"
    },
    "common.public": {
        "fr": "Public",
        "de": "Öffentlich",
        "es": "Público",
        "ar": "عام"
    },
    "common.allStatus": {
        "fr": "Tous les statuts",
        "de": "Alle Status",
        "es": "Todos los estados",
        "ar": "جميع الحالات"
    },
    "common.allCategories": {
        "fr": "Toutes les catégories",
        "de": "Alle Kategorien",
        "es": "Todas las categorías",
        "ar": "جميع الفئات"
    },
    "common.filterByStatus": {
        "fr": "Filtrer par statut",
        "de": "Nach Status filtern",
        "es": "Filtrar por estado",
        "ar": "تصفية حسب الحالة"
    },
    "common.adjustFilters": {
        "fr": "Ajuster les filtres",
        "de": "Filter anpassen",
        "es": "Ajustar filtros",
        "ar": "ضبط الفلاتر"
    },
    "common.unknown": {
        "fr": "Inconnu",
        "de": "Unbekannt",
        "es": "Desconocido",
        "ar": "غير معروف"
    },
    "common.notClassified": {
        "fr": "Non classé",
        "de": "Nicht klassifiziert",
        "es": "Sin clasificar",
        "ar": "غير مصنف"
    },
    "common.viewDetails": {
        "fr": "Voir les détails",
        "de": "Details anzeigen",
        "es": "Ver detalles",
        "ar": "عرض التفاصيل"
    },
    "common.activate": {
        "fr": "Activer",
        "de": "Aktivieren",
        "es": "Activar",
        "ar": "تفعيل"
    },
    "common.deactivate": {
        "fr": "Désactiver",
        "de": "Deaktivieren",
        "es": "Desactivar",
        "ar": "إلغاء التفعيل"
    },
    "common.discontinued": {
        "fr": "Arrêté",
        "de": "Eingestellt",
        "es": "Discontinuado",
        "ar": "متوقف"
    },
    "common.priority.label": {
        "fr": "Priorité",
        "de": "Priorität",
        "es": "Prioridad",
        "ar": "الأولوية"
    },
    "common.priority._value": {
        "fr": "Priorité",
        "de": "Priorität",
        "es": "Prioridad",
        "ar": "الأولوية"
    },
    "common.priority.critical": {
        "fr": "Critique",
        "de": "Kritisch",
        "es": "Crítico",
        "ar": "حرج"
    },
    "common.priority.high": {
        "fr": "Élevée",
        "de": "Hoch",
        "es": "Alta",
        "ar": "عالية"
    },
    "common.priority.low": {
        "fr": "Faible",
        "de": "Niedrig",
        "es": "Baja",
        "ar": "منخفضة"
    },
    "common.priority.medium": {
        "fr": "Moyenne",
        "de": "Mittel",
        "es": "Media",
        "ar": "متوسطة"
    },
    "common.priority.normal": {
        "fr": "Normale",
        "de": "Normal",
        "es": "Normal",
        "ar": "عادية"
    },
    "common.priority.urgent": {
        "fr": "Urgent",
        "de": "Dringend",
        "es": "Urgente",
        "ar": "عاجلة"
    },
    "common.status._label": {
        "fr": "Statut",
        "de": "Status",
        "es": "Estado",
        "ar": "الحالة"
    },
    "common.status.allSystemsOperational": {
        "fr": "Tous les systèmes opérationnels",
        "de": "Alle Systeme betriebsbereit",
        "es": "Todos los sistemas operativos",
        "ar": "جميع الأنظمة تعمل"
    },
    "common.status.minorIssuesDetected": {
        "fr": "Problèmes mineurs détectés",
        "de": "Kleinere Probleme erkannt",
        "es": "Problemas menores detectados",
        "ar": "تم اكتشاف مشاكل بسيطة"
    },
    "common.status.criticalAlert": {
        "fr": "Alerte critique",
        "de": "Kritische Warnung",
        "es": "Alerta crítica",
        "ar": "تنبيه حرج"
    },
    "common.status.systemOffline": {
        "fr": "Système hors ligne",
        "de": "System offline",
        "es": "Sistema fuera de línea",
        "ar": "النظام غير متصل"
    },
    "common.status.idle": {
        "fr": "Inactif",
        "de": "Inaktiv",
        "es": "Inactivo",
        "ar": "خامل"
    },
    "common.status.syncing": {
        "fr": "Synchronisation",
        "de": "Synchronisierung",
        "es": "Sincronizando",
        "ar": "مزامنة"
    },
    "common.status.processing": {
        "fr": "En cours de traitement",
        "de": "Wird verarbeitet",
        "es": "Procesando",
        "ar": "قيد المعالجة"
    },
    "common.status.complete": {
        "fr": "Terminé",
        "de": "Abgeschlossen",
        "es": "Completado",
        "ar": "مكتمل"
    },
    "common.status.error": {
        "fr": "Erreur",
        "de": "Fehler",
        "es": "Error",
        "ar": "خطأ"
    },
    "common.actions.analyze": {
        "fr": "Analyser",
        "de": "Analysieren",
        "es": "Analizar",
        "ar": "تحليل"
    },
}


def flatten_dict(d: dict, parent_key: str = "", sep: str = ".") -> dict:
    """Flatten a nested dictionary into dot-notation keys."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def unflatten_dict(d: dict, sep: str = ".") -> dict:
    """Convert dot-notation keys back to nested dictionary."""
    result = {}
    for key, value in d.items():
        parts = key.split(sep)
        current = result
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value
    return result


def get_translation(key: str, value: str, locale: str) -> str:
    """Get vernacular translation for a key, or generate a reasonable default."""
    # Check if we have a curated translation
    if key in VERNACULAR_TRANSLATIONS:
        if locale in VERNACULAR_TRANSLATIONS[key]:
            return VERNACULAR_TRANSLATIONS[key][locale]
    
    # For keys not in our dictionary, use the English value
    # In production, these would be reviewed by translators
    return value


def load_locale(locale: str) -> dict:
    """Load a locale file."""
    file_path = LOCALES_DIR / f"{locale}.json"
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_locale(locale: str, data: dict) -> None:
    """Save a locale file."""
    file_path = LOCALES_DIR / f"{locale}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  Saved {file_path}")


def sync_translations():
    """Sync all translations from en.json to other locales."""
    print("Loading English translations...")
    en_data = load_locale("en")
    en_flat = flatten_dict(en_data)
    
    for locale in LOCALES:
        if locale == "en":
            continue
        
        print(f"\nSyncing {locale.upper()} translations...")
        locale_data = load_locale(locale)
        locale_flat = flatten_dict(locale_data)
        
        # Find missing keys
        missing_keys = set(en_flat.keys()) - set(locale_flat.keys())
        
        if missing_keys:
            print(f"  Found {len(missing_keys)} missing translations")
            
            # Add translations for missing keys
            for key in missing_keys:
                en_value = en_flat[key]
                translation = get_translation(key, en_value, locale)
                locale_flat[key] = translation
            
            # Sort keys for consistent output
            sorted_flat = dict(sorted(locale_flat.items()))
            
            # Convert back to nested structure
            locale_data = unflatten_dict(sorted_flat)
            
            # Save updated locale
            save_locale(locale, locale_data)
            print(f"  Added {len(missing_keys)} new translations")
        else:
            print("  All translations present")


def check_missing():
    """Report missing translations without making changes."""
    print("Checking translation coverage...\n")
    en_data = load_locale("en")
    en_flat = flatten_dict(en_data)
    en_count = len(en_flat)
    
    print(f"English: {en_count} keys (reference)")
    
    for locale in LOCALES:
        if locale == "en":
            continue
        
        locale_data = load_locale(locale)
        locale_flat = flatten_dict(locale_data)
        locale_count = len(locale_flat)
        
        missing = set(en_flat.keys()) - set(locale_flat.keys())
        coverage = (locale_count / en_count) * 100 if en_count > 0 else 0
        
        print(f"{locale.upper()}: {locale_count} keys ({coverage:.1f}% coverage, {len(missing)} missing)")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        check_missing()
    else:
        sync_translations()
        print("\n✅ Translation sync complete!")
