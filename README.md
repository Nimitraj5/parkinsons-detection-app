# Parkinson's Disease Detection System

A Flask-based web application for detecting Parkinson's disease using voice analysis.

## Features

- User authentication and registration
- Audio file upload and analysis
- Voice feature extraction (jitter, shimmer, PPE)
- Machine learning-based Parkinson's disease prediction
- Disease staging and severity assessment
- PDF report generation
- Test history tracking

## Setup Instructions

### Local Development

#### Prerequisites

- Python 3.9 or higher
- pip (Python package installer)

#### Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd FSA_project
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Node.js dependencies (optional, for audio recording):**
   ```bash
   npm install
   ```

4. **Run the application:**
   ```bash
   python app.py
   ```

5. **Access the application:**
   Open your web browser and go to `http://localhost:5000`

### Render Deployment

#### Prerequisites

- A Render account
- Git repository with your code

#### Deployment Steps

1. **Push your code to a Git repository** (GitHub, GitLab, etc.)

2. **Create a new Web Service on Render:**
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click "New +" and select "Web Service"
   - Connect your Git repository

3. **Configure the service:**
   - **Name:** `parkinsons-detection-app` (or your preferred name)
   - **Environment:** `Python 3`
   - **Build Command:** `chmod +x build.sh && ./build.sh`
   - **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT`
   - **Plan:** Choose your preferred plan (Free tier available)

4. **Environment Variables (optional):**
   - `FLASK_ENV`: `production`
   - `PYTHON_VERSION`: `3.9.18`

5. **Deploy:**
   - Click "Create Web Service"
   - Render will automatically build and deploy your application

6. **Access your deployed app:**
   - Your app will be available at the provided Render URL
   - Example: `https://your-app-name.onrender.com`

## Usage

1. **Register/Login:** Create an account or login with existing credentials
2. **Upload Audio:** Upload an audio file for analysis
3. **View Results:** Get Parkinson's disease prediction and staging
4. **Export Reports:** Download PDF reports of your test results
5. **View History:** Check your previous test results

## Technical Details

- **Backend:** Flask (Python)
- **Database:** SQLite
- **ML Models:** Random Forest, LightGBM
- **Audio Processing:** Parselmouth (Praat)
- **Report Generation:** ReportLab

## File Structure

```
FSA_project/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── package.json          # Node.js dependencies
├── Model/                # Trained ML models
├── static/               # Static files (CSS, JS)
├── templates/            # HTML templates
├── uploads/              # Uploaded audio files
└── users1.db            # SQLite database
```

## Troubleshooting

- If you encounter issues with `parselmouth`, make sure you have the required system dependencies for Praat
- For Windows users, you may need to install Visual C++ build tools
- Ensure all model files are present in the `Model/` directory 