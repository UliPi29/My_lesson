from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from werkzeug.urls import url_parse
from app import db, login
from app.models import User
from app.forms import RegistrationForm, LoginForm
from flask import Blueprint

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/register', methods=['GET', 'POST'])
def register():
    """Регистрирует нового пользователя с ролью 'student'."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('Этот email уже зарегистрирован.', 'danger')
            return redirect(url_for('auth.register'))
        user = User(
            full_name=form.full_name.data,
            email=form.email.data,
            role='student'
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Регистрация успешна! Теперь вы можете войти.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Аутентифицирует пользователя и перенаправляет на соответствующую страницу."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Неверный email или пароль.', 'danger')
            return redirect(url_for('auth.login'))

        if user.is_blocked:
            flash('Ваш аккаунт заблокирован. Обратитесь к администратору.', 'danger')
            return redirect(url_for('auth.login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            if user.is_teacher():
                next_page = url_for('teacher.my_courses')
            elif user.is_admin():
                next_page = url_for('admin.users')
            else:
                next_page = url_for('student.my_courses')
        return redirect(next_page)
    return render_template('auth/login.html', form=form)


@bp.route('/logout')
def logout():
    """Выполняет выход пользователя из системы."""
    logout_user()
    return redirect(url_for('index'))