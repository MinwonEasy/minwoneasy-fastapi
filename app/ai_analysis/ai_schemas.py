from pydantic import BaseModel, ConfigDict
from typing import Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
from app.ai_analysis.ai_models import AnalysisType


class AIAnalysisBase(BaseModel):
    analysis_type: AnalysisType
    result: Dict[str, Any]
    confidence_score: Optional[Decimal] = None


class AIAnalysisCreate(AIAnalysisBase):
    complaint_id: int


class AIAnalysisResponse(AIAnalysisBase):
    model_config = ConfigDict(from_attributes=True)

    analysis_id: int
    complaint_id: int
    created_at: datetime


class AIAnalysisListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    analysis_id: int
    analysis_type: AnalysisType
    confidence_score: Optional[Decimal]
    created_at: datetime