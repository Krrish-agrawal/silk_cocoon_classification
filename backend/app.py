# Run with: python app.py
# Test frontend: python -m http.server 3000
# Install: pip install flask flask-cors ultralytics timm torch torchvision opencv-python pillow numpy

from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from ultralytics import YOLO
from torchvision import transforms
from PIL import Image
import torch, os, uuid, cv2
import timm
import numpy as np
import traceback

# Upload folder
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize Flask app
app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Load YOLO model for segmentation
print("Loading YOLO model...")
try:
    yolo = YOLO('best_s_300.pt')
    print("✓ YOLO model loaded successfully")
except Exception as e:
    print("✗ Failed to load YOLO model:", e)
    yolo = None

# Load EfficientNetB0 classification model
print("Loading EfficientNet classifier...")
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Using device: {device}")

try:
    clf = timm.create_model('efficientnet_b0', pretrained=False, num_classes=2)
    clf.load_state_dict(torch.load('best_classifier.pth', map_location=device))
    clf.to(device).eval()
    print("✓ EfficientNet classifier loaded successfully")
except Exception as e:
    print("✗ Failed to load EfficientNet classifier:", e)
    clf = None

# Image preprocessing pipeline - Updated to match your requirements
preprocess = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

# Process image: segmentation + classification - Updated with your logic
def process_image(image):
    if yolo is None:
        raise Exception("YOLO model not loaded")
    if clf is None:
        raise Exception("Classifier model not loaded")
    
    print("Processing image...")
    orig = np.array(image)
    # Fixed: Convert RGB to BGR for YOLO processing
    bgr = cv2.cvtColor(orig, cv2.COLOR_RGB2BGR)
    
    print("Running YOLO detection...")
    results = yolo(bgr)[0]
    
    if results.boxes is None:
        print("No objects detected")
        boxes = []
    else:
        boxes = results.boxes.xyxy.cpu().int().tolist()
    
    total = len(boxes)
    qualified = 0
    print(f"Found {total} detections")

    for i, (x1, y1, x2, y2) in enumerate(boxes):
        print(f"Processing detection {i+1}/{total}: ({x1}, {y1}, {x2}, {y2})")
        
        # Crop from BGR image for consistency
        crop = bgr[y1:y2, x1:x2]
        if crop.size == 0:
            print(f"  Skipping empty crop")
            continue
            
        try:
            # Convert BGR crop back to RGB for PIL processing
            crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            crop_pil = Image.fromarray(crop_rgb)
            
            # Apply preprocessing pipeline
            inp = preprocess(crop_pil).unsqueeze(0).to(device)
            
            with torch.no_grad():
                logits = clf(inp)
            
            prob = torch.softmax(logits, dim=1)[0, 1].item()
            label = 1 if prob > 0.5 else 0
            qualified += label
            
            print(f"  Classification: {'OK' if label == 1 else 'Defect'} (prob: {prob:.3f})")
            
            # Draw bounding box and label on original image
            color = (0, 255, 0) if label == 1 else (0, 0, 255)
            label_text = f"{'OK' if label == 1 else 'Defect'} {prob:.2f}"
            cv2.rectangle(orig, (x1, y1), (x2, y2), color, 4)
            cv2.putText(orig, label_text, (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        except Exception as e:
            print(f"  Error classifying crop {i+1}: {e}")

    defect = total - qualified
    qualified_percent = (qualified / total * 100) if total > 0 else 0.0
    defect_percent = (defect / total * 100) if total > 0 else 0.0

    # Determine grading based on qualified percentage
    def get_grade(qualified_pct):
        if qualified_pct >= 70.0:
            return "A"
        elif qualified_pct >= 50.0:
            return "B"
        else:
            return "C"
    
    grade = get_grade(qualified_percent)

    # Updated stats format to match your requirement
    stats_text = (
        "======== Final Cocoon Quality Report ========\n"
        f"Total Detections       : {total}\n"
        f"Qualified Cocoon Count : {qualified}\n"
        f"Defect Count           : {defect}\n"
        f"Qualified Cocoon %     : {qualified_percent:.2f}%\n"
        f"Defect %               : {defect_percent:.2f}%\n"
        f"Sample Grade           : {grade}"
    )

    # Also create a dictionary version for JSON response
    stats_dict = {
        "Total Detections": total,
        "Qualified Cocoon Count": qualified,
        "Defect Count": defect,
        "Qualified Cocoon %": round(qualified_percent, 2),
        "Defect %": round(defect_percent, 2),
        "Sample Grade": grade
    }

    # Convert back to RGB for PIL Image
    annotated_img = cv2.cvtColor(orig, cv2.COLOR_BGR2RGB)
    return Image.fromarray(annotated_img), stats_dict, stats_text

# API route: /classify
@app.route('/classify', methods=['POST'])
def classify_cocoon():
    print("\n" + "="*50)
    print("New classification request received")
    
    # Check if file is present
    if 'image' not in request.files:
        print("✗ No image file in request")
        return jsonify({"error": "No image file provided"}), 400
    
    file = request.files['image']
    if file.filename == '':
        print("✗ Empty filename")
        return jsonify({"error": "No image selected"}), 400

    # Save uploaded file
    filename = f"{uuid.uuid4().hex}.jpg"
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    try:
        file.save(image_path)
        print(f"✓ Image saved as: {filename}")
    except Exception as e:
        print(f"✗ Failed to save image: {e}")
        return jsonify({"error": f"Failed to save image: {str(e)}"}), 500

    try:
        # Load and process image
        print("Loading image...")
        image = Image.open(image_path).convert('RGB')
        print(f"Image size: {image.size}")
        
        print("Starting image processing...")
        annotated_image, stats_dict, stats_text = process_image(image)
        
        # Save result
        result_filename = 'result_' + filename
        result_path = os.path.join(app.config['UPLOAD_FOLDER'], result_filename)
        annotated_image.save(result_path)
        print(f"✓ Result saved as: {result_filename}")
        
        # Print report in server logs
        print("\n" + stats_text)
        print("=" * 46)
        
        return jsonify({
            "image_url": f"/uploads/{result_filename}",
            "stats": stats_dict,
            "report": stats_text
        })
        
    except Exception as e:
        print(f"✗ Error during processing: {e}")
        print("Full traceback:")
        traceback.print_exc()
        
        # Clean up uploaded file on error
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
        except:
            pass
            
        return jsonify({"error": f"Processing failed: {str(e)}"}), 500

# Static route to serve annotated images
@app.route('/uploads/<filename>')
def send_uploaded_file(filename):
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(file_path):
            print(f"✗ File not found: {filename}")
            return jsonify({"error": "File not found"}), 404
        
        print(f"✓ Serving file: {filename}")
        
        # Add CORS headers for images
        response = send_file(file_path, mimetype='image/jpeg')
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
    except Exception as e:
        print(f"✗ Error serving file {filename}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/ping')
def ping():
    return "Backend is alive!"

@app.route('/status')
def status():
    return jsonify({
        "yolo_loaded": yolo is not None,
        "classifier_loaded": clf is not None,
        "device": str(device),
        "upload_folder": UPLOAD_FOLDER
    })

if __name__ == '__main__':
    print("Starting Flask application...")
    print(f"Upload folder: {os.path.abspath(UPLOAD_FOLDER)}")
    print("Models status:")
    print(f"  YOLO: {'✓ Loaded' if yolo is not None else '✗ Not loaded'}")
    print(f"  Classifier: {'✓ Loaded' if clf is not None else '✗ Not loaded'}")
    print(f"  Device: {device}")
    print("\nStarting server on http://127.0.0.1:5000")
    print("Use /status endpoint to check model status")
    print("Use /ping endpoint to test connectivity")
    app.run(debug=True, host='127.0.0.1', port=5000)