from app.models import TestResult, Submission


def calc_student_avg(student_id, course):
    """Вычисляет средний балл ученика по тестам и заданиям курса."""
    total_score = 0
    items = 0
    for lesson in course.lessons:
        if lesson.test:
            res = TestResult.query.filter_by(student_id=student_id, test_id=lesson.test.id).first()
            if res and res.total > 0:
                total_score += (res.score / res.total * 5)
                items += 1
        sub = Submission.query.filter_by(student_id=student_id, lesson_id=lesson.id).first()
        if sub and sub.grade is not None:
            total_score += sub.grade
            items += 1
    return round((total_score / items), 2) if items > 0 else 0


def calc_student_progress(student_id, course):
    """Возвращает процент пройденных уроков (с учётом теста и задания)."""
    total = course.lessons.count()
    if total == 0:
        return 0
    completed = 0
    for lesson in course.lessons:
        lesson_done = True
        if lesson.test:
            if not TestResult.query.filter_by(student_id=student_id, test_id=lesson.test.id).first():
                lesson_done = False
        if lesson.assignment and lesson.assignment.strip():
            if not Submission.query.filter_by(student_id=student_id, lesson_id=lesson.id).first():
                lesson_done = False
        if lesson_done:
            completed += 1
    return round((completed / total * 100), 1)