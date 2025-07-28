import os
import re
import requests
import time
import urllib3
from bs4 import BeautifulSoup
from sqlalchemy.orm import sessionmaker
from models.Posts import NewsPost, init_db

DB_URL = os.getenv('DB_URL', 'mysql+pymysql://user:password@localhost/news_db')
CHECK_INTERVAL = os.getenv('CHECK_INTERVAL', 60)


class NewsParser:
    def __init__(self):
        urllib3.disable_warnings()
        self.engine = init_db(DB_URL)
        self.Session = sessionmaker(bind=self.engine)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
        }

    def get_or_create_news(self, session, title, url, content, source, source_type='site', media=None):
        existing_news = session.query(NewsPost).filter(NewsPost.url == url).first()
        if existing_news:
            return False

        news = NewsPost(
            title=title,
            url=url,
            content=content,
            media=media or [],
            source=source,
            source_type=source_type,
        )
        session.add(news)
        session.commit()
        return True

    def parse_sledcom_page(self, session):
        url = 'https://volgograd.sledcom.ru/'
        try:
            response = requests.get(url, verify=False, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')

            latest_news_block = soup.find('div', class_='bl-item clearfix')
            if latest_news_block:
                titles = latest_news_block.find_all('a')
                title = titles[1].text.strip()
                news_url = 'https://volgograd.sledcom.ru' + titles[1]['href']
                content, media = self.parse_sledcom_content(news_url)

                if self.get_or_create_news(session, title, news_url, content, 'sledcom', 'site', media):
                    print(f"[SLEDCOM] Добавлена новая новость: {title}.")
                else:
                    print("[SLEDCOM] Новых новостей нет.")

        except Exception as e:
            print(f"[SLEDCOM] Ошибка при парсинге: {e}.")

    def parse_sledcom_content(self, url):
        try:
            response = requests.get(url, verify=False, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')

            article = soup.find('article')
            paragraphs = article.find_all('p')
            content = ' '.join(p.get_text(strip=True) for p in paragraphs)

            media = []
            slider = soup.find('div', class_='b-one_slider')
            if slider:
                images = slider.find_all('img', class_='b-one_slider-image')
                for img in images:
                    if img.get('src'):
                        if img['src'].startswith('http'):
                            media.append(img['src'])
                        else:
                            base_url = 'https://volgograd.sledcom.ru'
                            absolute_url = base_url + img['src']
                            media.append(absolute_url)

            return content, media
        except Exception as e:
            print(f"[SLEDCOM] Ошибка при парсинге контента: {e}")
            return "", []

    def parse_mvd_page(self, session):
        base_url = 'https://34.мвд.рф'
        xn_url = 'https://34.xn--b1aew.xn--p1ai'

        try:
            response = requests.get(f"{xn_url}/новости", headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')

            latest_news_block = soup.find('div', class_='sl-item-title')
            if latest_news_block:
                title = latest_news_block.find('a').text.strip()
                news_path = latest_news_block.find('a')['href']
                content_url = f"{xn_url}{news_path}"
                display_url = f"{base_url}{news_path}"

                content, media = self.parse_mvd_content(content_url)

                if self.get_or_create_news(session, title, display_url, content, 'mvd', 'site', media):
                    print(f"[MVD] Добавлена новая новость: {title}.")
                else:
                    print("[MVD] Новых новостей нет.")

        except Exception as e:
            print(f"[MVD] Ошибка при парсинге: {e}.")

    def parse_mvd_content(self, url):
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')

            article = soup.find('div', class_='article')
            paragraphs = article.find_all('p')
            content = ' '.join(p.get_text(strip=True) for p in paragraphs)

            media = []
            images_container = soup.find('div', id='document-images')
            if images_container:
                links = images_container.find_all('a', class_='cboxElement')
                for link in links:
                    if link.get('href'):
                        img_url = link['href']
                        if not img_url.startswith('http'):
                            img_url = 'https:' + img_url if img_url.startswith(
                                '//') else 'https://static.mvd.ru' + img_url
                        media.append(img_url)

            return content, media
        except Exception as e:
            print(f"[MVD] Ошибка при парсинге контента: {e}")
            return "", []

    def parse_volgadmin_page(self, session):
        url = 'https://www.volgadmin.ru/d/list/news/admvlg'
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')

            latest_news_block = soup.find('div', class_='news_item')
            if latest_news_block:
                titles = latest_news_block.find_all('a')
                title = titles[1].text.strip()
                news_url = 'https://www.volgadmin.ru/d' + titles[1]['href']
                content, media = self.parse_volgadmin_content(news_url)

                if self.get_or_create_news(session, title, news_url, content, 'volgadmin', 'site', media):
                    print(f"[VOLGADMIN] Добавлена новая новость: {title}.")
                else:
                    print("[VOLGADMIN] Новых новостей нет.")

        except Exception as e:
            print(f"[VOLGADMIN] Ошибка при парсинге: {e}.")

    def parse_volgadmin_content(self, url):
        try:
            response = requests.get(url, headers=self.headers)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')

            article = soup.find('div', class_='rightcol')
            if not article:
                return "", []

            text_parts = []
            for p in article.find_all('p'):
                text = p.get_text(strip=True)
                if text:
                    text = text.replace('\xab', '"').replace('\xbb', '"')
                    text_parts.append(text)

            content = ' '.join(text_parts)

            media = []
            leftcol = soup.find('div', class_='leftcol')
            if leftcol:
                main_image = leftcol.find('a', class_='fancybox')
                if main_image and main_image.get('href'):
                    img_url = main_image['href']
                    if not img_url.startswith('http'):
                        img_url = 'https://www.volgadmin.ru' + img_url
                    media.append(img_url)

            return content, media
        except Exception as e:
            print(f"[VOLGADMIN] Ошибка при парсинге контента: {e}")
            return "", []

    def parse_volgograd_news_page(self, session):
        url = 'https://www.volgograd.ru/news/'
        try:
            response = requests.get(url, headers=self.headers, verify=False)
            soup = BeautifulSoup(response.text, 'html.parser')

            latest_news_block = soup.find('div', class_='col-md-12 news-item')
            if latest_news_block:
                title = latest_news_block.find('a').text.strip()
                news_url = 'https://www.volgograd.ru' + latest_news_block.find('a')['href']
                content, media = self.parse_volgograd_news_content(news_url)

                if self.get_or_create_news(session, title, news_url, content, 'volgograd.ru', 'site', media):
                    print(f"[VOLGOGRAD.RU] Добавлена новая новость: {title}.")
                else:
                    print("[VOLGOGRAD.RU] Новых новостей нет.")

        except Exception as e:
            print(f"[VOLGOGRAD.RU] Ошибка при парсинге: {e}.")

    def parse_volgograd_news_content(self, url):
        try:
            response = requests.get(url, headers=self.headers, verify=False)
            soup = BeautifulSoup(response.text, 'html.parser')

            article = soup.find('div', class_='news-detail')
            paragraphs = article.find_all('p')
            content = ' '.join(p.get_text(strip=True) for p in paragraphs)

            media = []

            for fancybox in soup.find_all('a', rel='fancybox'):
                if fancybox.get('href'):
                    img_url = fancybox['href']
                    if not img_url.startswith('http'):
                        img_url = 'https://www.volgograd.ru' + img_url
                    if 'resize_cache' not in img_url:
                        media.append(img_url)

            return content, list(set(media))
        except Exception as e:
            print(f"[VOLGOGRAD.RU] Ошибка при парсинге контента: {e}")
            return "", []

    def parse_genproc_page(self, session):
        url = 'https://epp.genproc.gov.ru/web/proc_34'
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')

            latest_news_block = soup.find('div', class_='feeds-main-page-portlet__list_item')
            if latest_news_block:
                title = latest_news_block.find('a', class_='feeds-main-page-portlet__list_text').text.strip()
                news_url = latest_news_block.find('a', class_='feeds-main-page-portlet__list_text')['href']
                if not news_url.startswith('http'):
                    news_url = 'https://epp.genproc.gov.ru' + news_url
                content, media = self.parse_genproc_content(news_url)

                if self.get_or_create_news(session, title, news_url, content, 'genproc', 'site', media):
                    print(f"[GENPROC] Добавлена новая новость: {title}.")
                else:
                    print("[GENPROC] Новых новостей нет.")

        except Exception as e:
            print(f"[GENPROC] Ошибка при парсинге: {e}.")

    def parse_genproc_content(self, url):
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')

            article_text = soup.find('div', class_='feeds-page__article_text')
            paragraphs = article_text.find_all('p') if article_text else []
            content = ' '.join(p.get_text(strip=True) for p in paragraphs)

            media = []
            image_container = soup.find('div', class_='feeds-page__article_image-list')
            if image_container:
                images = image_container.find_all('img')
                for img in images:
                    if img.get('src'):
                        img_url = img['src']
                        if not img_url.startswith('http'):
                            img_url = 'https://epp.genproc.gov.ru' + img_url
                        media.append(img_url)

            return content, list(set(media))
        except Exception as e:
            print(f"[GENPROC] Ошибка при парсинге контента: {e}")
            return "", []

    def parse_vesti_page(self, session):
        url = 'https://www.vesti.ru/search?q=волгоград&type=news&sort=date'
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')

            latest_news_block = soup.find('div', class_='list__item')
            if latest_news_block:
                title = latest_news_block.find('h3', class_='list__title').text.strip()
                news_url = 'https://www.vesti.ru' + latest_news_block.find('a', href=True)['href']
                content, media = self.parse_vesti_content(news_url)

                if self.get_or_create_news(session, title, news_url, content, 'vesti', 'site', media):
                    print(f"[VESTI] Добавлена новая новость: {title}.")
                else:
                    print("[VESTI] Новых новостей нет.")

        except Exception as e:
            print(f"[VESTI] Ошибка при парсинге: {e}.")

    def parse_vesti_content(self, url):
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')

            article = soup.find('div', class_='js-mediator-article')
            paragraphs = article.find_all('p') if article else []
            content = ' '.join(p.get_text(strip=True) for p in paragraphs)

            media = []
            unwanted_keywords = ['counter', 'pixel', 'tracker', 'logo', 'icon']

            media_container = soup.find('div', class_='article__media')
            if media_container:
                images = media_container.find_all('img')
                for img in images:
                    img_url = (img.get('data-src') or img.get('src', '')).strip()
                    if img_url and not any(keyword in img_url.lower() for keyword in unwanted_keywords):
                        img_url = self._clean_and_absolute_vesti_url(img_url)
                        if img_url:
                            media.append(img_url)

            for img in soup.select('.article__body img'):
                img_url = (img.get('src') or '').strip()
                if img_url and not any(keyword in img_url.lower() for keyword in unwanted_keywords):
                    img_url = self._clean_and_absolute_vesti_url(img_url)
                    if img_url:
                        media.append(img_url)

            return content, list(set(media))
        except Exception as e:
            print(f"[VESTI] Ошибка при парсинге контента: {e}")
            return "", []

    def parse_tass_page(self, session):
        url = 'https://tass.ru/tag/volgogradskaya-oblast'
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            latest_news_block = soup.find('a', class_='tass_pkg_link-v5WdK')
            if not latest_news_block:
                print("[TASS] Новостей не найдено")
                return

            title_element = latest_news_block.find('span', class_='tass_pkg_title-xVUT1')
            if not title_element:
                print("[TASS] Не удалось извлечь заголовок")
                return

            title = title_element.text.strip()
            news_url = 'https://tass.ru' + latest_news_block['href']
            content, media = self.parse_tass_content(news_url)

            if not content:
                print("[TASS] Не удалось получить контент новости")
                return

            cleaned_content = self._clean_tass_text(content)

            if self.get_or_create_news(session, title, news_url, cleaned_content, 'tass', 'site', media):
                print(f"[TASS] Добавлена новая новость: {title}.")
            else:
                print("[TASS] Новых новостей нет.")

        except requests.exceptions.RequestException as e:
            print(f"[TASS] Ошибка сети: {e}")
        except Exception as e:
            print(f"[TASS] Ошибка парсинга: {e}")

    def parse_tass_content(self, url):
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            article = soup.find('article')
            if not article:
                return "", []

            paragraphs = article.find_all('p')
            content = '\n'.join(p.get_text(strip=True) for p in paragraphs if p.text.strip())

            media = []
            media_container = soup.find('div', class_='NewsHeader_media__BePSx')
            if media_container:
                images = media_container.find_all('img')
                for img in images:
                    if img.get('src'):
                        img_url = img['src']
                        img_url = img_url.split('?')[0].split('#')[0]
                        if any(img_url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                            if not img_url.startswith('http'):
                                img_url = 'https:' + img_url if img_url.startswith(
                                    '//') else 'https://tass.ru' + img_url
                            media.append(img_url)

            return content, list(set(media))
        except requests.exceptions.RequestException as e:
            print(f"[TASS] Ошибка загрузки контента: {e}")
            return "", []
        except Exception as e:
            print(f"[TASS] Ошибка обработки контента: {e}")
            return "", []

    def _clean_tass_text(self, text):
        patterns = [
            r"^[А-ЯЁ]+, \d{1,2} [а-яё]+\. /ТАСС/\.",
            r"^[А-ЯЁ]+, \d{1,2} [а-яё]+\. — /ТАСС/",
            r"^/ТАСС/\.",
        ]
        if not text:
            return text
        for pattern in patterns:
            text = re.sub(pattern, "", text).strip()

        return text

    def _clean_and_absolute_vesti_url(self, url):
        if not url or url.startswith('data:'):
            return None

        clean_url = url.split('?')[0].split('#')[0]

        if clean_url.startswith('//'):
            return 'https:' + clean_url
        elif clean_url.startswith('/'):
            return 'https://www.vesti.ru' + clean_url
        elif not clean_url.startswith('http'):
            return None

        return clean_url

    def run(self):
        session = self.Session()
        print(f"Парсер новостных сайтов запущен. Ожидание новых записей.\nИспользуйте Ctrl+C для остановки.")
        try:
            i = 0
            while True:
                i += 1
                print(f"Итерация {i}:")
                self.parse_sledcom_page(session)
                self.parse_mvd_page(session)
                self.parse_volgadmin_page(session)
                self.parse_volgograd_news_page(session)
                self.parse_genproc_page(session)
                self.parse_vesti_page(session)
                self.parse_tass_page(session)

                time.sleep(int(CHECK_INTERVAL))
        except KeyboardInterrupt:
            print("Работа парсера завершена.")
        finally:
            session.close()


if __name__ == '__main__':
    parser = NewsParser()
    parser.run()
