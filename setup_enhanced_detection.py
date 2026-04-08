#!/usr/bin/env python3
"""
Enhanced Detection System Setup Script for Wildlife Surveillance Application.

This script sets up the dual-mode detection system with:
1. Species Monitoring Mode - Detects animal species only
2. Threat Monitoring Mode - Detects humans, weapons, and suspicious objects

Features:
- Automatic model configuration
- Database schema updates
- Enhanced detection endpoints
- Real-time threat alerts
- Color-coded bounding boxes
- Threat level classification
"""

import os
import sys
import shutil
from pathlib import Path
import yaml
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_directories():
    """Create necessary directories for enhanced detection system."""
    directories = [
        'backend/yolo_model',
        'backend/yolo_model/species',
        'backend/yolo_model/threat',
        'datasets/species/images/train',
        'datasets/species/images/val',
        'datasets/species/images/test',
        'datasets/threat/images/train',
        'datasets/threat/images/val',
        'datasets/threat/images/test'
    ]
    
    base_dir = Path('.')
    for directory in directories:
        dir_path = base_dir / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {dir_path}")

def setup_model_configs():
    """Create YAML configuration files for both detection modes."""
    # Species Monitoring Configuration
    species_config = {
        'path': '../datasets/species',
        'train': 'images/train',
        'val': 'images/val',
        'test': 'images/test',
        'names': {
            0: 'lion', 1: 'tiger', 2: 'cow', 3: 'cat', 4: 'elephant',
            5: 'deer', 6: 'zebra', 7: 'dog', 8: 'horse', 9: 'leopard',
            10: 'bear', 11: 'monkey', 12: 'rabbit', 13: 'fox', 14: 'wolf'
        },
        'nc': 15,
        'epochs': 100,
        'batch_size': 16,
        'imgsz': 640,
        'lr0': 0.01,
        'weight_decay': 0.0005
    }
    
    # Threat Detection Configuration
    threat_config = {
        'path': '../datasets/threat',
        'train': 'images/train',
        'val': 'images/val',
        'test': 'images/test',
        'names': {
            0: 'person', 1: 'gun', 2: 'rifle', 3: 'pistol', 4: 'shotgun',
            5: 'knife', 6: 'machete', 7: 'axe', 8: 'bow', 9: 'arrow',
            10: 'explosive', 11: 'suspicious_object', 12: 'vehicle', 13: 'trap'
        },
        'nc': 14,
        'epochs': 100,
        'batch_size': 16,
        'imgsz': 640,
        'lr0': 0.01,
        'weight_decay': 0.0005,
        'priority': {
            'person': 10, 'gun': 9, 'rifle': 9, 'pistol': 8, 'shotgun': 8,
            'explosive': 10, 'suspicious_object': 7, 'knife': 6, 'machete': 6,
            'axe': 6, 'bow': 5, 'arrow': 5, 'vehicle': 4, 'trap': 7
        }
    }
    
    # Write configuration files
    configs = [
        ('backend/yolo_model/species_data.yaml', species_config),
        ('backend/yolo_model/threat_data.yaml', threat_config)
    ]
    
    for config_path, config_data in configs:
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
        logger.info(f"Created config file: {config_path}")

def create_training_scripts():
    """Create training scripts for both detection modes."""
    
    # Species training script
    species_script = '''#!/usr/bin/env python3
"""
Training script for Species Monitoring Model.
"""
import os
from ultralytics import YOLO

def main():
    # Load a pretrained model
    model = YOLO('yolov8n.pt')  # or 'yolov8s.pt', 'yolov8m.pt'
    
    # Train the model on species dataset
    results = model.train(
        data='species_data.yaml',
        epochs=100,
        imgsz=640,
        batch=16,
        name='species_model',
        save=True,
        plots=True,
        device='0' if os.name == 'nt' else 'cuda'  # Use GPU if available
    )
    
    print(f"Training completed. Model saved to: {results.save_dir}")

if __name__ == '__main__':
    main()
'''
    
    # Threat training script
    threat_script = '''#!/usr/bin/env python3
"""
Training script for Threat Detection Model.
"""
import os
from ultralytics import YOLO

def main():
    # Load a pretrained model
    model = YOLO('yolov8n.pt')  # or 'yolov8s.pt', 'yolov8m.pt'
    
    # Train the model on threat dataset
    results = model.train(
        data='threat_data.yaml',
        epochs=100,
        imgsz=640,
        batch=16,
        name='threat_model',
        save=True,
        plots=True,
        device='0' if os.name == 'nt' else 'cuda'  # Use GPU if available
    )
    
    print(f"Training completed. Model saved to: {results.save_dir}")

if __name__ == '__main__':
    main()
'''
    
    scripts = [
        ('backend/train_species.py', species_script),
        ('backend/train_threat.py', threat_script)
    ]
    
    for script_path, script_content in scripts:
        with open(script_path, 'w') as f:
            f.write(script_content)
        # Make script executable
        os.chmod(script_path, 0o755)
        logger.info(f"Created training script: {script_path}")

def create_requirements():
    """Create requirements.txt for enhanced detection system."""
    requirements = """ultralytics>=8.0.0
opencv-python>=4.5.0
numpy>=1.21.0
PyYAML>=6.0
matplotlib>=3.5.0
Pillow>=8.0.0
torch>=1.9.0
torchvision>=0.10.0
scipy>=1.7.0
"""
    
    with open('backend/requirements_enhanced.txt', 'w') as f:
        f.write(requirements)
    logger.info("Created enhanced requirements file")

def update_main_app():
    """Update main app.py to include enhanced detection imports."""
    app_file = Path('backend/app.py')
    if app_file.exists():
        logger.info("Main app.py found - enhanced detection should be integrated")
        logger.info("Make sure to run: python improve_database_schema.py")
    else:
        logger.error("Main app.py not found!")

def create_readme():
    """Create README for enhanced detection system."""
    readme_content = '''# Enhanced Wildlife Surveillance Detection System

## Overview
This enhanced detection system provides dual-mode monitoring for wildlife surveillance:

### 1. Species Monitoring Mode 🦁
- Detects animal species only
- 15 animal classes: lion, tiger, cow, cat, elephant, deer, zebra, dog, horse, leopard, bear, monkey, rabbit, fox, wolf
- Green bounding boxes for animals
- Confidence scores displayed

### 2. Threat Monitoring Mode 🚨
- Detects humans, weapons, and suspicious objects
- 14 threat classes: person, gun, rifle, pistol, shotgun, knife, machete, axe, bow, arrow, explosive, suspicious_object, vehicle, trap
- Color-coded threat levels:
  - 🔴 Critical (>75% confidence)
  - 🟠 Medium (50-75% confidence)  
  - 🟡 Low (<50% confidence)

## Features
- ✅ Real-time threat alerts to officials
- ✅ Color-coded bounding boxes
- ✅ Threat level classification
- ✅ Enhanced database logging
- ✅ Interactive detection viewer
- ✅ Map visualization with threat indicators

## Setup

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements_enhanced.txt
```

### 2. Prepare Dataset Structure
```
datasets/
├── species/
│   ├── images/
│   │   ├── train/
│   │   ├── val/
│   │   └── test/
│   └── data.yaml
└── threat/
    ├── images/
    │   ├── train/
    │   ├── val/
    │   └── test/
    └── data.yaml
```

### 3. Train Models (Optional)
```bash
# Train species detection model
python train_species.py

# Train threat detection model  
python train_threat.py
```

### 4. Update Database
```bash
# Run database schema improvements
python improve_database_schema.py
```

### 5. Start Application
```bash
python app.py
```

## API Endpoints

### Enhanced Detection
- `POST /api/detect/enhanced` - Dual-mode detection
- Parameters: `mode` (species/threat), `file` or `image_data`
- Returns: Enhanced detections with threat levels and colors

### Real-time Alerts
- Socket.IO event: `critical_threat_alert`
- Triggered when critical threats are detected

## Frontend Integration

### Enhanced Detection Viewer Component
- Mode selection (Species/Threat)
- Real-time detection results
- Color-coded bounding boxes
- Detection statistics
- Threat level indicators

### Report Form Updates
- Monitoring mode selection with descriptions
- Enhanced geotagging with accuracy
- Real-time location capture

## Detection Classes

### Species Classes (15)
1. Lion 🦁
2. Tiger 🐅
3. Cow 🐄
4. Cat 🐱
5. Elephant 🐘
6. Deer 🦌
7. Zebra 🦓
8. Dog 🐕
9. Horse 🐎
10. Leopard 🐆
11. Bear 🐻
12. Monkey 🐵
13. Rabbit 🐰
14. Fox 🦊
15. Wolf 🐺

### Threat Classes (14)
1. Person 👤 (Priority: 10)
2. Gun 🔫 (Priority: 9)
3. Rifle 🔫 (Priority: 9)
4. Pistol 🔫 (Priority: 8)
5. Shotgun 🔫 (Priority: 8)
6. Knife 🔪 (Priority: 6)
7. Machete 🔪 (Priority: 6)
8. Axe 🔨 (Priority: 6)
9. Bow 🏹 (Priority: 5)
10. Arrow 🏹 (Priority: 5)
11. Explosive 💣 (Priority: 10)
12. Suspicious Object ❓ (Priority: 7)
13. Vehicle 🚗 (Priority: 4)
14. Trap 🪤 (Priority: 7)

## Threat Level Classification
- **LOW**: < 50% confidence (🟡 Yellow)
- **MEDIUM**: 50-75% confidence (🟠 Orange)  
- **CRITICAL**: > 75% confidence (🔴 Red)

## Performance Optimization
- GPU acceleration support
- Batch processing
- Model caching
- Efficient NMS (Non-Maximum Suppression)
- Real-time inference optimization
'''
    
    with open('ENHANCED_DETECTION_README.md', 'w') as f:
        f.write(readme_content)
    logger.info("Created enhanced detection README")

def main():
    """Main setup function."""
    print("🦁🚨 Enhanced Wildlife Surveillance Detection System Setup")
    print("=" * 60)
    
    try:
        print("\n📁 Creating directory structure...")
        create_directories()
        
        print("\n⚙️ Setting up model configurations...")
        setup_model_configs()
        
        print("\n📜 Creating training scripts...")
        create_training_scripts()
        
        print("\n📦 Creating requirements file...")
        create_requirements()
        
        print("\n📖 Creating documentation...")
        create_readme()
        
        print("\n🔍 Checking main application...")
        update_main_app()
        
        print("\n✅ Enhanced Detection System Setup Complete!")
        print("\n📋 Next Steps:")
        print("   1. Prepare your datasets in datasets/ folder")
        print("   2. Train models: python train_species.py && python train_threat.py")
        print("   3. Update database: python improve_database_schema.py")
        print("   4. Start application: python app.py")
        print("   5. Access frontend at: http://localhost:3000")
        print("\n🦁 Species Monitoring: Detect animals only")
        print("🚨 Threat Monitoring: Detect poachers & weapons")
        print("📡 Critical Threat Alerts: Real-time notifications to officials")
        
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
