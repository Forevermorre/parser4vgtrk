import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, BigInteger, String, Text, DateTime, JSON
from sqlalchemy.dialects.mysql import TINYINT, LONGTEXT
from sqlalchemy.ext.declarative import declarative_base

load_dotenv()
Base = declarative_base()


class TelegramPost(Base):
    __tablename__ = 'telegram_posts'

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    channel_id = Column(BigInteger, nullable=False)
    channel_name = Column(String(255), nullable=False)
    message_id = Column(BigInteger, nullable=False)
    text = Column(Text, nullable=False)
    url = Column(String(512), nullable=False)
    refactoredTitle = Column(String(255))
    refactoredText = Column(Text)
    resume = Column(Text)
    tags = Column(String(255))


class RSSPost(Base):
    __tablename__ = 'rss_posts'

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    source = Column(String(512), nullable=False)
    title = Column(String(512), nullable=False)
    summary = Column(Text)
    link = Column(String(512), nullable=False)
    rss_id = Column(String(255), nullable=False)
    source_type = Column(String(50), default='rss')
    refactoredTitle = Column(String(255))
    refactoredText = Column(Text)
    resume = Column(Text)
    tags = Column(String(255))


class NewsPost(Base):
    __tablename__ = 'news_posts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    publish_date = Column(String(50))
    title = Column(String(500))
    url = Column(String(500), unique=True)
    content = Column(LONGTEXT)
    media = Column(JSON, default=list)
    source = Column(String(100))
    source_type = Column(String(50), default='site')
    refactoredTitle = Column(String(255))
    refactoredText = Column(Text)
    resume = Column(Text)
    tags = Column(String(255))
    tg_sent = Column(TINYINT, default=0)
    dle_sent = Column(TINYINT, default=0)


def init_db(db_url=None):
    if not db_url:
        db_url = os.getenv('DB_URL', 'mysql+pymysql://user:password@localhost/news_db')

    if '?' not in db_url:
        db_url += "?charset=utf8mb4"

    engine = create_engine(db_url, pool_pre_ping=True, pool_recycle=3600)

    try:
        with engine.connect():
            print("Успешное подключение к базе данных.")

        Base.metadata.create_all(engine)
        print("Таблицы успешно созданы/проверены.")

        return engine
    except Exception as e:
        print(f"Ошибка при подключении к базе данных: {e}.")
        raise
