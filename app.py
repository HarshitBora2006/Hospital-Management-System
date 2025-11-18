from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
from jinja2 import FileSystemLoader
from werkzeug.utils import secure_filename
from datetime import datetime
import os, uuid
from pms_core import PatientManagementSystem
from data_manager import load_data, save_data

# --- Flask config ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.dirname(__file__),
    static_folder=os.path.join(BASE_DIR, 'static')
)
app.jinja_loader = FileSystemLoader(BASE_DIR)
app.secret_key = os.environ.get('SECRET_KEY', 'secret-key-change-this')

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/styles.css')
def serve_css():
    return send_from_directory(BASE_DIR, 'styles.css')


# --- Core backend ---
pms = PatientManagementSystem()
pms.setup_initial_patient()


# --- Role check decorator ---
def login_required(role=None):
    def decorator(func):
        def wrapper(*args, **kwargs):
            if 'username' not in session:
                flash("Please log in first.", "warning")
                return redirect(url_for('login'))
            if role and session.get('role') != role:
                flash("Access denied.", "danger")
                return redirect(url_for('login'))
            pms.current_user = {
                'username': session['username'],
                'role': session['role'],
                'id': session.get('id')
            }
            return func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator


# ---------------- Routes ----------------

@app.route('/')
def home():
    return redirect(url_for('login'))


# --- Signup ---
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username'].strip().lower()
        password = request.form['password'].strip()
        name = request.form['name'].strip()
        age = request.form['age'].strip()
        gender = request.form['gender'].strip()

        data = load_data()
        if username in data['users']:
            flash("Username already exists.", "danger")
            return redirect(url_for('signup'))

        patient_id = pms._generate_id()
        data['users'][username] = {'password': password, 'role': 'Patient', 'id': patient_id}
        data['patients'][patient_id] = {'id': patient_id, 'name': name, 'age': age, 'gender': gender}
        save_data(data)

        session['username'] = username
        session['role'] = 'Patient'
        session['id'] = patient_id
        pms.current_user = {'username': username, 'role': 'Patient', 'id': patient_id}

        flash(f"Welcome, {name}! Account created.", "success")
        return redirect(url_for('patient_dashboard'))

    return render_template('signup.html')


# --- Login ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        if pms.login(username, password):
            session['username'] = username
            session['role'] = pms.current_user['role']
            session['id'] = pms.current_user.get('id')

            role = session['role']
            if role == 'Admin':
                return redirect(url_for('admin_dashboard'))
            elif role == 'Doctor':
                return redirect(url_for('doctor_dashboard'))
            elif role == 'Patient':
                return redirect(url_for('patient_dashboard'))
        else:
            flash("Invalid username or password.", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    pms.current_user = None
    flash("Logged out successfully.", "info")
    return redirect(url_for('login'))


# ---------------- Admin ----------------
@app.route('/admin')
@login_required(role='Admin')
def admin_dashboard():
    pms.reload()
    data = pms.data
    patient_counts = {}
    for appt in data.get('appointments', []):
        if appt.get('status') == 'Approved':
            d = appt.get('date')
            patient_counts[d] = patient_counts.get(d, 0) + 1
    return render_template('admin.html', doctors=data['doctors'], patient_counts=patient_counts)


@app.route('/admin/add_doctor', methods=['POST'])
@login_required(role='Admin')
def add_doctor():
    name = request.form['name']
    specialty = request.form['specialty']
    password = request.form['password']
    result = pms.add_doctor(name, specialty, password)
    if isinstance(result, dict):
        flash(f"Doctor created: {result['name']} (username: {result['username']})", "success")
    else:
        flash(result, "danger")
    return redirect(url_for('admin_dashboard'))


@app.route('/api/patient_counts')
@login_required(role='Admin')
def api_patient_counts():
    pms.reload()
    data = pms.data
    counts = {}
    for appt in data.get('appointments', []):
        if appt.get('status') == 'Approved':
            d = appt.get('date')
            counts[d] = counts.get(d, 0) + 1
    dates = sorted(counts.keys())
    values = [counts[d] for d in dates]
    return jsonify({'dates': dates, 'counts': values})


# ---------------- Doctor ----------------
@app.route('/doctor')
@login_required(role='Doctor')
def doctor_dashboard():
    if session.get('role') != 'Doctor':
        flash("Access denied!")
        return redirect(url_for('login'))

    doctor_id = session.get('id')
    today = datetime.now().strftime('%Y-%m-%d')

    # Get today's appointments
    schedule = pms.get_today_appointments(doctor_id)

    # Get emergency cases
    emergencies = pms.get_emergency_cases(doctor_id)

    # Get incoming referrals
    incoming = pms.get_incoming_referrals(doctor_id)

    # Get other doctors for referral dropdown
    other_docs = {id: doc for id, doc in pms.data.get('doctors', {}).items() if id != doctor_id}

    return render_template(
        'doctor.html',
        schedule=schedule,      # Matches template loop {% for s in schedule %}
        emergencies=emergencies,
        today=today,
        other_docs=other_docs,
        incoming=incoming       # Matches template loop {% for i in incoming %}
    )


@app.route('/doctor/upload_report', methods=['POST'])
@login_required(role='Doctor')
def doctor_upload_report():
    patient_id = request.form['patient_id']
    details = request.form.get('details', '').strip()
    file = request.files.get('file')

    if not details and (not file or file.filename == ''):
        flash("Please provide a note or upload a file.", "warning")
        return redirect(url_for('doctor_dashboard'))

    data = load_data()
    doctor_name = session.get('username', 'Unknown Doctor')

    if 'reports' not in data:
        data['reports'] = {}
    if patient_id not in data['reports']:
        data['reports'][patient_id] = []

    report_entry = {"Date": datetime.now().strftime("%Y-%m-%d"), "Doctor": doctor_name}
    if details:
        report_entry["Details"] = details

    if file and allowed_file(file.filename):
        filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        report_entry["File"] = filename

    data['reports'][patient_id].append(report_entry)
    save_data(data)
    pms.reload()
    flash(f"Report uploaded for patient {patient_id}.", "success")
    return redirect(url_for('doctor_dashboard'))


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ---------------- Patient ----------------
@app.route('/patient')
@login_required(role='Patient')
def patient_dashboard():
    pms.reload()
    pat_id = session.get('id')
    reports = pms.get_patient_reports(pat_id)
    upcoming = pms.get_upcoming_checkup(pat_id)
    return render_template('patient.html', reports=reports, upcoming=upcoming)


@app.route('/patient/book', methods=['POST'])
@login_required(role='Patient')
def patient_book():
    pat_id = session.get('id')
    doctor_id = request.form['doctor_id']
    date = request.form['date']
    time = request.form['time']
    problem = request.form['problem']

    result = pms.book_appointment(pat_id, doctor_id, date, time, problem)
    flash(result, "success")
    return redirect(url_for('patient_dashboard'))


@app.route('/patient/emergency', methods=['POST'])
@login_required(role='Patient')
def patient_emergency():
    pat_id = session.get('id')
    doctor_id = request.form.get('doctor_id')  # optional
    problem = request.form['problem']

    result = pms.log_emergency(pat_id, doctor_id, problem)
    flash(result, "danger")
    return redirect(url_for('patient_dashboard'))


# ---------------- Run server ----------------
if __name__ == '__main__':
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(host=host, port=port, debug=debug)

