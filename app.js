// Handle tab switching
document.addEventListener("DOMContentLoaded", function () {
  const tabButtons = document.querySelectorAll(".tab-button");
  const tabContents = document.querySelectorAll(".tab-content");

  tabButtons.forEach((btn, idx) => {
    btn.addEventListener("click", () => {
      tabButtons.forEach(b => b.classList.remove("active"));
      tabContents.forEach(c => c.classList.remove("active"));

      btn.classList.add("active");
      tabContents[idx].classList.add("active");
    });
  });
});

// Handle cocoon image classification
async function runSegmentation() {
  const input = document.getElementById("uploadImage");
  const output = document.getElementById("outputImage");
  const details = document.getElementById("cocoonDetails");
  const loadingDiv = document.getElementById("loadingDiv");
  const errorDiv = document.getElementById("errorDiv");
  const classifyBtn = document.getElementById("classifyBtn");

  // Reset UI
  output.style.display = "none";
  details.innerHTML = "";
  loadingDiv.style.display = "none";
  errorDiv.style.display = "none";

  if (!input.files.length) {
    showError("Please upload a cocoon image first.");
    return;
  }

  // Show loading state
  loadingDiv.style.display = "block";
  classifyBtn.disabled = true;
  classifyBtn.textContent = "Processing...";

  try {
    const formData = new FormData();
    formData.append("image", input.files[0]);

    console.log("Sending request to Flask backend...");

    const response = await fetch("http://127.0.0.1:5000/classify", {
      method: "POST",
      body: formData
    });

    console.log("Response status:", response.status);

    if (!response.ok) {
      const errorText = await response.text();
      console.error("Server error:", errorText);
      throw new Error(`Server error (${response.status}): ${errorText}`);
    }

    const data = await response.json();
    console.log("Classification result:", data);

    // Build the full image URL
    const imageUrl = "http://127.0.0.1:5000" + data.image_url;
    console.log("Loading image from:", imageUrl);

    // Load and display the result image
    await loadImage(imageUrl);

    // Display the statistics
    displayResults(data.stats);

  } catch (error) {
    console.error("Classification Error:", error);
    showError("Classification failed: " + error.message);
  } finally {
    // Reset loading state
    loadingDiv.style.display = "none";
    classifyBtn.disabled = false;
    classifyBtn.textContent = "Run Classification";
  }
}

// Helper function to load image with promise
function loadImage(url) {
  return new Promise((resolve, reject) => {
    const output = document.getElementById("outputImage");

    output.onload = () => {
      output.style.display = "block";
      console.log("Image loaded successfully");
      resolve();
    };

    output.onerror = () => {
      console.error("Failed to load image:", url);
      reject(new Error("Failed to load result image"));
    };

    // Add timestamp to prevent caching issues
    output.src = url + "?t=" + Date.now();
  });
}

// Helper function to display results
function displayResults(stats) {
  const details = document.getElementById("cocoonDetails");

  details.innerHTML = `
    <pre style="font-family: monospace; background: #f9f9f9; padding: 10px; border: 1px solid #ccc; border-radius: 8px;">
======== Final Cocoon Quality Report ========
Total Detections       : ${stats["Total Detections"]}
Qualified Cocoon Count : ${stats["Qualified Cocoon Count"]}
Defect Count           : ${stats["Defect Count"]}
Qualified Cocoon %     : ${stats["Qualified Cocoon %"]}%
Defect %               : ${stats["Defect %"]}%
================================================
    </pre>
  `.trim();
}


// Helper function to show errors
function showError(message) {
  const errorDiv = document.getElementById("errorDiv");
  errorDiv.textContent = message;
  errorDiv.style.display = "block";
}
