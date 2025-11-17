# pms_core.py
import uuid
from datetime import datetime
from collections import defaultdict
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, DayLocator
from data_manager import load_data, save_data


class PatientManagementSystem:
    """Core logic and state management for the Patient Management System."""

    def __init__(self):
        self.data = load_data()
        self.current_user = None

    def reload(self):
        """Reload data from storage."""
        self.data = load_data()

    def _generate_id(self):
        """Generate a short unique ID."""
        return str(uuid.uuid4())[:8]

    # ------------------------------------------------------
    # AUTH
    # ------------------------------------------------------
    def login(self, username, password):
        user_info = self.data['users'].get(username)
        if user_info and user_info['password'] == password:
            self.current_user = {
                'username': username,
                'role': user_info['role'],
                'id': user_info.get('id')
            }
            return True
        return False

    # ------------------------------------------------------
    # ADMIN
    # ------------------------------------------------------
    def add_doctor(self, name, specialty, password):
        doctor_id = self._generate_id()
        username = name.lower().replace(' ', '_')

        if username in self.data['users']:
            return "Username already exists. Try a different name."

        self.data['doctors'][doctor_id] = {
            'id': doctor_id,
            'name': name,
            'specialty': specialty
        }

        self.data['users'][username] = {
            'password': password,
            'role': 'Doctor',
            'id': doctor_id
        }

        save_data(self.data)
        return {'name': name, 'username': username, 'id': doctor_id}

    def plot_daily_patients(self):
        """
        Plot a bar chart showing number of approved patients per day.
        """
        patient_counts = defaultdict(int)

        for appt in self.data.get('appointments', []):
            if str(appt.get('status', '')).strip().lower() == 'approved':
                patient_counts[appt.get('date')] += 1

        if not patient_counts:
            return "No appointment data available to plot."

        dates = sorted(patient_counts.keys())
        counts = [patient_counts[d] for d in dates]
        dt_dates = [datetime.strptime(d, '%Y-%m-%d') for d in dates]

        try:
            plt.style.use('ggplot')
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.bar(dt_dates, counts, width=0.8)
            ax.xaxis.set_major_formatter(DateFormatter('%b %d'))
            ax.xaxis.set_major_locator(DayLocator(interval=1))
            plt.xticks(rotation=45, ha='right')
            plt.title('Patient Visits Per Day')
            plt.xlabel('Date')
            plt.ylabel('Number of Patients')
            plt.tight_layout()
            plt.show()
            return "Graph displayed successfully."
        except Exception as e:
            return f"Error generating graph: {e}"

    # ------------------------------------------------------
    # DOCTOR
    # ------------------------------------------------------
    def get_today_appointments(self, doctor_id):
        today = datetime.now().strftime('%Y-%m-%d')

        # 10-minute slots between 09:00-12:00 and 14:00-18:00
        slots = []
        for h in range(9, 12):
            for m in range(0, 60, 10):
                slots.append(f"{h:02d}:{m:02d}")
        for h in range(14, 18):
            for m in range(0, 60, 10):
                slots.append(f"{h:02d}:{m:02d}")

        schedule = [{'time': t, 'status': 'Available', 'patient': '-', 'problem': '-', 'appt_id': None} for t in slots]

        for appt in self.data.get('appointments', []):
            status = str(appt.get('status', '')).strip().lower()
            if appt.get('doctor_id') == doctor_id and appt.get('date') == today and status == 'approved':
                appt_time = str(appt.get('time', '')).strip()
                for slot in schedule:
                    if slot['time'] == appt_time:
                        patient = self.data.get('patients', {}).get(appt.get('patient_id'), {})
                        slot['status'] = 'Booked'
                        slot['patient'] = patient.get('name', 'Unknown')
                        slot['problem'] = appt.get('problem', '-')
                        slot['appt_id'] = appt.get('id')
                        break

        return schedule

    def get_emergency_cases(self, doctor_id):
        emergencies = []
        for appt in self.data.get('appointments', []):
            if str(appt.get('status', '')).strip().lower() == 'emergency' and (
                appt.get('doctor_id') == doctor_id or not appt.get('doctor_id')
            ):
                patient = self.data['patients'].get(appt.get('patient_id'), {'name': 'Unknown'})
                emergencies.append({
                    'ID': appt.get('id'),
                    'Patient Name': patient.get('name', 'Unknown'),
                    'Age': patient.get('age', 'N/A'),
                    'Problem': appt.get('problem', 'N/A'),
                    'Time': appt.get('time', 'N/A'),
                    'Assigned Doctor': appt.get('doctor_id', 'Unassigned')
                })
        return emergencies

    def get_incoming_referrals(self, doctor_id):
        incoming = []
        for ref in self.data.get('referrals', []):
            if ref.get('to_doc_id') == doctor_id:
                patient = self.data['patients'].get(ref['patient_id'], {'name': 'Unknown'})
                from_doc = self.data['doctors'].get(ref.get('from_doc_id', ''), {'name': 'External Doctor'})
                incoming.append({
                    'Date': ref.get('date', 'Unknown'),
                    'Patient Name': patient['name'],
                    'Referred By': from_doc['name'],
                    'Notes': ref.get('notes', '')
                })
        return incoming

    def create_referral(self, patient_id, to_doc_id, notes):
        if patient_id not in self.data.get('patients', {}):
            return "Error: Patient ID not found."
        if to_doc_id not in self.data.get('doctors', {}):
            return "Error: Target Doctor ID not found."

        referral = {
            'patient_id': patient_id,
            'from_doc_id': self.current_user['id'],
            'to_doc_id': to_doc_id,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'notes': notes
        }

        self.data.setdefault('referrals', []).append(referral)
        save_data(self.data)
        return f"Referral created successfully for patient {patient_id}."

    def upload_report(self, patient_id, details=None, file_name=None):
        if patient_id not in self.data.get('patients', {}):
            return "Error: Patient ID not found."

        report_id = self._generate_id()
        report = {
            'report_id': report_id,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'doctor_id': self.current_user['id']
        }

        if file_name:
            report['File'] = file_name
        if details:
            report['Details'] = details

        self.data.setdefault('reports', {}).setdefault(patient_id, []).append(report)
        save_data(self.data)
        return f"Report {report_id} uploaded successfully."

    def get_patient_reports(self, patient_id):
        reports = self.data.get('reports', {}).get(patient_id, [])
        formatted = []
        for r in reports:
            doctor_name = self.data.get('doctors', {}).get(r.get('doctor_id', ''), {}).get('name', 'Unknown Doctor')
            entry = {
                'ID': r.get('report_id'),
                'Date': r.get('date'),
                'Doctor': doctor_name,
                'Details': r.get('Details', '')
            }
            if 'File' in r:
                entry['File'] = r['File']
            formatted.append(entry)
        return formatted

    # ------------------------------------------------------
    # PATIENT
    # ------------------------------------------------------
    def book_appointment(self, name, age, gender, date, time, problem):
        patient_id = self.current_user.get('id')
        if not patient_id:
            patient_id = self._generate_id()

        problem_to_specialty = {
            "Heart": "Cardiology",
            "Fever": "General Physician",
            "Skin": "Dermatologist",
            "Diabetes": "Endocrinologist",
            "Bone": "Orthopedic",
            "Can't say": "General Physician"
        }
        specialty = problem_to_specialty.get(problem, "General Physician")
        doctors = [doc for doc in self.data['doctors'].values() if doc['specialty'] == specialty]

        if not doctors:
            return f"No doctor available for {specialty}"

        doctors.sort(key=lambda d: sum(1 for a in self.data['appointments'] 
                                       if a['doctor_id']==d['id'] and a['date']==date))
        doctor = doctors[0]
        doctor_id = doctor['id']

        appointment = {
            'id': self._generate_id(),
            'patient_id': patient_id,
            'doctor_id': doctor_id,
            'date': date,
            'time': time,
            'problem': problem,
            'status': 'Approved'
        }

        self.data.setdefault('appointments', []).append(appointment)
        save_data(self.data)
        return f"Appointment booked successfully with Dr. {doctor['name']} ({doctor['specialty']})"

    def log_emergency(self, name, age, gender, problem):
        patient_id = self.current_user['id']

        if patient_id not in self.data.get('patients', {}):
            self.data.setdefault('patients', {})[patient_id] = {'id': patient_id, 'name': name, 'age': age, 'gender': gender}

        appt_id = self._generate_id()
        emergency = {
            'id': appt_id,
            'patient_id': patient_id,
            'doctor_id': None,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M'),
            'problem': problem,
            'status': 'Emergency'
        }

        self.data.setdefault('appointments', []).append(emergency)
        save_data(self.data)
        return f"Emergency logged. ID: {appt_id}."

    def get_patient_enquiries(self):
        pid = self.current_user['id']
        hist = []
        for appt in self.data.get('appointments', []):
            if appt.get('patient_id') == pid and str(appt.get('status', '')).strip().lower() != 'emergency':
                doc = self.data.get('doctors', {}).get(appt.get('doctor_id', ''), {}).get('name', 'N/A')
                hist.append({
                    'Date': appt.get('date'),
                    'Doctor': doc,
                    'Problem': appt.get('problem'),
                    'Status': appt.get('status')
                })
        return hist

    def get_upcoming_checkup(self):
        pid = self.current_user['id']
        now = datetime.now()
        upcoming = None

        for appt in self.data.get('appointments', []):
            if appt.get('patient_id') == pid and str(appt.get('status', '')).strip().lower() == 'approved':
                try:
                    appt_dt = datetime.strptime(f"{appt['date']} {appt['time']}", '%Y-%m-%d %H:%M')
                    if appt_dt > now and (not upcoming or appt_dt < upcoming['datetime']):
                        doc_name = self.data.get('doctors', {}).get(appt.get('doctor_id', ''), {}).get('name', 'N/A')
                        upcoming = {
                            'datetime': appt_dt,
                            'Date': appt['date'],
                            'Time': appt['time'],
                            'Doctor': doc_name,
                            'Problem': appt['problem']
                        }
                except Exception:
                    continue

        return upcoming

    def setup_initial_patient(self):
        data = load_data()
        if 'test_patient' not in data.get('users', {}):
            pid = self._generate_id()
            data.setdefault('users', {})['test_patient'] = {
                'password': 'patientpass',
                'role': 'Patient',
                'id': pid
            }
            data.setdefault('patients', {})[pid] = {'id': pid, 'name': 'Test Patient', 'age': '35', 'gender': 'M'}
            save_data(data)
            return True
        return False
