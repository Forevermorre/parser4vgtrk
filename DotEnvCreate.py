from pathlib import Path


def create_env_file():
    print("===== Создание конфигурационного файла для TelegramParser =====")

    print("Введите данные для подключения к Telegram API:")
    api_id = input("Введите API ID (полученный от my.telegram.org): ").strip()
    api_hash = input("Введите API HASH: ").strip()
    phone_number = input("Введите номер телефона (в международном формате, например +79012345678): ").strip()
    password = input("Введите пароль от Telegram (если установлен 2FA, иначе оставьте пустым): ").strip()

    print("\nВведите данные для подключения к MySQL:")
    db_user = input("Имя пользователя MySQL: ").strip()
    db_password = input("Пароль MySQL: ").strip()
    db_host = input("Хост MySQL (например, localhost): ").strip()
    db_name = input("Имя базы данных: ").strip()

    check_interval = input("Интервал обновления новостей (в секундах): ").strip()

    env_content = f"""API_ID={api_id}
API_HASH={api_hash}
PHONE_NUMBER={phone_number}
TELEGRAM_PASSWORD={password}
DB_URL=mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}
CHECK_INTERVAL={check_interval}
"""

    env_path = Path('.') / '.env'

    if env_path.exists():
        print("\nФайл .env уже существует.")
        overwrite = input("Перезаписать файл? [y/n]: ").strip().lower()
        if overwrite != 'y':
            print("Создание файла отменено.")
            return

    try:
        with open(env_path, 'w', encoding='utf-8') as file:
            file.write(env_content)
        print(f"\nФайл {env_path} успешно создан!")
        print("Теперь вы можете запустить парсеры.")
    except Exception as e:
        print(f"\nОшибка при создании файла: {e}.")


if __name__ == '__main__':
    create_env_file()
