from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, User, Department, Appointment, Treatment
from sqlalchemy import or_

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

@app.route('/')
def index():
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
            flash('No account found.', 'warning')
            return render_template('login.html')
        
        # Check if user is blacklisted
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
            flash('Incorrect password.', 'danger')
            return render_template('login.html')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out.', 'info')
    return redirect(url_for('login'))

# --- ADMIN DASHBOARD ---
@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    search_query = request.args.get('search', '').strip()
    
    if search_query:
        # Filter Doctors
        doctors = User.query.filter(
            User.role == 'doctor',
            or_(
                User.username.ilike(f'%{search_query}%'),
                User.email.ilike(f'%{search_query}%')
            )
        ).all()
        # Filter Patients
        patients = User.query.filter(
            User.role == 'patient',
            or_(
                User.username.ilike(f'%{search_query}%'),
                User.email.ilike(f'%{search_query}%')
            )
        ).all()
    else:
        doctors = User.query.filter_by(role='doctor').all()
        patients = User.query.filter_by(role='patient').all()

    departments = Department.query.all()
    appointments = Appointment.query.all()
    total_appointments = len(appointments)

    return render_template('admin_dashboard.html', 
                           doctors=doctors, 
                           patients=patients, 
                           departments=departments,
                           appointments=appointments,
                           total_appointments=total_appointments)

# --- Add Doctor Route ---
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
            flash('Email exists.', 'danger')
            return redirect(url_for('add_doctor'))
        new_doctor = User(username=username, email=email, password=password, role='doctor', department_id=department_id)
        db.session.add(new_doctor)
        db.session.commit()
        flash('Doctor added.', 'success')
        return redirect(url_for('admin_dashboard'))
    departments = Department.query.all()
    return render_template('add_doctor.html', departments=departments)

# --- Delete User Route ---
@app.route('/delete_user/<int:user_id>')
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    user = db.session.get(User, user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        flash('User removed.', 'success')
    return redirect(url_for('admin_dashboard'))

# --- Edit User Route ---
@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    user = db.session.get(User, user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        user.username = request.form.get('username')
        user.email = request.form.get('email')
        if user.role == 'doctor':
            user.department_id = request.form.get('department_id')
        
        db.session.commit()
        flash('User updated successfully.', 'success')
        return redirect(url_for('admin_dashboard'))

    departments = Department.query.all()
    return render_template('edit_user.html', user=user, departments=departments)

# --- Toggle Status (Blacklist) Route ---
@app.route('/toggle_status/<int:user_id>')
@login_required
def toggle_status(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    user = db.session.get(User, user_id)
    if user:
        user.is_active_user = not user.is_active_user # Toggle True/False
        db.session.commit()
        status = "Activated" if user.is_active_user else "Blacklisted"
        flash(f'User {status} successfully.', 'info')
    
    return redirect(url_for('admin_dashboard'))

# --- Patient History Route ---
@app.route('/patient_history/<int:patient_id>')
@login_required
def patient_history(patient_id):
    if current_user.role not in ['admin', 'doctor']:
        return redirect(url_for('index'))
    patient = db.session.get(User, patient_id)
    history = Appointment.query.filter_by(patient_id=patient_id).all()
    return render_template('patient_history.html', patient=patient, history=history)

# --- Doctor Dashboard ---
@app.route('/doctor_dashboard')
@login_required
def doctor_dashboard(): return "Doctor Dashboard"

# --- Patient Dashboard ---
@app.route('/patient_dashboard')
@login_required
def patient_dashboard(): return "Patient Dashboard"

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)