import json
import os

# --- Constants and Data File ---
DATA_FILE = 'pms_data.json'

def load_data():
    """
    Loads application data from the JSON file.
    Initializes default structure if the file is missing or corrupted.
    """
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                return data
        except json.JSONDecodeError:
            print(f"Warning: {DATA_FILE} corrupted. Starting with fresh data.")
    
    # Initialize default structure
    return {
        'users': {
            'admin': {'password': 'adminpass', 'role': 'Admin'},
        },
        'patients': {}, # {patient_id: {name, age, gender, ...}}
        'doctors': {}, # {doctor_id: {name, specialty, password}}
        'appointments': [], # [{id, patient_id, doctor_id, date, time, problem, status}]
        'reports': {}, # {patient_id: [{report_id, date, doctor_id, details}]}
        'referrals': [] # [{patient_id, from_doc_id, to_doc_id, date, notes}]
    }

def save_data(data):
    """Saves application data to the JSON file."""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)
