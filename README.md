## Дипломная работа к профессии Python-разработчик «API Сервис заказа товаров для розничных сетей».

---

## Описание
Приложение предназначено для автоматизации закупок в розничной сети. 
Пользователи сервиса — покупатель (менеджер торговой сети, который закупает товары для продажи в магазине) 
и поставщик товаров.

#### Клиент (покупатель):

* Клиент может авторизироваться, регистрироваться и восстанавливать пароль через API.
* Клиент через API может делать закупки по каталогу, в котором представлены товары от нескольких поставщиков.
* В одном заказе можно указать товары от разных поставщиков.
* Клиент указывает свои контактные данные. Они могут быть разными для разных заказов (например адрес доставки).
* Клиент может просматривать каталоги поставщиков, искать нужные ему товары по названию, 
  фильтровать по категории.

#### Поставщик:

* Через API информирует сервис об обновлении прайса.
* Может включать и отключать прием заказов.
* Может получать список оформленных заказов (с товарами из его прайса).
---

## Документация по проекту

В проекте используются переменные окружения. В рабочей дирректории необходимо создать файл .env с полями:

```
PG_USER=
PG_PASSWORD=
NGINX_EXTERNAL_PORT=
EMAIL_HOST_USER= 
EMAIL_HOST_PASSWORD=
```
_Примечание: для тестов можно использовать настройки по умолчанию для следующих полей (т.е. не заполнять):_
```
SECRET_KEY=  
ALLOWED_HOSTS=
PG_HOST=
PG_PORT=
```

_Примечание: настройки почты установлены для ящиков mail.ru. Чтобы получить пароль 
для использования в приложении нужно перейти во вкладку: **безопасность и пароли/ пароли для внешних приложений/ добавить**_
### Для запуска проекта необходимо:

Выполнить команды

```bash
docker-compose up
```
Запуск тестов:
```bash
docker exec app pytest
```