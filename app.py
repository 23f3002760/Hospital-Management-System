from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from sqlalchemy import or_
from datetime import datetime, timedelta
from models import db, User, Department, Appointment, Treatment

app = Flask(__name__)

app.config['SECRET_KEY'] = 'Hari'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --- MAIN ROUTES ---

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'doctor':
            return redirect(url_for('doctor_dashboard'))
        elif current_user.role == 'patient':
            return redirect(url_for('patient_dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        user_exists = User.query.filter_by(email=email).first()
        if user_exists:
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))

        new_user = User(username=username, email=email, password=password, role=role)
        db.session.add(new_user)
        db.session.commit()

        flash('Account created! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if not user:
            flash('No account found with this email. You can register as a new user.', 'warning')
            return render_template('login.html')
        
        if not user.is_active_user:
            flash('Your account has been deactivated. Contact admin.', 'danger')
            return render_template('login.html')

        if user.password == password:
            login_user(user)
            flash('Login successful!', 'success')

            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'doctor':
                return redirect(url_for('doctor_dashboard'))
            else:
                return redirect(url_for('patient_dashboard'))
        else:
            flash('Incorrect password. Try again.', 'danger')
            return render_template('login.html')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# --- ADMIN ROUTES ---

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('index'))

    search_query = request.args.get('search', '').strip()
    
    if search_query:
        doctors = User.query.filter(User.role == 'doctor', or_(User.username.ilike(f'%{search_query}%'), User.email.ilike(f'%{search_query}%'))).all()
        patients = User.query.filter(User.role == 'patient', or_(User.username.ilike(f'%{search_query}%'), User.email.ilike(f'%{search_query}%'))).all()
    else:
        doctors = User.query.filter_by(role='doctor').all()
        patients = User.query.filter_by(role='patient').all()

    departments = Department.query.all()
    appointments = Appointment.query.all()
    total_appointments = len(appointments)

    return render_template('admin_dashboard.html', doctors=doctors, patients=patients, departments=departments, appointments=appointments, total_appointments=total_appointments)

@app.route('/add_doctor', methods=['GET', 'POST'])
@login_required
def add_doctor():
    if current_user.role != 'admin':
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        department_id = request.form.get('department_id')

        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'danger')
            return redirect(url_for('add_doctor'))

        new_doctor = User(username=username, email=email, password=password, role='doctor', department_id=department_id)
        db.session.add(new_doctor)
        db.session.commit()
        
        flash('Doctor added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    departments = Department.query.all()
    return render_template('add_doctor.html', departments=departments)

@app.route('/delete_user/<int:user_id>')
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    user = db.session.get(User, user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        flash('User removed successfully.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    user = db.session.get(User, user_id)
    
    if request.method == 'POST':
        user.username = request.form.get('username')
        user.email = request.form.get('email')
        if user.role == 'doctor':
            user.department_id = request.form.get('department_id')
        db.session.commit()
        flash('User updated.', 'success')
        return redirect(url_for('admin_dashboard'))
    
    departments = Department.query.all()
    return render_template('edit_user.html', user=user, departments=departments)

@app.route('/toggle_status/<int:user_id>')
@login_required
def toggle_status(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    user = db.session.get(User, user_id)
    if user:
        user.is_active_user = not user.is_active_user
        db.session.commit()
        flash('User status updated.', 'info')
    return redirect(url_for('admin_dashboard'))

# --- DOCTOR ROUTES ---

@app.route('/doctor_dashboard')
@login_required
def doctor_dashboard():
    if current_user.role != 'doctor':
        return redirect(url_for('index'))
    
    appointments = Appointment.query.filter(
        Appointment.doctor_id == current_user.id,
        Appointment.status == 'Scheduled'
    ).all()
    
    patient_ids = set([appt.patient_id for appt in Appointment.query.filter_by(doctor_id=current_user.id).all()])
    patients = [db.session.get(User, pid) for pid in patient_ids]

    return render_template('doctor_dashboard.html', appointments=appointments, patients=patients)

@app.route('/appointment/<int:appointment_id>/update', methods=['GET', 'POST'])
@login_required
def update_treatment(appointment_id):
    if current_user.role != 'doctor':
        return redirect(url_for('index'))
        
    appointment = db.session.get(Appointment, appointment_id)
    if not appointment or appointment.doctor_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('doctor_dashboard'))
        
    treatment = appointment.treatment 
    
    if request.method == 'POST':
        diagnosis = request.form.get('diagnosis')
        prescription = request.form.get('prescription')
        tests = request.form.get('tests_done') 
        
        notes = f"Tests Done: {tests}" if tests else ""
        
        if treatment:
            treatment.diagnosis = diagnosis
            treatment.prescription = prescription
            treatment.doctor_notes = notes
        else:
            new_treatment = Treatment(
                appointment_id=appointment.id,
                diagnosis=diagnosis,
                prescription=prescription,
                doctor_notes=notes
            )
            db.session.add(new_treatment)
            
        db.session.commit()
        flash('Treatment details updated successfully.', 'success')
        return redirect(url_for('doctor_dashboard'))
        
    return render_template('update_treatment.html', appointment=appointment, treatment=treatment)

@app.route('/doctor/availability', methods=['GET', 'POST'])
@login_required
def doctor_availability():
    if current_user.role != 'doctor':
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        selected_slots = request.form.getlist('slots')
        # In a real app, save these slots to DB
        flash(f'Availability updated! {len(selected_slots)} slots opened.', 'success')
        return redirect(url_for('doctor_dashboard'))
    
    today = datetime.today()
    days = [(today + timedelta(days=i)).strftime('%d/%m/%Y') for i in range(7)]
    
    return render_template('doctor_availability.html', days=days)

@app.route('/appointment/<int:appointment_id>/complete')
@login_required
def complete_appointment(appointment_id):
    if current_user.role != 'doctor':
        return redirect(url_for('index'))
        
    appointment = db.session.get(Appointment, appointment_id)
    if appointment and appointment.doctor_id == current_user.id:
        appointment.status = 'Completed'
        db.session.commit()
        flash('Appointment marked as complete.', 'success')
        
    return redirect(url_for('doctor_dashboard'))

@app.route('/appointment/<int:appointment_id>/cancel')
@login_required
def cancel_appointment(appointment_id):
    if current_user.role != 'doctor':
        return redirect(url_for('index'))
        
    appointment = db.session.get(Appointment, appointment_id)
    if appointment and appointment.doctor_id == current_user.id:
        appointment.status = 'Cancelled'
        db.session.commit()
        flash('Appointment cancelled.', 'warning')
        
    return redirect(url_for('doctor_dashboard'))

# --- SHARED / PATIENT ROUTES ---

@app.route('/patient_history/<int:patient_id>')
@login_required
def patient_history(patient_id):
    if current_user.role not in ['admin', 'doctor'] and current_user.id != patient_id:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    patient = db.session.get(User, patient_id)
    history = Appointment.query.filter_by(patient_id=patient_id).all()
    return render_template('patient_history.html', patient=patient, history=history)

@app.route('/patient_dashboard')
@login_required
def patient_dashboard():
    if current_user.role != 'patient':
        return redirect(url_for('index'))
    return render_template('patient_dashboard.html')

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)