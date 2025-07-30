import os
import re
import requests
import time
import urllib3
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from sqlalchemy.orm import sessionmaker
from models.Posts import NewsPost, init_db

DB_URL = os.getenv('DB_URL', 'mysql+pymysql://user:password@localhost/news_db')
CHECK_INTERVAL = os.getenv('CHECK_INTERVAL', 60)


def get_or_create_news(session, title, url, content, source, source_type='site', media=None,
                       publish_date=None):
    existing_news = session.query(NewsPost).filter(NewsPost.url == url).first()
    if existing_news:
        return False

    news = NewsPost(
        publish_date=publish_date,
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


def clean_and_absolute_vesti_url(url):
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


def clean_tass_text(text):
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

    def parse_sledcom_page(self, session):
        url = 'https://volgograd.sledcom.ru/'
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')

            latest_news_block = soup.find('div', class_='bl-item clearfix')
            if latest_news_block:
                titles = latest_news_block.find_all('a')
                title = titles[1].text.strip()
                news_url = 'https://volgograd.sledcom.ru' + titles[1]['href']
                content, media, publish_date = self.parse_sledcom_content(news_url)

                if get_or_create_news(session, title, news_url, content, 'sledcom', 'site', media,
                                      publish_date):
                    print(f"[VOLGOGRAD.SLEDCOM.RU] Добавлена новость: {title}.")
                else:
                    print("[VOLGOGRAD.SLEDCOM.RU] Новых новостей нет.")

        except Exception as e:
            print(f"[VOLGOGRAD.SLEDCOM.RU] Ошибка при парсинге: {e}.")

    def parse_sledcom_content(self, url):
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')

            date_block = soup.find('div', class_='bl-item-date')
            publish_date = date_block.text.strip() if date_block else None

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

            return content, media, publish_date
        except Exception as e:
            print(f"[VOLGOGRAD.SLEDCOM.RU] Ошибка при парсинге контента: {e}.")
            return "", [], None

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

                content, media, publish_date = self.parse_mvd_content(content_url)

                if get_or_create_news(session, title, display_url, content, 'mvd', 'site', media, publish_date):
                    print(f"[34.МВД.РФ] Добавлена новость: {title}.")
                else:
                    print("[34.МВД.РФ] Новых новостей нет.")

        except Exception as e:
            print(f"[34.МВД.РФ] Ошибка при парсинге: {e}.")

    def parse_mvd_content(self, url):
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')

            date_block = soup.find('div', class_='article-date-item')
            publish_date = date_block.get_text(strip=True) if date_block else None

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

            return content, media, publish_date
        except Exception as e:
            print(f"[34.МВД.РФ] Ошибка при парсинге контента: {e}.")
            return "", [], None

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
                content, media, publish_date = self.parse_volgadmin_content(news_url)

                if get_or_create_news(session, title, news_url, content, 'volgadmin', 'site', media, publish_date):
                    print(f"[VOLGADMIN.RU] Добавлена новость: {title}.")
                else:
                    print("[VOLGADMIN.RU] Новых новостей нет.")

        except Exception as e:
            print(f"[VOLGADMIN.RU] Ошибка при парсинге: {e}.")

    def parse_volgadmin_content(self, url):
        try:
            response = requests.get(url, headers=self.headers)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')

            date_block = soup.find('p', class_='date')
            publish_date = date_block.get_text(strip=True) if date_block else None

            article = soup.find('div', class_='rightcol')
            if not article:
                return "", [], None

            paragraphs = [tag for tag in article.find_all('p', recursive=False) if tag.get_text(strip=True)]

            seen_texts = set()
            text_parts = []

            for tag in paragraphs:
                text = ' '.join(tag.stripped_strings)
                text = text.replace('\xa0', ' ').replace('\u200b', '').replace('\ufeff', '')

                text = text.replace(' ?757', ' №757').replace(' ? по', ' — по')

                if len(text.strip()) < 5:
                    continue

                if text not in seen_texts:
                    seen_texts.add(text)
                    text_parts.append(text)

            content = '\n\n'.join(text_parts)

            media = []
            leftcol = soup.find('div', class_='leftcol')
            if leftcol:
                main_image = leftcol.find('a', class_='fancybox')
                if main_image and main_image.get('href'):
                    img_url = main_image['href']
                    if not img_url.startswith('http'):
                        img_url = 'https://www.volgadmin.ru' + img_url
                    media.append(img_url)

            return content, media, publish_date

        except Exception as e:
            print(f"[VOLGADMIN.RU] Ошибка при парсинге контента: {e}.")
            return "", [], None

    def parse_volgograd_news_page(self, session):
        url = 'https://www.volgograd.ru/news/'
        try:
            response = requests.get(url, headers=self.headers, verify=False)
            soup = BeautifulSoup(response.text, 'html.parser')

            latest_news_block = soup.find('div', class_='col-md-12 news-item')
            if latest_news_block:
                title = latest_news_block.find('a').text.strip()
                news_url = 'https://www.volgograd.ru' + latest_news_block.find('a')['href']
                content, media, publish_date = self.parse_volgograd_news_content(news_url)

                if get_or_create_news(session, title, news_url, content, 'volgograd.ru', 'site', media,
                                      publish_date):
                    print(f"[VOLGOGRAD.RU] Добавлена новость: {title}.")
                else:
                    print("[VOLGOGRAD.RU] Новых новостей нет.")

        except Exception as e:
            print(f"[VOLGOGRAD.RU] Ошибка при парсинге: {e}.")

    def parse_volgograd_news_content(self, url):
        try:
            response = requests.get(url, headers=self.headers, verify=False)
            soup = BeautifulSoup(response.text, 'html.parser')

            article = soup.find('div', class_='news-detail')

            date_div = article.find('div', class_='date')
            publish_date = date_div.get_text(strip=True) if date_div else None

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

            return content, list(set(media)), publish_date
        except Exception as e:
            print(f"[VOLGOGRAD.RU] Ошибка при парсинге контента: {e}.")
            return "", [], None

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
                content, media, publish_date = self.parse_genproc_content(news_url)

                if get_or_create_news(session, title, news_url, content, 'genproc', 'site', media, publish_date):
                    print(f"[EPP.GENPROC.GOV.RU] Добавлена новость: {title}.")
                else:
                    print("[EPP.GENPROC.GOV.RU] Новых новостей нет.")
        except Exception as e:
            print(f"[EPP.GENPROC.GOV.RU] Ошибка при парсинге: {e}.")

    def parse_genproc_content(self, url):
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')

            publish_date = None
            date_li = soup.find('li', class_='feeds-page__info_item')
            if date_li:
                publish_date = date_li.get_text(strip=True)

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

            return content, list(set(media)), publish_date
        except Exception as e:
            print(f"[EPP.GENPROC.GOV.RU] Ошибка при парсинге контента: {e}.")
            return "", [], None

    def parse_vesti_page(self, session):
        url = 'https://www.vesti.ru/search?q=волгоград&type=news&sort=date'
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')

            latest_news_block = soup.find('div', class_='list__item')
            if latest_news_block:
                title = latest_news_block.find('h3', class_='list__title').text.strip()
                news_url = 'https://www.vesti.ru' + latest_news_block.find('a', href=True)['href']
                content, media, publish_date = self.parse_vesti_content(news_url)

                if get_or_create_news(session, title, news_url, content, 'vesti', 'site', media, publish_date):
                    print(f"[VESTI.RU] Добавлена новость: {title}.")
                else:
                    print("[VESTI.RU] Новых новостей нет.")
        except Exception as e:
            print(f"[VESTI.RU] Ошибка при парсинге: {e}.")

    def parse_vesti_content(self, url):
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')

            publish_date = None
            date_div = soup.find('div', class_='article__date')
            time_span = date_div.find('span', class_='article__time') if date_div else None

            if date_div and time_span:
                date_text = date_div.contents[0].get_text(strip=True)
                time_text = time_span.get_text(strip=True)
                publish_date = f"{date_text}, {time_text}"

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
                        img_url = clean_and_absolute_vesti_url(img_url)
                        if img_url:
                            media.append(img_url)

            for img in soup.select('.article__body img'):
                img_url = (img.get('src') or '').strip()
                if img_url and not any(keyword in img_url.lower() for keyword in unwanted_keywords):
                    img_url = clean_and_absolute_vesti_url(img_url)
                    if img_url:
                        media.append(img_url)

            return content, list(set(media)), publish_date
        except Exception as e:
            print(f"[VESTI.RU] Ошибка при парсинге контента: {e}.")
            return "", [], None

    def parse_tass_page(self, session):
        url = 'https://tass.ru/tag/volgogradskaya-oblast'
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            latest_news_block = soup.find('a', class_='tass_pkg_link-v5WdK')
            if not latest_news_block:
                print("[TASS.RU] Новостей не найдено.")
                return

            title_element = latest_news_block.find('span', class_='tass_pkg_title-xVUT1')
            if not title_element:
                print("[TASS.RU] Не удалось извлечь заголовок.")
                return

            title = title_element.text.strip()
            news_url = 'https://tass.ru' + latest_news_block['href']
            content, media, publish_date = self.parse_tass_content(news_url)

            if not content:
                print("[TASS.RU] Не удалось получить контент новости.")
                return

            cleaned_content = clean_tass_text(content)

            if get_or_create_news(session, title, news_url, cleaned_content, 'tass', 'site', media, publish_date):
                print(f"[TASS.RU] Добавлена новость: {title}.")
            else:
                print("[TASS.RU] Новых новостей нет.")

        except requests.exceptions.RequestException as e:
            print(f"[TASS.RU] Ошибка сети: {e}.")
        except Exception as e:
            print(f"[TASS.RU] Ошибка парсинга: {e}.")

    def parse_tass_content(self, url):
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            publish_date = None
            date_div = soup.find('div', class_='PublishedMark_date__a321B')
            if date_div:
                publish_date = date_div.get_text(strip=True)

            article = soup.find('article')
            if not article:
                return "", [], publish_date

            paragraphs = article.find_all('p')
            content = '\n'.join(p.get_text(strip=True) for p in paragraphs if p.text.strip())

            media = []
            media_container = soup.find('div', class_='NewsHeader_media__BePSx')
            if media_container:
                images = media_container.find_all('img')
                for img in images:
                    if img.get('src'):
                        img_url = img['src'].split('?')[0].split('#')[0]
                        if any(img_url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                            if not img_url.startswith('http'):
                                img_url = 'https:' + img_url if img_url.startswith(
                                    '//') else 'https://tass.ru' + img_url
                            media.append(img_url)

            return content, list(set(media)), publish_date
        except requests.exceptions.RequestException as e:
            print(f"[TASS.RU] Ошибка загрузки контента: {e}.")
            return "", [], None
        except Exception as e:
            print(f"[TASS.RU] Ошибка обработки контента: {e}.")
            return "", [], None

    def parse_volgoduma_site_page(self, session):
        base_url = 'https://volgoduma.ru/'
        try:
            response = requests.get(base_url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')

            latest_news_block = soup.find('div', class_='info-cards-item__inner')
            if latest_news_block:
                title_tag = latest_news_block.find('h2', class_='info-cards-item__title')
                title = title_tag.text.strip()

                url_tag = latest_news_block.find('a', href=True)
                news_url = urljoin(base_url, url_tag['href'])

                content, media, publish_date = self.parse_volgoduma_site_content(news_url)

                if get_or_create_news(session, title, news_url, content, 'volgoduma', 'site', media,
                                      publish_date):
                    print(f"[VOLGODUMA.RU] Добавлена новость: {title}.")
                else:
                    print("[VOLGODUMA.RU] Новых новостей нет.")
        except Exception as e:
            print(f"[VOLGODUMA.RU] Ошибка при парсинге главной страницы: {e}.")

    def parse_volgoduma_site_content(self, url):
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')

            date_block = soup.find('div', class_='news-item-date')
            publish_date = date_block.text.strip() if date_block else None

            content_block = soup.find('div', class_='news-item-text')
            paragraphs = content_block.find_all('p') if content_block else []
            content = ' '.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

            media = []
            img_block = content_block.find('div', class_='news-item-image')
            if img_block and img_block.find('img'):
                img = img_block.find('img')
                img_src = img['src']
                media.append(urljoin(url, img_src))

            gallery = content_block.find('div', class_='news-detail-gallery')
            if gallery:
                gallery_imgs = gallery.find_all('img')
                for img in gallery_imgs:
                    img_src = img.get('src')
                    if img_src:
                        media.append(urljoin(url, img_src))

            return content, media, publish_date
        except Exception as e:
            print(f"[VOLGODUMA.RU] Ошибка при парсинге контента новости: {e}.")
            return "", [], None

    def parse_mchs_page(self, session):
        base_url = 'https://34.mchs.gov.ru'
        try:
            response = requests.get(base_url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')

            latest_news = soup.find('a', class_='news-feed__list-item')
            if not latest_news:
                print("[34.MCHS.GOV.RU] Не найдена последняя новость.")
                return

            title_tag = latest_news.find('div', class_='news-feed__list-item-title')
            title = title_tag.text.strip() if title_tag else None

            relative_url = latest_news['href']
            news_url = urljoin(base_url, relative_url)

            content, media, publish_date = self.parse_mchs_content(news_url)

            if get_or_create_news(session, title, news_url, content, 'mchs', 'site', media, publish_date):
                print(f"[34.MCHS.GOV.RU] Добавлена новость: {title}.")
            else:
                print("[34.MCHS.GOV.RU] Новых новостей нет.")
        except Exception as e:
            print(f"[34.MCHS.GOV.RU] Ошибка при парсинге главной страницы: {e}.")

    def parse_mchs_content(self, url):
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')

            date_meta = soup.find('meta', itemprop='datePublished')
            publish_date = date_meta['content'] if date_meta else None

            article = soup.find('article', itemprop='articleBody')
            paragraphs = article.find_all('p') if article else []
            content = ' '.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

            media = []

            main_img = soup.find('img', class_='public__image-img')
            if main_img and main_img.get('src'):
                media.append(urljoin(url, main_img['src']))

            gallery = soup.find_all('div', class_='public__image')
            for img_div in gallery:
                img = img_div.find('img')
                if img and img.get('src'):
                    full_url = urljoin(url, img['src'])
                    if full_url not in media:
                        media.append(full_url)

            return content, media, publish_date
        except Exception as e:
            print(f"[34.MCHS.GOV.RU] Ошибка при парсинге контента: {e}.")
            return "", [], None

    def parse_mchs_operational_page(self, session):
        base_url = 'https://34.mchs.gov.ru'
        main_url = urljoin(base_url, '/deyatelnost/press-centr/operativnaya-informaciya')
        try:
            response = requests.get(main_url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')

            latest_news = soup.find('div', class_='articles-item')
            if not latest_news:
                print("[34.MCHS.GOV.RU (OPER)] Не найдена последняя новость.")
                return

            title_tag = latest_news.find('a', class_='articles-item__title')
            title = title_tag.text.strip() if title_tag else None

            relative_url = title_tag['href']
            news_url = urljoin(base_url, relative_url)

            content, media, publish_date = self.parse_mchs_operational_content(news_url)

            if get_or_create_news(session, title, news_url, content, 'mchs_oper', 'site', media, publish_date):
                print(f"[34.MCHS.GOV.RU (OPER)] Добавлена новость: {title}.")
            else:
                print("[34.MCHS.GOV.RU (OPER)] Новых новостей нет.")

        except Exception as e:
            print(f"[34.MCHS.GOV.RU (OPER)] Ошибка при парсинге страницы: {e}.")

    def parse_mchs_operational_content(self, url):
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')

            date_meta = soup.find('meta', itemprop='datePublished')
            publish_date = date_meta['content'] if date_meta else None

            article = soup.find('article', itemprop='articleBody')
            paragraphs = article.find_all('p') if article else []
            content = ' '.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

            media = []

            main_img = soup.find('img', class_='public__image-img')
            if main_img and main_img.get('src'):
                media.append(urljoin(url, main_img['src']))

            high_res_link = soup.find('a', class_='public__image-download')
            if high_res_link and high_res_link.get('href'):
                full_url = urljoin(url, high_res_link['href'])
                if full_url not in media:
                    media.append(full_url)

            return content, media, publish_date

        except Exception as e:
            print(f"[34.MCHS.GOV.RU (OPER)] Ошибка при парсинге контента: {e}.")
            return "", [], None

    def parse_rospotrebnadzor_page(self, session):
        base_url = 'https://34.rospotrebnadzor.ru'
        try:
            response = requests.get(base_url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            latest_news = soup.find('div', class_='news-item')
            if not latest_news:
                print("[34.ROSPOTREBNADZOR.RU] Блок с новостями не найден.")
                return

            title_tag = latest_news.find('div', class_='news-name').find('a')
            title = title_tag.text.strip() if title_tag else None

            relative_url = title_tag['href'] if title_tag else None
            news_url = urljoin(base_url, relative_url) if relative_url else None

            content, media, publish_date = self.parse_rospotrebnadzor_content(news_url) if news_url else ("", [], None)

            if get_or_create_news(session, title, news_url, content, 'rospotrebnadzor', 'site', media,
                                  publish_date):
                print(f"[34.ROSPOTREBNADZOR.RU] Добавлена новость: {title}.")
            else:
                print("[34.ROSPOTREBNADZOR.RU] Новых новостей нет.")

        except Exception as e:
            print(f"[34.ROSPOTREBNADZOR.RU] Ошибка при парсинге страницы новостей: {e}.")

    def parse_rospotrebnadzor_content(self, url):
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            date_tag = soup.find('div', class_='element_date')
            publish_date = date_tag.text.strip() if date_tag else None

            content_div = soup.find('div', class_='bx_item_description')
            paragraphs = content_div.find_all('p') if content_div else []
            content = ' '.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

            media = []
            images = content_div.find_all('img') if content_div else []
            for img in images:
                src = img.get('src')
                if src:
                    media.append(urljoin(url, src))

            return content, media, publish_date

        except Exception as e:
            print(f"[34.ROSPOTREBNADZOR.RU] Ошибка при парсинге контента: {e}.")
            return "", [], None

    def parse_fsvps_page(self, session):
        base_url = 'https://61.fsvps.gov.ru/news-cat/glavnoe/'
        try:
            response = requests.get(base_url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            latest_news = soup.find('div', class_='block-news-list-element')
            if not latest_news:
                print("[61.FSVPS.GOV.RU] Блок с новостями не найден.")
                return

            title_tag = latest_news.find('h4', class_='block-news-list-element-name').find('a')
            title = title_tag.text.strip() if title_tag else None
            relative_url = title_tag['href'] if title_tag else None
            full_url = urljoin(base_url, relative_url) if relative_url else None

            date_tag = latest_news.find('div', class_='block-news-list-element-data')
            publish_date = date_tag.text.strip() if date_tag else None

            content, media = self.parse_fsvps_content(full_url) if full_url else ("", [])

            if get_or_create_news(session, title, full_url, content, 'fsvps', 'site', media, publish_date):
                print(f"[61.FSVPS.GOV.RU] Добавлена новость: {title}.")
            else:
                print("[61.FSVPS.GOV.RU] Новых новостей нет.")

        except Exception as e:
            print(f"[61.FSVPS.GOV.RU] Ошибка при парсинге страницы новостей: {e}.")

    def parse_fsvps_content(self, url):
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            content = ''
            media = []

            content_container = soup.find('div', class_='node node-news node-promoted col-12 col-xl-12')
            if content_container:
                paragraphs = content_container.find_all('p')
                content = ' '.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

                images = content_container.find_all('img')
                for img in images:
                    src = img.get('src')
                    if src:
                        media.append(urljoin(url, src))

            return content, media

        except Exception as e:
            print(f"[61.FSVPS.GOV.RU] Ошибка при парсинге контента: {e}.")
            return "", []

    def parse_oblzdrav_page(self, session):
        base_url = 'https://oblzdrav.volgograd.ru'
        try:
            response = requests.get(base_url, headers=self.headers, verify=False)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            latest_news = soup.find('div', class_='news-item')
            if not latest_news:
                print("[OBLZDRAV.VOLGOGRAD.RU] Блок с новостями не найден.")
                return

            date_tag = latest_news.find('div', class_='date')
            publish_date = date_tag.text.strip() if date_tag else None

            title_tag = latest_news.find('h2').find('a')
            title = title_tag.text.strip() if title_tag else None
            relative_url = title_tag['href'] if title_tag else None
            news_url = urljoin(base_url, relative_url) if relative_url else None

            content, _, _ = self.parse_oblzdrav_content(news_url) if news_url else ("", [], None)

            if get_or_create_news(session, title, news_url, content, 'oblzdrav', 'site', [], publish_date):
                print(f"[OBLZDRAV.VOLGOGRAD.RU] Добавлена новость: {title}.")
            else:
                print("[OBLZDRAV.VOLGOGRAD.RU] Новых новостей нет.")

        except Exception as e:
            print(f"[OBLZDRAV.VOLGOGRAD.RU] Ошибка при парсинге страницы новостей: {e}.")

    def parse_oblzdrav_content(self, url):
        try:
            response = requests.get(url, headers=self.headers, verify=False)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            date_tag = soup.find('p', class_='date')
            publish_date = date_tag.text.strip() if date_tag else None

            content_div = soup.find('div', class_='news-page-content')
            paragraphs = content_div.find_all('p') if content_div else []
            content = ' '.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

            return content, [], publish_date

        except Exception as e:
            print(f"[OBLZDRAV.VOLGOGRAD.RU] Ошибка при парсинге контента: {e}.")
            return "", [], None

    def parse_culture_page(self, session):
        base_url = 'https://culture.volgograd.ru/current-activity/cooperation/news/'
        try:
            response = requests.get(base_url, headers=self.headers, verify=False)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            latest_news = soup.find('div', class_='col-md-12 news-item')
            if not latest_news:
                print("[CULTURE.VOLGOGRAD.RU] Блок с новостями не найден.")
                return

            title_tag = latest_news.find('h2').find('a')
            title = title_tag.text.strip() if title_tag else None
            relative_url = title_tag['href'] if title_tag else None
            full_url = urljoin(base_url, relative_url) if relative_url else None

            date_tag = latest_news.find('div', class_='date')
            publish_date = date_tag.text.strip() if date_tag else None

            content, media = self.parse_culture_content(full_url) if full_url else ("", [])

            if get_or_create_news(session, title, full_url, content, 'culture', 'site', media, publish_date):
                print(f"[CULTURE.VOLGOGRAD.RU] Добавлена новость: {title}.")
            else:
                print("[CULTURE.VOLGOGRAD.RU] Новых новостей нет.")

        except Exception as e:
            print(f"[CULTURE.VOLGOGRAD.RU] Ошибка при парсинге страницы новостей: {e}.")

    def parse_culture_content(self, url):
        try:
            response = requests.get(url, headers=self.headers, verify=False)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            content = ''
            media = []

            content_container = soup.find('div', class_='news-page-content')
            if content_container:
                paragraphs = content_container.find_all('p')
                content = ' '.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

                images = content_container.find_all('img')
                for img in images:
                    src = img.get('src')
                    if src:
                        media.append(urljoin(url, src))

                style_divs = content_container.find_all('div', style=True)
                for div in style_divs:
                    style = div.get('style')
                    if style and 'background:url' in style:
                        match = re.search(r"url\('?(.*?)'?\)", style)
                        if match:
                            img_url = match.group(1)
                            media.append(urljoin(url, img_url))

            return content, media

        except Exception as e:
            print(f"[CULTURE.VOLGOGRAD.RU] Ошибка при парсинге контента: {e}.")
            return "", []

    def parse_oblkompriroda_page(self, session):
        base_url = 'https://oblkompriroda.volgograd.ru/'
        try:
            response = requests.get(base_url, headers=self.headers, verify=False)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            latest_news = soup.find('div', class_='col-md-12 news-item')
            if not latest_news:
                print("[OBLKOMPRIRODA.VOLGOGRAD.RU] Блок с новостями не найден.")
                return

            title_tag = latest_news.find('h2').find('a')
            title = title_tag.text.strip() if title_tag else None
            relative_url = title_tag['href'] if title_tag else None
            full_url = urljoin(base_url, relative_url) if relative_url else None

            date_tag = latest_news.find('div', class_='date')
            publish_date = date_tag.text.strip() if date_tag else None

            content, media = self.parse_oblkompriroda_content(full_url) if full_url else ("", [])

            if get_or_create_news(session, title, full_url, content, 'oblkompriroda', 'site', media, publish_date):
                print(f"[OBLKOMPRIRODA.VOLGOGRAD.RU] Добавлена новость: {title}.")
            else:
                print("[OBLKOMPRIRODA.VOLGOGRAD.RU] Новых новостей нет.")

        except Exception as e:
            print(f"[OBLKOMPRIRODA.VOLGOGRAD.RU] Ошибка при парсинге страницы новостей: {e}.")

    def parse_oblkompriroda_content(self, url):
        try:
            response = requests.get(url, headers=self.headers, verify=False)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            media = []

            full_text_div = soup.find('div', id='full_text')
            topper_div = soup.find('div', class_='news-topper')

            content_parts = []

            if topper_div:
                paragraphs = topper_div.find_all(['p'])
                content_parts += [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]

                for img in topper_div.find_all('img'):
                    src = img.get('src')
                    if src:
                        media.append(urljoin(url, src))

                for div in topper_div.find_all('div', style=True):
                    style = div.get('style')
                    match = re.search(r"url\(['\"]?(.*?)['\"]?\)", style)
                    if match:
                        media.append(urljoin(url, match.group(1)))

            if full_text_div:
                paragraphs = full_text_div.find_all('p')
                content_parts += [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]

            content = ' '.join(content_parts).strip()
            return content, media

        except Exception as e:
            print(f"[OBLKOMPRIRODA.VOLGOGRAD.RU] Ошибка при парсинге контента: {e}.")
            return "", []

    def parse_zmsut_page(self, session):
        base_url = 'https://zmsut.sledcom.ru'
        main_url = urljoin(base_url, '/news/')
        try:
            response = requests.get(main_url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            latest_news = soup.find('div', class_='bl-item clearfix')
            if not latest_news:
                print("[ZMSUT.SLEDCOM.RU] Блок с новостями не найден.")
                return

            title_tag = latest_news.find('div', class_='bl-item-title').find('a')
            title = title_tag.text.strip() if title_tag else None
            relative_url = title_tag['href'] if title_tag else None
            full_url = urljoin(base_url, relative_url) if relative_url else None

            date_tag = latest_news.find('div', class_='bl-item-date')
            publish_date = date_tag.text.strip() if date_tag else None

            content, media = self.parse_zmsut_content(full_url) if full_url else ("", [])

            if get_or_create_news(session, title, full_url, content, 'zmsut', 'site', media, publish_date):
                print(f"[ZMSUT.SLEDCOM.RU] Добавлена новость: {title}.")
            else:
                print("[ZMSUT.SLEDCOM.RU] Новых новостей нет.")

        except Exception as e:
            print(f"[ZMSUT.SLEDCOM.RU] Ошибка при парсинге страницы новостей: {e}.")

    def parse_zmsut_content(self, url):
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            content = ''
            media = []

            article = soup.find('article', class_='c-detail')
            if article:
                paragraphs = article.find_all('p')
                content = ' '.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

                images = article.find_all('img')
                for img in images:
                    src = img.get('src')
                    if src:
                        media.append(urljoin(url, src))

            return content, media

        except Exception as e:
            print(f"[ZMSUT.SLEDCOM.RU] Ошибка при парсинге контента: {e}.")
            return "", []

    def parse_sfr_page(self, session):
        base_url = 'https://sfr.gov.ru/branches/volgograd/news/'
        try:
            response = requests.get(base_url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            news_block = soup.find('div', class_='d-flex justify-content-between news-months-group-wrapper')
            if not news_block:
                print("[SFR.GOV.RU] Блок с новостями не найден.")
                return

            title_tag = news_block.find('h2', class_='h4 mb-0')
            title = title_tag.get_text(strip=True) if title_tag else None
            link_tag = news_block.find('a')
            relative_url = link_tag.get('href') if link_tag else None
            full_url = urljoin(base_url, relative_url) if relative_url else None

            date_tag = news_block.find('div', class_='date-column')
            publish_date = date_tag.get_text(strip=True) if date_tag else None

            content, media = self.parse_sfr_content(full_url) if full_url else ("", [])

            if get_or_create_news(session, title, full_url, content, 'sfr', 'site', media, publish_date):
                print(f"[SFR.GOV.RU] Добавлена новость: {title}.")
            else:
                print("[SFR.GOV.RU] Новых новостей нет.")

        except Exception as e:
            print(f"[SFR.GOV.RU] Ошибка при парсинге страницы новостей: {e}.")

    def parse_sfr_content(self, url):
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            content = ''
            media = []

            article_block = soup.find('div', class_='col-12 col-lg-8')
            if article_block:
                paragraphs = article_block.find_all('p')
                content = ' '.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

                for img in article_block.find_all('img'):
                    src = img.get('src')
                    if src:
                        media.append(urljoin(url, src))

            return content, media

        except Exception as e:
            print(f"[SFR.GOV.RU] Ошибка при парсинге контента: {e}.")
            return "", []

    def parse_rpn_page(self, session):
        url = 'https://rpn.gov.ru/regions/34/news/'
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')

            news_blocks = soup.find_all('div', class_='contentBox__elem')

            if len(news_blocks) > 1:
                second_news_block = news_blocks[1]
                news_preview = second_news_block.find('div', class_='newsPreview')

                if news_preview:
                    title_link = news_preview.find('a', class_='text _dark _news')
                    title = title_link.text.strip() if title_link else None

                    link = news_preview.find('a', class_='newsPreview__imageBox')
                    if not link:
                        link = news_preview.find('a', class_='text _dark _news')

                    if link and link.get('href'):
                        news_url = 'https://rpn.gov.ru' + link['href'] if not link['href'].startswith('http') else link[
                            'href']
                    else:
                        news_url = None

                    date_block = news_preview.find('p', class_='newsPreview__date')
                    publish_date = date_block.text.strip() if date_block else None

                    if title and news_url:
                        content, media, detailed_date = self.parse_rpn_content(news_url)

                        final_date = detailed_date if detailed_date else publish_date

                        if get_or_create_news(session, title, news_url, content, 'rpn', 'site', media, final_date):
                            print(f"[RPN.GOV.RU] Добавлена новость: {title}.")
                        else:
                            print("[RPN.GOV.RU] Новых новостей нет.")
                    else:
                        print("[RPN.GOV.RU] Не удалось извлечь заголовок или URL новости.")
            else:
                print("[RPN.GOV.RU] На странице меньше двух новостей.")

        except Exception as e:
            print(f"[RPN.GOV.RU] Ошибка при парсинге: {e}.")

    def parse_rpn_content(self, url):
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')

            date_block = soup.find('h4')
            publish_date = date_block.text.strip() if date_block else None

            content_div = soup.find('div', class_='contentBox')
            content = ""
            if content_div:
                news_text_block = content_div.find('div', class_='ui')
                if news_text_block:
                    paragraphs = news_text_block.find_all('p', recursive=False)
                    seen_texts = set()

                    for p in paragraphs:
                        text = p.get_text(strip=True)
                        if text and text not in seen_texts:
                            content += text + ' '
                            seen_texts.add(text)
                else:
                    paragraphs = content_div.find_all('p', recursive=False)
                    seen_texts = set()

                    for p in paragraphs:
                        text = p.get_text(strip=True)
                        if text and text not in seen_texts:
                            content += text + ' '
                            seen_texts.add(text)

            content = content.strip()
            media = []
            images = content_div.find_all('img') if content_div else []
            for img in images:
                if img.get('src'):
                    img_url = img['src']
                    if not img_url.startswith('http'):
                        img_url = 'https://rpn.gov.ru' + img_url
                    media.append(img_url)

            return content, media, publish_date
        except Exception as e:
            print(f"[RPN.GOV.RU] Ошибка при парсинге контента: {e}.")
            return "", [], None

    def parse_ria_page(self, session):
        url = 'https://ria.ru/location_Volgograd/'
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')

            news_block = soup.find('div', class_='list-item')
            if news_block:
                title_tag = news_block.find('a', class_='list-item__title')
                title = title_tag.text.strip() if title_tag else None

                link = news_block.find('a', class_='list-item__title')
                if link and link.get('href'):
                    news_url = link['href'] if link['href'].startswith('http') else 'https://ria.ru' + link['href']
                else:
                    news_url = None

                date_block = news_block.find('div', {'data-type': 'date'})
                publish_date = date_block.text.strip() if date_block else None

                if title and news_url:
                    content, media = self.parse_ria_content(news_url)

                    if get_or_create_news(session, title, news_url, content, 'ria', 'site', media, publish_date):
                        print(f"[RIA.RU] Добавлена новость: {title}.")
                    else:
                        print("[RIA.RU] Новых новостей нет.")
                else:
                    print("[RIA.RU] Не удалось извлечь заголовок или URL.")
            else:
                print("[RIA.RU] Новостные блоки не найдены.")

        except Exception as e:
            print(f"[RIA.RU] Ошибка: {str(e)}.")

    def parse_ria_content(self, url):
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            media = []
            header = soup.find('div', class_='article__header')
            if header:
                img = header.find('img')
                if img and img.get('src'):
                    img_url = img['src']
                    if not img_url.startswith('http'):
                        img_url = 'https://ria.ru' + img_url
                    media.append(img_url)

            content_blocks = soup.find_all('div', class_='article__block')
            content = []
            seen_texts = set()

            for block in content_blocks:
                text_div = block.find('div', class_='article__text')
                if text_div:
                    text = text_div.get_text(strip=True)
                    text = re.sub(r'^МОСКВА, \d{1,2} [а-я]+ - РИА Новости\.\s*', '', text)
                    if text and text not in seen_texts:
                        content.append(text)
                        seen_texts.add(text)

            content = ' '.join(content)

            return content, media
        except Exception as e:
            print(f"[RIA.RU] Ошибка при парсинге контента: {e}.")
            return "", []

    def parse_xras_page(self, session):
        url = 'https://xras.ru/project_diary.html'
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')

            post = soup.find('div', class_='post')
            if post:
                title_tag = post.find('div', class_='post-title').find('a')
                title = title_tag.text.strip() if title_tag else None

                if title_tag and title_tag.get('href'):
                    news_url = 'https://xras.ru/' + title_tag['href'] if not title_tag['href'].startswith('http') else \
                        title_tag['href']
                else:
                    news_url = None

                date_block = post.find('div', class_='post-date')
                publish_date = date_block.text.strip() if date_block else None

                if title and news_url:
                    content, media = self.parse_xras_content(news_url)

                    if get_or_create_news(session, title, news_url, content, 'xras', 'site', media, publish_date):
                        print(f"[XRAS.RU] Добавлена новость: {title}.")
                    else:
                        print("[XRAS.RU] Новых новостей нет.")
                else:
                    print("[XRAS.RU] Не удалось извлечь заголовок или URL.")
            else:
                print("[XRAS.RU] Посты не найдены.")

        except Exception as e:
            print(f"[XRAS.RU] Ошибка: {str(e)}.")

    def parse_xras_content(self, url):
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')

            media = []
            content_wrap = soup.find('div', class_='content-tex-wrap')

            if content_wrap:
                video = content_wrap.find('video')
                if video and video.find('source'):
                    video_src = video.find('source')['src']
                    if not video_src.startswith('http'):
                        video_src = 'https://xras.ru' + video_src
                    media.append(video_src)

                images = content_wrap.find_all('img')
                for img in images:
                    if img.get('src'):
                        img_url = img['src']
                        if not img_url.startswith('http'):
                            img_url = 'https://xras.ru' + img_url
                        media.append(img_url)

            content = []
            main_content = content_wrap.find_all(['p', 'figure'], recursive=False)
            seen_texts = set()

            for element in main_content:
                if element.find_parent('section',
                                       class_=lambda x: x and ('pagination' in x or 'diary-post__caption' in x)):
                    continue

                if element.name == 'p':
                    text = element.get_text(strip=True)
                    if text and text not in seen_texts:
                        content.append(text)
                        seen_texts.add(text)

            content = ' '.join(content)

            return content, media
        except Exception as e:
            print(f"[XRAS.RU] Ошибка при парсинге контента: {e}.")
            return "", []

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
                self.parse_volgoduma_site_page(session)
                self.parse_mchs_page(session)
                self.parse_mchs_operational_page(session)
                self.parse_rospotrebnadzor_page(session)
                self.parse_fsvps_page(session)
                self.parse_oblzdrav_page(session)
                self.parse_culture_page(session)
                self.parse_oblkompriroda_page(session)
                self.parse_zmsut_page(session)
                self.parse_sfr_page(session)
                self.parse_rpn_page(session)
                self.parse_ria_page(session)
                self.parse_xras_page(session)

                time.sleep(int(CHECK_INTERVAL))
        except KeyboardInterrupt:
            print("Работа парсера завершена.")
        finally:
            session.close()


if __name__ == '__main__':
    parser = NewsParser()
    parser.run()
