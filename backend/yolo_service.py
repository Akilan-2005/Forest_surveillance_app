"""
YOLO Detection Service for Wildlife Offence Detection System.

This module provides a reusable YOLO detection service that integrates
the YOLO model loader from the standalone YOLO project.

Usage:
    from yolo_service import get_yolo_service, YOLOService
    
    # Get singleton instance
    yolo = get_yolo_service()
    
    # Run detection on image bytes
    detections = yolo.detect_from_bytes(image_bytes)
"""

import os
import io
import yaml
import base64
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import logging

# Configure logging
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
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    logger.warning("onnxruntime not available")

try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False
    logger.warning("ultralytics not available")


class YOLOService:
    """
    YOLO object detection service for the Wildlife Offence Detection platform.
    
    This class wraps the YOLO detection logic and provides a clean interface
    for the Flask backend to run object detection on uploaded images.
    
    Features:
    - Loads YOLOv8 model from .mat file with fallback to Ultralytics
    - Provides detection from image bytes (base64 or raw)
    - Returns structured detection results with bounding boxes
    - Singleton pattern for efficient model loading
    """
    
    def __init__(self, mat_file_path: str = None, yaml_file_path: str = None):
        """
        Initialize the YOLO service.
        
        Args:
            mat_file_path: Path to the .mat model file. If None, uses default path.
            yaml_file_path: Path to the data.yaml classes file. If None, uses default path.
        """
        # Default paths - use the custom model from 'new' folder in Desktop
        base_dir = Path(__file__).parent
        
        if mat_file_path is None:
            # Check environment variable first, then use custom model from 'new' folder
            mat_file_path = os.getenv(
                'YOLO_MODEL_PATH',
                str(base_dir / '..' / '..' / 'new' / 'yolov8n.mat')
            )
        
        if yaml_file_path is None:
            yaml_file_path = os.getenv(
                'YOLO_CLASSES_PATH',
                str(base_dir / '..' / '..' / 'new' / 'data.yaml')
            )
        
        self.mat_file_path = Path(mat_file_path)
        self.yaml_file_path = Path(yaml_file_path)
        self.class_names = {}
        self.model = None
        self.session = None
        self.input_shape = (640, 640)  # Default YOLOv8 input size
        self.fallback_mode = False
        self._initialized = False
        
        logger.info(f"YOLOService initialized with model: {self.mat_file_path}")
    
    def initialize(self) -> bool:
        """
        Load the model and initialize the service.
        
        Returns:
            True if initialization successful, False otherwise.
        """
        if self._initialized:
            return True
        
        try:
            self._load_classes()
            self._load_model()
            self._initialized = True
            logger.info(f"YOLOService initialized successfully (fallback: {self.fallback_mode})")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize YOLOService: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def is_initialized(self) -> bool:
        """Check if the service is initialized."""
        return self._initialized
    
    def _load_classes(self):
        """Load class names from YAML file."""
        try:
            if not self.yaml_file_path.exists():
                logger.warning(f"YAML file not found: {self.yaml_file_path}")
                # Use empty dictionary so we fallback to the model's built-in names (e.g., COCO names)
                self.class_names = {}
                return
            
            with open(self.yaml_file_path, 'r') as f:
                data = yaml.safe_load(f)
            
            if 'names' in data:
                self.class_names = data['names']
            else:
                logger.warning("No 'names' key found in YAML, using default class indices")
                self.class_names = {i: f"class_{i}" for i in range(80)}
            
            logger.info(f"Loaded {len(self.class_names)} classes: {self.class_names}")
        except Exception as e:
            logger.error(f"Failed to load YAML classes: {e}")
            self.class_names = {i: f"class_{i}" for i in range(80)}
    
    def _load_model(self):
        """Load model from .mat file or fallback to Ultralytics."""
        if not self.mat_file_path.exists():
            logger.error(f"Model file not found: {self.mat_file_path}")
            self._try_fallback()
            return
        
        # First, try to inspect the .mat file
        if SCIPY_AVAILABLE:
            try:
                self._inspect_mat_file()
            except Exception as e:
                logger.warning(f"Could not inspect .mat file: {e}")
        
        # Try to convert to ONNX if possible
        if self._try_onnx_conversion():
            return
        
        # Fallback to Ultralytics
        self._try_fallback()
    
    def _inspect_mat_file(self):
        """Inspect the .mat file structure."""
        try:
            mat_contents = loadmat(str(self.mat_file_path), struct_as_record=False, squeeze_me=True)
            logger.info(f"MAT file keys: {list(mat_contents.keys())}")
            
            # Log the structure to help debugging
            for key in mat_contents.keys():
                if not key.startswith('__'):
                    value = mat_contents[key]
                    logger.info(f"Key '{key}': type={type(value)}, shape={getattr(value, 'shape', 'N/A')}")
        except Exception as e:
            logger.error(f"Error inspecting .mat file: {e}")
    
    def _try_onnx_conversion(self) -> bool:
        """Attempt to convert .mat to ONNX format."""
        if not ONNX_AVAILABLE:
            return False
        
        # Check if ONNX file already exists
        onnx_path = self.mat_file_path.with_suffix('.onnx')
        if onnx_path.exists():
            logger.info(f"Found existing ONNX file: {onnx_path}")
            return self._load_onnx(str(onnx_path))
        
        # For now, return False to trigger fallback
        # Direct .mat to ONNX conversion requires specific MATLAB export format
        logger.info("ONNX conversion not available, will use fallback")
        return False
    
    def _load_onnx(self, onnx_path: str) -> bool:
        """Load ONNX model."""
        try:
            self.session = ort.InferenceSession(onnx_path)
            input_shape = self.session.get_inputs()[0].shape
            if len(input_shape) >= 2:
                self.input_shape = (input_shape[2], input_shape[3]) if len(input_shape) > 3 else (640, 640)
            logger.info(f"Loaded ONNX model with input shape: {self.input_shape}")
            return True
        except Exception as e:
            logger.error(f"Failed to load ONNX: {e}")
            return False
    
    def _try_fallback(self):
        """Fallback to using Ultralytics YOLOv8."""
        if not ULTRALYTICS_AVAILABLE:
            logger.error("Ultralytics not available - cannot use fallback")
            raise RuntimeError("No suitable model runtime available")
        
        logger.info("Using Ultralytics YOLOv8 fallback")
        
        # Check if PyTorch weights exist in the same directory as the .mat file
        pt_path = self.mat_file_path.with_suffix('.pt')
        
        if pt_path.exists():
            logger.info(f"Loading PyTorch weights: {pt_path}")
            try:
                self.model = YOLO(str(pt_path))
                self.fallback_mode = True
                logger.info(f"Successfully loaded custom model from {pt_path}")
                return
            except Exception as e:
                logger.warning(f"Failed to load .pt weights: {e}")
        
        # Check if there's a yolov8n.pt in the backend/yolo_model directory
        backend_dir = Path(__file__).parent
        yolo_model_pt = backend_dir / 'yolo_model' / 'yolov8n.pt'
        if yolo_model_pt.exists():
            logger.info(f"Loading backend yolo_model: {yolo_model_pt}")
            try:
                self.model = YOLO(str(yolo_model_pt))
                self.fallback_mode = True
                logger.info("Successfully loaded yolov8n.pt from backend/yolo_model")
                return
            except Exception as e:
                logger.warning(f"Failed to load backend model: {e}")
        
        # Load pretrained nano model (will download if not present)
        logger.info("Loading pretrained YOLOv8n model (this may download ~6MB on first run)")
        try:
            import torch
            # Set cache directory to backend folder
            torch.hub.set_dir(str(backend_dir / 'yolo_model'))
            self.model = YOLO('yolov8n.pt')
            self.fallback_mode = True
            logger.info("Loaded pretrained YOLOv8n model successfully")
        except Exception as e:
            logger.error(f"Failed to load pretrained model: {e}")
            raise RuntimeError(f"Could not load any model: {e}")
    
    def preprocess(self, image: np.ndarray) -> Tuple[np.ndarray, Tuple[float, float], Tuple[float, float]]:
        """
        Preprocess image for inference.
        
        Returns:
            preprocessed_image: Image ready for model input
            scale_factors: (scale_x, scale_y) for bbox scaling
            padding: (pad_x, pad_y) added during letterboxing
        """
        if not CV2_AVAILABLE:
            raise RuntimeError("OpenCV required for image preprocessing")
        
        original_h, original_w = image.shape[:2]
        input_h, input_w = self.input_shape
        
        # Calculate scaling to fit image within input size while maintaining aspect ratio
        scale = min(input_w / original_w, input_h / original_h)
        new_w = int(original_w * scale)
        new_h = int(original_h * scale)
        
        # Resize image
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        
        # Create padded image (letterbox)
        padded = np.full((input_h, input_w, 3), 114, dtype=np.uint8)
        pad_x = (input_w - new_w) // 2
        pad_y = (input_h - new_h) // 2
        padded[pad_y:pad_y + new_h, pad_x:pad_x + new_w] = resized
        
        # Normalize to [0, 1] and convert to RGB
        processed = padded[..., ::-1].astype(np.float32) / 255.0
        
        # Transpose to CHW format and add batch dimension
        processed = np.transpose(processed, (2, 0, 1))
        processed = np.expand_dims(processed, axis=0)
        
        return processed, (scale, scale), (pad_x, pad_y)
    
    def postprocess(
        self, 
        outputs: np.ndarray, 
        scale: Tuple[float, float], 
        padding: Tuple[float, float],
        original_shape: Tuple[int, int],
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45
    ) -> List[Dict[str, Any]]:
        """
        Postprocess model outputs to extract detections.
        
        Args:
            outputs: Raw model output
            scale: Scaling factors used during preprocessing
            padding: Padding added during preprocessing
            original_shape: Original image (H, W)
            conf_threshold: Confidence threshold
            iou_threshold: IoU threshold for NMS
        
        Returns:
            List of detection dictionaries
        """
        detections = []
        
        if outputs.shape[0] == 1:
            outputs = outputs[0]
        
        # YOLOv8 output format: [num_predictions, 84] where 84 = 4 (box) + 80 (classes)
        
        if outputs.shape[-1] < 5:
            # Transpose if needed
            outputs = outputs.T
        
        boxes = []
        scores = []
        class_ids = []
        
        num_classes = len(self.class_names)
        
        for pred in outputs:
            if len(pred) < 5:
                continue
            
            # Extract box coordinates and class scores
            x_center, y_center, width, height = pred[:4]
            class_scores = pred[4:4 + num_classes] if len(pred) >= 4 + num_classes else pred[4:]
            
            if len(class_scores) == 0:
                continue
            
            # Get class with highest score
            class_id = np.argmax(class_scores)
            confidence = class_scores[class_id]
            
            if confidence < conf_threshold:
                continue
            
            # Convert from center format to corner format
            x1 = x_center - width / 2
            y1 = y_center - height / 2
            x2 = x_center + width / 2
            y2 = y_center + height / 2
            
            boxes.append([x1, y1, x2, y2])
            scores.append(confidence)
            class_ids.append(class_id)
        
        if len(boxes) == 0:
            return detections
        
        boxes = np.array(boxes)
        scores = np.array(scores)
        class_ids = np.array(class_ids)
        
        # Apply Non-Maximum Suppression
        if CV2_AVAILABLE and len(boxes) > 0:
            indices = cv2.dnn.NMSBoxes(
                boxes.tolist(),
                scores.tolist(),
                conf_threshold,
                iou_threshold
            )
            
            if isinstance(indices, np.ndarray):
                indices = indices.flatten()
            elif isinstance(indices, tuple):
                indices = list(indices)
            
            scale_x, scale_y = scale
            pad_x, pad_y = padding
            orig_h, orig_w = original_shape
            input_h, input_w = self.input_shape
            
            for idx in indices:
                box = boxes[idx]
                score = scores[idx]
                class_id = int(class_ids[idx])
                
                # Convert from input space to original image space
                x1, y1, x2, y2 = box
                
                # Remove padding
                x1 -= pad_x
                y1 -= pad_y
                x2 -= pad_x
                y2 -= pad_y
                
                # Remove scaling
                x1 /= scale_x
                y1 /= scale_y
                x2 /= scale_x
                y2 /= scale_y
                
                # Clip to image bounds
                x1 = max(0, min(x1, orig_w))
                y1 = max(0, min(y1, orig_h))
                x2 = max(0, min(x2, orig_w))
                y2 = max(0, min(y2, orig_h))
                
                detections.append({
                    'label': self.class_names.get(class_id, f"class_{class_id}"),
                    'confidence': float(score),
                    'box': [int(x1), int(y1), int(x2), int(y2)]
                })
        
        return detections
    
    def detect(
        self, 
        image: np.ndarray, 
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45
    ) -> List[Dict[str, Any]]:
        """
        Run object detection on an image.
        
        Args:
            image: Input image (BGR format from OpenCV)
            conf_threshold: Minimum confidence for detections
            iou_threshold: IoU threshold for NMS
        
        Returns:
            List of detection dictionaries with keys: label, confidence, box
        """
        if not self._initialized:
            raise RuntimeError("YOLOService not initialized. Call initialize() first.")
        
        original_shape = image.shape[:2]
        
        # Preprocess
        processed, scale, padding = self.preprocess(image)
        
        # Run inference
        if self.fallback_mode and self.model is not None:
            # Ultralytics inference
            results = self.model.predict(
                source=image,
                conf=conf_threshold,
                iou=iou_threshold,
                verbose=False
            )[0]
            
            detections = []
            if results.boxes is not None:
                for box in results.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = float(box.conf[0].cpu().numpy())
                    cls_id = int(box.cls[0].cpu().numpy())
                    
                    # Map to our custom classes if available
                    label = self.class_names.get(cls_id, results.names.get(cls_id, f"class_{cls_id}"))
                    
                    detections.append({
                        'label': label,
                        'confidence': conf,
                        'box': [int(x1), int(y1), int(x2), int(y2)]
                    })
            
            return detections
        
        elif self.session is not None:
            # ONNX inference
            input_name = self.session.get_inputs()[0].name
            outputs = self.session.run(None, {input_name: processed})
            
            # Process outputs
            return self.postprocess(
                outputs[0], 
                scale, 
                padding, 
                original_shape,
                conf_threshold,
                iou_threshold
            )
        
        else:
            raise RuntimeError("No model loaded for inference")
    
    def detect_from_bytes(
        self, 
        image_bytes: bytes,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45
    ) -> List[Dict[str, Any]]:
        """
        Run detection on raw image bytes.
        
        Args:
            image_bytes: Raw image bytes (JPEG/PNG)
            conf_threshold: Confidence threshold
            iou_threshold: IoU threshold for NMS
        
        Returns:
            List of detection dictionaries
        """
        if not CV2_AVAILABLE:
            raise RuntimeError("OpenCV required for image decoding")
        
        # Decode image from bytes
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            raise ValueError("Could not decode image from bytes")
        
        return self.detect(image, conf_threshold, iou_threshold)
    
    def detect_from_base64(
        self,
        base64_string: str,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45
    ) -> List[Dict[str, Any]]:
        """
        Run detection on base64-encoded image.
        
        Args:
            base64_string: Base64-encoded image (with or without data URI prefix)
            conf_threshold: Confidence threshold
            iou_threshold: IoU threshold for NMS
        
        Returns:
            List of detection dictionaries
        """
        # Handle data URI format
        if base64_string.startswith('data:'):
            header, b64 = base64_string.split(',', 1)
            image_bytes = base64.b64decode(b64)
        else:
            image_bytes = base64.b64decode(base64_string)
        
        return self.detect_from_bytes(image_bytes, conf_threshold, iou_threshold)


# Global service instance (lazy loaded)
_yolo_service = None

def get_yolo_service(mat_file_path: str = None, yaml_file_path: str = None) -> YOLOService:
    """
    Get or create the global YOLO service instance.
    
    This function implements the singleton pattern to ensure the model
    is loaded only once at application startup.
    
    Args:
        mat_file_path: Path to .mat model file (optional)
        yaml_file_path: Path to data.yaml file (optional)
    
    Returns:
        YOLOService instance
    """
    global _yolo_service
    if _yolo_service is None:
        _yolo_service = YOLOService(mat_file_path, yaml_file_path)
        _yolo_service.initialize()
    return _yolo_service

def reset_yolo_service():
    """Reset the global service instance (useful for testing)."""
    global _yolo_service
    _yolo_service = None
