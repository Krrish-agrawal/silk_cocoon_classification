from flask import Flask, request, send_file, jsonify, send_from_directory
from flask_cors import CORS
from ultralytics import YOLO
from torchvision import transforms
from PIL import Image
import torch, os, uuid, cv2, traceback, timm, numpy as np

# Upload folder
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize Flask app, serve static files from 'static/'
app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Serve the SPA entrypoint
@app.route('/')
def serve_frontend():
    return send_from_directory(app.static_folder, 'index.html')

# Serve other frontend assets (JS, CSS, images)
@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

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

# Preprocessing pipeline
preprocess = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225])
])

def process_image(image):
    if yolo is None:
        raise Exception("YOLO model not loaded")
    if clf is None:
        raise Exception("Classifier model not loaded")

    orig = np.array(image)
    bgr = cv2.cvtColor(orig, cv2.COLOR_RGB2BGR)
    results = yolo(bgr)[0]
    boxes = results.boxes.xyxy.cpu().int().tolist() if results.boxes is not None else []
    total = len(boxes)
    qualified = 0

    for i, (x1, y1, x2, y2) in enumerate(boxes):
        crop = bgr[y1:y2, x1:x2]
        if crop.size == 0:
            continue
        try:
            crop_pil = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
            inp = preprocess(crop_pil).unsqueeze(0).to(device)
            with torch.no_grad():
                logits = clf(inp)
            prob = torch.softmax(logits, dim=1)[0, 1].item()
            label = 1 if prob > 0.5 else 0
            qualified += label
            color = (0, 255, 0) if label else (0, 0, 255)
            text = f"{'OK' if label else 'Defect'} {prob:.2f}"
            cv2.rectangle(orig, (x1, y1), (x2, y2), color, 4)
            cv2.putText(orig, text, (x1, y1-5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        except Exception:
            continue

    defect = total - qualified
    qp = (qualified / total * 100) if total else 0.0
    dp = (defect / total * 100) if total else 0.0
    grade = "A" if qp >= 70 else "B" if qp >= 50 else "C"

    stats_dict = {
        "Total Detections": total,
        "Qualified Cocoon Count": qualified,
        "Defect Count": defect,
        "Qualified Cocoon %": round(qp, 2),
        "Defect %": round(dp, 2),
        "Sample Grade": grade
    }

    annotated = cv2.cvtColor(orig, cv2.COLOR_BGR2RGB)
    return Image.fromarray(annotated), stats_dict, None

@app.route('/classify', methods=['POST'])
def classify_cocoon():
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No image selected"}), 400

    filename = f"{uuid.uuid4().hex}.jpg"
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(path)

    try:
        image = Image.open(path).convert('RGB')
        annotated_img, stats, _ = process_image(image)
        result_fn = 'result_' + filename
        result_path = os.path.join(app.config['UPLOAD_FOLDER'], result_fn)
        annotated_img.save(result_path)
        return jsonify({
            "image_url": f"/uploads/{result_fn}",
            "stats": stats
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Processing failed: {str(e)}"}), 500

@app.route('/uploads/<filename>')
def send_uploaded_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
    resp = send_file(file_path, mimetype='image/jpeg')
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

@app.route('/ping')
def ping():
    return "Backend is alive!"

@app.route('/status')
def status():
    return jsonify({
        "yolo_loaded": yolo is not None,
        "classifier_loaded": clf is not None,
        "device": str(device)
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
