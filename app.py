from flask import Flask, request, send_file, jsonify, send_from_directory
from flask_cors import CORS
from PIL import Image
import os, uuid, cv2, traceback, numpy as np
import requests

# Upload folder
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize Flask app, serve static files from 'static/'
app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


HF_API_TOKEN = os.environ.get("HF_API_TOKEN")  
SEGMENTATION_API_URL = "https://api-inference.huggingface.co/models/KrrishAgrawal/cocoon_segmentation_krrish"
CLASSIFICATION_API_URL = "https://api-inference.huggingface.co/models/KrrishAgrawal/cocoon_classification_krrish"

@app.route('/')
def serve_frontend():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

def call_huggingface_api(api_url, image_path, api_token=None):
    """
    Helper function to call Hugging Face Inference API
    """
    headers = {}
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"
    
    try:
        with open(image_path, "rb") as f:
            response = requests.post(api_url, headers=headers, data=f, timeout=30)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            raise Exception("Rate limit exceeded. Please try again later.")
        elif response.status_code == 503:
            raise Exception("Model is loading. Please wait and try again.")
        else:
            raise Exception(f"API error: {response.status_code} - {response.text}")
            
    except requests.exceptions.Timeout:
        raise Exception("Request timed out. Please try again.")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Request failed: {str(e)}")

def process_image_with_hf_api(image_path):
    """
    Process image using Hugging Face APIs for both segmentation and classification
    """
    print("Processing image with Hugging Face API...")
    
    # Call segmentation model (YOLO)
    print("Calling segmentation API...")
    seg_result = call_huggingface_api(SEGMENTATION_API_URL, image_path, HF_API_TOKEN)
    print(f"Segmentation result: {seg_result}")
    
    # For this example, we'll assume the segmentation API returns bounding boxes
    # You may need to adapt this based on your actual model's output format
    
    # Load original image for annotation
    image = Image.open(image_path).convert('RGB')
    orig = np.array(image)
    
    # Process segmentation results (adapt based on your model's output format)
    total = 0
    qualified = 0
    
    # This is a placeholder - you'll need to adapt based on your model's actual output
    if isinstance(seg_result, list) and len(seg_result) > 0:
        total = len(seg_result)
        
        for i, detection in enumerate(seg_result):
            # Extract bounding box coordinates (adapt based on your model's output)
            # This assumes your model returns something like:
            # [{"box": {"xmin": x1, "ymin": y1, "xmax": x2, "ymax": y2}, "label": "cocoon", "score": confidence}]
            
            if "box" in detection:
                box = detection["box"]
                x1, y1, x2, y2 = int(box["xmin"]), int(box["ymin"]), int(box["xmax"]), int(box["ymax"])
                
                # Crop the detected region for classification
                crop = orig[y1:y2, x1:x2]
                if crop.size == 0:
                    continue
                
                # Save crop temporarily for classification API call
                crop_path = f"temp_crop_{i}_{uuid.uuid4().hex}.jpg"
                crop_image = Image.fromarray(crop)
                crop_image.save(crop_path)
                
                try:
                    # Call classification API
                    print(f"Classifying crop {i+1}/{total}...")
                    clf_result = call_huggingface_api(CLASSIFICATION_API_URL, crop_path, HF_API_TOKEN)
                    print(f"Classification result for crop {i}: {clf_result}")
                    
                    # Process classification result (adapt based on your model's output)
                    # Assuming it returns something like: [{"label": "OK", "score": 0.95}, {"label": "Defect", "score": 0.05}]
                    if isinstance(clf_result, list) and len(clf_result) > 0:
                        best_prediction = max(clf_result, key=lambda x: x["score"])
                        label = 1 if best_prediction["label"].lower() in ["ok", "qualified", "good"] else 0
                        prob = best_prediction["score"]
                    else:
                        label = 0
                        prob = 0.5
                    
                    qualified += label
                    
                    # Draw bounding box and label on original image
                    color = (0, 255, 0) if label else (0, 0, 255)
                    text = f"{'OK' if label else 'Defect'} {prob:.2f}"
                    cv2.rectangle(orig, (x1, y1), (x2, y2), color, 4)
                    cv2.putText(orig, text, (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                    
                    print(f"Detection {i+1}: {'OK' if label else 'Defect'} (prob: {prob:.3f})")
                    
                finally:
                    # Clean up temporary crop file
                    if os.path.exists(crop_path):
                        os.remove(crop_path)
    
    # Calculate statistics
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
    
    # Convert annotated image back to PIL format
    annotated_img = cv2.cvtColor(orig, cv2.COLOR_BGR2RGB)
    return Image.fromarray(annotated_img), stats_dict

@app.route('/classify', methods=['POST'])
def classify_cocoon():
    print("\n" + "="*50)
    print("New classification request received")
    
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No image selected"}), 400

    filename = f"{uuid.uuid4().hex}.jpg"
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(path)
    print(f"✓ Image saved as: {filename}")

    try:
        print("Starting image processing with Hugging Face API...")
        annotated_img, stats = process_image_with_hf_api(path)
        
        # Save result
        result_fn = 'result_' + filename
        result_path = os.path.join(app.config['UPLOAD_FOLDER'], result_fn)
        annotated_img.save(result_path)
        print(f"✓ Result saved as: {result_fn}")
        
        # Print report in server logs
        print("\n======== Final Cocoon Quality Report ========")
        for key, value in stats.items():
            print(f"{key:<25}: {value}")
        print("=" * 46)
        
        return jsonify({
            "image_url": f"/uploads/{result_fn}",
            "stats": stats
        })
        
    except Exception as e:
        print(f"✗ Error during processing: {e}")
        print("Full traceback:")
        traceback.print_exc()
        
        # Clean up uploaded file on error
        try:
            if os.path.exists(path):
                os.remove(path)
        except:
            pass
            
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
        "huggingface_api_configured": HF_API_TOKEN is not None,
        "segmentation_model": SEGMENTATION_API_URL.split('/')[-1] if SEGMENTATION_API_URL else None,
        "classification_model": CLASSIFICATION_API_URL.split('/')[-1] if CLASSIFICATION_API_URL else None,
        "using_huggingface_api": True
    })

if __name__ == '__main__':
    print("Starting Flask application...")
    print(f"Upload folder: {os.path.abspath(UPLOAD_FOLDER)}")
    print("Using Hugging Face Inference API")
    print(f"HF API Token configured: {'✓' if HF_API_TOKEN else '✗'}")
    print(f"Segmentation API: {SEGMENTATION_API_URL}")
    print(f"Classification API: {CLASSIFICATION_API_URL}")
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
