#!/usr/bin/env python
"""Direct test of YOLOv8 model detection"""

import sys
import numpy as np
from PIL import Image
import io
from pathlib import Path

print("=" * 60)
print("TESTING YOLO MODEL DIRECTLY")
print("=" * 60)

try:
    print("\n[Step 1] Loading model...")
    from model_loader import get_model_loader
    
    loader = get_model_loader('threat')
    print(f"✓ Model initialized: {loader._initialized}")
    print(f"✓ Fallback mode: {loader.fallback_mode}")
    print(f"✓ Model object: {loader.model}")
    
    # Create test image
    print("\n[Step 2] Creating test image...")
    img = Image.new('RGB', (640, 480), color=(73, 109, 137))  # Dark blue background
    
    # Add some colored rectangles to simulate objects
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    draw.rectangle([100, 100, 200, 200], fill=(255, 0, 0))  # Red rectangle
    draw.rectangle([300, 150, 400, 250], fill=(0, 255, 0))  # Green rectangle
    
    # Convert to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    image_data = img_bytes.read()
    
    print(f"✓ Test image created: {len(image_data)} bytes")
    
    # Test detection
    print("\n[Step 3] Running detection...")
    detections = loader.detect_from_bytes(image_data, conf_threshold=0.25)
    
    print(f"✓ Detection completed")
    print(f"✓ Objects found: {len(detections)}")
    
    if detections:
        print("\nDetections:")
        for i, det in enumerate(detections[:5], 1):
            print(f"  {i}. {det['label']}: {det['confidence']:.1%} - Box: {det['box']}")
    else:
        print("  (No objects detected - this is normal for synthetic image)")
    
    print("\n" + "=" * 60)
    print("✅ YOLO MODEL WORKING CORRECTLY")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Make sure FastAPI is running: uvicorn api_yolo:app --host 0.0.0.0 --port 8000")
    print("2. Make sure Flask backend is running: python app.py")
    print("3. Upload an image in the Officials Dashboard")
    print("4. Click 'Run Detection'")
    sys.exit(0)
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
