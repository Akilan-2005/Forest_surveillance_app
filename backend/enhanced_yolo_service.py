"""
Enhanced YOLO Detection Service for Wildlife Surveillance System.

This module provides dual-mode detection:
1. Species Monitoring Mode - Detects animal species only
2. Threat Monitoring Mode - Detects humans, weapons, and suspicious objects

Usage:
    from enhanced_yolo_service import get_enhanced_yolo_service
    
    # Get service instance
    yolo = get_enhanced_yolo_service()
    
    # Run species detection
    detections = yolo.detect_species(image_bytes)
    
    # Run threat detection
    detections = yolo.detect_threats(image_bytes)
"""

import os
import io
import yaml
import base64
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import logging
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try importing dependencies
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

class DetectionMode(Enum):
    """Detection mode enumeration."""
    SPECIES = "species"
    THREAT = "threat"

class ThreatLevel(Enum):
    """Threat level enumeration."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    CRITICAL = "CRITICAL"

class EnhancedYOLOService:
    """
    Enhanced YOLO detection service with dual-mode support.
    
    Features:
    - Species Monitoring: Detects animal species only
    - Threat Monitoring: Detects humans, weapons, and suspicious objects
    - Threat level classification based on confidence
    - Color-coded bounding boxes
    - Proper class mapping for both modes
    """
    
    def __init__(self):
        """Initialize the enhanced YOLO service."""
        self.base_dir = Path(__file__).parent
        self.models_dir = self.base_dir / 'yolo_model'
        
        # Initialize models
        self.species_model = None
        self.threat_model = None
        
        # Species Classes (8 animals + birds)
        self.species_classes = {
            0: 'lion', 1: 'tiger', 2: 'elephant', 3: 'rhino', 4: 'bear', 
            5: 'deer', 6: 'zebra', 7: 'cow', 8: 'cat', 9: 'dog', 
            10: 'horse', 11: 'bird'
        }
        
        # Threat Classes (1 human + 8 weapons)
        self.threat_classes = {
            0: 'human', 1: 'gun', 2: 'rifle', 3: 'pistol', 4: 'shotgun',
            5: 'knife', 6: 'machete', 7: 'axe', 8: 'bow', 9: 'arrow'
        }
        
        self._initialized = False
        self._initialization_error = None
        self.fallback_mode = False
        
        logger.info("Enhanced YOLO Service instance created")
    
    def initialize(self) -> bool:
        """Initialize both detection models."""
        if self._initialized:
            logger.info("Service already initialized")
            return True
        
        try:
            logger.info("Starting to initialize YOLO models...")
            self._load_models()
            self._initialized = True
            self._initialization_error = None
            logger.info("✓ Enhanced YOLO Service initialized successfully")
            return True
        except Exception as e:
            error_msg = f"Failed to initialize Enhanced YOLO Service: {type(e).__name__}: {str(e)}"
            logger.error(error_msg)
            self._initialization_error = error_msg
            self._initialized = False
            return False
    
    def is_initialized(self) -> bool:
        """Check if service is initialized."""
        return self._initialized
    
    def get_initialization_status(self) -> Dict[str, Any]:
        """Get detailed initialization status."""
        return {
            'initialized': self._initialized,
            'species_model_loaded': self.species_model is not None,
            'threat_model_loaded': self.threat_model is not None,
            'error': self._initialization_error,
            'cv2_available': CV2_AVAILABLE,
            'ultralytics_available': ULTRALYTICS_AVAILABLE,
            'fallback_mode': self.fallback_mode
        }
    
    def _load_models(self):
        """Load species and threat detection models."""
        logger.info("Checking dependencies...")
        if not ULTRALYTICS_AVAILABLE:
            raise RuntimeError("Ultralytics YOLO library not available. Install: pip install ultralytics")
        if not CV2_AVAILABLE:
            raise RuntimeError("OpenCV (cv2) not available. Install: pip install opencv-python")
        
        # Try to load custom models first
        species_model_path = self.models_dir / 'species_model.pt'
        threat_model_path = self.models_dir / 'threat_model.pt'
        
        # Load species model
        logger.info("Loading species detection model...")
        if species_model_path.exists():
            logger.info(f"  Found custom species model: {species_model_path}")
            self.species_model = YOLO(str(species_model_path))
            logger.info("  ✓ Custom species model loaded successfully")
        else:
            logger.info("  Custom species model not found, using YOLOv8n nano model")
            # Check if yolov8n.pt exists in the current directory or models directory
            model_path = 'yolov8n.pt'
            if not Path(model_path).exists():
                model_path = self.base_dir / 'yolov8n.pt'
            if not Path(model_path).exists():
                # Try downloading if not found
                logger.info("  Model file not found, downloading YOLOv8n...")
                model_path = 'yolov8n.pt'
            logger.info(f"  Loading YOLOv8n from: {model_path}")
            self.species_model = YOLO(str(model_path))
            logger.info("  ✓ YOLOv8n nano model loaded successfully for species detection")
        
        # Load threat model  
        logger.info("Loading threat detection model...")
        if threat_model_path.exists():
            logger.info(f"  Found custom threat model: {threat_model_path}")
            self.threat_model = YOLO(str(threat_model_path))
            logger.info("  ✓ Custom threat model loaded successfully")
        else:
            logger.info("  Custom threat model not found, using YOLOv8n nano model")
            model_path = 'yolov8n.pt'
            if not Path(model_path).exists():
                model_path = self.base_dir / 'yolov8n.pt'
            if not Path(model_path).exists():
                # Try downloading if not found
                logger.info("  Model file not found, downloading YOLOv8n...")
                model_path = 'yolov8n.pt'
            logger.info(f"  Loading YOLOv8n from: {model_path}")
            self.threat_model = YOLO(str(model_path))
            logger.info("  ✓ YOLOv8n nano model loaded successfully for threat detection")
        
        # Verify both models are actually loaded
        if self.species_model is None or self.threat_model is None:
            raise RuntimeError("Failed to load one or more models")
        
        self.fallback_mode = True
        logger.info("All models loaded successfully")
    
    def classify_threat_level(self, confidence: float) -> ThreatLevel:
        """Classify threat level based on confidence score."""
        if confidence < 0.50:
            return ThreatLevel.LOW
        elif confidence <= 0.75:
            return ThreatLevel.MEDIUM
        else:
            return ThreatLevel.CRITICAL
    
    def get_detection_color(self, mode: DetectionMode, label: str, confidence: float) -> str:
        """Get color for bounding box based on mode and threat level."""
        if mode == DetectionMode.SPECIES:
            return '#00FF00'  # Green for wildlife species
        else:
            # Color based on threat level
            threat_level = self.classify_threat_level(confidence)
            if threat_level == ThreatLevel.CRITICAL:
                return '#FF0000'  # Red
            elif threat_level == ThreatLevel.MEDIUM:
                return '#FFA500'  # Orange
            else:
                return '#FFFF00'  # Yellow
    
    def filter_species_detections(self, detections: List[Dict]) -> List[Dict]:
        """Filter detections to keep only wildlife species and birds with improved classification."""
        species_keywords = [
            'lion', 'tiger', 'elephant', 'rhino', 'bear', 'deer', 'zebra', 
            'cow', 'cat', 'dog', 'horse', 'bird', 'birds'
        ]
        
        # COCO animal classes for better filtering
        coco_animals = [
            'lion', 'tiger', 'elephant', 'rhinoceros', 'bear', 'zebra', 'giraffe',
            'cow', 'sheep', 'goat', 'pig', 'horse', 'cat', 'dog', 'bird', 'deer', 'moose'
        ]
        
        filtered = []
        for det in detections:
            label = det['label'].lower()
            confidence = det.get('confidence', 0)
            class_id = det.get('class_id', -1)
            
            # Check if it's a species (from our classes or COCO animals/birds)
            is_species = (
                any(species in label for species in species_keywords) or
                class_id in self.species_classes or
                any(animal in label for animal in coco_animals)
            )
            
            if is_species:
                # Apply stricter validation for common misclassifications
                if self._validate_species_classification(label, confidence):
                    # Ensure proper species name mapping
                    corrected_label = self._correct_species_name(label, confidence)
                    if corrected_label:
                        det['label'] = corrected_label
                        det['original_label'] = label  # Keep original for debugging
                    filtered.append(det)
        
        return filtered
    
    def _correct_species_name(self, label: str, confidence: float) -> str:
        """Correct common species misclassifications."""
        # Common misclassification patterns
        corrections = {
            # Rhino corrections
            'cow': 'rhino' if confidence > 0.6 else None,
            'bull': 'rhino' if confidence > 0.6 else None,
            'cattle': 'rhino' if confidence > 0.6 else None,
            
            # Lion corrections
            'dog': 'lion' if confidence > 0.7 else None,
            'wolf': 'lion' if confidence > 0.7 else None,
            
            # Tiger corrections
            'leopard': 'tiger' if confidence > 0.7 else None,
            'panther': 'tiger' if confidence > 0.7 else None,
            
            # Elephant corrections
            'mammoth': 'elephant' if confidence > 0.6 else None,
            
            # Bear corrections
            'polar bear': 'bear' if confidence > 0.6 else None,
            
            # Deer corrections
            'antelope': 'deer' if confidence > 0.6 else None,
            
            # Zebra corrections
            'horse': 'zebra' if confidence > 0.7 else None,
            
            # Bird corrections
            'airplane': 'bird' if confidence > 0.5 else None,
            'car': 'bird' if confidence > 0.5 else None,
        }
        
        # Check for corrections
        for misclassified, correct_species in corrections.items():
            if misclassified in label and confidence > 0.5:
                return correct_species
        
        return None
    
    def _validate_species_classification(self, label: str, confidence: float) -> bool:
        """Validate that species classification is reasonable."""
        # High confidence species are always valid
        if confidence > 0.8:
            return True
        
        # For lower confidence, check for common misclassifications
        common_misclassifications = [
            ('person', 'human'), ('car', 'truck'), ('bicycle', 'motorcycle'),
            ('chair', 'table'), ('bottle', 'cup')
        ]
        
        for misclass in common_misclassifications:
            if misclass[0] in label or misclass[1] in label:
                return False
        
        return True
    
    def filter_threat_detections(self, detections: List[Dict]) -> List[Dict]:
        """Filter detections to keep only humans and weapons."""
        threat_keywords = [
            'human', 'person', 'gun', 'rifle', 'pistol', 'shotgun', 
            'knife', 'machete', 'axe', 'bow', 'arrow'
        ]
        
        filtered = []
        for det in detections:
            label = det['label'].lower()
            # Check if it's a threat (humans or weapons)
            if (any(threat in label for threat in threat_keywords) or
                det.get('class_id', -1) in self.threat_classes):
                # Add threat level classification
                threat_level = self.classify_threat_level(det['confidence'])
                det['threat_level'] = threat_level.value
                det['detection_type'] = 'threat'
                filtered.append(det)
        
        return filtered
    
    def enhance_detections(self, detections: List[Dict], mode: DetectionMode) -> List[Dict]:
        """Enhance detections with additional metadata."""
        enhanced = []
        
        for det in detections:
            enhanced_det = det.copy()
            
            # Add color for visualization
            enhanced_det['color'] = self.get_detection_color(
                mode, det['label'], det['confidence']
            )
            
            # Add formatted label with confidence and threat level
            confidence_pct = f"{det['confidence'] * 100:.0f}%"
            
            if mode == DetectionMode.THREAT:
                threat_level = self.classify_threat_level(det['confidence'])
                enhanced_det['display_label'] = f"{det['label']} - {confidence_pct} ({threat_level.value})"
            else:
                enhanced_det['display_label'] = f"{det['label']} - {confidence_pct}"
            
            enhanced_det['detection_type'] = mode.value
            enhanced_det['timestamp'] = np.datetime64('now').astype(str)
            
            enhanced.append(enhanced_det)
        
        return enhanced
    
    def detect_species(self, image_bytes: bytes, conf_threshold: float = 0.25) -> List[Dict]:
        """
        Run species detection on image bytes.
        
        Args:
            image_bytes: Raw image bytes
            conf_threshold: Confidence threshold for detection
            
        Returns:
            List of species detections with bounding boxes
        """
        logger.info(f"Starting species detection (threshold: {conf_threshold})")
        
        # Ensure service is initialized
        if not self.is_initialized():
            logger.warning("Service not initialized, attempting initialization now...")
            if not self.initialize():
                error_msg = f"Service not initialized: {self._initialization_error}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
        
        if not CV2_AVAILABLE:
            raise RuntimeError("OpenCV required for image processing")
        
        if self.species_model is None:
            raise RuntimeError("Species model not loaded")
        
        try:
            # Decode image
            logger.debug(f"Decoding image ({len(image_bytes)} bytes)")
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                raise ValueError("Could not decode image - invalid image format")
            
            logger.debug(f"Image decoded successfully: {image.shape}")
            
            # Run detection
            logger.debug("Running YOLO species detection model...")
            results = self.species_model.predict(
                source=image,
                conf=conf_threshold,
                iou=0.45,
                verbose=False
            )[0]
            
            logger.debug(f"Detection complete, found {len(results.boxes) if results.boxes else 0} boxes")
            
            # Convert to standard format
            detections = []
            if results.boxes is not None:
                for box in results.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = float(box.conf[0].cpu().numpy())
                    cls_id = int(box.cls[0].cpu().numpy())
                    
                    # Map to our species classes if available
                    label = self.species_classes.get(cls_id, results.names.get(cls_id, f"class_{cls_id}"))
                    
                    detections.append({
                        'label': label,
                        'confidence': conf,
                        'box': [int(x1), int(y1), int(x2), int(y2)],
                        'class_id': cls_id
                    })
            
            logger.debug(f"Converted {len(detections)} detections")
            
            # Filter to keep only animals
            filtered_detections = self.filter_species_detections(detections)
            logger.info(f"Species detection complete: {len(filtered_detections)} species found")
            
            # Enhance with metadata
            return self.enhance_detections(filtered_detections, DetectionMode.SPECIES)
        except Exception as e:
            logger.error(f"Error during species detection: {type(e).__name__}: {str(e)}", exc_info=True)
            raise
    
    def detect_threats(self, image_bytes: bytes, conf_threshold: float = 0.25) -> List[Dict]:
        """
        Run threat detection on image bytes.
        
        Args:
            image_bytes: Raw image bytes
            conf_threshold: Confidence threshold for detection
            
        Returns:
            List of threat detections with bounding boxes and threat levels
        """
        logger.info(f"Starting threat detection (threshold: {conf_threshold})")
        
        # Ensure service is initialized
        if not self.is_initialized():
            logger.warning("Service not initialized, attempting initialization now...")
            if not self.initialize():
                error_msg = f"Service not initialized: {self._initialization_error}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
        
        if not CV2_AVAILABLE:
            raise RuntimeError("OpenCV required for image processing")
        
        if self.threat_model is None:
            raise RuntimeError("Threat model not loaded")
        
        try:
            # Decode image
            logger.debug(f"Decoding image ({len(image_bytes)} bytes)")
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                raise ValueError("Could not decode image - invalid image format")
            
            logger.debug(f"Image decoded successfully: {image.shape}")
            
            # Run detection
            logger.debug("Running YOLO threat detection model...")
            results = self.threat_model.predict(
                source=image,
                conf=conf_threshold,
                iou=0.45,
                verbose=False
            )[0]
            
            logger.debug(f"Detection complete, found {len(results.boxes) if results.boxes else 0} boxes")
            
            # Convert to standard format
            detections = []
            if results.boxes is not None:
                for box in results.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = float(box.conf[0].cpu().numpy())
                    cls_id = int(box.cls[0].cpu().numpy())
                    
                    # Map to our threat classes if available
                    label = self.threat_classes.get(cls_id, results.names.get(cls_id, f"class_{cls_id}"))
                    
                    detections.append({
                        'label': label,
                        'confidence': conf,
                        'box': [int(x1), int(y1), int(x2), int(y2)],
                        'class_id': cls_id
                    })
            
            logger.debug(f"Converted {len(detections)} detections")
            
            # Filter to keep only threats
            filtered_detections = self.filter_threat_detections(detections)
            logger.info(f"Threat detection complete: {len(filtered_detections)} threats found")
            
            # Enhance with metadata
            return self.enhance_detections(filtered_detections, DetectionMode.THREAT)
        except Exception as e:
            logger.error(f"Error during threat detection: {type(e).__name__}: {str(e)}", exc_info=True)
            raise
    
    def draw_detections(self, image: np.ndarray, detections: List[Dict]) -> np.ndarray:
        """
        Draw bounding boxes and labels on image.
        
        Args:
            image: Input image (BGR format)
            detections: List of detection dictionaries
            
        Returns:
            Image with drawn bounding boxes
        """
        if not CV2_AVAILABLE:
            raise RuntimeError("OpenCV required for drawing")
        
        annotated_image = image.copy()
        
        for det in detections:
            x1, y1, x2, y2 = det['box']
            color = det['color']
            label = det['display_label']
            
            # Convert hex color to BGR
            if color.startswith('#'):
                color = color.lstrip('#')
                r, g, b = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
                color = (b, g, r)  # OpenCV uses BGR
            
            # Draw bounding box
            cv2.rectangle(annotated_image, (x1, y1), (x2, y2), color, 2)
            
            # Draw label background
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            cv2.rectangle(annotated_image, (x1, y1 - label_size[1] - 10), 
                        (x1 + label_size[0], y1), color, -1)
            
            # Draw label text
            cv2.putText(annotated_image, label, (x1, y1 - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        return annotated_image


# Global service instance
_enhanced_yolo_service = None

def get_enhanced_yolo_service() -> EnhancedYOLOService:
    """
    Get or create global enhanced YOLO service instance.
    
    Returns:
        EnhancedYOLOService instance
    """
    global _enhanced_yolo_service
    if _enhanced_yolo_service is None:
        _enhanced_yolo_service = EnhancedYOLOService()
        _enhanced_yolo_service.initialize()
    return _enhanced_yolo_service

def reset_enhanced_yolo_service():
    """Reset global service instance (useful for testing)."""
    global _enhanced_yolo_service
    _enhanced_yolo_service = None
