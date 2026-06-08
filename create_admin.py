"""Скрипт для создания администратора в приложении."""
from dotenv import load_dotenv
load_dotenv()
from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    existing = User.query.filter_by(email='admin@test.ru').first()
    if existing:
        print("Администратор уже существует!")
        exit()
    
    admin = User(
        full_name='Администратор',
        email='admin@test.ru',
        role='admin'
    )
    admin.set_password('admin123')
    
    db.session.add(admin)
    db.session.commit()
    print("Администратор создан успешно!")
    print("Email: admin@test.ru")
    print("Пароль: admin123")