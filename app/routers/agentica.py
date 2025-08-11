from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
import httpx
import os
from typing import Optional
import asyncio

router = APIRouter()

AGENTICA_SERVICE_URL = os.getenv("AGENTICA_SERVICE_URL", "http://localhost:9000")
OCR_SERVICE_URL = os.getenv("OCR_SERVICE_URL", "http://localhost:7001")


class ComplaintProcessRequest(BaseModel):
    raw_text: str
    ocr_text: Optional[str] = None


class ComplaintProcessResponse(BaseModel):
    success: bool
    original_text: str
    formal_text: str
    department: str
    reason: str
    confidence: float
    ocr_text: Optional[str] = None


async def call_agentica_api(endpoint: str, data: dict, max_retries: int = 2):
    url = f"{AGENTICA_SERVICE_URL}{endpoint}"
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(url, json=data)
                if r.status_code == 200:
                    return r.json()
                if attempt == max_retries - 1:
                    raise HTTPException(status_code=r.status_code, detail=f"Agentica API 오류: {r.text}")
        except (httpx.ConnectError, httpx.TimeoutException):
            if attempt == max_retries - 1:
                raise HTTPException(status_code=503 if isinstance(e, httpx.ConnectError) else 504,
                                    detail="Agentica 서비스 연결 실패" if isinstance(e, httpx.ConnectError) else "Agentica 응답 시간 초과")
            await asyncio.sleep(1)
        except Exception as e:
            if attempt == max_retries - 1:
                raise HTTPException(status_code=500, detail=f"내부 서버 오류: {str(e)}")
            await asyncio.sleep(1)


async def process_ocr(file: UploadFile) -> Optional[str]:
    try:
        content = await file.read()
        if len(content) / (1024 * 1024) > 10:
            return f"[파일 크기 초과]"
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(f"{OCR_SERVICE_URL}/ocr/extract",
                                  files={"file": (file.filename, content, file.content_type)})
            if r.status_code == 200:
                t = r.json().get("extracted_text", "").strip()
                return t if t else "[텍스트 없음]"
            return f"[OCR 실패: HTTP {r.status_code}]"
    except:
        return "[OCR 서비스 오류]"



@router.post("/process-complaint", response_model=ComplaintProcessResponse)
async def process_complaint(raw_text: str = Form(...), file: Optional[UploadFile] = File(None)):
    try:
        ocr_text = await process_ocr(file) if file else None
        formal_text = (await call_agentica_api("/text/transform", {"rawText": raw_text})).get("formalText", raw_text)
        classify_result = await call_agentica_api("/classify", {"text": raw_text})
        classify_data = classify_result[0] if isinstance(classify_result, list) and classify_result else classify_result
        return ComplaintProcessResponse(
            success=True,
            original_text=raw_text,
            formal_text=formal_text,
            department=classify_data.get("best_department", "일반민원과"),
            reason=classify_data.get("reason", "자동 분류"),
            confidence=classify_data.get("confidence", 0.8),
            ocr_text=ocr_text
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"민원 처리 중 오류: {str(e)}")


@router.post("/transform-text")
async def transform_text_only(request: ComplaintProcessRequest):
    return await call_agentica_api("/text/transform", {"rawText": request.raw_text})


@router.post("/classify-department")
async def classify_department_only(request: ComplaintProcessRequest):
    return await call_agentica_api("/classify", {"text": request.raw_text})


@router.post("/process-text-only")
async def process_text_only(request: ComplaintProcessRequest):
    try:
        formal_text = (await call_agentica_api("/text/transform", {"rawText": request.raw_text})).get("formalText", request.raw_text)
        classify_result = await call_agentica_api("/classify", {"text": request.raw_text})
        classify_data = classify_result[0] if isinstance(classify_result, list) and classify_result else classify_result
        return ComplaintProcessResponse(
            success=True,
            original_text=request.raw_text,
            formal_text=formal_text,
            department=classify_data.get("best_department", "일반민원과"),
            reason=classify_data.get("reason", "자동 분류"),
            confidence=classify_data.get("confidence", 0.8),
            ocr_text=None
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"텍스트 처리 중 오류: {str(e)}")
