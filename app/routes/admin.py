from flask import render_template, Blueprint, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import User, Course, Enrollment, TestResult, Submission, Lesson
from app.forms import ChangePasswordForm
from app import db

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.before_request
def check_admin():
    if not current_user.is_admin():
        return "Доступ запрещён", 403

@bp.route('/users')
@login_required
def users():
    query = User.query.filter(User.id != current_user.id)

    role = request.args.get('role')
    if role and role in ('student', 'teacher', 'admin'):
        query = query.filter_by(role=role)

    status = request.args.get('status')
    if status == 'active':
        query = query.filter_by(is_blocked=False)
    elif status == 'blocked':
        query = query.filter_by(is_blocked=True)

    users = query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users, role=role, status=status)

@bp.route('/users/create', methods=['GET', 'POST'])
@login_required
def create_user():
    if request.method == 'POST':
        email = request.form.get('email')
        role = request.form.get('role', 'teacher')
        if role not in ('teacher', 'admin'):
            flash('Можно создать только учителя или администратора', 'danger')
            return redirect(url_for('admin.create_user'))
        if User.query.filter_by(email=email).first():
            flash('Email занят', 'danger')
            return redirect(url_for('admin.create_user'))
        user = User(
            full_name=request.form.get('full_name'),
            email=email,
            role=role
        )
        user.set_password(request.form.get('password'))
        db.session.add(user)
        db.session.commit()
        flash('Пользователь создан', 'success')
        return redirect(url_for('admin.users'))
    return render_template('admin/create_user.html')

@bp.route('/users/<int:user_id>/toggle_block')
@login_required
def toggle_block(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'admin': flash('Администратора нельзя заблокировать', 'warning')
    else:
        user.is_blocked = not user.is_blocked
        db.session.commit()
        flash('Статус изменён', 'success')
    return redirect(url_for('admin.users'))

@bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'admin': flash('Нельзя удалить админа', 'warning')
    else:
        db.session.delete(user)
        db.session.commit()
        flash('Пользователь удалён', 'success')
    return redirect(url_for('admin.users'))

@bp.route('/courses')
@login_required
def courses():
    query = Course.query
    search = request.args.get('q', '').strip()
    if search:
        query = query.filter(
            db.or_(
                Course.title.ilike(f'%{search}%'),
                Course.author.has(User.full_name.ilike(f'%{search}%')),
                Course.author.has(User.email.ilike(f'%{search}%'))
            )
        )
    courses = query.order_by(Course.created_at.desc()).all()
    return render_template('admin/courses.html', courses=courses, search=search)

@bp.route('/statistics')
@login_required
def statistics():
    total_users = User.query.count()
    admins = User.query.filter_by(role='admin').count()
    teachers = User.query.filter_by(role='teacher').count()
    students = User.query.filter_by(role='student').count()
    total_courses = Course.query.count()

    active_avgs = []
    for student in User.query.filter_by(role='student').all():
        total_score = 0
        items = 0
        for enr in student.enrollments:
            course = enr.course
            for lesson in course.lessons:
                if lesson.test:
                    res = TestResult.query.filter_by(student_id=student.id, test_id=lesson.test.id).first()
                    if res and res.total > 0:
                        total_score += (res.score / res.total * 5)
                        items += 1
                sub = Submission.query.filter_by(student_id=student.id, lesson_id=lesson.id).first()
                if sub and sub.grade is not None:
                    total_score += sub.grade
                    items += 1
        if items > 0:
            active_avgs.append(total_score / items)

    avg_score = round(sum(active_avgs) / len(active_avgs), 2) if active_avgs else 0

    return render_template('admin/statistics.html', 
                           total_users=total_users, admins=admins, teachers=teachers, students=students,
                           total_courses=total_courses, avg_score=avg_score)

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash('Пароль изменён', 'success')
        else:
            flash('Неверный пароль', 'danger')
    return render_template('admin/profile.html', form=form)