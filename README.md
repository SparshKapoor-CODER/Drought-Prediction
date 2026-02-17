# Drought-Driven Forest Loss Risk Prediction

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Earth Engine](https://img.shields.io/badge/Earth%20Engine-API-green)](https://earthengine.google.com/)
[![PyTorch](https://img.shields.io/badge/PyTorch-1.9+-red)](https://pytorch.org/)

This repository contains the complete code and methodology for predicting **forest loss risk** based on drought conditions, using satellite data and machine learning. The project integrates Google Earth Engine for data extraction, PyTorch for model training, and geospatial tools for producing a final risk map.

**Key outcomes:**
- A labelled dataset linking drought indicators (rainfall anomalies, SPI) to subsequent forest loss.
- A neural network classifier trained to estimate the probability of forest loss.
- A spatially explicit risk map for India (2021–2023 features → predicted loss after 2023), visualised in Earth Engine.

---

## Table of Contents
- [Problem Statement](#problem-statement)
- [Data Sources](#data-sources)
- [Methodology](#methodology)
  - [1. Feature Extraction in Earth Engine](#1-feature-extraction-in-earth-engine)
  - [2. Machine Learning in PyTorch](#2-machine-learning-in-pytorch)
  - [3. Generating the Risk Map](#3-generating-the-risk-map)
- [Repository Structure](#repository-structure)
- [Requirements](#requirements)
- [Reproduction Instructions](#reproduction-instructions)
  - [Earth Engine Setup](#earth-engine-setup)
  - [Python Environment](#python-environment)
  - [Step-by-Step Workflow](#step-by-step-workflow)
- [Results](#results)
- [Remaining Tasks](#remaining-tasks)
- [License](#license)
- [Contact](#contact)

---

## Problem Statement

Traditional forest monitoring detects loss only after it occurs. This project shifts from **detection to prediction** by analysing historical rainfall patterns (drought indicators) and using them to estimate the future risk of forest degradation. Such early warnings can support proactive environmental management and climate-risk analysis.

---

## Data Sources

All data are publicly available and processed in Google Earth Engine.

| Dataset | Source | Used For |
|---------|--------|----------|
| **Global Forest Change v1.12** | [Hansen / UMD](https://earthenginepartners.appspot.com/science-2013-global-forest) | Tree cover (2000), loss year (2001–2023), gain |
| **CHIRPS Daily Rainfall** | [UCSB / CHG](https://www.chc.ucsb.edu/data/chirps) | Precipitation totals, anomalies, SPI |
| **LSIB Country Boundaries** | [USDOS](https://data.usgs.gov/datacatalog/data/LSIB_SIMPLE) | India boundary for masking |

---

## Methodology

### 1. Feature Extraction in Earth Engine

We define five-year periods (2001–2005, 2006–2010, …, 2016–2020) and for each period (except the last) compute:

- **`rainfall_total`** – total precipitation (CHIRPS sum)
- **`rainfall_anomaly`** – difference from the long-term mean of 5-year totals
- **`spi`** – standardised precipitation index approximated as z-score
- **`treecover2000`** – static tree cover percentage (Hansen)
- **`past_loss`** – binary indicator of any loss before the start of the period

The **label** is whether forest loss occurred in the **next** 5-year period (derived from Hansen `lossyear`).  
Pixels with <25% tree cover in 2000 are masked out.

For each feature–label pair (four in total), 5000 points are sampled and exported as CSV to Google Drive.

### 2. Machine Learning in PyTorch

The four CSV files are combined and cleaned. A simple feedforward neural network with two hidden layers (64, 32 neurons) and dropout is trained to predict the binary loss label.

- **Train / test split**: temporal – train on the first three periods, test on the last (2016–2020 → 2021–2023).
- **Class imbalance** handled via weighted loss (`nn.CrossEntropyLoss` with class weights).
- **Early stopping** (patience=10) prevents overfitting.
- The final model is saved as `forest_loss_nn.pth` and the fitted scaler as `scaler.pkl`.

### 3. Generating the Risk Map

The same features are created in Earth Engine for the **2021–2023 period**. The 5-band image is exported as a GeoTIFF (`features_2021_2023.tif`).  
A Python script loads this raster, applies the saved scaler and model, and produces a continuous probability map (`forest_loss_risk_2021_2023.tif`). The map is then uploaded back to Earth Engine for interactive visualisation.

---

## Repository Structure

```
.
├── gee_scripts/
│   ├── Forest_cover_6.js              # Initial visualisation of forest loss periods
│   ├── Rainfall1.js                   # Rainfall data exploration
│   ├── export_training_data.js        # Creates training CSVs for all periods
│   ├── export_features_2021_2023.js   # Exports feature image for prediction
│   └── display_risk_map.js            # Visualises final risk map in Earth Engine
├── python/
│   ├── Data_Exploration.ipynb         # Jupyter notebook: combine CSVs, EDA
│   ├── train_model.py                 # PyTorch training script
│   ├── predict_risk_map.py            # Applies model to GeoTIFF, saves probability map
│   └── requirements.txt               # Python dependencies
├── data/                              # Folder for downloaded CSVs / GeoTIFFs (not tracked)
├── outputs/                           # Final risk map and results
├── README.md
└── LICENSE
```

*Note: Adjust file names according to your actual files.*

---

## Requirements

- **Earth Engine** – a registered account ([sign up](https://earthengine.google.com/))
- **Python 3.8+** with the following packages:
  - `pandas`, `numpy`, `matplotlib`, `seaborn`
  - `torch` (PyTorch)
  - `rasterio`, `joblib`, `scikit-learn`
  - `geopandas` (optional, for shapefile handling)

### Install Python Dependencies

```bash
pip install -r python/requirements.txt
```

---

## Reproduction Instructions

### Earth Engine Setup

1. Open the [Earth Engine Code Editor](https://code.earthengine.google.com/).
2. Copy the scripts from the `gee_scripts/` folder into new scripts and run them **in order**:
   - **`export_training_data.js`** – creates four CSV files in your Google Drive (`GEE_training_data/` folder).
   - **`export_features_2021_2023.js`** – exports the feature GeoTIFF for the most recent period.
3. Download the CSVs and the GeoTIFF to your local `data/` folder.

### Python Environment

1. Clone this repository.
2. Install dependencies (see [Requirements](#requirements) above).
3. Place the downloaded CSVs in `data/` and the GeoTIFF as `data/features_2021_2023.tif`.

### Step-by-Step Workflow

#### a) Prepare Training Data

Run the notebook `Data_Exploration.ipynb` (or a separate script) to:

- Combine the four CSV files.
- Drop unnecessary columns (`.geo`, `system:index`).
- Save the cleaned dataset as `data/forest_loss_training_data_clean.csv`.

```bash
jupyter notebook python/Data_Exploration.ipynb
```

#### b) Train the Model

Execute `train_model.py` (or the notebook cells) to:

- Load the cleaned CSV.
- Perform temporal train/test split.
- Train the neural network with early stopping.
- Save `forest_loss_nn.pth` and `scaler.pkl`.

```bash
python python/train_model.py
```

#### c) Generate the Risk Map

Run `predict_risk_map.py`:

- Load the feature GeoTIFF, scaler, and model.
- Predict probabilities for every pixel.
- Save the result as `data/forest_loss_risk_2021_2023.tif`.

```bash
python python/predict_risk_map.py
```

#### d) Visualise in Earth Engine

1. Upload the probability GeoTIFF to your Earth Engine assets:
   - Click **Assets** → **NEW** → **Image upload**
   - Select `data/forest_loss_risk_2021_2023.tif`
   - Name it (e.g., `forest_loss_risk_2021_2023`)

2. Create a new Earth Engine script using the code below and run it:

```javascript
var risk = ee.Image('users/your-username/forest_loss_risk_2021_2023');
var india = ee.FeatureCollection('USDOS/LSIB_SIMPLE/2017')
              .filter(ee.Filter.eq('country_na', 'India'));

Map.centerObject(india, 5);
Map.addLayer(risk.clip(india), {min:0, max:1, palette:['darkgreen','yellow','red']}, 'Risk');
Map.addLayer(ee.Image().paint(india,0,1), {palette:'black'}, 'Boundary');
```

---

## Results

The final risk map for India (2021–2023 features → predicted loss after 2023) is visualised in Earth Engine using the script above.

**Expected output:**
- A continuous probability map where:
  - **Dark green** = low risk
  - **Yellow** = moderate risk
  - **Red** = high risk

*[Add a screenshot from Earth Engine here]*

### Validation

When the next Hansen Global Forest Change update is released, the actual loss for 2024+ can be compared with the risk probabilities to compute metrics such as:
- AUC (Area Under the ROC Curve)
- Precision and Recall
- F1-Score

---

## Remaining Tasks

### Before Publishing to GitHub:

1. **Adjust file paths and names** if your actual scripts differ from the defaults.
2. **Create the `requirements.txt`** file with all Python packages (see example below).
3. **Create the `LICENSE`** file (choose MIT, Apache, GPL, etc.).
4. **Add a screenshot** of your final risk map from Earth Engine (highly recommended).
5. **Update the `[Your Name]` and contact details** in the Contact section.
6. **Ensure all GEE scripts are properly commented** with usage instructions.
7. **Test the entire workflow** from start to finish to confirm reproducibility.
8. **Push everything** to a new GitHub repository.

### Example `requirements.txt`

```
pandas==1.5.3
numpy==1.24.3
matplotlib==3.7.1
seaborn==0.12.2
torch==1.13.1
rasterio==1.3.5
joblib==1.2.0
scikit-learn==1.2.2
geopandas==0.12.1
jupyter==1.0.0
```

### Recommended Additions

- **GitHub Actions workflow** for automatic tests and documentation generation.
- **Contributing guidelines** (`CONTRIBUTING.md`) if you expect external contributions.
- **Example Jupyter notebook** showing how to load and interpret the risk map.

---

## License

This project is licensed under the MIT License – see the LICENSE file for details.

---

## Contact

**Author:** Sparsh Kapoor

Feel free to open an issue or pull request for improvements or questions.

---

**Last updated:** February 2026
