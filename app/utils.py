import shutil
from pathlib import Path
from fastapi import UploadFile
import secrets
import os

# Директория для хранения всех загружаемых изображений
UPLOAD_DIR = Path("static/images")

def save_upload_file(upload_file: UploadFile) -> str:
    """
    Сохраняет загруженный файл в директорию UPLOAD_DIR с уникальным именем
    и возвращает относительный URL для доступа к нему.

    Args:
        upload_file: Файл, полученный от FastAPI.

    Returns:
        Относительный URL сохраненного файла (например, /static/images/your_file.png).
    """
    # Создаем директорию, если ее не существует
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    token_hex = secrets.token_hex(8)
    file_extension = Path(upload_file.filename).suffix
    filename = f"{token_hex}{file_extension}"
    file_path = UPLOAD_DIR / filename
    
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
        
    return f"/static/images/{filename}"

def delete_file(file_path: str | None):
    """
    Удаляет файл с диска, если он существует.

    Args:
        file_path: Относительный URL файла (например, /static/images/your_file.png).
    """
    if not file_path:
        return

    # Преобразуем URL в локальный путь к файлу.
    # Убираем начальный слэш, чтобы Path правильно сконструировал путь.
    try:
        local_path = Path(file_path.lstrip('/'))
        if local_path.exists() and local_path.is_file():
            os.remove(local_path)
    except Exception as e:
        # В реальном приложении здесь должно быть логирование ошибки
        print(f"Ошибка при удалении файла {file_path}: {e}")
