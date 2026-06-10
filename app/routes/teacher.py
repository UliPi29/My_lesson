import uuid, os
from flask import render_template, Blueprint, current_app, redirect, url_for, flash, abort, send_from_directory, request
from flask_login import login_required, current_user
from app.models import Lesson, File, Test, Question, AnswerOption, Course, Enrollment, Submission, TestResult, User
from app.forms import ChangePasswordForm, CourseForm, GradeForm, LessonForm
from werkzeug.utils import secure_filename
from app import db
from app.storage import upload_file, delete_file as storage_delete
from app.routes.calc_student import calc_student_avg, calc_student_progress

bp = Blueprint('teacher', __name__, url_prefix='/teacher')


@bp.route('/my_courses')
@login_required
def my_courses():
    """Отображает список курсов, созданных учителем (или все курсы для администратора)."""
    if not current_user.is_teacher() and not current_user.is_admin():
        abort(403)
    if current_user.is_admin():
        courses = Course.query.order_by(Course.created_at.desc()).all()
    else:
        courses = Course.query.filter_by(author_id=current_user.id).order_by(Course.created_at.desc()).all()
    return render_template('teacher/my_courses.html', courses=courses)


@bp.route('/create_course', methods=['GET', 'POST'])
@login_required
def create_course():
    """Создаёт новый курс (доступно учителю или администратору)."""
    if not current_user.is_teacher() and not current_user.is_admin():
        abort(403)
    form = CourseForm()
    if form.validate_on_submit():
        course = Course(title=form.title.data, author_id=current_user.id)
        db.session.add(course)
        db.session.commit()
        flash('Курс создан', 'success')
        return redirect(url_for('teacher.my_courses'))
    return render_template('teacher/course_form.html', form=form, course=None)


@bp.route('/edit_course/<int:course_id>', methods=['GET', 'POST'])
@login_required
def edit_course(course_id):
    """Редактирует название курса."""
    course = Course.query.get_or_404(course_id)
    if course.author_id != current_user.id and not current_user.is_admin():
        abort(403)
    form = CourseForm(obj=course)
    if form.validate_on_submit():
        course.title = form.title.data
        db.session.commit()
        flash('Курс обновлён', 'success')
        return redirect(url_for('teacher.my_courses'))
    return render_template('teacher/course_form.html', form=form, course=course)


@bp.route('/delete_course/<int:course_id>', methods=['POST'])
@login_required
def delete_course(course_id):
    """Удаляет курс."""
    course = Course.query.get_or_404(course_id)
    if course.author_id != current_user.id and not current_user.is_admin():
        abort(403)
    db.session.delete(course)
    db.session.commit()
    flash('Курс удалён', 'success')
    return redirect(url_for('teacher.my_courses'))


@bp.route('/course/<int:course_id>/lessons')
@login_required
def course_lessons(course_id):
    """Показывает список уроков курса с возможностью управления."""
    course = Course.query.get_or_404(course_id)
    if course.author_id != current_user.id and not current_user.is_admin():
        abort(403)
    lessons = course.lessons.order_by(Lesson.order_num).all()
    return render_template('teacher/course_lessons.html', course=course, lessons=lessons)


@bp.route('/course/<int:course_id>/create_lesson', methods=['GET', 'POST'])
@login_required
def create_lesson(course_id):
    """Создаёт новый урок в указанном курсе."""
    course = Course.query.get_or_404(course_id)
    if course.author_id != current_user.id:
        abort(403)
    form = LessonForm()
    if form.validate_on_submit():
        lesson = Lesson(
            title=form.title.data,
            content=form.content.data,
            assignment=form.assignment.data,
            course_id=course.id,
            order_num=form.order_num.data or (course.lessons.count() + 1)
        )
        db.session.add(lesson)
        db.session.commit()
        flash('Урок создан', 'success')
        return redirect(url_for('teacher.course_lessons', course_id=course.id))
    return render_template('teacher/lesson_form.html', form=form, course=course, lesson=None)


@bp.route('/edit_lesson/<int:lesson_id>', methods=['GET', 'POST'])
@login_required
def edit_lesson(lesson_id):
    """Редактирует заголовок, содержание, задание и порядок урока."""
    lesson = Lesson.query.get_or_404(lesson_id)
    if lesson.course.author_id != current_user.id and not current_user.is_admin():
        abort(403)
    form = LessonForm(obj=lesson)
    if form.validate_on_submit():
        lesson.title = form.title.data
        lesson.content = form.content.data
        lesson.assignment = form.assignment.data
        lesson.order_num = form.order_num.data
        db.session.commit()
        flash('Урок обновлён', 'success')
        return redirect(url_for('teacher.course_lessons', course_id=lesson.course_id))
    return render_template('teacher/lesson_form.html', form=form, lesson=lesson, course=None)


@bp.route('/delete_lesson/<int:lesson_id>', methods=['POST'])
@login_required
def delete_lesson(lesson_id):
    """Удаляет урок."""
    lesson = Lesson.query.get_or_404(lesson_id)
    course_id = lesson.course_id
    if lesson.course.author_id != current_user.id and not current_user.is_admin():
        abort(403)
    db.session.delete(lesson)
    db.session.commit()
    flash('Урок удалён', 'success')
    return redirect(url_for('teacher.course_lessons', course_id=course_id))


@bp.route('/lesson/<int:lesson_id>/materials', methods=['GET', 'POST'])
@login_required
def lesson_materials(lesson_id):
    """Управляет учебными материалами урока (загрузка, просмотр, удаление)."""
    lesson = Lesson.query.get_or_404(lesson_id)
    if lesson.course.author_id != current_user.id and not current_user.is_admin():
        abort(403)
    if request.method == 'POST':
        uploaded = request.files.get('file')
        if uploaded and uploaded.filename:
            original_name = uploaded.filename
            safe = secure_filename(original_name)
            ext = os.path.splitext(safe)[1] or os.path.splitext(original_name)[1]
            unique_name = f"{uuid.uuid4().hex}{ext}"
            file_path = upload_file(uploaded, unique_name)
            new_file = File(
                filename=unique_name,
                original_name=original_name,
                file_path=file_path,
                file_type='material',
                uploader_id=current_user.id,
                lesson_id=lesson.id
            )
            db.session.add(new_file)
            db.session.commit()
            flash('Файл загружен', 'success')
        return redirect(url_for('teacher.lesson_materials', lesson_id=lesson.id))
    files = File.query.filter_by(lesson_id=lesson.id, file_type='material').all()
    return render_template('teacher/lesson_materials.html', lesson=lesson, files=files, active='materials')


@bp.route('/download_file/<int:file_id>')
@login_required
def download_file(file_id):
    """Скачивает файл (материал или работу ученика)."""
    f = File.query.get_or_404(file_id)
    directory = os.path.dirname(f.file_path)
    filename = os.path.basename(f.file_path)
    return send_from_directory(directory, filename, as_attachment=True, download_name=f.original_name)


@bp.route('/delete_file/<int:file_id>', methods=['POST'])
@login_required
def delete_file(file_id):
    """Удаляет файл (материал или работу ученика)."""
    f = File.query.get_or_404(file_id)
    storage_delete(f.file_path)
    db.session.delete(f)
    db.session.commit()
    flash('Файл удалён', 'success')
    return redirect(request.referrer or url_for('teacher.my_courses'))


@bp.route('/lesson/<int:lesson_id>/edit_content', methods=['POST'])
@login_required
def edit_lesson_content(lesson_id):
    """Редактирует текстовое поле content или assignment урока."""
    lesson = Lesson.query.get_or_404(lesson_id)
    if lesson.course.author_id != current_user.id and not current_user.is_admin():
        abort(403)
    field = request.form.get('field', 'content')
    if field in ('content', 'assignment'):
        setattr(lesson, field, request.form.get('text', ''))
        db.session.commit()
        flash('Сохранено', 'success')
    return redirect(request.referrer or url_for('teacher.lesson_materials', lesson_id=lesson.id))


@bp.route('/lesson/<int:lesson_id>/assignment')
@login_required
def lesson_assignment(lesson_id):
    """Показывает страницу с заданием урока и списком сданных работ."""
    lesson = Lesson.query.get_or_404(lesson_id)
    if lesson.course.author_id != current_user.id and not current_user.is_admin():
        abort(403)
    return render_template('teacher/lesson_assignment.html', lesson=lesson, active='assignment')


@bp.route('/lesson/<int:lesson_id>/test')
@login_required
def lesson_test(lesson_id):
    """Отображает страницу управления тестом урока."""
    lesson = Lesson.query.get_or_404(lesson_id)
    if lesson.course.author_id != current_user.id and not current_user.is_admin():
        abort(403)
    test = Test.query.filter_by(lesson_id=lesson_id).first()
    return render_template('teacher/lesson_test.html', lesson=lesson, test=test, active='test')


@bp.route('/lesson/<int:lesson_id>/create_test', methods=['GET', 'POST'])
@login_required
def create_test(lesson_id):
    """Создаёт новый тест для урока."""
    lesson = Lesson.query.get_or_404(lesson_id)
    if lesson.course.author_id != current_user.id and not current_user.is_admin():
        abort(403)
    if request.method == 'POST':
        title = request.form.get('title', f'Тест: {lesson.title}')
        test = Test(title=title, lesson_id=lesson_id)
        db.session.add(test)
        db.session.commit()
        flash('Тест создан', 'success')
        return redirect(url_for('teacher.lesson_test', lesson_id=lesson.id))
    return render_template('teacher/create_test.html', lesson=lesson)


@bp.route('/question/<int:question_id>/add_answer', methods=['GET', 'POST'])
@login_required
def add_answer(question_id):
    """Добавляет вариант ответа к вопросу."""
    question = Question.query.get_or_404(question_id)
    if request.method == 'POST':
        text = request.form.get('text')
        is_correct = request.form.get('is_correct') == 'on'
        if question.question_type == 'single_choice' and is_correct:
            existing = AnswerOption.query.filter_by(question_id=question_id, is_correct=True).first()
            if existing:
                flash('Для вопроса с одним правильным ответом уже выбран правильный вариант. Сначала снимите отметку с существующего.', 'danger')
                return redirect(url_for('teacher.lesson_test', lesson_id=question.test.lesson_id))
        answer = AnswerOption(text=text, is_correct=is_correct, question_id=question_id)
        db.session.add(answer)
        db.session.commit()
        flash('Вариант ответа добавлен', 'success')
        return redirect(url_for('teacher.lesson_test', lesson_id=question.test.lesson_id))
    return render_template('teacher/add_answer.html', question=question)


@bp.route('/course/<int:course_id>/students')
@login_required
def course_students(course_id):
    """Отображает список зачисленных студентов на курс с их прогрессом и средним баллом."""
    course = Course.query.get_or_404(course_id)
    if course.author_id != current_user.id and not current_user.is_admin():
        abort(403)
    enrollments = Enrollment.query.filter_by(course_id=course_id).all()
    students_data = []
    for enr in enrollments:
        progress = calc_student_progress(enr.student_id, course)
        avg = calc_student_avg(enr.student_id, course)
        students_data.append({
            'student': enr.student,
            'enrolled_at': enr.enrolled_at,
            'progress': progress,
            'avg': avg
        })
    return render_template('teacher/course_students.html', course=course, students_data=students_data)


@bp.route('/course/<int:course_id>/enroll', methods=['POST'])
@login_required
def enroll_student(course_id):
    """Добавляет студента на курс по email."""
    course = Course.query.get_or_404(course_id)
    email = request.form.get('email', '').strip()
    if not email:
        flash('Введите email ученика', 'warning')
        return redirect(url_for('teacher.course_students', course_id=course_id))
    student = User.query.filter_by(email=email, role='student').first()
    if not student:
        flash('Ученик с таким email не найден', 'danger')
    elif Enrollment.query.filter_by(student_id=student.id, course_id=course_id).first():
        flash('Ученик уже зачислен', 'warning')
    else:
        db.session.add(Enrollment(student_id=student.id, course_id=course_id))
        db.session.commit()
        flash('Ученик добавлен', 'success')
    return redirect(url_for('teacher.course_students', course_id=course_id))


@bp.route('/course/<int:course_id>/unroll/<int:student_id>', methods=['POST'])
@login_required
def unroll_student(course_id, student_id):
    """Отчисляет студента с курса."""
    course = Course.query.get_or_404(course_id)
    if course.author_id != current_user.id and not current_user.is_admin():
        abort(403)
    enr = Enrollment.query.filter_by(course_id=course_id, student_id=student_id).first_or_404()
    db.session.delete(enr)
    db.session.commit()
    flash('Ученик отчислен с курса', 'success')
    return redirect(url_for('teacher.course_students', course_id=course_id))


@bp.route('/course/<int:course_id>/student/<int:student_id>/works')
@login_required
def student_works(course_id, student_id):
    """Показывает все работы (задания) конкретного студента по курсу."""
    course = Course.query.get_or_404(course_id)
    if course.author_id != current_user.id and not current_user.is_admin():
        abort(403)
    student = User.query.get_or_404(student_id)
    submissions = Submission.query.join(Lesson).filter(
        Lesson.course_id == course_id,
        Submission.student_id == student_id
    ).order_by(Submission.submitted_at.desc()).all()
    return render_template('teacher/student_works.html', course=course, student=student, submissions=submissions)


@bp.route('/submissions/<int:submission_id>', methods=['GET', 'POST'])
@login_required
def grade_submission(submission_id):
    """Выставляет оценку и комментарий к работе студента."""
    sub = Submission.query.get_or_404(submission_id)
    if sub.lesson.course.author_id != current_user.id:
        abort(403)
    form = GradeForm(obj=sub)
    if form.validate_on_submit():
        sub.grade = form.grade.data
        sub.feedback = form.feedback.data
        db.session.commit()
        flash('Оценка сохранена', 'success')
        return redirect(url_for('teacher.lesson_assignment', lesson_id=sub.lesson_id))
    return render_template('teacher/grade_submission.html', submission=sub, form=form)


@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Позволяет учителю сменить пароль."""
    if not current_user.is_teacher() and not current_user.is_admin():
        abort(403)
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash('Пароль изменён', 'success')
        else:
            flash('Неверный текущий пароль', 'danger')
    return render_template('teacher/profile.html', form=form)


@bp.route('/statistics')
@login_required
def statistics():
    """Отображает общую статистику по курсам учителя (количество студентов, прогресс, средний балл)."""
    if not current_user.is_teacher() and not current_user.is_admin():
        abort(403)
    if current_user.is_admin():
        courses = Course.query.all()
    else:
        courses = Course.query.filter_by(author_id=current_user.id).all()
    stats = []
    for course in courses:
        total_students = course.enrollments.count()
        total_lessons = course.lessons.count()

        # Средний балл только активных учеников
        active_avgs = []
        for enr in course.enrollments:
            avg = calc_student_avg(enr.student_id, course)
            if avg > 0:
                active_avgs.append(avg)
        avg_grade = round(sum(active_avgs) / len(active_avgs), 2) if active_avgs else 0

        # Прогресс (все ученики)
        students_progress = []
        for enr in course.enrollments:
            prog = calc_student_progress(enr.student_id, course)
            students_progress.append(prog)
        avg_prog = round(sum(students_progress) / len(students_progress), 1) if students_progress else 0

        stats.append({
            'course': course,
            'total_students': total_students,
            'avg_progress': avg_prog,
            'avg_grade': avg_grade
        })
    return render_template('teacher/course_statistics.html', stats=stats)


@bp.route('/course/<int:course_id>/performance')
@login_required
def course_performance(course_id):
    """Детальная успеваемость студентов по курсу (прогресс и средний балл)."""
    course = Course.query.get_or_404(course_id)
    if course.author_id != current_user.id and not current_user.is_admin():
        abort(403)
    total_lessons = course.lessons.count()
    stats = []
    for enrollment in course.enrollments:
        student = enrollment.student
        progress = calc_student_progress(student.id, course)
        avg = calc_student_avg(student.id, course)
        stats.append({
            'student': student,
            'progress': progress,
            'avg_score': avg
        })
    return render_template('teacher/course_performance.html', course=course, stats=stats)


@bp.route('/question/<int:question_id>/delete')
@login_required
def delete_question(question_id):
    """Удаляет вопрос из теста."""
    question = Question.query.get_or_404(question_id)
    lesson_id = question.test.lesson_id
    if question.test.lesson.course.author_id != current_user.id and not current_user.is_admin():
        abort(403)
    db.session.delete(question)
    db.session.commit()
    flash('Вопрос удалён', 'success')
    return redirect(url_for('teacher.lesson_test', lesson_id=lesson_id))


@bp.route('/lesson/<int:lesson_id>/add_question', methods=['GET', 'POST'])
@login_required
def add_question(lesson_id):
    """Добавляет новый вопрос в тест урока."""
    lesson = Lesson.query.get_or_404(lesson_id)
    test = Test.query.filter_by(lesson_id=lesson_id).first()
    if not test:
        flash('Сначала создайте тест', 'warning')
        return redirect(url_for('teacher.lesson_test', lesson_id=lesson_id))
    if request.method == 'POST':
        text = request.form.get('text')
        question_type = request.form.get('question_type', 'single_choice')
        question = Question(text=text, question_type=question_type, test_id=test.id)
        db.session.add(question)
        db.session.commit()
        flash('Вопрос создан. Теперь добавьте варианты ответов.', 'success')
        return redirect(url_for('teacher.edit_question', question_id=question.id))
    return render_template('teacher/add_question.html', lesson=lesson, test=test)


@bp.route('/answer/<int:answer_id>/delete')
@login_required
def delete_answer(answer_id):
    """Удаляет вариант ответа."""
    opt = AnswerOption.query.get_or_404(answer_id)
    question_id = opt.question_id
    if opt.question.test.lesson.course.author_id != current_user.id and not current_user.is_admin():
        abort(403)
    db.session.delete(opt)
    db.session.commit()
    flash('Вариант удалён', 'success')
    return redirect(url_for('teacher.edit_question', question_id=question_id))


@bp.route('/question/<int:question_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_question(question_id):
    """Редактирует текст вопроса, тип и управляет вариантами ответов."""
    question = Question.query.get_or_404(question_id)
    if question.test.lesson.course.author_id != current_user.id and not current_user.is_admin():
        abort(403)

    if request.method == 'POST' and 'update_question' in request.form:
        new_type = request.form.get('question_type', 'single_choice')
        if new_type == 'single_choice':
            correct_options = AnswerOption.query.filter_by(question_id=question.id, is_correct=True).all()
            if len(correct_options) > 1:
                for opt in correct_options[1:]:
                    opt.is_correct = False
                flash('Тип изменён на «один ответ». Лишние правильные варианты сняты.', 'warning')
        question.text = request.form.get('text')
        question.question_type = new_type
        db.session.commit()
        flash('Вопрос обновлён', 'success')
        return redirect(url_for('teacher.edit_question', question_id=question.id))

    if request.method == 'POST' and 'add_option' in request.form:
        text = request.form.get('option_text', '').strip()
        is_correct = request.form.get('is_correct') == 'on'
        if text:
            if question.question_type == 'single_choice' and is_correct:
                AnswerOption.query.filter_by(question_id=question.id, is_correct=True).update({'is_correct': False})
                db.session.commit()
            new_opt = AnswerOption(text=text, is_correct=is_correct, question_id=question.id)
            db.session.add(new_opt)
            db.session.commit()
            flash('Вариант ответа добавлен', 'success')
        return redirect(url_for('teacher.edit_question', question_id=question.id))

    return render_template('teacher/edit_question.html', question=question)
