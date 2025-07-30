# Парсер новостей
## Установка

1. Клонируйте репозиторий:

```bash
git clone https://github.com/Forevermorre/parser4vgtrk.git
cd parser4vgtrk
```

2. Установите зависимости:

```bash
pip install -r requirements.txt
```

3. Создайте файл **.env** с данными для авторизации:

```bash
python DotEnvCreate.py
```
Или создайте **.env** в корневой директории проекта вручную:
```
API_ID=ваш_api_id
API_HASH=ваш_api_hash
PHONE_NUMBER=ваш_номер_телефона
TELEGRAM_PASSWORD=ваш_пароль_для_2FA
DB_URL=mysql+pymysql://имя_пользователя:пароль@хост/название_базы_данных
CHECK_INTERVAL=время_обновления_новостей_в_секундах
```
(Вам потребуются **API ID** и **API HASH** с [my.telegram.org](https://my.telegram.org/), а также **данные** для подключения к БД)

4. Настройка источников:

**data/channels.txt** — список Telegram-каналов. Примеры:
```
https://t.me/parser4vgtrk
https://t.me/parser4vgtrk2
```
**data/sites.txt** — список RSS-лент. Примеры:
```
https://lenta.ru/rss/news
https://www.kommersant.ru/RSS/news.xml
https://ria.ru/export/rss2/archive/index.xml
```

5. Запуск:

**Telegram-парсер:**
```bash
python TelegramParser.py
```
При первом запуске потребуется ввести код подтверждения из Telegram и, при необходимости, пароль 2FA.

**RSS-парсер:**
```bash
python RSSParser.py
```

**Парсер новостей:**
```bash
python NewsParser.py
```
Источники данных — официальные новостные сайты Волгоградской области:
- [https://volgograd.sledcom.ru/](https://volgograd.sledcom.ru/)
- [https://34.мвд.рф/новости](https://34.xn--b1aew.xn--p1ai/новости)
- [https://www.volgadmin.ru/d/list/news/admvlg](https://www.volgadmin.ru/d/list/news/admvlg)
- [https://www.volgograd.ru/news/](https://www.volgograd.ru/news/)
- [https://epp.genproc.gov.ru/web/proc_34](https://epp.genproc.gov.ru/web/proc_34)
- [https://www.vesti.ru/search?q=волгоград&type=news&sort=date](https://www.vesti.ru/search?q=волгоград&type=news&sort=date)
- [https://tass.ru/tag/volgogradskaya-oblast](https://tass.ru/tag/volgogradskaya-oblast)
- [https://volgoduma.ru/](https://volgoduma.ru/)
- [https://34.mchs.gov.ru](https://34.mchs.gov.ru)
- [https://34.mchs.gov.ru/deyatelnost/press-centr/operativnaya-informaciya](https://34.mchs.gov.ru/deyatelnost/press-centr/operativnaya-informaciya)
- [https://34.rospotrebnadzor.ru](https://34.rospotrebnadzor.ru)
- [https://61.fsvps.gov.ru/news-cat/glavnoe/](https://61.fsvps.gov.ru/news-cat/glavnoe/)
- [https://oblzdrav.volgograd.ru](https://oblzdrav.volgograd.ru)
- [https://culture.volgograd.ru/current-activity/cooperation/news/](https://culture.volgograd.ru/current-activity/cooperation/news/)
- [https://oblkompriroda.volgograd.ru/](https://oblkompriroda.volgograd.ru/)
- [https://zmsut.sledcom.ru](https://zmsut.sledcom.ru)
- [https://sfr.gov.ru/branches/volgograd/news/](https://sfr.gov.ru/branches/volgograd/news/)
- [https://rpn.gov.ru/regions/34/news/](https://rpn.gov.ru/regions/34/news/)
- [https://ria.ru/location_Volgograd/](https://ria.ru/location_Volgograd/)
- [https://xras.ru/project_diary.html](https://xras.ru/project_diary.html)

6. Очистка таблиц:

```bash
python ClearDatabase.py
```