from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
from ..revenue_pipeline import get_revenue_pipeline

router = APIRouter(prefix="/api/v1", tags=["generator"])
logger = logging.getLogger(__name__)

class GenerateRequest(BaseModel):
    url: str
    auto_deploy: bool = True

class GenerateResponse(BaseModel):
    job_id: str
    status: str
    message: str
    details: Optional[Dict[str, Any]] = None

# In-memory job store for MVP (replace with Redis/Database later)
jobs: Dict[str, Dict[str, Any]] = {}

@router.post("/generate", response_model=GenerateResponse)
async def generate_infrastructure(request: GenerateRequest, background_tasks: BackgroundTasks):
    """
    Trigger the infrastructure generation pipeline for a YouTube video.
    """
    try:
        job_id = f"job_{len(jobs) + 1}"
        jobs[job_id] = {"status": "processing", "url": request.url}
        
        # for MVP, we'll run it synchronously or background task?
        # The user wants "real-time logs" in the UI eventually. 
        # For this step, let's keep it simple and await it if it's not too long, 
        # BUT revenue pipeline takes minutes. Background task is better.
        
        background_tasks.add_task(run_pipeline_background, job_id, request.url, request.auto_deploy)
        
        return GenerateResponse(
            job_id=job_id,
            status="queued",
            message="Infrastructure generation started",
            details={"url": request.url}
        )

    except Exception as e:
        logger.error(f"Failed to start generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/generate/{job_id}")
async def get_generation_status(job_id: str):
    """
    Get the status of a generation job.
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return jobs[job_id]

async def run_pipeline_background(job_id: str, url: str, auto_deploy: bool):
    """
    Background task wrapper for the pipeline.
    """
    try:
        logger.info(f"Starting pipeline for job {job_id}")
        pipeline = get_revenue_pipeline(auto_deploy=auto_deploy)
        
        # This is a long-running process
        result = await pipeline.process_video_to_deployment(url)
        
        if result['success']:
            jobs[job_id]['status'] = 'completed'
            jobs[job_id]['result'] = result
            logger.info(f"Job {job_id} completed successfully")
        else:
            jobs[job_id]['status'] = 'failed'
            jobs[job_id]['error'] = result.get('error')
            logger.error(f"Job {job_id} failed: {result.get('error')}")
            
    except Exception as e:
        jobs[job_id]['status'] = 'failed'
        jobs[job_id]['error'] = str(e)
        logger.error(f"Job {job_id} exception: {e}")
