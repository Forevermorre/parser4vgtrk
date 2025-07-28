import sys
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import sessionmaker

load_dotenv()
DB_URL = os.getenv('DB_URL', 'mysql+pymysql://user:password@localhost/news_db')


def clear_news_posts():
    try:
        engine = create_engine(DB_URL)
        Session = sessionmaker(bind=engine)
        session = Session()

        metadata = MetaData()
        metadata.reflect(bind=engine)
        news_posts = Table('news_posts', metadata, autoload_with=engine)

        session.execute(news_posts.delete())
        session.commit()

        print(f"Все записи из таблицы news_posts успешно удалены.")

    except Exception as e:
        session.rollback()
        print(f"Ошибка при очистке таблицы: {e}.", file=sys.stderr)
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    confirm = input("Вы уверены, что хотите удалить все записи из news_posts? [y/n]: ")
    if confirm.lower() == 'y':
        clear_news_posts()
    else:
        print("Очистка отменена.")
