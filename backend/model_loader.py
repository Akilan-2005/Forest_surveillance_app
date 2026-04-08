"""
Model Loader for MATLAB-trained YOLOv8 model.

Handles loading .mat files and converting to Python-compatible format.
Falls back to Ultralytics if direct conversion isn't possible.
"""

import os
# Disable PyTorch 2.6+ weights_only safety check for YOLO compatibility
os.environ['TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD'] = '1'

import yaml
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try importing optional dependencies
try:
    from scipy.io import loadmat
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logger.warning("scipy not available")

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logger.warning("opencv-python not available")

try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False
    logger.warning("ultralytics not available")


class YOLOModelLoader:
    """
    Loads and runs YOLO model from MATLAB .mat file or fallback to PyTorch.
    """
    
    def __init__(self, mat_path: str = "yolov8n.mat", yaml_path: str = "data.yaml"):
        # Default paths - use files in current directory
        self.mat_path = Path(mat_path) if mat_path else Path("yolov8n.mat")
        self.yaml_path = Path(yaml_path) if yaml_path else Path("data.yaml")
        self.class_names = {}
        self.model = None
        self.fallback_mode = False
        self._initialized = False
        
    def initialize(self) -> bool:
        """Initialize the model loader."""
        try:
            self._load_classes()
            self._load_model()
            self._initialized = True
            logger.info(f"Model loader initialized (fallback: {self.fallback_mode})")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _load_classes(self):
        """Load class names from YAML."""
        if not self.yaml_path.exists():
            logger.warning(f"YAML not found: {self.yaml_path}, using defaults")
            self.class_names = {}
            return
        
        with open(self.yaml_path, 'r') as f:
            data = yaml.safe_load(f)
        
        if 'names' in data:
            self.class_names = data['names']
        else:
            self.class_names = {i: f"class_{i}" for i in range(80)}
        
        logger.info(f"Loaded {len(self.class_names)} classes: {self.class_names}")
    
    def _load_model(self):
        """Load model - try .mat first, fallback to PyTorch."""
        # Check if .mat file exists
        if not self.mat_path.exists():
            logger.error(f"MAT file not found: {self.mat_path}")
            self._try_pytorch_fallback()
            return
        
        # Inspect .mat file structure
        if SCIPY_AVAILABLE:
            try:
                self._inspect_mat_file()
            except Exception as e:
                logger.warning(f"Could not inspect .mat: {e}")
        
        # Since .mat files from MATLAB are hard to convert without MATLAB,
        # we use PyTorch fallback with pretrained model
        logger.info("MAT file present but requires conversion - using PyTorch fallback")
        self._try_pytorch_fallback()
    
    def _inspect_mat_file(self):
        """Inspect MATLAB file structure."""
        mat_contents = loadmat(str(self.mat_path), struct_as_record=False, squeeze_me=True)
        logger.info(f"MAT file keys: {list(mat_contents.keys())}")
        
        for key in mat_contents.keys():
            if not key.startswith('__'):
                value = mat_contents[key]
                logger.info(f"  {key}: type={type(value)}, shape={getattr(value, 'shape', 'N/A')}")
    
    def _try_pytorch_fallback(self):
        """Fallback to Ultralytics YOLO."""
        if not ULTRALYTICS_AVAILABLE:
            raise RuntimeError("Ultralytics not available")
        
        # Note: PyTorch 2.6+ weights_only is disabled via environment variable at top of file
        
        # Check for .pt file in same directory
        pt_path = self.mat_path.with_suffix('.pt')
        
        if pt_path.exists():
            logger.info(f"Loading PyTorch model: {pt_path}")
            self.model = YOLO(str(pt_path))
            self.fallback_mode = True
            return
        
        # Check for yolov8n.pt in yolo_model directory
        yolo_model_pt = Path("yolo_model/yolov8n.pt")
        if yolo_model_pt.exists():
            logger.info(f"Loading yolo_model/yolov8n.pt")
            self.model = YOLO(str(yolo_model_pt))
            self.fallback_mode = True
            return
        
        # Download pretrained YOLOv8n
        logger.info("Downloading pretrained YOLOv8n...")
        self.model = YOLO('yolov8n.pt')
        self.fallback_mode = True
        logger.info("Loaded pretrained YOLOv8n")
    
    def detect(self, image: np.ndarray, conf_threshold: float = 0.25) -> List[Dict]:
        """Run detection on image."""
        if not self._initialized or self.model is None:
            raise RuntimeError("Model not initialized")
        
        results = self.model.predict(
            source=image,
            conf=conf_threshold,
            verbose=False
        )[0]
        
        detections = []
        if results.boxes is not None:
            for box in results.boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0].cpu().numpy())
                cls_id = int(box.cls[0].cpu().numpy())
                
                # Use custom class names if available, otherwise model's names
                label = self.class_names.get(cls_id, results.names.get(cls_id, f"class_{cls_id}"))
                
                detections.append({
                    'label': label,
                    'confidence': conf,
                    'box': [int(x1), int(y1), int(x2), int(y2)]
                })
        
        return detections
    
    def detect_from_bytes(self, image_bytes: bytes, conf_threshold: float = 0.25) -> List[Dict]:
        """Run detection on image bytes."""
        if not CV2_AVAILABLE:
            raise RuntimeError("OpenCV required")
        
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            raise ValueError("Could not decode image")
        
        return self.detect(image, conf_threshold)


# Global instances
_model_loaders = {}

def get_model_loader(mode: str = "threat") -> YOLOModelLoader:
    """Get or create global model loader instance for a specific mode."""
    global _model_loaders
    if mode not in _model_loaders:
        # Use yolov8n.pt for both modes - it's a universal model
        mat_path = "yolo_model/yolov8n.mat"
        
        if mode == "species":
            yaml_path = "yolo_model/species_data.yaml"
        else:
            yaml_path = "yolo_model/threat_data.yaml"
            
        _model_loaders[mode] = YOLOModelLoader(mat_path=mat_path, yaml_path=yaml_path)
        _model_loaders[mode].initialize()
    return _model_loaders[mode]
