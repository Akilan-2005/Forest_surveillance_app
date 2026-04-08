"""
FastAPI YOLO backend - runs alongside Flask on port 8000
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
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
    try:
        loader_threat = get_model_loader(mode="threat")
        loader_species = get_model_loader(mode="species")
        if not loader_threat._initialized or not loader_species._initialized:
            logger.error("One or more models failed to initialize!")
            logger.info("Models will attempt to initialize on first request")
        else:
            logger.info("YOLO Models ready")
    except Exception as e:
        logger.error(f"Error during startup model initialization: {e}")
        logger.info("Models will attempt to initialize on first request")

@app.get("/")
async def root():
    """Health check."""
    loader = get_model_loader(mode="threat")
    return {
        "status": "ok",
        "model_loaded": loader._initialized,
        "fallback_mode": loader.fallback_mode,
        "classes": loader.class_names
    }

@app.post("/detect")
async def detect_objects(
    file: UploadFile = File(...),
    offence_type: str = Form(None)
):
    """
    Detect objects in uploaded image.
    Returns: { "detections": [{ "label": "...", "confidence": 0.93, "box": [x1, y1, x2, y2], "threat_level": "..." }] }
    """
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            logger.warning(f"Invalid file type: {file.content_type}")
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read image bytes
        contents = await file.read()
        
        if len(contents) > 10 * 1024 * 1024:  # 10MB limit
            logger.warning(f"File too large: {len(contents)} bytes")
            raise HTTPException(status_code=400, detail="File too large (max 10MB)")
        
        logger.info(f"Processing image: {file.filename}, size: {len(contents)} bytes, offence_type: {offence_type}")
        
        # Get model loader
        mode = "species" if offence_type == "Species Monitoring" else "threat"
        loader = get_model_loader(mode=mode)
        
        if not loader._initialized:
            logger.error(f"Model not initialized for mode: {mode}")
            raise HTTPException(status_code=503, detail=f"Model not initialized: {mode} detection unavailable")
        
        logger.info(f"Running {mode} detection on image...")
        # Run detection
        detections = loader.detect_from_bytes(contents)
        
        # Filter based on offence_type
        ANIMAL_CLASSES = {'lion', 'tiger', 'cow', 'cat', 'elephant', 'deer', 'zebra', 'dog', 'horse', 'bird', 'sheep', 'bear', 'giraffe'}
        THREAT_CLASSES = {'person', 'human', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat', 'knife', 'gun', 'rifle', 'pistol', 'shotgun', 'machete', 'axe', 'bow', 'arrow', 'explosive'}

        filtered_detections = []
        
        if mode == "species":
            for d in detections:
                if d['label'].lower() in ANIMAL_CLASSES:
                    # No threat level for species
                    d['threat_level'] = 'NONE'
                    filtered_detections.append(d)
        else:
            for d in detections:
                # Always accept threat classes, or optionally accept anything not an animal
                if d['label'].lower() in THREAT_CLASSES or d['label'].lower() not in ANIMAL_CLASSES:
                    # Calculate threat level for poachers/weapons
                    conf = d['confidence']
                    if conf > 0.75:
                        d['threat_level'] = 'CRITICAL'
                    elif conf >= 0.50:
                        d['threat_level'] = 'MEDIUM'
                    else:
                        d['threat_level'] = 'LOW'
                    filtered_detections.append(d)
                    
        detections = filtered_detections
        
        logger.info(f"Detection complete. Found {len(detections)} objects")
        
        return JSONResponse(content={
            "detections": detections,
            "count": len(detections),
            "filename": file.filename,
            "mode": mode
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Detection error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
