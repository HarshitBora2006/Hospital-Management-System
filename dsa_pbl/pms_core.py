import uuid
from datetime import datetime
from collections import defaultdict
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, DayLocator

from data_manager import load_data, save_data


class PatientManagementSystem:
    """Handles all core logic and state management for the PMS."""

    def __init__(self):
        self.data = load_data()
        self.current_user = None

    def reload(self):
        self.data = load_data()

    def _generate_id(self):
        """Generates a short unique ID."""
        return str(uuid.uuid4())[:8]

    # -------------------------------------------------------------------------
    # AUTHENTICATION
    # -------------------------------------------------------------------------
    def login(self, username, password):
        """Authenticate a user."""
        user_info = self.data['users'].get(username)
        if user_info and user_info['password'] == password:
            self.current_user = {
                'username': username,
                'role': user_info['role'],
                'id': user_info.get('id')
            }
            return True
        return False

    # -------------------------------------------------------------------------
    # ADMIN FUNCTIONS
    # -------------------------------------------------------------------------
    def add_doctor(self, name, specialty, password):
        """Create a new doctor account."""
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
        """Display patient count per day using Matplotlib."""
        patient_counts = defaultdict(int)

        for appt in self.data['appointments']:
            if appt.get('status') == 'Approved':
                patient_counts[appt['date']] += 1

        if not patient_counts:
            return "No appointment data available to plot."

        dates = sorted(patient_counts.keys())
        counts = [patient_counts[d] for d in dates]
        datetime_dates = [datetime.strptime(d, '%Y-%m-%d') for d in dates]

        try:
            plt.style.use('ggplot')
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.bar(datetime_dates, counts, width=0.8, color='skyblue')
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

    # -------------------------------------------------------------------------
    # DOCTOR FUNCTIONS
    # -------------------------------------------------------------------------
    def get_today_appointments(self, doctor_id):
        """Return today's appointments for a doctor."""
        today = datetime.now().strftime('%Y-%m-%d')
        appointments = []

        for appt in self.data['appointments']:
            if (
                appt.get('doctor_id') == doctor_id
                and appt.get('date') == today
                and appt.get('status') == 'Approved'
            ):
                patient = self.data['patients'].get(appt['patient_id'], {'name': 'Unknown'})
                appointments.append({
                    'ID': appt['id'],
                    'Patient Name': patient.get('name', 'Unknown'),
                    'Age': patient.get('age', 'N/A'),
                    'Gender': patient.get('gender', 'N/A'),
                    'Problem': appt.get('problem', 'N/A'),
                    'Time': appt.get('time', 'N/A')
                })

        return appointments

    def get_emergency_cases(self, doctor_id):
        """Return all emergency cases related to this doctor."""
        emergencies = []
        for appt in self.data['appointments']:
            if appt.get('status') == 'Emergency' and (
                appt.get('doctor_id') == doctor_id or not appt.get('doctor_id')
            ):
                patient = self.data['patients'].get(appt['patient_id'], {'name': 'Unknown'})
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
        """Return referrals assigned to this doctor."""
        incoming = []
        for ref in self.data['referrals']:
            if ref.get('to_doc_id') == doctor_id:
                patient = self.data['patients'].get(ref['patient_id'], {'name': 'Unknown'})
                from_doc = self.data['doctors'].get(ref['from_doc_id'], {'name': 'External Doctor'})
                incoming.append({
                    'Date': ref.get('date', 'Unknown'),
                    'Patient Name': patient['name'],
                    'Referred By': from_doc['name'],
                    'Notes': ref.get('notes', '')
                })
        return incoming

    def create_referral(self, patient_id, to_doc_id, notes):
        """Create a new referral from one doctor to another."""
        if patient_id not in self.data['patients']:
            return "Error: Patient ID not found."
        if to_doc_id not in self.data['doctors']:
            return "Error: Target Doctor ID not found."

        referral = {
            'patient_id': patient_id,
            'from_doc_id': self.current_user['id'],
            'to_doc_id': to_doc_id,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'notes': notes
        }

        self.data['referrals'].append(referral)
        save_data(self.data)
        target_doc = self.data['doctors'][to_doc_id]['name']
        return f"Referral created successfully for patient {patient_id} to Dr. {target_doc}."

    def upload_report(self, patient_id, details=None, file_name=None):
        """Doctor uploads a new report — either text or file."""
        if patient_id not in self.data['patients']:
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

        if patient_id not in self.data['reports']:
            self.data['reports'][patient_id] = []

        self.data['reports'][patient_id].append(report)
        save_data(self.data)

        msg = f"Report {report_id} uploaded successfully for patient {patient_id}."
        if file_name:
            msg += f" (File: {file_name})"
        return msg

    def get_patient_reports(self, patient_id):
        """Return all reports for a given patient, supporting both text and file uploads."""
        reports = self.data.get('reports', {}).get(patient_id, [])
        detailed_reports = []

        for report in reports:
            doctor_name = (
                report.get('Doctor')
                or self.data['doctors'].get(report.get('doctor_id', ''), {}).get('name', 'Unknown Doctor')
            )
            details = report.get('Details') or report.get('details', '')
            file_name = report.get('File')

            formatted = {
                'ID': report.get('report_id', 'N/A'),
                'Date': report.get('Date') or report.get('date', 'Unknown Date'),
                'Doctor': doctor_name,
                'Details': details
            }

            if file_name:
                formatted['File'] = file_name

            detailed_reports.append(formatted)

        return detailed_reports

    # -------------------------------------------------------------------------
    # PATIENT FUNCTIONS
    def book_appointment(self, name, age, gender, date, time, problem):
        """Patient creates a new appointment request (with fixed allowed times)."""
        patient_id = self.current_user['id']

        if patient_id not in self.data['patients']:
            self.data['patients'][patient_id] = {
                'id': patient_id,
                'name': name,
                'age': age,
                'gender': gender
            }

        # Validate time is within allowed slots
        allowed_times = []
        for h in range(9, 12):  # 09:00–11:50
            for m in range(0, 60, 10):
                allowed_times.append(f"{h:02d}:{m:02d}")
        for h in range(14, 18):  # 14:00–17:50
            for m in range(0, 60, 10):
                allowed_times.append(f"{h:02d}:{m:02d}")

        if time not in allowed_times:
            return "❌ Please select a valid time between 09:00–12:00 or 14:00–18:00."

        # Select a doctor (for now, first available)
        doc_ids = list(self.data['doctors'].keys())
        if not doc_ids:
            return "No doctors available currently. Please try again later."
        assigned_doc_id = doc_ids[0]

        # Check for booking conflict
        for appt in self.data['appointments']:
            if (appt['doctor_id'] == assigned_doc_id and
                appt['date'] == date and
                appt['time'] == time and
                appt['status'] == 'Approved'):
                return f"❌ Doctor is already booked at {time} on {date}. Please choose another slot."

        # Save appointment
        appt_id = self._generate_id()
        appointment = {
            'id': appt_id,
            'patient_id': patient_id,
            'doctor_id': assigned_doc_id,
            'date': date,
            'time': time,
            'problem': problem,
            'status': 'Approved'
        }
        self.data['appointments'].append(appointment)
        save_data(self.data)

        doc_name = self.data['doctors'].get(assigned_doc_id, {}).get('name', 'Pending')
        return f"✅ Appointment booked successfully! ID: {appt_id}. You are scheduled with Dr. {doc_name} on {date} at {time}."


    def log_emergency(self, name, age, gender, problem):
        """Patient logs an emergency case."""
        patient_id = self.current_user['id']
        if patient_id not in self.data['patients']:
            self.data['patients'][patient_id] = {'id': patient_id, 'name': name, 'age': age, 'gender': gender}

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

        self.data['appointments'].append(emergency)
        save_data(self.data)
        return f"Emergency logged! ID: {appt_id}. A doctor will contact you soon."

    def get_patient_enquiries(self):
        """Show all non-emergency appointments for a patient."""
        patient_id = self.current_user['id']
        history = []
        for appt in self.data['appointments']:
            if appt.get('patient_id') == patient_id and appt.get('status') != 'Emergency':
                doc_name = self.data['doctors'].get(appt.get('doctor_id', ''), {}).get('name', 'N/A')
                history.append({
                    'Date': appt.get('date', 'N/A'),
                    'Doctor': doc_name,
                    'Problem': appt.get('problem', 'N/A'),
                    'Status': appt.get('status', 'N/A')
                })
        return history

    def get_upcoming_checkup(self):
        """Return the next approved future appointment."""
        patient_id = self.current_user['id']
        now = datetime.now()
        upcoming = None

        for appt in self.data['appointments']:
            if appt.get('patient_id') == patient_id and appt.get('status') == 'Approved':
                try:
                    appt_dt = datetime.strptime(f"{appt['date']} {appt['time']}", '%Y-%m-%d %H:%M')
                    if appt_dt > now and (not upcoming or appt_dt < upcoming['datetime']):
                        doc_name = self.data['doctors'].get(appt.get('doctor_id', ''), {}).get('name', 'N/A')
                        upcoming = {
                            'datetime': appt_dt,
                            'Date': appt['date'],
                            'Time': appt['time'],
                            'Doctor': doc_name,
                            'Problem': appt['problem']
                        }
                except ValueError:
                    continue

        return upcoming if upcoming else None

    def setup_initial_patient(self):
        """Create a default test patient if none exists."""
        data = load_data()
        if 'test_patient' not in data['users']:
            patient_id = self._generate_id()
            data['users']['test_patient'] = {
                'password': 'patientpass',
                'role': 'Patient',
                'id': patient_id
            }
            data['patients'][patient_id] = {'id': patient_id, 'name': 'Test Patient', 'age': '35', 'gender': 'M'}
            save_data(data)
            return True
        return False
