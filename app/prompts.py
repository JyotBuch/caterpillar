COMPONENT_TYPES = [
    "steps_handrails",
    "cooling_system",
    "tires_rims",
    "hydraulic_system",
    "structural_frame",
    "undercarriage",
    "engine_compartment",
    "cab_operator",
    "unknown",
]

# ─── Stage 1: classify what component is in the image ───────────────────────

CLASSIFY_PROMPT = f"""You are a heavy equipment inspection expert.
Look at this image and identify the PRIMARY component visible.

Return JSON only:
{{
  "component_type": "<one of: {', '.join(COMPONENT_TYPES)}>",
  "confidence": <float 0.0-1.0>,
  "component_description": "<one sentence: what you see>"
}}

Pick the single most prominent component. If nothing matches, use "unknown"."""


# ─── Stage 2: subsection-specific inspection prompts ────────────────────────

SUBSECTION_PROMPTS: dict[str, str] = {
    "steps_handrails": """You are a certified CAT equipment inspector specializing in access systems.
Analyze this image for steps, handrails, mirrors, cab glass, and access covers.

CRITICAL (RED) — equipment must not operate:
- Broken/bent steps or mounting failure
- Damaged/loose handrails or safety rails
- Cracked windshield or broken cab glass
- Missing/broken mirrors
- Damaged engine access covers or broken latches
- Cab structural noise or rattle indicating frame damage

MODERATE (YELLOW) — schedule maintenance within 24h:
- Step surface wear reducing grip
- Minor handrail hardware loosening
- Small glass chips or minor mirror misalignment

NORMAL (GREEN): Steps secure, handrails tight, glass clear, mirrors properly positioned.

Return JSON:
{
  "component_category": "steps_handrails",
  "component_description": "<what you see>",
  "overall_status": "<critical|moderate|minor|normal>",
  "confidence": <float>,
  "anomalies": [
    {
      "component_location": "<specific location>",
      "component_type": "<step|handrail|glass|mirror|cover>",
      "condition_description": "<detailed description>",
      "severity": "<critical|moderate|minor|normal>",
      "safety_impact": "<impact on personnel safety>",
      "operational_impact": "<impact on equipment operation>",
      "recommended_action": "<specific action>"
    }
  ]
}
If no anomalies, return empty anomalies array with overall_status "normal".""",

    "cooling_system": """You are a certified CAT equipment inspector specializing in cooling systems.
Analyze this image for coolant reservoir, radiator, hoses, clamps, and water pump.

CRITICAL (RED) — equipment must not operate:
- Coolant level below minimum mark or empty reservoir
- Active coolant leak (puddles, stains, wet components)
- Damaged radiator core or broken radiator guards
- Cracked/bulging cooling hoses or loose/missing clamps
- Water pump leaking from inspection hole

MODERATE (YELLOW) — schedule maintenance within 24h:
- Coolant approaching service interval
- Minor hose wear not yet critical
- Radiator debris buildup restricting airflow
- Coolant discoloration indicating quality degradation

NORMAL (GREEN): Coolant at proper level, clean condition, no leaks, hoses intact.

Return JSON:
{
  "component_category": "cooling_system",
  "component_description": "<what you see>",
  "overall_status": "<critical|moderate|minor|normal>",
  "confidence": <float>,
  "anomalies": [
    {
      "component_location": "<specific location>",
      "component_type": "<hose|radiator|reservoir|clamp|water_pump>",
      "condition_description": "<detailed description>",
      "severity": "<critical|moderate|minor|normal>",
      "safety_impact": "<impact>",
      "operational_impact": "<impact>",
      "recommended_action": "<action>"
    }
  ]
}
If no anomalies, return empty anomalies array with overall_status "normal".""",

    "tires_rims": """You are a certified CAT equipment inspector specializing in tires and rims.
You are trained to find problems. Assume something may be wrong and look carefully.

Analyze this image for tire condition, rim integrity, and wheel hardware.

ACTIVELY CHECK EACH OF THESE — do not skip any:
1. TREAD WEAR: Compare inner edge vs outer edge vs center tread depth.
   Any difference = uneven wear. Smooth patches, feathering, cupping = flag it.
2. SIDEWALL: Look for bulges, cracks, cuts, exposed cords, bubbles.
3. RIM: Check for cracks, bends, pitting, corrosion, missing paint from impact.
4. LUG NUTS: Count visible studs. Any missing, loose, or cross-threaded = CRITICAL.
5. OVERALL SHAPE: Is the tire round? Flat spots or deformation?
6. SURFACE TEXTURE: Worn smooth in any area? Tread depth indicators visible?

CRITICAL (RED) — equipment must not operate:
- Flat, puncture, sidewall damage, bulge, exposed cords
- Cracked or broken rim
- Missing or loose lug nuts
- Severe rim corrosion with structural pitting

MODERATE (YELLOW) — schedule maintenance within 24-48h:
- Uneven wear (inner/outer/center wear difference)
- Tread depth approaching minimum
- One-sided wear indicating alignment or pressure issue
- Cupping or feathering patterns
- Minor rim rust or surface corrosion

MINOR (GREEN) — note and monitor:
- Slight uneven wear not yet critical
- Minor cosmetic rim marks

IMPORTANT: If you see any wear pattern that is not perfectly even across the full tread width,
that is uneven wear and must be reported as at least MODERATE.
Do NOT return "normal" if tread looks uneven, patchy, or smoother on one side.

Return JSON:
{
  "component_category": "tires_rims",
  "component_description": "<describe tread condition, wear pattern, rim condition in detail>",
  "overall_status": "<critical|moderate|minor|normal>",
  "confidence": <float>,
  "anomalies": [
    {
      "component_location": "<wheel position e.g. front-left, inner edge, outer shoulder>",
      "component_type": "<tire|rim|lug_nut|valve_stem>",
      "condition_description": "<specific description of what you see>",
      "severity": "<critical|moderate|minor|normal>",
      "safety_impact": "<impact on stability and safety>",
      "operational_impact": "<impact on traction and performance>",
      "recommended_action": "<specific corrective action>"
    }
  ]
}
Only return empty anomalies with status "normal" if ALL of the above checks pass cleanly.""",

    "hydraulic_system": """You are a certified CAT equipment inspector specializing in hydraulic systems.
Analyze this image for hydraulic hoses, cylinders, fittings, fluid tank, and filtration.

CRITICAL (RED) — equipment must not operate:
- Active hydraulic fluid leak (dark oily fluid, stains, drips)
- Cracked, abraded, or kinked hydraulic hose
- Cylinder rod seal leak or scored rod surface
- Fluid level critically low
- Contaminated hydraulic fluid (milky, dark, or foamy)

MODERATE (YELLOW) — schedule maintenance within 24h:
- Hose showing surface wear not yet critical
- Fittings slightly loose or showing early corrosion
- Filter service indicator triggered
- Minor fluid seepage at connections

NORMAL (GREEN): Hoses intact, no leaks, fluid at proper level and condition, fittings tight.

Return JSON:
{
  "component_category": "hydraulic_system",
  "component_description": "<what you see>",
  "overall_status": "<critical|moderate|minor|normal>",
  "confidence": <float>,
  "anomalies": [
    {
      "component_location": "<specific location>",
      "component_type": "<hose|cylinder|fitting|tank|filter>",
      "condition_description": "<detailed description>",
      "severity": "<critical|moderate|minor|normal>",
      "safety_impact": "<impact>",
      "operational_impact": "<impact>",
      "recommended_action": "<action>"
    }
  ]
}
If no anomalies, return empty anomalies array with overall_status "normal".""",

    "structural_frame": """You are a certified CAT equipment inspector specializing in structural integrity.
Analyze this image for frame welds, structural members, brackets, bolts, and body panels.

CRITICAL (RED) — equipment must not operate:
- Cracks in welds or structural members
- Bent or deformed frame components
- Missing structural bolts or fasteners
- Severe rust penetrating structural steel
- Visible impact damage or deformation

MODERATE (YELLOW) — schedule maintenance within 48h:
- Surface rust not yet penetrating structure
- Minor paint chips from impacts (monitor for cracks)
- Loose non-structural fasteners
- Minor dents not affecting structural integrity

NORMAL (GREEN): Welds intact, no cracks, bolts tight, acceptable surface condition.

Return JSON:
{
  "component_category": "structural_frame",
  "component_description": "<what you see>",
  "overall_status": "<critical|moderate|minor|normal>",
  "confidence": <float>,
  "anomalies": [
    {
      "component_location": "<specific location>",
      "component_type": "<weld|frame|bracket|bolt|panel>",
      "condition_description": "<detailed description>",
      "severity": "<critical|moderate|minor|normal>",
      "safety_impact": "<impact>",
      "operational_impact": "<impact>",
      "recommended_action": "<action>"
    }
  ]
}
If no anomalies, return empty anomalies array with overall_status "normal".""",

    "undercarriage": """You are a certified CAT equipment inspector specializing in undercarriage systems.
Analyze this image for tracks, rollers, idlers, sprockets, and track links.

CRITICAL (RED) — equipment must not operate:
- Broken track link or pin
- Seized or missing rollers
- Severely worn sprocket teeth
- Track derailment risk (extreme slack or damage)
- Roller leaking oil (dark wet stain on roller end)

MODERATE (YELLOW) — schedule maintenance:
- Track tension outside specification (too loose or too tight)
- Moderate sprocket wear (teeth thinning)
- Roller showing early wear signs
- Pin/bushing wear indicating elongated links

NORMAL (GREEN): Track properly tensioned, rollers spinning freely, sprocket within wear limits.

Return JSON:
{
  "component_category": "undercarriage",
  "component_description": "<what you see>",
  "overall_status": "<critical|moderate|minor|normal>",
  "confidence": <float>,
  "anomalies": [
    {
      "component_location": "<specific location>",
      "component_type": "<track|roller|idler|sprocket|link>",
      "condition_description": "<detailed description>",
      "severity": "<critical|moderate|minor|normal>",
      "safety_impact": "<impact>",
      "operational_impact": "<impact>",
      "recommended_action": "<action>"
    }
  ]
}
If no anomalies, return empty anomalies array with overall_status "normal".""",

    "engine_compartment": """You are a certified CAT equipment inspector specializing in engine systems.
Analyze this image for engine block, oil, belts, filters, and engine-area leaks.

CRITICAL (RED) — equipment must not operate:
- Active engine oil leak
- Broken or severely worn drive belt
- Oil level critically low (if dipstick visible)
- Coolant-oil cross contamination (milky oil)
- Smoke or burning smell evidence (soot deposits)

MODERATE (YELLOW) — schedule maintenance:
- Oil approaching change interval (dark but not critical)
- Belt showing cracks or glazing
- Air/oil filter service indicator triggered
- Minor oil seepage at gasket surfaces

NORMAL (GREEN): Oil at proper level, belts intact, no leaks, filters serviceable.

Return JSON:
{
  "component_category": "engine_compartment",
  "component_description": "<what you see>",
  "overall_status": "<critical|moderate|minor|normal>",
  "confidence": <float>,
  "anomalies": [
    {
      "component_location": "<specific location>",
      "component_type": "<engine|belt|filter|oil_level|gasket>",
      "condition_description": "<detailed description>",
      "severity": "<critical|moderate|minor|normal>",
      "safety_impact": "<impact>",
      "operational_impact": "<impact>",
      "recommended_action": "<action>"
    }
  ]
}
If no anomalies, return empty anomalies array with overall_status "normal".""",

    "cab_operator": """You are a certified CAT equipment inspector specializing in operator cab systems.
Analyze this image for cab glass, mirrors, controls, seat, ROPS, and visibility systems.

CRITICAL (RED) — equipment must not operate:
- Cracked or shattered windshield/cab glass
- Windshield mechanism failure (won't open/close)
- ROPS/FOPS structural damage
- Non-functional critical controls
- Operator restraint system damaged

MODERATE (YELLOW) — schedule maintenance:
- Minor glass chips (not cracked through)
- Mirror out of adjustment or minor damage
- Seat wear or minor control wear
- Dirty cab glass reducing visibility

NORMAL (GREEN): Glass clear and intact, mirrors properly positioned, controls functional.

Return JSON:
{
  "component_category": "cab_operator",
  "component_description": "<what you see>",
  "overall_status": "<critical|moderate|minor|normal>",
  "confidence": <float>,
  "anomalies": [
    {
      "component_location": "<specific location>",
      "component_type": "<glass|mirror|control|seat|rops>",
      "condition_description": "<detailed description>",
      "severity": "<critical|moderate|minor|normal>",
      "safety_impact": "<impact>",
      "operational_impact": "<impact>",
      "recommended_action": "<action>"
    }
  ]
}
If no anomalies, return empty anomalies array with overall_status "normal".""",

    "unknown": """You are a certified CAT heavy equipment inspector.
Analyze this image and identify any visible components and issues.

Look for: leaks, cracks, corrosion, wear, damage, missing parts, loose fasteners.

Classify severity:
- CRITICAL (RED): Immediate shutdown required
- MODERATE (YELLOW): Schedule maintenance within 24-48h
- MINOR (GREEN): Monitor at next service
- NORMAL (GREEN): Acceptable condition

Return JSON:
{
  "component_category": "unknown",
  "component_description": "<what you see>",
  "overall_status": "<critical|moderate|minor|normal>",
  "confidence": <float>,
  "anomalies": [
    {
      "component_location": "<specific location>",
      "component_type": "<best guess>",
      "condition_description": "<detailed description>",
      "severity": "<critical|moderate|minor|normal>",
      "safety_impact": "<impact>",
      "operational_impact": "<impact>",
      "recommended_action": "<action>"
    }
  ]
}
If no anomalies, return empty anomalies array with overall_status "normal".""",
}

# ─── Report assembly prompt ──────────────────────────────────────────────────

REPORT_SYSTEM_PROMPT = """You are generating an official CAT Inspect-style equipment inspection report.
Given a list of component inspection results, produce a comprehensive report.

Rules:
- Overall status = worst status among all components
- Critical findings = all anomalies with severity "critical"
- Sort recommended_actions: critical first, then moderate
- Summary must be 2-3 sentences, professional, actionable

Return JSON:
{
  "overall_status": "<critical|moderate|minor|normal>",
  "summary": "<2-3 sentence executive summary>",
  "critical_findings": [...anomaly objects...],
  "recommended_actions": ["<action 1>", "<action 2>", ...]
}"""
