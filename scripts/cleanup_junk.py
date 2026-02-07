import json
import re

# Translation Dictionaries
replacements = {
    "fr": {
        "ACTIVE": "Actif", "INACTIVE": "Inactif", "ENABLED": "Activé", "DISABLED": "Désactivé",
        "PENDING": "En attente", "COMPLETED": "Terminé", "CANCELLED": "Annulé", "ARCHIVED": "Archivé",
        "LOW": "Bas", "MEDIUM": "Moyen", "HIGH": "Élevé", "CRITICAL": "Critique", "URGENT": "Urgent",
        "LOW_VELOCITY": "Vitesse faible", "STANDARD_NODE": "Nœud standard", "HIGH_PRIORITY": "Haute priorité", "URGENT_ESCALATION": "Escalade urgente", "CRITICAL_THRESHOLD": "Seuil critique",
        "DELETE": "Supprimer", "EDIT": "Modifier", "SAVE": "Enregistrer", "CANCEL": "Annuler", "UPDATE": "Mettre à jour",
        "DETAILS": "Détails", "PROTOCOL": "Protocole", "STATION": "Station", "SYNC": "Synchroniser",
        "CONNECTED": "Connecté", "DISCONNECTED": "Déconnecté", "NOT_CONNECTED": "Non connecté",
        "INITIALIZED_ON": "Initialisé le", "REQUEST_VOLUME": "Volume de requêtes", "ERROR_RATE": "Taux d'erreur",
        "EXECUTE_COMMAND": "Exécuter la commande", "VIEW_INTEL": "Voir les renseignements", "TERMINATE": "Terminer",
        "SENSEI_OS_COMMAND": "Commande Sensei OS",
        "ABORT": "Annuler", "COMMIT_DATA": "Valider les données", "ESTABLISH_INSPECTION": "Établir l'inspection",
        "FAILED": "Échoué", "PASSED": "Réussi", "AUDIT": "Audit", "CUSTOMER": "Client", "PREVENTIVE": "Préventif",
        "FINAL": "Final", "RECEIVING": "Réception", 
        "NOMENCLATURE": "Nomenclature", "REVISION": "Révision", "DUPLICATE": "Dupliquer",
        "USER": "Utilisateur", "ADMINISTRATEUR": "Administrateur", "OPTIONAL": "Optionnel",
        "CRITICAL_ANOMALIES": "Anomalies critiques", "STRATEGIC_USER_STORIES": "Histoires utilisateur stratégiques",
        "PRIMARY_LOGO_NODE": "Nœud de logo principal", "UPDATE_STREAM": "Flux de mise à jour", "INTERFACE_ACCENT_SYNC": "Sync accent interface",
        "OPERATIVE_IDENTITY": "Identité opérationnelle", "ACCESS_LAYER": "Couche d'accès", "DEPARTMENT_NODE": "Nœud département", "SYNC_STATUS": "Statut sync", "LAST_PULSE": "Dernière impulsion",
        "REFINE_NODE": "Affiner le nœud", "ROTATE_ROLE": "Rotation de rôle", "RESEND_SYNC": "Renvoyer sync", "DEAUTHORIZE": "Désautoriser", "REAUTHORIZE": "Réautoriser", "TERMINATE_PROTOCOL": "Terminer le protocole",
        "SITE_CODE": "Code site", "SITE_IDENTITY": "Identité du site", "TEMPORAL_SYNC": "Sync temporelle", "CURRENCY": "Devise", "STATUS_NODE": "Nœud de statut",
        "ADDRESS_UNAVAILABLE": "Adresse indisponible", "VALUE_UNAVAILABLE": "Valeur indisponible",
        "PRODUCT_": "Produit_", "UNKNOWN_SUPPLIER": "Fournisseur inconnu", "MTBF": "MTBF", "MTTR": "MTTR", "AOI": "AOI", "ICT": "ICT", "FCT": "FCT", "MRP": "MRP", "NCR": "NCR", "LSL": "LSL", "USL": "USL", "NDC": "NDC", "CAPA": "CAPA", "AQL": "AQL", "FAI": "FAI", "MSA": "MSA", "OEE": "OEE"
    },
    "es": {
        "ACTIVE": "Activo", "INACTIVE": "Inactivo", "ENABLED": "Habilitado", "DISABLED": "Deshabilitado",
        "PENDING": "Pendiente", "COMPLETED": "Completado", "CANCELLED": "Cancelado", "ARCHIVED": "Archivado",
        "LOW": "Bajo", "MEDIUM": "Medio", "HIGH": "Alto", "CRITICAL": "Crítico", "URGENT": "Urgente",
        "LOW_VELOCITY": "Velocidad baja", "STANDARD_NODE": "Nodo estándar", "HIGH_PRIORITY": "Alta prioridad", "URGENT_ESCALATION": "Escalamiento urgente", "CRITICAL_THRESHOLD": "Umbral crítico",
        "DELETE": "Eliminar", "EDIT": "Editar", "SAVE": "Guardar", "CANCEL": "Cancelar", "UPDATE": "Actualizar",
        "DETAILS": "Detalles", "PROTOCOL": "Protocolo", "STATION": "Estación", "SYNC": "Sincronizar",
        "CONNECTED": "Conectado", "DISCONNECTED": "Desconectado", "NOT_CONNECTED": "No conectado",
        "INITIALIZED_ON": "Inicializado el", "REQUEST_VOLUME": "Volumen de solicitudes", "ERROR_RATE": "Tasa de error",
        "EXECUTE_COMMAND": "Ejecutar comando", "VIEW_INTEL": "Ver inteligencia", "TERMINATE": "Terminar",
        "SENSEI_OS_COMMAND": "Comando Sensei OS",
        "ABORT": "Abortar", "COMMIT_DATA": "Confirmar datos", "ESTABLISH_INSPECTION": "Establecer inspección",
        "FAILED": "Fallido", "PASSED": "Aprobado", "AUDIT": "Auditoría", "CUSTOMER": "Cliente", "PREVENTIVE": "Preventivo",
        "FINAL": "Final", "RECEIVING": "Recepción",
        "NOMENCLATURE": "Nomenclatura", "REVISION": "Revisión", "DUPLICATE": "Duplicar",
        "USER": "Usuario", "ADMINISTRATEUR": "Administrador", "OPTIONAL": "Opcional",
        "CRITICAL_ANOMALIES": "Anomalías críticas", "STRATEGIC_USER_STORIES": "Historias de usuario estratégicas",
        "PRIMARY_LOGO_NODE": "Nodo de logo principal", "UPDATE_STREAM": "Flujo de actualización", "INTERFACE_ACCENT_SYNC": "Sync acento interfaz",
        "OPERATIVE_IDENTITY": "Identidad operativa", "ACCESS_LAYER": "Capa de acceso", "DEPARTMENT_NODE": "Nodo departamento", "SYNC_STATUS": "Estado sync", "LAST_PULSE": "Último pulso",
        "REFINE_NODE": "Refinar nodo", "ROTATE_ROLE": "Rotar rol", "RESEND_SYNC": "Reenviar sync", "DEAUTHORIZE": "Desautorizar", "REAUTHORIZE": "Reautorizar", "TERMINATE_PROTOCOL": "Terminar protocolo",
        "SITE_CODE": "Código sitio", "SITE_IDENTITY": "Identidad del sitio", "TEMPORAL_SYNC": "Sync temporal", "CURRENCY": "Moneda", "STATUS_NODE": "Nodo de estado",
        "ADDRESS_UNAVAILABLE": "Dirección no disponible", "VALUE_UNAVAILABLE": "Valor no disponible",
        "PRODUCT_": "Producto_", "UNKNOWN_SUPPLIER": "Proveedor desconocido", "MTBF": "MTBF", "MTTR": "MTTR", "AOI": "AOI", "ICT": "ICT", "FCT": "FCT", "MRP": "MRP", "NCR": "NCR", "LSL": "LSL", "USL": "USL", "NDC": "NDC", "CAPA": "CAPA", "AQL": "AQL", "FAI": "FAI", "MSA": "MSA", "OEE": "OEE"
    },
    "de": {
        "ACTIVE": "Aktiv", "INACTIVE": "Inaktiv", "ENABLED": "Aktiviert", "DISABLED": "Deaktiviert",
        "PENDING": "Ausstehend", "COMPLETED": "Abgeschlossen", "CANCELLED": "Abgebrochen", "ARCHIVED": "Archiviert",
        "LOW": "Niedrig", "MEDIUM": "Mittel", "HIGH": "Hoch", "CRITICAL": "Kritisch", "URGENT": "Dringend",
        "LOW_VELOCITY": "Niedrige Geschwindigkeit", "STANDARD_NODE": "Standard-Knoten", "HIGH_PRIORITY": "Hohe Priorität", "URGENT_ESCALATION": "Dringende Eskalation", "CRITICAL_THRESHOLD": "Kritischer Schwellenwert",
        "DELETE": "Löschen", "EDIT": "Bearbeiten", "SAVE": "Speichern", "CANCEL": "Abbrechen", "UPDATE": "Aktualisieren",
        "DETAILS": "Details", "PROTOCOL": "Protokoll", "STATION": "Station", "SYNC": "Synchronisieren",
        "CONNECTED": "Verbunden", "DISCONNECTED": "Getrennt", "NOT_CONNECTED": "Nicht verbunden",
        "INITIALIZED_ON": "Initialisiert am", "REQUEST_VOLUME": "Anfragevolumen", "ERROR_RATE": "Fehlerrate",
        "EXECUTE_COMMAND": "Befehl ausführen", "VIEW_INTEL": "Intel anzeigen", "TERMINATE": "Beenden",
        "SENSEI_OS_COMMAND": "Sensei OS Befehl",
        "ABORT": "Abbrechen", "COMMIT_DATA": "Daten bestätigen", "ESTABLISH_INSPECTION": "Inspektion einrichten",
        "FAILED": "Fehlgeschlagen", "PASSED": "Bestanden", "AUDIT": "Audit", "CUSTOMER": "Kunde", "PREVENTIVE": "Präventiv",
        "FINAL": "Final", "RECEIVING": "Wareneingang",
        "NOMENCLATURE": "Nomenklatur", "REVISION": "Revision", "DUPLICATE": "Duplizieren",
        "USER": "Benutzer", "ADMINISTRATEUR": "Administrator", "OPTIONAL": "Optional",
        "CRITICAL_ANOMALIES": "Kritische Anomalien", "STRATEGIC_USER_STORIES": "Strategische User Stories",
        "PRIMARY_LOGO_NODE": "Primärer Logo-Knoten", "UPDATE_STREAM": "Update-Stream", "INTERFACE_ACCENT_SYNC": "Schnittstellen-Akzent-Sync",
        "OPERATIVE_IDENTITY": "Operative Identität", "ACCESS_LAYER": "Zugriffsebene", "DEPARTMENT_NODE": "Abteilungsknoten", "SYNC_STATUS": "Sync-Status", "LAST_PULSE": "Letzter Puls",
        "REFINE_NODE": "Knoten verfeinern", "ROTATE_ROLE": "Rolle rotieren", "RESEND_SYNC": "Sync erneut senden", "DEAUTHORIZE": "Deautorisieren", "REAUTHORIZE": "Reautorisieren", "TERMINATE_PROTOCOL": "Protokoll beenden",
        "SITE_CODE": "Standortcode", "SITE_IDENTITY": "Standortidentität", "TEMPORAL_SYNC": "Zeit-Sync", "CURRENCY": "Währung", "STATUS_NODE": "Status-Knoten",
        "ADDRESS_UNAVAILABLE": "Adresse nicht verfügbar", "VALUE_UNAVAILABLE": "Wert nicht verfügbar",
        "PRODUCT_": "Produkt_", "UNKNOWN_SUPPLIER": "Unbekannter Lieferant", "MTBF": "MTBF", "MTTR": "MTTR", "AOI": "AOI", "ICT": "ICT", "FCT": "FCT", "MRP": "MRP", "NCR": "NCR", "LSL": "LSL", "USL": "USL", "NDC": "NDC", "CAPA": "CAPA", "AQL": "AQL", "FAI": "FAI", "MSA": "MSA", "OEE": "OEE"
    }
}

# Generic title casing function for fallbacks
def clean_string(s):
    if not isinstance(s, str): return s
    # Check if it looks like CONSTANT_CASE (at least 3 uppercase chars, maybe underscores, no lowercase)
    if re.match(r'^[A-Z0-9_]{3,}$', s):
        # Replace underscores with spaces
        cleaned = s.replace('_', ' ')
        # Title Case
        return cleaned.title()
    return s

def process_value(val, locale_dict):
    if not isinstance(val, str):
        return val
    
    # Check for direct dictionary match
    if val in locale_dict:
        return locale_dict[val]
    
    # Check for dictionary match if we replace spaces with underscores (some keys might have been space separated in previous runs)
    underscored = val.replace(' ', '_')
    if underscored in locale_dict:
        return locale_dict[underscored]

    # Check if it is ALL CAPS and needs cleaning
    if re.match(r'^[A-Z0-9_]+$', val) and len(val) > 1 and not val.isdigit():
         # If no specific translation, generic clean
         return clean_string(val)
         
    return val

def recursive_clean(data, locale_dict):
    if isinstance(data, dict):
        return {k: recursive_clean(v, locale_dict) for k, v in data.items()}
    elif isinstance(data, list):
        return [recursive_clean(item, locale_dict) for item in data]
    else:
        return process_value(data, locale_dict)

def main():
    files = ['es', 'fr', 'de']
    
    for lang in files:
        filepath = f'frontend/src/locales/{lang}.json'
        print(f"Processing {filepath}...")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            cleaned_data = recursive_clean(data, replacements.get(lang, {}))
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(cleaned_data, f, ensure_ascii=False, indent=2)
            
            print(f"Finished {lang}.")
            
        except Exception as e:
            print(f"Error processing {lang}: {e}")

if __name__ == "__main__":
    main()
