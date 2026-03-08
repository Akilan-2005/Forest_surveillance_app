"""
FastAPI YOLO backend - runs alongside Flask on port 8000
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import numpy as np
from PIL import Image
import io
import logging

from model_loader import get_model_loader

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="YOLO Object Detection API",
    description="Object detection for Wildlife Ranger Dashboard",
    version="1.0.0"
)

# CORS middleware - allow requests from React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize model on startup
@app.on_event("startup")
async def startup_event():
    logger.info("FastAPI YOLO starting up...")
    loader = get_model_loader()
    if not loader._initialized:
        logger.error("Model failed to initialize!")
    else:
        logger.info("YOLO Model ready")

@app.get("/")
async def root():
    """Health check."""
    loader = get_model_loader()
    return {
        "status": "ok",
        "model_loaded": loader._initialized,
        "fallback_mode": loader.fallback_mode,
        "classes": loader.class_names
    }

@app.post("/detect")
async def detect_objects(file: UploadFile = File(...)):
    """
    Detect objects in uploaded image.
    Returns: { "detections": [{ "label": "...", "confidence": 0.93, "box": [x1, y1, x2, y2] }] }
    """
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read image bytes
        contents = await file.read()
        
        if len(contents) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(status_code=400, detail="File too large (max 10MB)")
        
        logger.info(f"Processing image: {file.filename}, size: {len(contents)} bytes")
        
        # Get model loader
        loader = get_model_loader()
        
        if not loader._initialized:
            raise HTTPException(status_code=503, detail="Model not initialized")
        
        # Run detection
        detections = loader.detect_from_bytes(contents)
        
        logger.info(f"Detected {len(detections)} objects")
        
        return JSONResponse(content={
            "detections": detections,
            "count": len(detections),
            "filename": file.filename
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Detection error: {e}")
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
