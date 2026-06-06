from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, IntegerField, FileField, FloatField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, NumberRange

class RegistrationForm(FlaskForm):
    full_name = StringField('ФИО', validators=[DataRequired(), Length(max=200)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Подтвердите пароль', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Зарегистрироваться')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')

class CourseForm(FlaskForm):
    title = StringField('Название курса', validators=[DataRequired(), Length(max=200)])
    submit = SubmitField('Сохранить')

class LessonForm(FlaskForm):
    title = StringField('Название урока', validators=[DataRequired()])
    content = TextAreaField('Текстовые материалы (теория)')
    assignment = TextAreaField('Текст задания для учеников')
    order_num = IntegerField('Порядковый номер', validators=[Optional()])
    submit = SubmitField('Сохранить')

class FileUploadForm(FlaskForm):
    file = FileField('Файл', validators=[DataRequired()])
    submit = SubmitField('Загрузить')

class TestForm(FlaskForm):
    title = StringField('Название теста', validators=[DataRequired()])
    submit = SubmitField('Создать/Обновить')

class QuestionForm(FlaskForm):
    text = TextAreaField('Текст вопроса', validators=[DataRequired()])
    question_type = SelectField('Тип', choices=[('single_choice', 'Один ответ'), ('multiple_choice', 'Несколько ответов')])
    submit = SubmitField('Добавить вопрос')

class AnswerOptionForm(FlaskForm):
    text = StringField('Вариант ответа', validators=[DataRequired()])
    is_correct = BooleanField('Правильный ответ')
    submit = SubmitField('Добавить вариант')

class GradeForm(FlaskForm):
    grade = FloatField('Оценка (1-5)', validators=[DataRequired()])
    feedback = TextAreaField('Комментарий')
    submit = SubmitField('Сохранить оценку')

class AddStudentForm(FlaskForm):
    email = StringField('Email ученика', validators=[DataRequired(), Email()])
    submit = SubmitField('Добавить на курс')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Текущий пароль', validators=[DataRequired()])
    new_password = PasswordField('Новый пароль', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Подтвердите пароль', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Сменить пароль')