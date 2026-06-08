from flask import abort, render_template, Blueprint, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app.models import Enrollment, Lesson, TestResult, Course, File, Submission, Test, Question, AnswerOption, UserAnswer
from werkzeug.utils import secure_filename
import uuid, os
from sqlalchemy import func
from app import db
from app.storage import upload_file
from app.routes.calc_student import calc_student_avg, calc_student_progress

bp = Blueprint('student', __name__, url_prefix='/student')


@bp.route('/my_courses')
@login_required
def my_courses():
    """Отображает список курсов, на которые записан студент, с прогрессом и средним баллом."""
    if not current_user.is_student(): abort(403)
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    courses_data = []
    for enr in enrollments:
        course = enr.course
        progress = calc_student_progress(current_user.id, course)
        avg = calc_student_avg(current_user.id, course)
        completed = 0
        for lesson in course.lessons:
            lesson_done = True
            if lesson.test:
                if not TestResult.query.filter_by(student_id=current_user.id, test_id=lesson.test.id).first():
                    lesson_done = False
            if lesson.assignment and lesson.assignment.strip():
                if not Submission.query.filter_by(student_id=current_user.id, lesson_id=lesson.id).first():
                    lesson_done = False
            if lesson_done:
                completed += 1
        courses_data.append({
            'course': course,
            'completed_lessons': completed,
            'total_lessons': course.lessons.count(),
            'progress': progress,
            'avg': avg
        })
    return render_template('student/my_courses.html', courses=courses_data)


@bp.route('/course/<int:course_id>')
@login_required
def course_detail(course_id):
    """Показывает страницу курса со списком уроков и статусом их выполнения."""
    course = Course.query.get_or_404(course_id)
    if not Enrollment.query.filter_by(student_id=current_user.id, course_id=course_id).first() and not current_user.is_admin():
        abort(403)
    lessons = course.lessons.order_by(Lesson.order_num).all()
    lesson_progress = {}
    for lesson in lessons:
        lesson_done = True
        if lesson.test:
            if not TestResult.query.filter_by(student_id=current_user.id, test_id=lesson.test.id).first():
                lesson_done = False
        if lesson.assignment and lesson.assignment.strip():
            if not Submission.query.filter_by(student_id=current_user.id, lesson_id=lesson.id).first():
                lesson_done = False
        lesson_progress[lesson.id] = lesson_done
    return render_template('student/course_detail.html', course=course, lessons=lessons, lesson_progress=lesson_progress)


@bp.route('/course/<int:course_id>/lessons/<int:lesson_id>')
@login_required
def lesson_view(course_id, lesson_id):
    """Отображает содержимое урока (материалы, тест, задание) в зависимости от выбранной вкладки."""
    lesson = Lesson.query.get_or_404(lesson_id)
    if lesson.course_id != course_id: abort(404)
    tab = request.args.get('tab', 'materials')
    materials = File.query.filter_by(lesson_id=lesson_id, file_type='material').all()
    test = lesson.test
    submission = Submission.query.filter_by(student_id=current_user.id, lesson_id=lesson_id).first()
    return render_template('student/lesson_view.html', lesson=lesson, tab=tab, materials=materials, test=test, submission=submission)


@bp.route('/lesson/<int:lesson_id>/test/take', methods=['GET', 'POST'])
@login_required
def take_test(lesson_id):
    """Обрабатывает прохождение теста: GET — показывает вопросы, POST — проверяет и сохраняет результат."""
    lesson = Lesson.query.get_or_404(lesson_id)
    test = lesson.test
    if not test: abort(404)
    if request.method == 'POST':
        score = 0
        total = len(test.questions.all())
        old_result = TestResult.query.filter_by(student_id=current_user.id, test_id=test.id).first()
        if old_result:
            UserAnswer.query.filter_by(test_result_id=old_result.id).delete()
            db.session.delete(old_result)
            db.session.commit()
        result = TestResult(student_id=current_user.id, test_id=test.id, score=0, total=total)
        db.session.add(result)
        db.session.commit()
        for q in test.questions:
            selected = request.form.getlist(f'q_{q.id}')
            selected = [int(s) for s in selected]
            correct = [ao.id for ao in q.answer_options if ao.is_correct]
            for ans_id in selected:
                ua = UserAnswer(test_result_id=result.id, question_id=q.id, answer_option_id=ans_id)
                db.session.add(ua)
            if set(selected) == set(correct):
                score += 1
        result.score = score
        db.session.commit()
        flash(f'Тест завершён. Результат: {score}/{total}', 'success')
        return redirect(url_for('student.lesson_view', course_id=lesson.course_id, lesson_id=lesson_id, tab='test'))
    return render_template('student/take_test.html', test=test)


@bp.route('/lesson/<int:lesson_id>/submit', methods=['POST'])
@login_required
def submit_assignment(lesson_id):
    """Принимает загруженный файл с заданием и сохраняет его как ответ студента."""
    lesson = Lesson.query.get_or_404(lesson_id)
    if 'file' not in request.files:
        flash('Нет файла', 'danger')
        return redirect(url_for('student.lesson_view', course_id=lesson.course_id, lesson_id=lesson.id, tab='assignment'))
    file = request.files['file']
    if file.filename == '':
        flash('Файл не выбран', 'warning')
        return redirect(url_for('student.lesson_view', course_id=lesson.course_id, lesson_id=lesson.id, tab='assignment'))
    original_name = file.filename
    safe = secure_filename(original_name)
    ext = os.path.splitext(safe)[1] or os.path.splitext(original_name)[1]
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = upload_file(file, unique_name)
    db_file = File(filename=unique_name, original_name=original_name, file_path=file_path, file_type='submission', uploader_id=current_user.id, lesson_id=lesson.id)
    db.session.add(db_file)
    db.session.commit()
    sub = Submission.query.filter_by(student_id=current_user.id, lesson_id=lesson_id).first()
    if sub:
        sub.file_id = db_file.id
        sub.grade = None
        sub.feedback = None
    else:
        sub = Submission(student_id=current_user.id, lesson_id=lesson_id, file_id=db_file.id)
        db.session.add(sub)
    db.session.commit()
    flash(f'Файл «{original_name}» успешно отправлен', 'success')
    return redirect(url_for('student.lesson_view', course_id=lesson.course_id, lesson_id=lesson.id, tab='assignment'))


@bp.route('/profile')
@login_required
def profile():
    """Показывает личную статистику студента по всем курсам (успеваемость и прогресс)."""
    if not current_user.is_student(): abort(403)
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    stats = []
    for enr in enrollments:
        course = enr.course
        completed = 0
        for lesson in course.lessons:
            lesson_done = True
            if lesson.test:
                if not TestResult.query.filter_by(student_id=current_user.id, test_id=lesson.test.id).first():
                    lesson_done = False
            if lesson.assignment and lesson.assignment.strip():
                if not Submission.query.filter_by(student_id=current_user.id, lesson_id=lesson.id).first():
                    lesson_done = False
            if lesson_done:
                completed += 1
        avg = calc_student_avg(current_user.id, course)
        stats.append({'course': course, 'completed': completed, 'total': course.lessons.count(), 'avg': avg})
    return render_template('student/profile.html', stats=stats)