# [Макс бот](https://t.me/maxzens_bot)

Простой [Telegram-бот](https://t.me/maxzens_bot), генерирующий сообщения на основе тех, что были написаны другими пользователями беседы при помощи [Цепей Маркова](https://habr.com/en/post/455762/). Идея взята у ВК-ботов [сглыпа](https://vk.com/sglypa) и [Witless](https://vk.com/witless).


# Запуск

Инструкция для запуска бота локально:

1. Установите Python.
2. Склонируйте этот репозиторий.
3. Установите зависимости: `pip install -r requirements.txt`
4. Сделайте копию файла `.env.example`, переименуйте его в `.env`.
5. Создайте Telegram-бота у [BotFather](https://t.me/botfather).
6. Токен этого бота засуньте в файл `.env`, что бы получилось что-то по типу `TOKEN=asd123`
7. Запустите бота: `python main.py`
