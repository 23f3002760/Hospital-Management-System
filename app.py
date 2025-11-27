from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Department, Appointment, Treatment

app = Flask(__name__)

app.config['SECRET_KEY'] = 'Hari'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Where to send users if they try to access a private page

@login_manager.user_loader
def load_user(user_id):
    """Reloads the user object from the user ID stored in the session."""
    # UPDATED: Use db.session.get() to avoid the LegacyAPIWarning
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

        # Checks if atleast one user already exists
        user_exists = User.query.filter_by(email=email).first()
        if user_exists:
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))

        # Create new user
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

        # If user not found 
        if not user:
            flash('No account found with this email. You can register as a new user.', 'warning')
            return render_template('login.html')

        # Plain password check 
        if user.password == password:
            login_user(user)
            flash('Login successful!', 'success')

            # Redirect based on role
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

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    return "Admin Dashboard"

@app.route('/doctor_dashboard')
@login_required
def doctor_dashboard():
    return "Doctor Dashboard"

@app.route('/patient_dashboard')
@login_required
def patient_dashboard():
    return "Patient Dashboard"

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Creates the db if it doesn't exist
    app.run(debug=True)