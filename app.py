from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash, send_file
import pickle
import os
import numpy as np
from werkzeug.utils import secure_filename
import sqlite3
from functools import wraps
from datetime import datetime
import parselmouth
import joblib
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
import tempfile

app = Flask(__name__)
app.secret_key = "parkinsons_detection_secret_key"  # Needed for session management
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# Load models and scalers
motor_scaler = joblib.load("Model/scaler_rf.pkl")
motor_model = joblib.load("Model/optimized_lightgbm_model_core.pkl")
motor_model1 = joblib.load("Model/motor_model_rf.pkl")
staging_scaler = joblib.load("Model/rf_scaler.pkl")
rf_model = joblib.load("Model/rf_model1.pkl")


def init_db():
    conn = sqlite3.connect('users1.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        age INTEGER NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        jitter REAL NOT NULL,
        shimmer REAL NOT NULL,
        motor_updrs REAL NOT NULL,  -- Changed from hnr
        ppe REAL NOT NULL,
        prediction REAL NOT NULL,
        stage TEXT,
        test_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect('users1.db')
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def extract_features(file_path):
    try:
        sound = parselmouth.Sound(file_path)
        pitch = sound.to_pitch()
        point_process = parselmouth.praat.call(sound, "To PointProcess (periodic, cc)", 75, 500)
        pulses = parselmouth.praat.call([sound, pitch], "To PointProcess (cc)")
        
        jitter = parselmouth.praat.call(pulses, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3)
        shimmer = parselmouth.praat.call([sound, pulses], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
        
        pitch_values = pitch.selected_array['frequency']
        pitch_values = pitch_values[pitch_values > 0]
        ppe = np.std(np.log(pitch_values)) if len(pitch_values) > 0 else 0
        age = session.get('user_age', 30)

        motor_features = np.array([[age, shimmer, float(jitter), ppe]])
        scaled_motor = motor_scaler.transform(motor_features)
        predicted_motor = motor_model.predict(scaled_motor)[0]

        staging_data = np.array([[predicted_motor, age, shimmer, ppe]])
        
        scaled_staging = staging_scaler.transform(staging_data)
        return {
            "age": age,
            "jitter": float(jitter),
            "shimmer": float(shimmer),
            "ppe": float(ppe),
            "motor_updrs": float(predicted_motor),
            "scaled_features": scaled_staging.tolist()
        }
    except Exception as e:
        print(f"Feature extraction error: {str(e)}")
        return None

def predict_parkinson(scaled_features):
    try:
        if not scaled_features or len(scaled_features) == 0:
            return {"error": "Invalid input features"}
        
        # Ensure no NaN values in features
        scaled_features = [[float(val or 0) for val in row] for row in scaled_features]
        
         
        
        print("scaled_features:",scaled_features)  
        prediction = rf_model.predict(scaled_features)[0]
        
        
        # Staging logic with safe value casting
        prediction_value = float(prediction)
        print(prediction_value)

        if prediction_value <= 25:
            stage, description = "Stage 1", "Unilateral symptoms only"
        elif prediction_value <= 35:
            stage, description = "Stage 1.5", "Unilateral + axial involvement"
        elif prediction_value <= 45:
            stage, description = "Stage 2", "Bilateral symptoms, no balance impairment"
        elif prediction_value <= 55:
            stage, description = "Stage 2.5", "Mild bilateral disease + recovery on pull test"
        elif prediction_value <= 70:
            stage, description = "Stage 3", "Balance impairment, physically independent"
        elif prediction_value <= 85:
            stage, description = "Stage 4", "Severe disability, still able to walk/stand"
        else:
            stage, description = "Stage 5", "Wheelchair/bedridden unless aided"

        # Calculate severity using original features
        try:
            jitter = float(scaled_features[0][0]) if len(scaled_features) > 0 and len(scaled_features[0]) > 0 else 0
            shimmer = float(scaled_features[0][2]) if len(scaled_features) > 0 and len(scaled_features[0]) > 2 else 0
            ppe = float(scaled_features[0][3]) if len(scaled_features) > 0 and len(scaled_features[0]) > 3 else 0
            severity_score = jitter + shimmer + ppe
        except (ValueError, TypeError):
            severity_score = 0
        
        if severity_score < 0.5:
            severity_stage = "Early Stage"
        elif severity_score < 1.0:
            severity_stage = "Moderate Stage"
        else:
            severity_stage = "Advanced Stage"

        return {
            "prediction": prediction_value,
            "stage": stage,
            "description": description,
            "severity_stage": severity_stage
        }
    except Exception as e:
        print(f"Prediction error: {str(e)}")
        return {"error": f"Prediction failed: {str(e)}"}

@app.route("/predict", methods=["POST"])
@login_required
def predict():
    try:
        data = request.json.get("features", {})
        
        # Sanitize input to prevent NaN and non-numeric values
        features = {
            "jitter": float(data.get("jitter", 0) or 0),
            "shimmer": float(data.get("shimmer", 0) or 0),
            "motor_updrs": float(data.get("motor_updrs", 0) or 0),  # Changed from hnr
            "ppe": float(data.get("ppe", 0) or 0),
            "scaled_features": data.get("scaled_features", [])
        }

        age = session.get('user_age', 30)

        motor_features = np.array([age, features["shimmer"], float(features["jitter"]), features["ppe"]]).reshape(1,-1)
        # scaled_motor = motor_scaler.transform(motor_features)
        predicted_motor = motor_model1.predict(motor_features)
        print("Predicted Motor:",predicted_motor)
# [predicted_motor, age, shimmer, ppe]
        prediction_features = [[predicted_motor,age,features["shimmer"],features["ppe"]]]
        #prediction_features = [[18.153992905105532,72,0.1386841480961315,0.5631752373901396]]
        #prediction_features = features["scaled_features"]
        print(features["motor_updrs"])
        print("shimmer:",features["shimmer"])
        print(prediction_features)
        
        			
        # Validate scaled_features format
        if not features["scaled_features"] or not isinstance(features["scaled_features"], list):
            features["scaled_features"] = [[0, 0, 0, 0]]  # Default placeholder
        
        # Ensure no NaN values in nested lists
        for i, row in enumerate(features["scaled_features"]):
            if not isinstance(row, list):
                features["scaled_features"][i] = [0, 0, 0, 0]
            else:
                features["scaled_features"][i] = [float(val or 0) for val in row]

        prediction_result = predict_parkinson(prediction_features)
        if "error" in prediction_result:
            return jsonify(prediction_result), 400

        # Store results in database
        try:
            with get_db_connection() as conn:
                conn.execute('''
                INSERT INTO user_results 
                (user_id, jitter, shimmer, motor_updrs, ppe, prediction, stage)
                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (
                    session['user_id'],
                    features["jitter"],
                    features["shimmer"],
                    features["motor_updrs"],
                    features["ppe"],
                    prediction_result['prediction'],
                    prediction_result['stage']
                ))
                conn.commit()
        except sqlite3.Error as e:
            print(f"Database error during result storage: {str(e)}")
            # Continue even if storage fails

        return jsonify({
            "prediction": round(prediction_result['prediction'], 2),
            "stage": prediction_result['stage'],
            "description": prediction_result['description'],
            "severity_stage": prediction_result['severity_stage']
        })

    except Exception as e:
        print(f"API Error: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/")
def index():
    if 'user_id' in session:
        return redirect(url_for('home'))
    return render_template("login.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, name, age FROM users WHERE email = ? AND password = ?", (email, password))
                user = cursor.fetchone()
            
            if user:
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                session['user_age'] = user['age']
                session['user_email'] = email
                flash("Login successful!", "success")
                return redirect(url_for('home'))
            else:
                flash("Invalid email or password", "error")
        except sqlite3.Error as e:
            flash(f"Database error: {str(e)}", "error")
    
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        age = request.form.get("age")
        email = request.form.get("email")
        password = request.form.get("password")
        
        # Basic validation
        if not all([name, age, email, password]):
            flash("Please fill in all fields", "error")
            return render_template("register.html")
        
        try:
            age = int(age)
            if age < 1:
                flash("Please enter a valid age", "error")
                return render_template("register.html")
        except ValueError:
            flash("Age must be a number", "error")
            return render_template("register.html")
        
        try:
            # Check if email already exists
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
                existing_user = cursor.fetchone()
            
            if existing_user:
                flash("Email already registered", "error")
                return render_template("register.html")
            
            # Insert new user
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (name, age, email, password) VALUES (?, ?, ?, ?)",
                    (name, age, email, password)
                )
                conn.commit()
            
            flash("Registration successful! You can now login.", "success")
            return redirect(url_for('login'))
        except sqlite3.Error as e:
            flash(f"Database error: {str(e)}", "error")
            return render_template("register.html")
    
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out", "info")
    return redirect(url_for('login'))

@app.route("/home")
@login_required
def home():
    user_data = {
        'name': session.get('user_name'),
        'age': session.get('user_age'),
        'email': session.get('user_email')
    }
    return render_template("index.html", user=user_data)

@app.route("/upload", methods=["POST"])
@login_required
def upload_audio():
    """
    Handles audio upload and extracts features.
    """
    if "audio" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    audio_file = request.files["audio"]
    if audio_file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    
    filename = secure_filename(audio_file.filename)
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    audio_file.save(file_path)
    
    # Extract features
    features = extract_features(file_path)
    os.remove(file_path)  # Clean up file after processing
    
    return jsonify({"features": features})



@app.route("/history")
@login_required
def history():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, jitter, shimmer, motor_updrs, ppe, prediction, stage, test_date
                FROM user_results
                WHERE user_id = ?
                ORDER BY test_date DESC
                """,
                (session['user_id'],))
            results = cursor.fetchall()
        
        return render_template("history.html", results=results, user_name=session.get('user_name'))
    except sqlite3.Error as e:
        flash(f"Database error: {str(e)}", "error")
        return redirect(url_for('home'))

@app.route("/export_single_pdf/<int:test_id>")
@login_required
def export_single_pdf(test_id):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT jitter, shimmer, motor_updrs, ppe, prediction, stage, test_date
                FROM user_results
                WHERE id = ? AND user_id = ?
            """, (test_id, session['user_id']))
            result = cursor.fetchone()
            
            if not result:
                flash("Test result not found", "error")
                return redirect(url_for('history'))
            
            # Create a temporary file for the PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                # Create the PDF document
                doc = SimpleDocTemplate(
                    tmp.name,
                    pagesize=A4,
                    rightMargin=72,
                    leftMargin=72,
                    topMargin=72,
                    bottomMargin=72
                )
                
                # Get styles
                styles = getSampleStyleSheet()
                title_style = ParagraphStyle(
                    'CustomTitle',
                    parent=styles['Heading1'],
                    fontSize=24,
                    spaceAfter=30,
                    textColor=colors.HexColor('#4285F4')
                )
                
                # Create content
                content = []
                
                # Add title
                content.append(Paragraph("Parkinson's Disease Test Report", title_style))
                content.append(Paragraph(f"Generated on: {result['test_date']}", styles["Normal"]))
                content.append(Paragraph(f"Patient: {session.get('user_name')}", styles["Normal"]))
                content.append(Spacer(1, 20))
                
                # Add test results table
                content.append(Paragraph("Test Results", styles["Heading2"]))
                data = [
                    ["Parameter", "Value"],
                    ["Jitter", f"{result['jitter']:.6f}"],
                    ["Shimmer", f"{result['shimmer']:.6f}"],
                    ["Motor UPDRS", f"{result['motor_updrs']:.2f}"],
                    ["PPE", f"{result['ppe']:.6f}"]
                ]
                
                table = Table(data, colWidths=[2*inch, 3*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 10),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                content.append(table)
                content.append(Spacer(1, 20))
                
                # Add analysis section
                content.append(Paragraph("Analysis", styles["Heading2"]))
                prediction_color = colors.HexColor('#721c24') if result['prediction'] > 0 else colors.HexColor('#155724')
                prediction_style = ParagraphStyle(
                    'Prediction',
                    parent=styles['Normal'],
                    fontSize=14,
                    textColor=prediction_color,
                    backColor=colors.HexColor('#f8d7da' if result['prediction'] > 0 else '#d4edda'),
                    borderPadding=10,
                    borderWidth=1,
                    borderRadius=5
                )
                content.append(Paragraph(f"Prediction: {result['prediction']:.2f}", prediction_style))
                content.append(Paragraph(f"Stage: {result['stage']}", styles["Normal"]))
                content.append(Spacer(1, 20))
                
                # Add footer
                footer_style = ParagraphStyle(
                    'Footer',
                    parent=styles['Normal'],
                    fontSize=8,
                    textColor=colors.grey,
                    alignment=1  # Center alignment
                )
                content.append(Paragraph("This report is generated automatically by the Parkinson's Disease Detection System.", footer_style))
                content.append(Paragraph("For medical advice, please consult with a healthcare professional.", footer_style))
                
                # Build the PDF
                doc.build(content)
                tmp_path = tmp.name
            
            # Send the PDF file
            return send_file(
                tmp_path,
                as_attachment=True,
                download_name=f'parkinsons_test_result_{test_id}.pdf',
                mimetype='application/pdf'
            )
            
    except Exception as e:
        flash(f"Error generating PDF: {str(e)}", "error")
        return redirect(url_for('history'))

if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    init_db()  # Initialize database on startup
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))