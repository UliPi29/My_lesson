from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from datetime import datetime

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(200), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='student')
    is_blocked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_teacher(self): return self.role == 'teacher'
    def is_admin(self): return self.role == 'admin'
    def is_student(self): return self.role == 'student'

    def __repr__(self): return f'<User {self.email}>'

class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    author = db.relationship('User', backref=db.backref('courses_created', cascade='all, delete-orphan', lazy=True), lazy=True)
    lessons = db.relationship('Lesson', backref='course', lazy='dynamic', cascade='all, delete-orphan')
    enrollments = db.relationship('Enrollment', backref='course', lazy='dynamic', cascade='all, delete-orphan')

class Lesson(db.Model):
    __tablename__ = 'lessons'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)
    assignment = db.Column(db.Text)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id', ondelete='CASCADE'), nullable=False)
    order_num = db.Column(db.Integer)
    files = db.relationship('File', backref='lesson', lazy='dynamic', cascade='all, delete-orphan')
    submissions = db.relationship('Submission', backref='lesson', lazy='dynamic', cascade='all, delete-orphan')
    test = db.relationship('Test', backref='lesson', uselist=False, cascade='all, delete-orphan')

class Test(db.Model):
    __tablename__ = 'tests'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id', ondelete='CASCADE'), unique=True, nullable=False)
    questions = db.relationship('Question', backref='test', lazy='dynamic', cascade='all, delete-orphan')
    test_results = db.relationship('TestResult', backref='test', lazy='dynamic', cascade='all, delete-orphan')

class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), default='single_choice')
    test_id = db.Column(db.Integer, db.ForeignKey('tests.id', ondelete='CASCADE'), nullable=False)
    answer_options = db.relationship('AnswerOption', backref='question', lazy='dynamic', cascade='all, delete-orphan')

class AnswerOption(db.Model):
    __tablename__ = 'answer_options'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False)

class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id', ondelete='CASCADE'), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('student_id', 'course_id', name='unique_student_course'),)
    student = db.relationship('User', backref=db.backref('enrollments', cascade='all, delete-orphan', lazy=True), lazy=True)

class File(db.Model):
    __tablename__ = 'files'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(256), nullable=False)
    original_name = db.Column(db.String(256))
    file_path = db.Column(db.String(512))
    file_type = db.Column(db.String(20))
    uploader_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id', ondelete='CASCADE'))
    uploader = db.relationship('User', backref=db.backref('files', cascade='all, delete-orphan', lazy=True), lazy=True)
    submission = db.relationship('Submission', backref='file', uselist=False, cascade='all, delete-orphan')

class Submission(db.Model):
    __tablename__ = 'submissions'
    id = db.Column(db.Integer, primary_key=True)
    grade = db.Column(db.Float, nullable=True)
    feedback = db.Column(db.Text)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id', ondelete='CASCADE'), nullable=False)
    file_id = db.Column(db.Integer, db.ForeignKey('files.id', ondelete='CASCADE'), nullable=False)
    student = db.relationship('User', backref=db.backref('submissions', cascade='all, delete-orphan', lazy=True), lazy=True)

class TestResult(db.Model):
    __tablename__ = 'test_results'
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Float)
    total = db.Column(db.Float)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    test_id = db.Column(db.Integer, db.ForeignKey('tests.id', ondelete='CASCADE'), nullable=False)
    student = db.relationship('User', backref=db.backref('test_results', cascade='all, delete-orphan', lazy=True), lazy=True)
    answers = db.relationship('UserAnswer', backref='test_result', lazy='dynamic', cascade='all, delete-orphan')

class UserAnswer(db.Model):
    __tablename__ = 'user_answers'
    id = db.Column(db.Integer, primary_key=True)
    test_result_id = db.Column(db.Integer, db.ForeignKey('test_results.id', ondelete='CASCADE'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False)
    answer_option_id = db.Column(db.Integer, db.ForeignKey('answer_options.id', ondelete='CASCADE'), nullable=False)