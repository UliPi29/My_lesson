import os
from flask import current_app

def upload_file(file_stream, filename):
    """Сохраняет файл в локальную директорию UPLOAD_FOLDER."""
    path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
    file_stream.save(path)
    return path

def delete_file(key):
    """Удаляет файл из локального хранилища."""
    path = key if os.path.isabs(key) else os.path.join(current_app.config['UPLOAD_FOLDER'], key)
    if os.path.exists(path):
        os.remove(path)