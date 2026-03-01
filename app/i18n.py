"""Internationalization (i18n) support for CAT AI Inspector."""

TRANSLATIONS = {
    "en": {
        # UI Labels
        "title": "CAT AI Inspector",
        "subtitle": "Equipment Intelligence & Diagnostics",
        "component_image": "EQUIPMENT PHOTO",
        "drop_image": "Drop image here",
        "or_click": "or click to browse files",
        "voice_notes": "VOICE NOTES",
        "click_to_record": "Click to record",
        "recording": "Recording…",
        "record_saved": "Recording saved",
        "routing_strategy": "CLASSIFICATION STRATEGY",
        "llm_classifies": "LLM classifies + inspects",
        "clip_mode": "CLIP",
        "inspect_btn": "Inspect Component",
        "transcript_query": "TRANSCRIPT SEARCH",
        "search_placeholder": "e.g. seized pin, low oil",
        "video_filter": "Filter by video",
        "both_videos": "Both videos",
        "wheel_loader": "Wheel Loader",
        "excavator": "Excavator",
        "search_btn": "Search",
        "no_inspections": "No inspections yet",
        "upload_prompt": "Upload equipment photo and click Inspect to begin. Add voice notes for richer analysis.",
        "generate_report": "Generate Report",
        "overall_status": "Overall Status",
        "anomalies": "Anomalies",
        "severity": "Severity",
        "confidence": "Confidence",
        "location": "Location",
        "condition": "Condition",
        "safety_impact": "Safety Impact",
        "operational_impact": "Operational Impact",
        "recommended_action": "Recommended Action",
        "close": "Close",
        "export_json": "Export JSON",
        "critical_findings": "Critical Findings",
        "executive_summary": "Executive Summary",
        "component_breakdown": "Component Breakdown",
        "recommended_actions": "Recommended Actions",
        "resume_at": "Resume @",
        "finding_type": "Finding Type",
        "severity_label": "Severity",
        "timestamp": "Timestamp",
        "language": "Language",
        "detected_component": "Detected Component",
        "inspection_results": "Inspection Results",
        "clear_all": "Clear All",
        "equipment_report": "Equipment Report",
        "training_video": "Training Video",
        "no_critical": "No critical findings.",
        "no_anomalies": "No anomalies detected",
        
        # Status badges
        "critical": "CRITICAL",
        "moderate": "MODERATE",
        "minor": "MINOR",
        "normal": "NORMAL",
        
        # Messages
        "inspecting": "Analyzing…",
        "loading": "Loading…",
        "query_searching": "Searching…",
        "query_matches": "match",
        "query_matches_plural": "matches",
        "query_found": "found",
        "no_results": "No results found",
        "error": "Error",
        "success": "Success",
        "inspection_failed": "Inspection failed:",
        "query_failed": "Query failed",
        "report_generating": "⏳ Generating…",
        "report_failed": "Error:",
    },
    "es": {
        # UI Labels
        "title": "Inspector IA CAT",
        "subtitle": "Inteligencia y Diagnóstico de Equipos",
        "component_image": "FOTO DEL EQUIPO",
        "drop_image": "Suelta la imagen aquí",
        "or_click": "o haz clic para examinar archivos",
        "voice_notes": "NOTAS DE VOZ",
        "click_to_record": "Haz clic para grabar",
        "recording": "Grabando…",
        "record_saved": "Grabación guardada",
        "routing_strategy": "ESTRATEGIA DE CLASIFICACIÓN",
        "llm_classifies": "LLM clasifica + inspecciona",
        "clip_mode": "CLIP",
        "inspect_btn": "Inspeccionar Componente",
        "transcript_query": "BÚSQUEDA DE TRANSCRIPCIONES",
        "search_placeholder": "p. ej., pasador atascado, aceite bajo",
        "video_filter": "Filtrar por video",
        "both_videos": "Ambos videos",
        "wheel_loader": "Cargador de Ruedas",
        "excavator": "Excavadora",
        "search_btn": "Buscar",
        "no_inspections": "Sin inspecciones aún",
        "upload_prompt": "Carga una foto del equipo y haz clic en Inspeccionar para comenzar. Agrega notas de voz para un análisis más rico.",
        "generate_report": "Generar Informe",
        "overall_status": "Estado General",
        "anomalies": "Anomalías",
        "severity": "Severidad",
        "confidence": "Confianza",
        "location": "Ubicación",
        "condition": "Condición",
        "safety_impact": "Impacto en Seguridad",
        "operational_impact": "Impacto Operacional",
        "recommended_action": "Acción Recomendada",
        "close": "Cerrar",
        "export_json": "Exportar JSON",
        "critical_findings": "Hallazgos Críticos",
        "executive_summary": "Resumen Ejecutivo",
        "component_breakdown": "Desglose de Componentes",
        "recommended_actions": "Acciones Recomendadas",
        "resume_at": "Reanudar en",
        "finding_type": "Tipo de Hallazgo",
        "severity_label": "Severidad",
        "timestamp": "Marca de Tiempo",
        "language": "Idioma",
        "detected_component": "Componente Detectado",
        "inspection_results": "Resultados de Inspección",
        "clear_all": "Limpiar Todo",
        "equipment_report": "Informe de Equipo",
        "training_video": "Video de Capacitación",
        "no_critical": "Sin hallazgos críticos.",
        "no_anomalies": "✓ Sin anomalías detectadas",
        
        # Status badges
        "critical": "CRÍTICO",
        "moderate": "MODERADO",
        "minor": "MENOR",
        "normal": "NORMAL",
        
        # Messages
        "inspecting": "Analizando…",
        "loading": "Cargando…",
        "query_searching": "Buscando…",
        "query_matches": "coincidencia",
        "query_matches_plural": "coincidencias",
        "query_found": "encontrada",
        "no_results": "No se encontraron resultados",
        "error": "Error",
        "success": "Éxito",
        "inspection_failed": "La inspección falló:",
        "query_failed": "La consulta falló",
        "report_generating": "⏳ Generando…",
        "report_failed": "Error:",
    }
}


def get_text(key: str, lang: str = "en") -> str:
    """Get translated text by key and language code."""
    if lang not in TRANSLATIONS:
        lang = "en"
    return TRANSLATIONS[lang].get(key, key)


def get_inspection_prompt(component_type: str, language: str = "en") -> str:
    """Get inspection prompt for component in specified language."""
    
    en_prompt = f"""You are an expert CAT equipment inspector. Carefully inspect this {component_type} component image.

Provide a detailed structured inspection analyzing:
1. Overall condition and cleanliness
2. Any visible anomalies, damage, wear, or defects
3. Safety hazards or concerns
4. Operational impacts

For each anomaly found, specify:
- Component location
- Condition description  
- Severity (critical/moderate/minor/normal)
- Safety impact
- Operational impact
- Recommended action

Return valid JSON only, no markdown or explanation."""

    es_prompt = f"""Eres un inspector experto de equipos CAT. Inspecciona cuidadosamente esta imagen del componente {component_type}.

Proporciona un análisis de inspección detallado y estructurado considerando:
1. Condición general y limpieza
2. Anomalías visibles, daños, desgaste o defectos
3. Riesgos o preocupaciones de seguridad
4. Impactos operacionales

Para cada anomalía encontrada, especifica:
- Ubicación del componente
- Descripción de la condición
- Severidad (crítica/moderada/menor/normal)
- Impacto en seguridad
- Impacto operacional
- Acción recomendada

Devuelve solo JSON válido, sin markdown o explicación."""
    
    return es_prompt if language == "es" else en_prompt


def get_calibration_prompt(component_type: str, similar_findings: list, language: str = "en") -> str:
    """Get prompt for severity calibration based on similar findings."""
    
    findings_text = "\n".join([
        f"- {f.get('severity', 'unknown').upper()}: {f.get('condition_description', '')} (Verdict: {f.get('nick_verdict', 'N/A')})"
        for f in similar_findings
    ])
    
    en_prompt = f"""Based on these similar expert findings from training videos:

{findings_text}

Re-evaluate the severity classification. Are the findings consistent? Should the severity be adjusted?

Provide only JSON with adjusted severity if needed."""

    es_prompt = f"""Basándote en estos hallazgos similares de expertos de videos de capacitación:

{findings_text}

Re-evalúa la clasificación de severidad. ¿Son los hallazgos consistentes? ¿Debería ajustarse la severidad?

Proporciona solo JSON con la severidad ajustada si es necesario."""
    
    return es_prompt if language == "es" else en_prompt


def get_report_prompt(language: str = "en") -> str:
    """Get report generation prompt in specified language."""
    
    en_prompt = """Generate a structured equipment inspection report with:

1. Executive Summary - concise overview of findings and urgency
2. Overall Status - critical/moderate/minor/normal
3. Critical Findings - prioritized list of urgent issues
4. Component Breakdown - status of each component inspected
5. Recommended Actions - ordered by priority and safety impact

Format as JSON with proper structure."""

    es_prompt = """Genera un informe de inspección de equipo estructurado que incluya:

1. Resumen Ejecutivo - descripción general concisa de hallazgos y urgencia
2. Estado General - crítico/moderado/menor/normal
3. Hallazgos Críticos - lista priorizada de problemas urgentes
4. Desglose de Componentes - estado de cada componente inspeccionado
5. Acciones Recomendadas - ordenadas por prioridad e impacto en seguridad

Formatea como JSON con estructura adecuada."""
    
    return es_prompt if language == "es" else en_prompt
