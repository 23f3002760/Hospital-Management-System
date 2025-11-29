from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from sqlalchemy import or_
from datetime import datetime, timedelta
from models import db, User, Department, Appointment, Treatment, DoctorAvailability

app = Flask(__name__) 

# --- CONFIGURATION ---
app.config['SECRET_KEY'] = 'Hari'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)    
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Constant for consistent date formatting
DATE_FMT = '%Y-%m-%d'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --- AUTH ROUTES ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        
        # Simple check: Does user exist?
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))

        new_user = User(
            username=request.form.get('username'),
            email=email,
            password=request.form.get('password'),
            role=request.form.get('role')
        )
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

        # Guard Clause 1: User doesn't exist?
        if not user:
            flash('No account found.', 'warning')
            return render_template('login.html')
        
        # Guard Clause 2: Wrong password?
        if user.password != password:
            flash('Incorrect password.', 'danger')
            return render_template('login.html')

        # Guard Clause 3: Account inactive?
        if not user.is_active_user:
            flash('Account deactivated. Contact admin.', 'danger')
            return render_template('login.html')

        # Success!
        login_user(user)
        flash('Login successful!', 'success')

        if user.role == 'admin': return redirect(url_for('admin_dashboard'))
        if user.role == 'doctor': return redirect(url_for('doctor_dashboard'))
        return redirect(url_for('patient_dashboard'))

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# --- GENERAL ROUTES ---

@app.route('/')
def index():
    # Keep it simple: Just show the homepage. 
    # Login handles the redirection to dashboards.
    return render_template('index.html')

@app.route('/departments')
@login_required
def departments():
    return render_template('departments.html', departments=Department.query.all())

@app.route('/department/<int:department_id>')
@login_required
def department_details(department_id):
    dept = db.session.get(Department, department_id)
    doctors = User.query.filter_by(role='doctor', department_id=department_id).all()
    return render_template('department_details.html', department=dept, doctors=doctors)

# --- ADMIN ROUTES ---

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin': return redirect(url_for('index'))

    search = request.args.get('search', '').strip()
    
    # Base queries
    docs = User.query.filter_by(role='doctor')
    pats = User.query.filter_by(role='patient')

    # Simplified Search Logic
    if search:
        search_filter = or_(User.username.ilike(f'%{search}%'), User.email.ilike(f'%{search}%'))
        docs = docs.filter(search_filter)
        pats = pats.filter(search_filter)

    return render_template('admin_dashboard.html', 
                           doctors=docs.all(), 
                           patients=pats.all(), 
                           departments=Department.query.all(), 
                           appointments=Appointment.query.all(),
                           total_appointments=Appointment.query.count())

@app.route('/add_doctor', methods=['GET', 'POST'])
@login_required
def add_doctor():
    if current_user.role != 'admin': return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        if User.query.filter_by(email=email).first():
            flash('Email exists.', 'danger')
        else:
            new_doc = User(
                username=request.form.get('username'),
                email=email,
                password=request.form.get('password'),
                role='doctor',
                department_id=request.form.get('department_id')
            )
            db.session.add(new_doc)
            db.session.commit()
            flash('Doctor added.', 'success')
            return redirect(url_for('admin_dashboard'))

    return render_template('add_doctor.html', departments=Department.query.all())

@app.route('/delete_user/<int:user_id>')
@login_required
def delete_user(user_id):
    if current_user.role != 'admin': return redirect(url_for('index'))
    
    user = db.session.get(User, user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        flash('User deleted.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/toggle_status/<int:user_id>')
@login_required
def toggle_status(user_id):
    if current_user.role != 'admin': return redirect(url_for('index'))

    user = db.session.get(User, user_id)
    if user:
        user.is_active_user = not user.is_active_user
        db.session.commit()
        flash('Status updated.', 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if current_user.role != 'admin' and current_user.id != user_id:
        return redirect(url_for('index'))

    user = db.session.get(User, user_id)
    
    if request.method == 'POST':
        user.username = request.form.get('username')
        user.email = request.form.get('email')
        
        if current_user.role == 'admin' and user.role == 'doctor':
            user.department_id = request.form.get('department_id')
        
        db.session.commit()
        flash('Updated successfully.', 'success')
        
        # Simple Redirect Logic
        if current_user.role == 'admin': return redirect(url_for('admin_dashboard'))
        if current_user.role == 'doctor': return redirect(url_for('doctor_dashboard'))
        return redirect(url_for('patient_dashboard'))

    return render_template('edit_user.html', user=user, departments=Department.query.all())

# --- DOCTOR ROUTES ---

@app.route('/doctor_dashboard')
@login_required
def doctor_dashboard():
    if current_user.role != 'doctor': return redirect(url_for('index'))
    
    appointments = Appointment.query.filter_by(doctor_id=current_user.id, status='Scheduled').all()
    # Simplified list comprehension to get unique patients
    patients = {db.session.get(User, a.patient_id) for a in Appointment.query.filter_by(doctor_id=current_user.id).all()}
    
    return render_template('doctor_dashboard.html', appointments=appointments, patients=list(patients))

@app.route('/doctor/availability', methods=['GET', 'POST'])
@login_required
def doctor_availability():
    if current_user.role != 'doctor':
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        DoctorAvailability.query.filter_by(doctor_id=current_user.id).delete()
        
        selected_slots = request.form.getlist('slots') 
        
        for item in selected_slots:
            # We expect format: "2025-11-29_Morning"
            date_str, slot_type = item.split('_') 
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            new_avail = DoctorAvailability(
                doctor_id=current_user.id,
                available_date=date_obj,
                slot_type=slot_type.capitalize()
            )
            db.session.add(new_avail)
            
        db.session.commit()
        flash('Availability schedule updated successfully!', 'success')
        return redirect(url_for('doctor_dashboard'))
    
    today = datetime.today()
    
    # Output format to %Y-%m-%d (e.g., 2025-11-29 x7)
    days = [(today + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
    
    return render_template('doctor_availability.html', days=days)

@app.route('/appointment/<int:appointment_id>/update', methods=['GET', 'POST'])
@login_required
def update_treatment(appointment_id):
    if current_user.role != 'doctor': return redirect(url_for('index'))
    
    appt = db.session.get(Appointment, appointment_id)
    if not appt or appt.doctor_id != current_user.id: return redirect(url_for('doctor_dashboard'))

    if request.method == 'POST':
        diag = request.form.get('diagnosis')
        pres = request.form.get('prescription')
        notes = f"Tests: {request.form.get('tests_done')}" if request.form.get('tests_done') else ""

        if appt.treatment:
            appt.treatment.diagnosis = diag
            appt.treatment.prescription = pres
            appt.treatment.doctor_notes = notes
        else:
            db.session.add(Treatment(appointment_id=appt.id, diagnosis=diag, prescription=pres, doctor_notes=notes))
            
        db.session.commit()
        return redirect(url_for('doctor_dashboard'))
        
    return render_template('update_treatment.html', appointment=appt, treatment=appt.treatment)

@app.route('/doctor/<int:doctor_id>/details')
@login_required
def doctor_profile(doctor_id):
    doctor = db.session.get(User, doctor_id)
    return render_template('doctor_profile.html', doctor=doctor)

# --- PATIENT ROUTES ---

@app.route('/patient_dashboard')
@login_required
def patient_dashboard():
    if current_user.role != 'patient': return redirect(url_for('index'))
    
    my_appts = Appointment.query.filter_by(patient_id=current_user.id).all()
    return render_template('patient_dashboard.html', departments=Department.query.all(), appointments=my_appts)

@app.route('/patient_history/<int:patient_id>')
@login_required
def patient_history(patient_id):
    if current_user.role not in ['admin', 'doctor'] and current_user.id != patient_id:
        return redirect(url_for('index'))
    return render_template('patient_history.html', patient=db.session.get(User, patient_id), history=Appointment.query.filter_by(patient_id=patient_id).all())


# --- APPOINTMENT OPERATIONS ---

@app.route('/book_appointment/<int:doctor_id>', methods=['GET', 'POST'])
@login_required
def book_appointment(doctor_id):
    doctor = db.session.get(User, doctor_id)
    
    if request.method == 'POST':
        # Simplified Time Logic
        time_str = '09:00' if request.form.get('slot') == 'Morning' else '16:00'
        
        new_appt = Appointment(
            patient_id=current_user.id,
            doctor_id=doctor_id,
            appointment_date=datetime.strptime(request.form.get('date'), DATE_FMT).date(),
            appointment_time=datetime.strptime(time_str, '%H:%M').time(),
            status='Scheduled'
        )
        db.session.add(new_appt)
        db.session.commit()
        flash('Booked!', 'success')
        return redirect(url_for('patient_dashboard'))
    
    availabilities = DoctorAvailability.query.filter(
        DoctorAvailability.doctor_id == doctor_id, 
        DoctorAvailability.available_date >= datetime.today().date()
    ).order_by(DoctorAvailability.available_date).all()
    
    return render_template('book_appointment.html', doctor=doctor, availabilities=availabilities)

@app.route('/appointment/<int:appointment_id>/cancel')
@login_required
def cancel_appointment(appointment_id):
    appt = db.session.get(Appointment, appointment_id)
    if not appt: return redirect(url_for('index'))

    # Check permission (Owner or Doctor)
    if (current_user.role == 'patient' and appt.patient_id == current_user.id) or \
       (current_user.role == 'doctor' and appt.doctor_id == current_user.id):
        appt.status = 'Cancelled'
        db.session.commit()
        flash('Cancelled.', 'info')
    
    return redirect(url_for('doctor_dashboard') if current_user.role == 'doctor' else url_for('patient_dashboard'))

@app.route('/appointment/<int:appointment_id>/reschedule', methods=['GET', 'POST'])
@login_required
def reschedule_appointment(appointment_id):
    # 1. Fetch Appointment & Verify Owner
    appt = db.session.get(Appointment, appointment_id)
    if not appt or appt.patient_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('patient_dashboard'))

    doctor = db.session.get(User, appt.doctor_id)

    if request.method == 'POST':
        # 2. Parse New Date & Time
        new_date_str = request.form.get('date')
        new_slot = request.form.get('slot')
        
        new_date = datetime.strptime(new_date_str, DATE_FMT).date()
        time_str = '09:00' if new_slot == 'Morning' else '16:00'
        new_time = datetime.strptime(time_str, '%H:%M').time()

        # 3. Check for Double Booking
        # We check if *another* appointment exists at this same time
        collision = Appointment.query.filter_by(
            doctor_id=doctor.id,
            appointment_date=new_date,
            appointment_time=new_time,
            status='Scheduled'
        ).first()

        if collision and collision.id != appt.id:
            flash('That slot is already booked. Please choose another.', 'danger')
            return redirect(url_for('reschedule_appointment', appointment_id=appt.id))

        # 4. Update the Appointment
        appt.appointment_date = new_date
        appt.appointment_time = new_time
        db.session.commit()
        
        flash('Appointment rescheduled successfully!', 'success')
        return redirect(url_for('patient_dashboard'))

    # GET: Show available slots so user knows what to pick
    availabilities = DoctorAvailability.query.filter(
        DoctorAvailability.doctor_id == doctor.id,
        DoctorAvailability.available_date >= datetime.today().date()
    ).order_by(DoctorAvailability.available_date).all()

    return render_template('reschedule_appointment.html', appointment=appt, doctor=doctor, availabilities=availabilities)

@app.route('/appointment/<int:appointment_id>/complete')
@login_required
def complete_appointment(appointment_id):
    appt = db.session.get(Appointment, appointment_id)
    if appt and current_user.role == 'doctor' and appt.doctor_id == current_user.id:
        appt.status = 'Completed'
        db.session.commit()
    return redirect(url_for('doctor_dashboard'))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)