try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    print("OpenCV not available, YOLOv3 detection will use fallback methods")
    OPENCV_AVAILABLE = False
    cv2 = None
    np = None

import base64
import io
from PIL import Image
import os
import requests
from typing import Dict, List, Tuple, Optional

class YOLOv3WildlifeDetector:
    """
    YOLOv3-based wildlife offence detector for identifying:
    - Weapons (guns, rifles, traps, snares)
    - Vehicles in restricted areas
    - Dead animals or carcasses
    - Injured wildlife
    - Deforestation activities
    """
    
    def __init__(self):
        self.net = None
        self.classes = []
        self.colors = []
        self.confidence_threshold = 0.5
        self.nms_threshold = 0.4
        self.input_size = (416, 416)
        
        # Wildlife offence related classes
        self.offence_classes = {
            'person': 0,
            'gun': 1,
            'rifle': 2,
            'knife': 3,
            'car': 4,
            'truck': 5,
            'motorcycle': 6,
            'bicycle': 7,
            'dog': 8,
            'cat': 9,
            'horse': 10,
            'cow': 11,
            'elephant': 12,
            'bear': 13,
            'bird': 14,
            'fish': 15,
            'boat': 16,
            'airplane': 17,
            'train': 18,
            'bus': 19
        }
        
        # Severity mapping for detected objects
        self.severity_mapping = {
            'gun': 'Critical',
            'rifle': 'Critical',
            'knife': 'Critical',
            'person': 'Medium',  # Person in restricted area
            'car': 'Medium',
            'truck': 'Medium',
            'motorcycle': 'Medium',
            'boat': 'Medium',
            'airplane': 'Medium',
            'train': 'Medium',
            'bus': 'Medium',
            'bicycle': 'Low',
            'dog': 'Low',
            'cat': 'Low',
            'horse': 'Low',
            'cow': 'Low',
            'elephant': 'Low',
            'bear': 'Low',
            'bird': 'Low',
            'fish': 'Low'
        }
        
        self.initialize_model()
    
    def initialize_model(self):
        """Initialize YOLOv3 model"""
        try:
            # Check if OpenCV is available
            if not OPENCV_AVAILABLE:
                print("OpenCV not available. Using fallback detection.")
                return
            
            # Try to load pre-trained YOLOv3 weights
            weights_path = "yolov3.weights"
            config_path = "yolov3.cfg"
            names_path = "coco.names"
            
            # Check if files exist, if not, download them
            if not os.path.exists(weights_path):
                print("YOLOv3 weights not found. Using fallback detection.")
                return
            
            if not os.path.exists(config_path):
                print("YOLOv3 config not found. Using fallback detection.")
                return
            
            if not os.path.exists(names_path):
                print("YOLOv3 names not found. Using fallback detection.")
                return
            
            # Load YOLOv3 network
            self.net = cv2.dnn.readNet(weights_path, config_path)
            
            # Load class names
            with open(names_path, 'r') as f:
                self.classes = [line.strip() for line in f.readlines()]
            
            # Generate colors for each class
            np.random.seed(42)
            self.colors = np.random.uniform(0, 255, size=(len(self.classes), 3))
            
            print("YOLOv3 model initialized successfully")
            
        except Exception as e:
            print(f"Failed to initialize YOLOv3 model: {e}")
            print("Falling back to rule-based detection")
    
    def download_yolo_files(self):
        """Download YOLOv3 files if not present"""
        try:
            # Download YOLOv3 config
            if not os.path.exists("yolov3.cfg"):
                config_url = "https://raw.githubusercontent.com/pjreddie/darknet/master/cfg/yolov3.cfg"
                response = requests.get(config_url)
                with open("yolov3.cfg", "wb") as f:
                    f.write(response.content)
            
            # Download COCO names
            if not os.path.exists("coco.names"):
                names_url = "https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names"
                response = requests.get(names_url)
                with open("coco.names", "wb") as f:
                    f.write(response.content)
            
            print("YOLOv3 files downloaded successfully")
            
        except Exception as e:
            print(f"Failed to download YOLOv3 files: {e}")
    
    def preprocess_image(self, image_data: str) -> Optional[np.ndarray]:
        """Preprocess image for YOLOv3 input"""
        try:
            # Handle base64 encoded image
            if image_data.startswith('data:') and ';base64,' in image_data:
                header, b64 = image_data.split(',', 1)
                image_bytes = base64.b64decode(b64)
            else:
                image_bytes = base64.b64decode(image_data)
            
            # Convert to PIL Image
            image = Image.open(io.BytesIO(image_bytes))
            
            # Convert to OpenCV format
            image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            return image_cv
            
        except Exception as e:
            print(f"Error preprocessing image: {e}")
            return None
    
    def detect_objects(self, image) -> List[Dict]:
        """Detect objects in image using YOLOv3"""
        if not OPENCV_AVAILABLE or self.net is None:
            return self.fallback_detection(image)
        
        try:
            # Create blob from image
            blob = cv2.dnn.blobFromImage(
                image, 1/255.0, self.input_size, swapRB=True, crop=False
            )
            
            # Set input to network
            self.net.setInput(blob)
            
            # Get output layer names
            layer_names = self.net.getLayerNames()
            output_layers = [layer_names[i[0] - 1] for i in self.net.getUnconnectedOutLayers()]
            
            # Forward pass
            outputs = self.net.forward(output_layers)
            
            # Process detections
            detections = self.process_detections(outputs, image.shape)
            
            return detections
            
        except Exception as e:
            print(f"YOLOv3 detection error: {e}")
            return self.fallback_detection(image)
    
    def process_detections(self, outputs: List, image_shape: Tuple) -> List[Dict]:
        """Process YOLOv3 outputs to extract detections"""
        height, width = image_shape[:2]
        boxes = []
        confidences = []
        class_ids = []
        
        for output in outputs:
            for detection in output:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                
                if confidence > self.confidence_threshold:
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)
                    
                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)
                    
                    boxes.append([x, y, w, h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)
        
        # Apply non-maximum suppression
        indices = cv2.dnn.NMSBoxes(boxes, confidences, self.confidence_threshold, self.nms_threshold)
        
        detections = []
        if len(indices) > 0:
            for i in indices.flatten():
                x, y, w, h = boxes[i]
                class_id = class_ids[i]
                confidence = confidences[i]
                
                detection = {
                    'class_id': class_id,
                    'class_name': self.classes[class_id] if class_id < len(self.classes) else 'unknown',
                    'confidence': confidence,
                    'bbox': [x, y, w, h],
                    'center': [x + w//2, y + h//2]
                }
                detections.append(detection)
        
        return detections
    
    def fallback_detection(self, image) -> List[Dict]:
        """Fallback detection using OpenCV and rule-based analysis"""
        detections = []
        
        try:
            if not OPENCV_AVAILABLE:
                # Simple fallback when OpenCV is not available
                return [{
                    'class_id': -1,
                    'class_name': 'image_analyzed',
                    'confidence': 0.2,
                    'bbox': [0, 0, 100, 100],
                    'center': [50, 50]
                }]
            
            # Convert to grayscale for analysis
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Edge detection
            edges = cv2.Canny(gray, 50, 150)
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Analyze contours for potential objects
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 1000:  # Minimum area threshold
                    x, y, w, h = cv2.boundingRect(contour)
                    
                    # Simple shape analysis
                    aspect_ratio = w / h
                    if 0.5 < aspect_ratio < 2.0:  # Roughly square or rectangular
                        detection = {
                            'class_id': -1,
                            'class_name': 'potential_object',
                            'confidence': 0.3,
                            'bbox': [x, y, w, h],
                            'center': [x + w//2, y + h//2]
                        }
                        detections.append(detection)
            
        except Exception as e:
            print(f"Fallback detection error: {e}")
        
        return detections
    
    def analyze_wildlife_offence(self, image_data: str, description: str = "") -> Dict:
        """Analyze image for wildlife offences using YOLOv3"""
        try:
            # Preprocess image
            image = self.preprocess_image(image_data)
            if image is None:
                return self.get_fallback_analysis(description)
            
            # Detect objects
            detections = self.detect_objects(image)
            
            # Analyze detections for offences
            offence_analysis = self.analyze_detections(detections, description)
            
            return offence_analysis
            
        except Exception as e:
            print(f"Wildlife offence analysis error: {e}")
            return self.get_fallback_analysis(description)
    
    def analyze_detections(self, detections: List[Dict], description: str = "") -> Dict:
        """Analyze detections for wildlife offences"""
        offence_detected = False
        offence_type = "unknown"
        severity = "Low"
        confidence = 0.0
        detected_objects = []
        analysis_description = ""
        
        if not detections:
            return {
                "offence_detected": False,
                "offence_type": "unknown",
                "severity": "Low",
                "confidence": 0.0,
                "detected_objects": [],
                "description": "No objects detected in the image"
            }
        
        # Analyze each detection
        for detection in detections:
            class_name = detection['class_name'].lower()
            confidence = detection['confidence']
            detected_objects.append(class_name)
            
            # Check for high-severity objects
            if class_name in ['gun', 'rifle', 'knife']:
                offence_detected = True
                offence_type = "weapon_detected"
                severity = "Critical"
                analysis_description += f"CRITICAL: {class_name} detected with {confidence:.2f} confidence. "
            
            # Check for vehicles in restricted areas
            elif class_name in ['car', 'truck', 'motorcycle', 'boat']:
                offence_detected = True
                offence_type = "vehicle_in_restricted_area"
                severity = "Medium"
                analysis_description += f"Vehicle detected: {class_name} with {confidence:.2f} confidence. "
            
            # Check for wildlife
            elif class_name in ['dog', 'cat', 'horse', 'cow', 'elephant', 'bear', 'bird', 'fish']:
                offence_detected = True
                offence_type = "wildlife_present"
                severity = "Low"
                analysis_description += f"Wildlife detected: {class_name} with {confidence:.2f} confidence. "
        
        # Analyze description for additional context
        if description:
            description_lower = description.lower()
            if any(word in description_lower for word in ['gun', 'weapon', 'shoot', 'kill', 'dead', 'carcass']):
                offence_detected = True
                offence_type = "text_analysis_offence"
                severity = "Critical"
                analysis_description += "Critical keywords found in description. "
            elif any(word in description_lower for word in ['trap', 'snare', 'vehicle', 'cutting', 'tree']):
                offence_detected = True
                offence_type = "text_analysis_offence"
                severity = "Medium"
                analysis_description += "Suspicious keywords found in description. "
        
        # Determine overall confidence
        if detections:
            confidence = max([d['confidence'] for d in detections])
            
        # If no specific recognized offence is picked up but an offence was reported
        if not offence_detected and confidence == 0.0:
            offence_detected = True
            offence_type = "reported_offence"
            severity = "Medium"
            analysis_description = "Reported offence under investigation. "
            
        # Adjust Severity based on overall confidence of detections
        if confidence >= 0.8:
            severity = "Critical"
        elif confidence >= 0.5:
            severity = "Medium"
        elif confidence > 0:
            severity = "Low"
            
        return {
            "offence_detected": offence_detected,
            "offence_type": offence_type,
            "severity": severity,
            "confidence": confidence,
            "detected_objects": detected_objects,
            "description": analysis_description or "Reported offence under investigation"
        }
    
    def get_fallback_analysis(self, description: str = "") -> Dict:
        """Fallback analysis when YOLOv3 is not available"""
        offence_detected = False
        offence_type = "unknown"
        severity = "Low"
        confidence = 0.0
        detected_objects = []
        analysis_description = "AI analysis unavailable - using text analysis only"
        
        if description:
            description_lower = description.lower()
            
            # Check for critical keywords
            critical_keywords = ['gun', 'weapon', 'shoot', 'kill', 'dead', 'carcass', 'blood']
            if any(word in description_lower for word in critical_keywords):
                offence_detected = True
                offence_type = "text_analysis_offence"
                severity = "Critical"
                confidence = 0.7
                analysis_description = "Critical keywords detected in description"
            
            # Check for medium severity keywords
            elif any(word in description_lower for word in ['trap', 'snare', 'vehicle', 'cutting', 'tree']):
                offence_detected = True
                offence_type = "text_analysis_offence"
                severity = "Medium"
                confidence = 0.5
                analysis_description = "Suspicious keywords detected in description"
            
            # Check for low severity keywords
            elif any(word in description_lower for word in ['animal', 'wildlife', 'forest', 'park']):
                offence_detected = True
                offence_type = "text_analysis_offence"
                severity = "Low"
                confidence = 0.3
                analysis_description = "Wildlife-related keywords detected in description"
        
        return {
            "offence_detected": offence_detected,
            "offence_type": offence_type,
            "severity": severity,
            "confidence": confidence,
            "detected_objects": detected_objects,
            "description": analysis_description
        }

# Global detector instance
yolo_detector = YOLOv3WildlifeDetector()
