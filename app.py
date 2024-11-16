from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename
import os
import webbrowser
import threading
app = Flask(__name__)
app.secret_key = 'm'
from sqlalchemy import event
from sqlalchemy.engine import Engine

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# إعداد قاعدة البيانات
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///clinic.db'  # استخدم مسار مناسب لقاعدة البيانات
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# إعداد مجلد رفع الملفات
UPLOAD_FOLDER = 'static/uploads/'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}  # أنواع الملفات المسموح بها
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
db = SQLAlchemy(app)

# التحقق من امتداد الملف المرفوع
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
#----------------------------------------------------------------------------#
class Patient(db.Model):
    __tablename__ = 'patients'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    address = db.Column(db.String(200), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    social_status = db.Column(db.String(50), nullable=False)
    chronic_diseases = db.Column(db.String(200), nullable=True)
    diagnosis = db.Column(db.String(200), nullable=True)
    previous_medications = db.Column(db.String(200), nullable=True)
    previous_imaging = db.Column(db.String(200), nullable=True)
    previous_tests = db.Column(db.String(200), nullable=True)
    consultations = db.relationship('Consultation', backref='patient', lazy=True, cascade="all, delete-orphan")
    imaging = db.relationship('Imaging', backref='patient', lazy=True, cascade="all, delete-orphan")
    tests = db.relationship('Test', backref='patient', lazy=True, cascade="all, delete-orphan")
    date = db.Column(db.String(20), nullable=False)  # التاريخ
    date = db.Column(db.Date)

    def __repr__(self):
        return f'<Patient {self.name}>'

class Consultation(db.Model):
    __tablename__ = 'consultations'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20), nullable=False)  # التاريخ
    time = db.Column(db.String(5), nullable=False)   # الوقت
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    status = db.Column(db.String(100), nullable=True)  # وضع المريض (مثل: مستقر، يحتاج متابعة)
    notes = db.Column(db.String(200), nullable=True)  # ملاحظات إضافية

    def __repr__(self):
        return f'<Consultation {self.date} {self.time}>'

class Imaging(db.Model):
    __tablename__ = 'imaging'
    id = db.Column(db.Integer, primary_key=True)
    imaging_type = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    result = db.Column(db.String(200), nullable=False)
    file_path = db.Column(db.String(200), nullable=True)  # مسار الملف المرفوع
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)

    def __repr__(self):
        return f'<Imaging {self.imaging_type}>'

class Test(db.Model):
    __tablename__ = 'tests'
    id = db.Column(db.Integer, primary_key=True)
    test_type = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    result = db.Column(db.String(200), nullable=False)
    file_path = db.Column(db.String(200), nullable=True)  # مسار الملف المرفوع
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)

    def __repr__(self):
        return f'<Test {self.test_type}>'
#--------------------------------------------------------------------------------#
@app.route('/add_patient', methods=['GET', 'POST'])
def add_patient():
    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        address = request.form['address']
        gender = request.form['gender']
        social_status = request.form['social_status']
        chronic_diseases = request.form['chronic_diseases']
        diagnosis = request.form['diagnosis']
        previous_medications = request.form['previous_medications']
        previous_imaging = request.form['previous_imaging']
        previous_tests = request.form['previous_tests']
        patient_date = request.form['date']
        new_patient = Patient(name=name, age=age, address=address, gender=gender,
                              social_status=social_status, chronic_diseases=chronic_diseases,
                              diagnosis=diagnosis, previous_medications=previous_medications,
                              previous_imaging=previous_imaging, previous_tests=previous_tests,
                              date=patient_date)

        db.session.add(new_patient)
        db.session.commit()
        return redirect(url_for('index'))

    return render_template('add_patient.html')
#--------------------------------------------------------------------------------#
@app.route('/')
def index():
    patients = Patient.query.all()
    consultations_today = Consultation.query.filter_by(date=datetime.today().strftime('%Y-%m-%d')).all()
    imaging = Imaging.query.all()
    tests = Test.query.all()

    total_patients = len(patients)
    total_consultations = len(consultations_today)
    total_imaging = len(imaging)
    total_tests = len(tests)

    return render_template('index.html', total_patients=total_patients, total_consultations=total_consultations,
                           total_imaging=total_imaging, total_tests=total_tests, patients=patients)
#--------------------------------------------------------------------------------#
@app.route('/add_imaging', methods=['GET', 'POST'])
def add_imaging():
    patients = Patient.query.all()  # للحصول على قائمة المرضى
    if request.method == 'POST':
        patient_id = request.form['patient_id']
        imaging_type = request.form['imaging_type']
        date = request.form['date']
        result = request.form['result']
        
        # معالجة رفع الملف
        file = request.files['file']
        file_path = None

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)  # حفظ الملف في المجلد المحدد

        new_imaging = Imaging(imaging_type=imaging_type, date=date, result=result,
                              file_path=file_path, patient_id=patient_id)
        db.session.add(new_imaging)
        db.session.commit()
        success_message = "تم إضافة الأشعة بنجاح!"
        return redirect(url_for('index'))
    
    return render_template('add_imaging.html', patients=patients)
#--------------------------------------------------------------------------------#
@app.route('/add_consultation', methods=['GET', 'POST'])
def add_consultation():
    if request.method == 'POST':
        patient_id = request.form['patient_id']  # الحصول على patient_id من النموذج
        consultation_date = request.form['date']
        consultation_time = request.form['time']
        status = request.form['status']
        notes = request.form['notes']

        # تحقق إذا كان الوقت مفقوداً
        if not consultation_time:
            flash('الوقت غير موجود!')
            return redirect(url_for('add_consultation'))

        # الحصول على المريض باستخدام patient_id
        patient = Patient.query.get_or_404(patient_id)

        # إضافة الاستشارة للمريض
        consultation = Consultation(date=consultation_date, time=consultation_time, status=status, notes=notes, patient=patient)
        db.session.add(consultation)
        db.session.commit()
        flash('تم إضافة الاستشارة بنجاح!')
        return redirect(url_for('index'))

    # جلب جميع المرضى من قاعدة البيانات
    patients = Patient.query.all()
    
    # تمرير المرضى إلى القالب
    return render_template('add_consultation.html', patients=patients)
#--------------------------------------------------------------------------------#
@app.route('/add_test', methods=['GET', 'POST'])
def add_test():
    patients = Patient.query.all()  # للحصول على قائمة المرضى
    if request.method == 'POST':
        patient_id = request.form['patient_id']
        test_type = request.form['test_type']
        date = request.form['date']
        result = request.form['result']
        
        # معالجة رفع الملف
        file = request.files['test_file']
        file_path = None

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)  # حفظ الملف في المجلد المحدد

        new_test = Test(test_type=test_type, date=date, result=result, file_path=file_path, patient_id=patient_id)
        db.session.add(new_test)
        db.session.commit()
        flash('تم إضافة التحليل بنجاح!')
        return redirect(url_for('index'))
    patients = Patient.query.all()
    return render_template('add_test.html', patients=patients)
#--------------------------------------------------------------------------------#
@app.route('/view_patients', methods=['GET', 'POST'])
def view_patients():
    patients = Patient.query.all()
    search_query = request.args.get('search', '')  # البحث بالاسم
    if search_query:
        patients = Patient.query.filter(Patient.name.ilike(f'%{search_query}%')).all()
    else:
        patients = Patient.query.all()

    return render_template('view_patients.html', patients=patients)
#--------------------------------------------------------------------------------#
@app.route('/reports/<int:patient_id>', methods=['GET', 'POST'])
def reports(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    consultations = Consultation.query.filter_by(patient_id=patient.id).all()
    imaging = Imaging.query.filter_by(patient_id=patient.id).all()
    tests = Test.query.filter_by(patient_id=patient.id).all()

    # إضافة استشارة
    if request.method == 'POST' and 'add_consultation' in request.form:
        date = request.form['date']
        time = request.form['time']
        status = request.form['status']
        notes = request.form['notes']
        new_consultation = Consultation(date=date, time=time, status=status, notes=notes, patient_id=patient.id)
        db.session.add(new_consultation)
        db.session.commit()
        return redirect(url_for('reports', patient_id=patient.id))

    # إضافة إشاعة
    if request.method == 'POST' and 'add_imaging' in request.form:
        imaging_type = request.form['imaging_type']
        date = request.form['date']
        result = request.form['result']
        new_imaging = Imaging(imaging_type=imaging_type, date=date, result=result, patient_id=patient.id)
        db.session.add(new_imaging)
        db.session.commit()
        return redirect(url_for('reports', patient_id=patient.id))

    # إضافة تحليل
    if request.method == 'POST' and 'add_test' in request.form:
        test_type = request.form['test_type']
        date = request.form['date']
        result = request.form['result']
        new_test = Test(test_type=test_type, date=date, result=result, patient_id=patient.id)
        db.session.add(new_test)
        db.session.commit()
        return redirect(url_for('reports', patient_id=patient.id))

    return render_template('reports.html', patient=patient,
                           consultations=consultations, imaging=imaging, tests=tests)
# --------------------------------------------------------------------------------#
# Edit Patient
@app.route('/patient/edit/<int:patient_id>', methods=['GET', 'POST'])
def edit_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    if request.method == 'POST':
        patient.name = request.form['name']
        patient.age = request.form['age']
        patient.address = request.form['address']
        patient.gender = request.form['gender']
        patient.social_status = request.form['social_status']
        patient.chronic_diseases = request.form['chronic_diseases']
        patient.diagnosis = request.form['diagnosis']
        patient.previous_medications = request.form['previous_medications']
        patient.previous_imaging = request.form['previous_imaging']
        patient.previous_tests = request.form['previous_tests']
        patient.date = request.form['date']
        db.session.commit()
        flash('Patient details updated successfully!', 'success')
        return redirect(url_for('reports', patient_id=patient.id))
    return render_template('edit_patient.html', patient=patient)

@app.route('/patient/delete/<int:patient_id>', methods=['POST'])
def delete_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    try:
        db.session.delete(patient)
        db.session.commit()
        flash('تم حذف المريض بنجاح!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ أثناء حذف المريض.', 'danger')
        print(f"Error deleting Patient: {e}")  # For debugging purposes
    return redirect(url_for('view_patients'))

#--------------------------------------------------------------------------------#
def open_browser():
    webbrowser.open("http://127.0.0.1:5000")
#--------------------------------------------------------------------------------#
with app.app_context():
    db.create_all()
if __name__ == '__main__':
    threading.Timer(1, open_browser).start()
    app.run(debug=True,use_reloader=False,host='0.0.0.0', port=5000)
