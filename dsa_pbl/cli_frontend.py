# Import the backend core logic
from pms_core import PatientManagementSystem
from data_manager import load_data 

# --- CLI Menu Handlers (Frontend) ---

def admin_menu(pms):
    """Handles the Admin user interface and options."""
    while True:
        print("\n--- Admin Dashboard ---")
        print("1. Add a Doctor")
        print("2. Show Patient Traffic Graph")
        print("3. Logout")
        choice = input("Enter choice: ")

        if choice == '1':
            name = input("Doctor's Full Name: ")
            specialty = input("Specialty (e.g., Cardiology): ")
            password = input("Initial Password: ")
            
            result = pms.add_doctor(name, specialty, password)
            if isinstance(result, dict):
                print(f"\n--- Doctor Account Created ---")
                print(f"Name: {result['name']}")
                print(f"Username: {result['username']}")
                print(f"ID: {result['id']}")
                print("----------------------------\n")
            else:
                print(result) # Print error message (if username exists)

        elif choice == '2':
            result = pms.plot_daily_patients()
            print(result)

        elif choice == '3':
            break

        else:
            print("Invalid choice.")

def doctor_menu(pms):
    """Handles the Doctor user interface and options."""
    doc_id = pms.current_user['id']
    doc_info = pms.data['doctors'].get(doc_id, {})
    doc_name = doc_info.get('name', 'Doctor')
    print(f"\nWelcome, Dr. {doc_name} ({doc_info.get('specialty', 'N/A')})!")
    
    while True:
        print("\n--- Doctor Dashboard ---")
        print("1. Today's Appointments")
        print("2. Emergency Cases")
        print("3. Incoming Referrals (Referred to me)")
        print("4. Create Referral (Refer Patient to another doctor)")
        print("5. Reports: Upload")
        print("6. Reports: View Past Reports")
        print("7. Logout")
        choice = input("Enter choice: ")

        if choice == '1':
            appts = pms.get_today_appointments(doc_id)
            print("\n--- Today's Approved Appointments ---")
            if appts:
                for a in appts:
                    print(f"ID: {a['ID']} | Time: {a['Time']} | Name: {a['Patient Name']} (Age: {a['Age']}, Gender: {a['Gender']}) | Problem: {a['Problem']}")
            else:
                print("No appointments scheduled for today.")

        elif choice == '2':
            emergencies = pms.get_emergency_cases(doc_id)
            print("\n--- Emergency Cases ---")
            if emergencies:
                 for e in emergencies:
                    print(f"ID: {e['ID']} | Time: {e['Time']} | Name: {e['Patient Name']} | Problem: {e['Problem']} | Assigned: {e['Assigned Doctor']}")
            else:
                print("No emergency cases currently pending.")
                
        elif choice == '3':
            incoming = pms.get_incoming_referrals(doc_id)
            print("\n--- Incoming Referrals ---")
            if incoming:
                for i in incoming:
                    print(f"Date: {i['Date']} | Patient: {i['Patient Name']} | From: {i['Referred By']} | Notes: {i['Notes']}")
            else:
                print("No incoming patient referrals.")

        elif choice == '4':
            patient_id = input("Enter Patient ID to refer: ")
            
            current_doc_id = pms.current_user['id']
            other_doctors = {d_id: info['name'] for d_id, info in pms.data['doctors'].items() if d_id != current_doc_id}
            if not other_doctors:
                print("Cannot refer: No other doctors in the system.")
                continue
                
            print("\nAvailable Doctors to Refer To:")
            for d_id, d_name in other_doctors.items():
                print(f"  [{d_id}] - Dr. {d_name}")
            
            to_doc_id = input("Enter Target Doctor ID: ")
            notes = input("Enter referral notes/reason: ")
            
            result = pms.create_referral(patient_id, to_doc_id, notes)
            print(result)

        elif choice == '5':
            patient_id = input("Enter Patient ID to upload report for: ")
            details = input("Enter full report details/findings: ")
            result = pms.upload_report(patient_id, details)
            print(result)

        elif choice == '6':
            patient_id = input("Enter Patient ID to view past reports: ")
            reports = pms.get_patient_reports(patient_id)
            print(f"\n--- Past Reports for Patient {patient_id} ---")
            if reports:
                for r in reports:
                    print(f"ID: {r['ID']} | Date: {r['Date']} | Doctor: {r['Doctor']}")
                    print(f"  Details: {r['Details']}")
            else:
                print("No reports found for this patient ID.")
        
        elif choice == '7':
            break

        else:
            print("Invalid choice.")

def patient_menu(pms):
    """Handles the Patient user interface and options."""
    pat_id = pms.current_user['id']
    patient_info = pms.data['patients'].get(pat_id, {'name': 'New Patient'})
    print(f"\nWelcome, {patient_info['name']}!")

    while True:
        print("\n--- Patient Dashboard ---")
        print("1. Book an Appointment")
        print("2. Report Emergency")
        print("3. View Reports (Past and Present)")
        print("4. View Enquiry History (Past Appointments)")
        print("5. Check Up (Upcoming Appointment)")
        print("6. Logout")
        choice = input("Enter choice: ")

        if choice == '1':
            name = input("Your Full Name: ")
            age = input("Your Age: ")
            gender = input("Your Gender (M/F/O): ")
            date = input("Preferred Date (YYYY-MM-DD): ")
            time = input("Preferred Time (HH:MM - e.g., 14:30): ")
            problem = input("Briefly describe your problem: ")
            
            result = pms.book_appointment(name, age, gender, date, time, problem)
            print(result)

        elif choice == '2':
            name = input("Your Full Name: ")
            age = input("Your Age: ")
            gender = input("Your Gender (M/F/O): ")
            problem = input("Describe the emergency: ")
            result = pms.log_emergency(name, age, gender, problem)
            print(result)

        elif choice == '3':
            reports = pms.get_patient_reports(pat_id)
            print("\n--- Your Reports ---")
            if reports:
                for r in reports:
                    print(f"Date: {r['Date']} | Doctor: {r['Doctor']}")
                    print(f"  Details: {r['Details']}")
            else:
                print("No reports have been uploaded for you yet.")

        elif choice == '4':
            history = pms.get_patient_enquiries()
            print("\n--- Past Appointment History ---")
            if history:
                for h in history:
                    print(f"Date: {h['Date']} | Doctor: {h['Doctor']} | Problem: {h['Problem']} | Status: {h['Status']}")
            else:
                print("No past appointments found.")

        elif choice == '5':
            checkup = pms.get_upcoming_checkup()
            print("\n--- Upcoming Check Up ---")
            if checkup:
                print(f"Date: {checkup['Date']}")
                print(f"Time: {checkup['Time']}")
                print(f"Doctor: Dr. {checkup['Doctor']}")
                print(f"Reason: {checkup['Problem']}")
            else:
                print("You have no upcoming appointments.")
        
        elif choice == '6':
            break

        else:
            print("Invalid choice.")


# --- Main Application Loop ---

def main():
    """Initializes the system and runs the main login loop."""
    pms = PatientManagementSystem()
    print("--- Welcome to the Modular Patient Management System (PMS) CLI ---")
    
    # Initialize basic patient data if needed
    if pms.setup_initial_patient():
         print("Pre-configured Patient Account: Username 'test_patient', Password 'patientpass'.")
    
    # Check if there are doctors/patients, otherwise prompt for setup
    data = load_data()
    if len(data['doctors']) == 0:
        print("\nNote: No doctors found. Please log in as Admin ('admin' / 'adminpass') to add a doctor first.")
        
    while True:
        print("\n--- Login Dashboard ---")
        print("1. Login as Admin")
        print("2. Login as Doctor")
        print("3. Login as Patient")
        print("4. Exit")
        
        choice = input("Enter choice (1-4): ")
        
        if choice == '4':
            print("Thank you for using PMS. Goodbye!")
            break
        
        if choice in ['1', '2', '3']:
            username = input("Enter Username: ")
            password = input("Enter Password: ")

            if pms.login(username, password):
                role = pms.current_user['role']
                print(f"\nLogin successful as {role}!")
                
                if role == 'Admin':
                    admin_menu(pms)
                elif role == 'Doctor':
                    doctor_menu(pms)
                elif role == 'Patient':
                    patient_menu(pms)
                
                # After exiting the menu, reset current user
                pms.current_user = None 
            else:
                print("Login failed: Invalid username or password.")
        else:
            print("Invalid choice, please try again.")

if __name__ == '__main__':
    main()