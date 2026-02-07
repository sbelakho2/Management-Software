import json

def update_locales():
    # Spanish Fixes
    es_fixes = {
        "osVer": "Versión SO",
        "abortProtocol": "Abortar protocolo",
        "activeUsers": "Usuarios activos",
        "systemOffline": "Sistema desconectado",
        "exportProtocol": "Exportar protocolo",
        # Title Case -> Sentence Case Corrections
        "activeOperativesAssigned": "Operativos asignados",
        "relatedProduct": "Producto relacionado",
        "targetHorizon": "Fecha objetivo",
        "newInspection": "Nueva inspección",
        "newProduct": "Nuevo producto",
        "globalIdentity": "Identidad global",
        "technicalSpecs": "Especificaciones técnicas",
        "logisticsParams": "Parámetros logísticos",
        "originNode": "Nodo origen",
        "correctiveAction": "Acción correctiva"
    }

    # German Fixes
    de_fixes = {
        "progressKpi": "Fortschritts-KPI",
        "protocolType": "Protokolltyp",
        "resolutionTitle": "Lösungstitel",
        "statusNode": "Statusknoten",
        "targetHorizon": "Zielhorizont",
        "activeUsers": "Aktive Benutzer",
        "systemOffline": "System offline",
        "abortProtocol": "Protokoll abbrechen",
        "exportProtocol": "Protokoll exportieren"
    }

    # French Fixes
    fr_fixes = {
        "osVer": "Version SE",
        "progressKpi": "KPI de progression",
        "protocolType": "Type de protocole",
        "resolutionTitle": "Titre de résolution",
        "statusNode": "Nœud de statut"
    }

    files = {
        "es": es_fixes,
        "de": de_fixes,
        "fr": fr_fixes
    }

    for lang, fixes in files.items():
        file_path = f'frontend/src/locales/{lang}.json'
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Recursive search and replace
            def apply_fixes(obj, fix_map):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if isinstance(v, str):
                            # Check if the key is in our fix list
                            if k in fix_map:
                                obj[k] = fix_map[k]
                            # specific check for Title Case values in Spanish if needed, 
                            # but mapped keys are safer.
                        else:
                            apply_fixes(v, fix_map)
            
            apply_fixes(data, fixes)

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Updated {lang}.json")

        except Exception as e:
            print(f"Error processing {lang}: {e}")

if __name__ == "__main__":
    update_locales()
