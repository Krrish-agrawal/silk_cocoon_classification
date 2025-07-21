// Silk Production Calculator - Technical Analysis Only (No Pricing)

document.getElementById("valuationForm").addEventListener("submit", function (e) {
    e.preventDefault();
    
    // Get form values - simplified inputs
    const cocoonWeight = parseFloat(document.getElementById("cocoonWeightInput").value); // kg of cocoons
    const qualifiedPercentage = parseFloat(document.getElementById("qualifiedInput").value); // % qualified
    const output = document.getElementById("priceOutput");

    // Real data from Word document - DC% to Average Renditta mapping
    const rendittaData = {
        5: 6.25,
        5.5: 6.25833333,
        6: 6.3,
        6.5: 6.35,
        7: 6.35833333,
        7.5: 6.35,
        8: 6.44166667,
        8.5: 6.45,
        9: 6.49166667,
        9.5: 6.53333333,
        10: 6.55,
        10.5: 6.64166667,
        11: 6.625,
        11.5: 6.65,
        12: 6.675,
        12.5: 6.71666667,
        13: 6.75,
        13.5: 6.775,
        14: 6.81666667,
        14.5: 6.85,
        15: 6.85,
        15.5: 6.9,
        16: 6.94166667,
        16.5: 6.94166667,
        17: 6.98333333,
        17.5: 7.03333333,
        18: 7.05,
        18.5: 7.08333333,
        19: 7.13333333,
        19.5: 7.15,
        20: 7.175,
        20.5: 7.225,
        21: 7.25,
        21.5: 7.26666667,
        22: 7.31666667,
        22.5: 7.35,
        23: 7.35833333,
        23.5: 7.40833333,
        24: 7.45,
        24.5: 7.45,
        25: 7.5
    };

    // Input validation
    if (isNaN(cocoonWeight) || cocoonWeight <= 0) {
        output.innerHTML = `<div class="warning">Please enter a valid cocoon weight in kg.</div>`;
        output.style.display = "block";
        return;
    }

    if (isNaN(qualifiedPercentage) || qualifiedPercentage <= 0 || qualifiedPercentage > 100) {
        output.innerHTML = `<div class="warning">Please enter a valid qualified percentage (1-100).</div>`;
        output.style.display = "block";
        return;
    }

    // Calculate defect percentage
    const defectPercentage = 100 - qualifiedPercentage;
    
    // Grade assignment based on qualified percentage
    let grade;
    if (qualifiedPercentage >= 90) {
        grade = 'A';
    } else if (qualifiedPercentage >= 75) {
        grade = 'B';
    } else {
        grade = 'C';
    }

    // Find closest defect percentage in data and get renditta
    let closestDefectPercentage = 25; // default to highest
    let minDifference = Math.abs(defectPercentage - 25);
    
    // Find the closest match in our data
    for (let dc in rendittaData) {
        const difference = Math.abs(defectPercentage - parseFloat(dc));
        if (difference < minDifference) {
            minDifference = difference;
            closestDefectPercentage = parseFloat(dc);
        }
    }

    // Get renditta (silk yield percentage) from data
    const renditta = rendittaData[closestDefectPercentage];
    
    // Calculate silk production
    // Formula: Silk Production (kg) = Cocoon Weight (kg) / Renditta
    const silkProduced = cocoonWeight / renditta;

    // Calculate effective cocoon weight used (only qualified cocoons contribute)
    const effectiveCocoonWeight = cocoonWeight * (qualifiedPercentage / 100);
    const wasteCocoonWeight = cocoonWeight * (defectPercentage / 100);

    // Generate Renditta Reference Table first
    let rendittaTableHTML = `
        <div class="calculation-section" style="margin-bottom: 20px;">
            <strong>📊 Renditta Reference Table:</strong><br>
            <table style="width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 12px;">
                <tr style="background-color: #f1f2f6;">
                    <th style="padding: 6px; border: 1px solid #ddd;">Defect %</th>
                    <th style="padding: 6px; border: 1px solid #ddd;">Renditta</th>
                    <th style="padding: 6px; border: 1px solid #ddd;">Defect %</th>
                    <th style="padding: 6px; border: 1px solid #ddd;">Renditta</th>
                    <th style="padding: 6px; border: 1px solid #ddd;">Defect %</th>
                    <th style="padding: 6px; border: 1px solid #ddd;">Renditta</th>
                </tr>`;
    
    const rendittaEntries = Object.entries(rendittaData);
    const rowCount = Math.ceil(rendittaEntries.length / 3);
    
    for (let i = 0; i < rowCount; i++) {
        rendittaTableHTML += '<tr>';
        for (let j = 0; j < 3; j++) {
            const index = i + j * rowCount;
            if (index < rendittaEntries.length) {
                const [defect, renditta] = rendittaEntries[index];
                rendittaTableHTML += `
                    <td style="padding: 6px; border: 1px solid #ddd; text-align: center;">${defect}</td>
                    <td style="padding: 6px; border: 1px solid #ddd; text-align: center;">${parseFloat(renditta).toFixed(2)}</td>
                `;
            } else {
                rendittaTableHTML += `
                    <td style="padding: 6px; border: 1px solid #ddd;"></td>
                    <td style="padding: 6px; border: 1px solid #ddd;"></td>
                `;
            }
        }
        rendittaTableHTML += '</tr>';
    }
    rendittaTableHTML += '</table></div>';

    // Generate comprehensive output
    let resultHTML = rendittaTableHTML + `
        <div class="calculation-section">
            <strong>🎯 Your Input:</strong><br>
            Cocoon Weight Available: ${cocoonWeight} kg<br>
            Qualified Percentage: ${qualifiedPercentage}%<br>
            Defect Percentage: ${defectPercentage}%<br>
            Quality Grade: <strong>${grade}</strong>
        </div>
        
        <div class="calculation-section">
            <strong>📊 Cocoon Analysis:</strong><br>
            Effective Cocoon Weight (Qualified): ${effectiveCocoonWeight.toFixed(2)} kg<br>
            Waste Cocoon Weight (Defective): ${wasteCocoonWeight.toFixed(2)} kg<br>
            Closest Defect % in Data: ${closestDefectPercentage}%<br>
            Corresponding Renditta: ${renditta.toFixed(2)}
        </div>
        
        <div class="highlight">
            <strong>🚀 Silk Production Result:</strong><br>
            <strong>Total Silk Production: ${silkProduced.toFixed(2)} kg</strong><br>
            Using Renditta: ${renditta.toFixed(2)} (from real data)
        </div>`;

    // Quality insights
    if (qualifiedPercentage < 90) {
        const improvedRenditta = rendittaData[5]; // Best case scenario
        const improvedSilk = cocoonWeight / improvedRenditta;
        const additionalSilk = improvedSilk - silkProduced;
        
        resultHTML += `
            <div class="warning">
                <strong>💡 Quality Improvement Potential:</strong><br>
                If you improve to 95% qualified (5% defect):<br>
                • Renditta would be: ${improvedRenditta.toFixed(2)}<br>
                • Additional silk production: ${additionalSilk.toFixed(2)} kg<br>
                • Total potential production: ${improvedSilk.toFixed(2)} kg silk
            </div>`;
    }

    // Silk yield ratio (silk produced / cocoon input)
    const silkYieldRatio = (silkProduced / cocoonWeight) * 100;
    
    resultHTML += `
        <div class="calculation-section">
            <strong>📈 Production Metrics:</strong><br>
            Silk Yield Ratio: ${silkYieldRatio.toFixed(2)}% (silk output/cocoon input)<br>
            Grade Classification: ${grade} (${qualifiedPercentage >= 90 ? 'Premium' : qualifiedPercentage >= 75 ? 'Standard' : 'Economy'})<br>
            Data Accuracy: Using closest match (${closestDefectPercentage}% defect)
        </div>`;

    // Summary table
    resultHTML += `
        <div class="calculation-section" style="margin-top: 15px;">
            <strong>📋 Production Summary:</strong><br>
            <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
                <tr style="background-color: #f1f2f6;">
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Parameter</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Value</strong></td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">Input Cocoon Weight</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">${cocoonWeight} kg</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">Qualified %</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">${qualifiedPercentage}% (Grade ${grade})</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">Renditta (from data)</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">${renditta.toFixed(2)}</td>
                </tr>
                <tr style="background-color: #d5f4e6;">
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Silk Production</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>${silkProduced.toFixed(2)} kg</strong></td>
                </tr>

            </table>
        </div>`;

    // Display results
    output.innerHTML = resultHTML;
    output.style.display = "block";
});