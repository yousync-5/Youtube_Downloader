import os
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
import requests
from main import main_pipeline

app = FastAPI()

# 실행 디렉토리 보정 (항상 youtube_processor에서 실행되도록)
os.chdir(os.path.dirname(os.path.abspath(__file__)))

class PreprocessRequest(BaseModel):
    youtube_url: str
    movie_name: Optional[str] = None
    actor_name: Optional[str] = None
    webhook_url: Optional[str] = None  # 결과를 보낼 콜백 URL
    job_id: Optional[str] = None

class PreprocessResponse(BaseModel):
    token_id: Optional[List[int]] = None
    status: str
    message: str
    job_id: Optional[str] = None

@app.post("/process", response_model=PreprocessResponse)
def process_youtube(
    req: PreprocessRequest,
    background_tasks: BackgroundTasks
):
    # 백그라운드에서 파이프라인 실행 및 결과 webhook 전송
    def run_pipeline_and_callback():
        try:
            token_id = main_pipeline(req.youtube_url, req.movie_name, req.actor_name)
            payload = {
                "token_id": token_id,  # 방금 DB에 저장된 Token의 id
                "status": "completed",
                "message": "전처리 완료",
                "job_id": req.job_id
            }
        except Exception as e:
            payload = {
                "token_id": None,
                "status": "failed",
                "message": str(e),
                "job_id": req.job_id
            }
        if req.webhook_url:
            try:
                requests.post(req.webhook_url, json=payload, timeout=10)
            except Exception as e:
                print(f"[Webhook 전송 실패] {e}")

    background_tasks.add_task(run_pipeline_and_callback)
    return PreprocessResponse(
        status="processing",
        message="전처리 요청이 접수되었습니다.",
        job_id=req.job_id
    ) 