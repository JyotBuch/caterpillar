from pydantic import BaseModel
from typing import Optional
from enum import Enum


class Severity(str, Enum):
    CRITICAL = "critical"   # RED  - stop operation immediately
    MODERATE = "moderate"   # YELLOW - schedule maintenance
    MINOR = "minor"         # GREEN - monitor
    NORMAL = "normal"       # GREEN - acceptable


class AnomalyItem(BaseModel):
    component_location: str
    component_type: str
    condition_description: str
    severity: Severity
    safety_impact: str
    operational_impact: str
    recommended_action: str


class ComponentInspection(BaseModel):
    component_category: str
    component_description: str
    overall_status: Severity
    anomalies: list[AnomalyItem]
    voice_notes: Optional[str] = None
    confidence: float


class InspectionReport(BaseModel):
    report_id: str
    timestamp: str
    overall_status: Severity
    inspections: list[ComponentInspection]
    critical_findings: list[AnomalyItem]
    summary: str
    recommended_actions: list[str]
