import sys
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import sessionmaker

load_dotenv()
DB_URL = os.getenv('DB_URL', 'mysql+pymysql://user:password@localhost/news_db')


def clear_table(table_name):
    try:
        engine = create_engine(DB_URL)
        Session = sessionmaker(bind=engine)
        session = Session()

        metadata = MetaData()
        metadata.reflect(bind=engine)

        if table_name not in metadata.tables:
            print(f"Ошибка: Таблица {table_name} не существует в базе данных.")
            return False

        table = Table(table_name, metadata, autoload_with=engine)
        count_before = session.query(table).count()
        session.execute(table.delete())
        session.commit()

        print(f"Удалено {count_before} записей из таблицы {table_name}.")

        return True

    except Exception as e:
        session.rollback()
        print(f"Ошибка при очистке таблицы {table_name}: {e}.", file=sys.stderr)
        return False
    finally:
        session.close()


if __name__ == "__main__":
    print("Доступные таблицы для очистки:\n1. telegram_posts\n2. rss_posts\n3. news_posts")
    choice = input("Выберите таблицу для очистки (1-3): ")
    table_mapping = {
        '1': 'telegram_posts',
        '2': 'rss_posts',
        '3': 'news_posts'
    }

    table_name = table_mapping.get(choice)
    if not table_name:
        print("Неверный выбор. Введите число от 1 до 3.")
        sys.exit(1)

    confirm = input(f"Вы уверены, что хотите удалить все записи из таблицы {table_name}? [y/n]: ")
    if confirm.lower() == 'y':
        if clear_table(table_name):
            print(f"Таблица {table_name} успешно очищена.")
        else:
            print(f"Не удалось очистить таблицу {table_name}.")
    else:
        print("Очистка отменена.")
