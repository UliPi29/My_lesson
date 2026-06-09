import os
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, redirect, render_template, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, upgrade
from flask_login import LoginManager, current_user
from config import Config

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'
login.login_message = 'Пожалуйста, войдите.'
login.login_message_category = 'warning'


@login.user_loader
def load_user(user_id):
    """Загружает пользователя по ID для Flask-Login."""
    from app.models import User
    return db.session.get(User, int(user_id))


def create_app():
    """Создаёт и настраивает экземпляр Flask-приложения."""
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)

    from app.routes.auth import bp as auth_bp
    from app.routes.student import bp as student_bp
    from app.routes.teacher import bp as teacher_bp
    from app.routes.admin import bp as admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(admin_bp)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Автоматическое накатывание миграций и создание админа (для хостинга Render)
    with app.app_context():
        upgrade()

        _ensure_admin_exists()

    @app.route('/')
    def index():
        """Перенаправляет авторизованного пользователя в его профиль, иначе показывает главную."""
        if current_user.is_authenticated:
            if current_user.is_teacher():
                return redirect(url_for('teacher.profile'))
            elif current_user.is_admin():
                return redirect(url_for('admin.profile'))
            return redirect(url_for('student.profile'))
        return render_template('index.html')

    return app


def _ensure_admin_exists():
    """Проверяет наличие администратора и создаёт его при необходимости."""
    from app.models import User

    admin_email = 'admin@test.ru'
    admin_password = os.environ.get('ADMIN_DEFAULT_PASSWORD', 'admin123')

    if User.query.filter_by(email=admin_email).first() is None:
        admin = User(
            full_name='Администратор',
            email=admin_email,
            role='admin'
        )
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()
        print(f"Администратор {admin_email} создан. Пароль: {admin_password}")
    else:
        print(f"Администратор {admin_email} уже существует.")
