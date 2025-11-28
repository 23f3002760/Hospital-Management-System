from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# Initializing the database
db = SQLAlchemy()

class User(db.Model, UserMixin):
    """
    User Table: Stores login credentials and profile info for all roles.
    Roles: 'admin', 'doctor', 'patient'
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False) # admin, doctor, patient
    phone_number = db.Column(db.String(15), nullable=True)
    
    # NEW: Status field for Blacklisting
    is_active_user = db.Column(db.Boolean, default=True) 
    
    # Specific for Doctors (Foreign Key to Department)
    # This will be NULL for Patients and Admins as they have no department
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    
    # Relationships
    # 'appointments_doctor' fetches all appointments where this user is the doctor
    # 'appointments_patient' fetches all appointments where this user is the patient
    doctor_appointments = db.relationship('Appointment', foreign_keys='Appointment.doctor_id', backref='doctor_ref', lazy=True)
    patient_appointments = db.relationship('Appointment', foreign_keys='Appointment.patient_id', backref='patient_ref', lazy=True)

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"

class Department(db.Model):
    """
    Department Table: Stores medical specializations (e.g., Cardiology, Neurology).
    """
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Relationship to link Doctors to this department
    doctors = db.relationship('User', backref='department', lazy=True)

    def __repr__(self):
        return f"<Department {self.name}>"

class Appointment(db.Model):
    """
    Appointment Table: Handles scheduling between a Patient and a Doctor.
    """
    __tablename__ = 'appointments'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Keys
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Scheduling Details
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), default='Pending') # Pending, Completed, Cancelled
    
    # Relationship to Treatment (One-to-One)
    treatment = db.relationship('Treatment', backref='appointment', uselist=False, lazy=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Appointment {self.id} - {self.status}>"

class Treatment(db.Model):
    """
    Treatment Table: Stores medical records for a completed appointment.
    """
    __tablename__ = 'treatments'
    
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=False)
    
    diagnosis = db.Column(db.Text, nullable=False)
    prescription = db.Column(db.Text, nullable=False)
    doctor_notes = db.Column(db.Text, nullable=True)
    
    date_recorded = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Treatment for Appt {self.appointment_id}>"