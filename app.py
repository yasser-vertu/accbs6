# app.py

from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail, Message
from config import Config
from database_setup import db, User, Client, Specification
from utils import days_since_grant, generate_certificate_number, send_email_notification, export_clients_to_excel
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
migrate = Migrate(app, db)
mail = Mail(app)

# ------------------ Routes ------------------

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# تسجيل الدخول
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('dashboard'))
        else:
            flash('اسم المستخدم أو كلمة المرور خاطئة', 'danger')
    return render_template('login.html')

# تسجيل الخروج
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# لوحة التحكم
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    total_clients = Client.query.count()
    near_expiry = Client.query.filter(Client.grant_date != None).all()
    alert_clients = [c for c in near_expiry if days_since_grant(c.grant_date) >= 300]
    return render_template('dashboard.html', total_clients=total_clients, alert_clients=alert_clients)

# إدارة المستخدمين
@app.route('/users')
def users():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    all_users = User.query.all()
    return render_template('users.html', users=all_users)

# تغيير كلمة المرور
@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        new_password = request.form['new_password']
        user.password = new_password
        db.session.commit()
        flash('تم تحديث كلمة المرور', 'success')
        return redirect(url_for('dashboard'))
    return render_template('change_password.html')

# إدارة العملاء
@app.route('/clients')
def clients():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    all_clients = Client.query.all()
    return render_template('clients.html', clients=all_clients)

# إضافة/تعديل العميل
@app.route('/client_form', methods=['GET', 'POST'])
def client_form():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        company_name = request.form['company_name']
        email = request.form['email']
        specification_id = request.form['specification_id']
        spec = Specification.query.get(specification_id)
        cert_number = generate_certificate_number(spec.last_certificate_number)
        spec.last_certificate_number = cert_number
        new_client = Client(
            company_name=company_name,
            email=email,
            specification_id=spec.id,
            certificate_number=cert_number
        )
        db.session.add(new_client)
        db.session.commit()
        flash('تم حفظ بيانات العميل', 'success')
        return redirect(url_for('clients'))
    specs = Specification.query.all()
    return render_template('client_form.html', specs=specs)

# تصدير العملاء
@app.route('/export_clients')
def export_clients():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    clients = Client.query.all()
    filename = export_clients_to_excel(clients)
    return f"تم تصدير البيانات إلى {filename}"

if __name__ == '__main__':
    app.run(debug=True)