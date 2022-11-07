# coding: utf-8

import asyncio
from datetime import datetime
import json
import os
import random
import re
import time
from typing import cast

import aiofiles
import aiogram
import dateparser
import dotenv
import markovify
from aiogram import Dispatcher
from aiogram.types import Message as MessageType
from loguru import logger

from middleware import BotMessagesMiddleware

dotenv.load_dotenv()


BOT = aiogram.Bot(
	os.environ["TOKEN"],
	parse_mode=aiogram.types.ParseMode.HTML
)
DP = Dispatcher(BOT)

USER_BASE = {}

@DP.message_handler(commands=["start"])
async def hello_handler(msg: MessageType):
	# Из-за Middleware, эта команда будет работать только в беседах.

	await msg.answer("Отлично! 😊\n\nЧто бы я работал, тебе нужно выдать мне права администратора. 🫂\nПосле выдачи я сумею работать как положено 👀")

@DP.chat_join_request_handler()
@DP.message_handler(content_types=["new_chat_members", "group_chat_created", "supergroup_chat_created"])
async def chat_join_handler(msg: MessageType):
	"""
	Вызывается, когда бота добавляют в чат.
	"""

	# Проверяем, был ли добавлен бот или кто-то иной?

	bot_id = (await BOT.get_me()).id
	if not any([i for i in msg.new_chat_members if i.id == bot_id]):
		return

	# В группу добавили именно этого бота, отправляем об этом сообщение:

	await msg.answer("<b>Привет! 🙋</b>\n\nСпасибо за то что добавил меня к себе в беседу.\nДля моей работы выдай мне права администратора.")

@DP.message_handler(commands=["stats", "statistics", "stat"])
async def stats_handler(msg: MessageType):
	"""
	Команда статистики.
	"""

	await msg.answer(f"<b>Статистика ℹ️</b>\n\nВ базе данных этой группы хранится <code>{len(USER_BASE[str(msg.chat.id)]['Messages'])}</code> сообщений.")

async def check_admin(msg: MessageType):
	"""
	Проверяет на наличие прав администратора в группе. Возвращает `False`, если прав админа у пользователя нет.
	"""

	if not (await BOT.get_chat_member(msg.chat.id, msg.from_user.id)).is_chat_admin():
		await msg.answer("⚠️ Данную команду могут использовать только <b>администраторы чата</b>.")

		return False

	return True

@DP.message_handler(commands=["disable", "turn_off", "turnoff", "off"])
async def disable_handler(msg: MessageType):
	"""
	Вызывается для отключения генерации сообщений бота.
	"""

	if not await check_admin(msg):
		return

	args = (msg.get_args() or "")
	disabled_seconds = 0 

	parsed = None
	if args:
		parsed = dateparser.parse(args)
	else:
		disabled_seconds = 7 * 24 * 60 * 60

	if parsed:
		disabled_seconds = (datetime.now().timestamp() - parsed.timestamp())

	# Проверяем на то, насколько бот был выключен:

	if disabled_seconds < 2 * 60:
		await msg.answer(f"Пожалуйста, укажи время на которое нужно выключить генерацию сообщений. Указанное тобою значение (<code>{seconds_to_userfriendly_string(disabled_seconds)}</code>) уж слишком мало.\n\nПример: <code>/disable 5 часов</code>")

		return

	await msg.answer(f"Окей, я отключу генерацию сообщений в этой беседе на <code>{seconds_to_userfriendly_string(disabled_seconds)}</code>.\n\nℹ️ Администраторы могут меня включить, прописав команду /enable.")
	update_record(
		msg.chat.id,
		{
			"OffUntil": int(time.time()) + int(disabled_seconds)
		}
	)

@DP.message_handler(commands=["enable", "turn_on", "turnon", "on"])
async def enable_handler(msg: MessageType):
	"""
	Вызывается для включения генерации сообщений бота.
	"""

	if not await check_admin(msg):
		return

	await msg.answer(
		"Окей, теперь я снова могу генерировать сообщения! 🙂"
		if USER_BASE[str(msg.chat.id)]["OffUntil"] else
		"Я и так включён, так как не был отключён администраторами беседы до этого."
	)

	update_record(
		msg.chat.id,
		{
			"OffUntil": 0
		}
	)

async def onBotStart(dp: aiogram.Dispatcher) -> None:
	"""
	Метод вызывается после запуска бота.
	"""

	global USER_BASE

	logger.info("Привет, мир!")

	# Загружаем базу данных:
	USER_BASE = await load_db()

async def bg_saver():
	"""
	Задача, которая в фоновом режиме выгружает содержимое базы.
	"""

	while True:
		await asyncio.sleep(1)

		try:
			await save_db()
		except Exception as error:
			logger.error(f"Ошибка при сохранении базы в файл: {error}")

def seconds_to_userfriendly_string(seconds, max=2, minutes=True, hours=True, days=True, weeks=False, months=False, years=False, decades=False):
	"""Преобразовывает UNIX-время как строку вида "5 часов, 17 секунд".

	Args:
		seconds ([type]): [description]
		max (int, optional): [description]. Defaults to 2.
		minutes (bool, optional): [description]. Defaults to True.
		hours (bool, optional): [description]. Defaults to True.
		days (bool, optional): [description]. Defaults to True.
		weeks (bool, optional): [description]. Defaults to False.
		months (bool, optional): [description]. Defaults to False.
		years (bool, optional): [description]. Defaults to False.
		decades (bool, optional): [description]. Defaults to False.

	Returns:
		[type]: [description]
	"""

	seconds = int(seconds)

	if seconds < 0: seconds = -seconds
	newSeconds = seconds; string = []; values = [60, 3600, 86400, 604800, 2678400, 31536000, 315360000]; maxCount = max; valuesgot = {"decades": 0, "years": 0, "months": 0, "weeks": 0, "days": 0, "hours": 0, "minutes": 0, "seconds": 0}; stringslocal = [["век","века","века","века","веков"], ["год","года","года","года","лет"],["месяц","месяца","месяца","месяца","месяцев"],["неделя","недели","недели","неделей"],["день","дня","дня","дней"],["час","часа","часа","часов"],["минута","минуты","минуты","минут",],["секунда","секунды","секунды","секунд"]]
	while True:
		if newSeconds >= values[6] and decades: newSeconds -= values[6]; valuesgot["decades"] += 1
		elif newSeconds >= values[5] and years: newSeconds -= values[5]; valuesgot["years"] += 1
		elif newSeconds >= values[4] and months: newSeconds -= values[4]; valuesgot["months"] += 1
		elif newSeconds >= values[3] and weeks: newSeconds -= values[3]; valuesgot["weeks"] += 1
		elif newSeconds >= values[2] and days: newSeconds -= values[2]; valuesgot["days"] += 1
		elif newSeconds >= values[1] and hours: newSeconds -= values[1]; valuesgot["hours"] += 1
		elif newSeconds >= values[0] and minutes: newSeconds -= values[0]; valuesgot["minutes"] += 1
		else: valuesgot["seconds"] += newSeconds; newSeconds = 0; break
	for index, key in enumerate(valuesgot):
		if valuesgot[key] != 0:
			if len(stringslocal[index]) > valuesgot[key]: string.append(str(valuesgot[key]) + " " + stringslocal[index][valuesgot[key] - 1])
			else: string.append(str(valuesgot[key]) + " " + stringslocal[index][len(stringslocal[index]) - 1])
	if len(string) == 0: string.append("0 секунд")
	newStr = []
	for fstring in string:
		if maxCount > 0: newStr.append(fstring); maxCount -= 1
		else: break
	return ", ".join(newStr)

async def save_db(only_chat_id: int | str | None = None, folder = "db"):
	"""
	Сохраняет базу данных в файлы. Если `only_chat_id` указан, то будет сохранён лишь указанный ID из БД на диск.
	"""

	filenames_to_save = [str(only_chat_id)]
	if not only_chat_id:
		filenames_to_save = list(USER_BASE)

	for index, key in enumerate(filenames_to_save):
		# Проверяем, обновлено ли это значение:
		dict_to_save = USER_BASE[key].copy()

		# FIXME: Костыль. Мне лень делать что то более умное.
		if dict_to_save["OffUntil"] <= int(time.time()):
			dict_to_save["OffUntil"] = 0
			USER_BASE[key]["OffUntil"] = 0

		if not dict_to_save["_isUpdated"]:
			continue

		dict_to_save.pop("_isUpdated")
		USER_BASE[key]["_isUpdated"] = False

		async with aiofiles.open(
			os.path.join(folder, key + ".jsonc"), 
			"w", encoding="utf-8"
		) as file:
			await file.write(
				json.dumps(
					dict_to_save,
					ensure_ascii=False
				)
			)

async def load_db(only_chat_id: int | str | None = None, folder="db"):
	"""
	Загружает базу данных из файлов, возвращая загруженное значение. Если `only_chat_id` указан, то будет возвращено только это значение из БД, в ином случае, будет возвращён dict из всех значений в БД.
	"""

	dict_to_return = {}

	filenames_to_open = [str(only_chat_id)]
	if not only_chat_id:
		filenames_to_open = [os.path.splitext(i)[0] for i in os.listdir(folder)]

	filenames_to_open_with_path = [os.path.join(folder, i + ".jsonc") for i in filenames_to_open]

	for index, path in enumerate(filenames_to_open_with_path):
		async with aiofiles.open(path, "r", encoding="utf-8") as file:
			contents = await file.read()
			
			dict_to_return.update({
				filenames_to_open[index]: {
					**json.loads(contents),
					"_isUpdated": False
				}
			})

	return dict_to_return

def populate_base(chat_id: int | str):
	"""
	Добавляет в базу данных "пустую", "чистую" запись, если таковой ещё ни разу не было.
	"""

	if str(chat_id) in USER_BASE:
		return

	USER_BASE.update({
		str(chat_id): {
			"_isUpdated": False,
			"ID": chat_id,
			"Messages": [],
			"Attachments": [],
			"OffUntil": 0
		}
	})

def update_record(chat_id: int | str, new_value: dict):
	"""
	Обновляет запись в БД.
	"""

	USER_BASE[str(chat_id)].update({
		**new_value,
		"_isUpdated": True
	})	

def add_database_message(chat_id: int | str, message_text: str):
	"""
	Добавляет текст полученного сообщения в базу.
	"""

	message_text = message_text.strip()

	if not message_text:
		return

	new_messages = USER_BASE[str(chat_id)]["Messages"]
	new_messages.append(message_text)

	update_record(
		chat_id,
		{
			"Messages": new_messages
		}
	)

@DP.message_handler()
async def message_handler(msg: MessageType):
	"""
	Вызывается при получении любого нового сообщения (кроме тех, что в личном чате.)
	"""

	# Сохраняем текст сообщения в базу данных.
	message_text = msg.text or msg.caption

	add_database_message(
		msg.chat.id,
		message_text
	)

	# Проверяем, включена ли генерация:
	if USER_BASE[str(msg.chat.id)]["OffUntil"] > int(time.time()) and USER_BASE[str(msg.chat.id)]["OffUntil"]:
		return

	# Генерируем случайное сообщение.
	# Для начала мы проверяем, упомянули ли где-то бота: если да, то шанс повысится.

	is_triggered = any([i for i in ["макс", "max", "@maxzens_bot"] if i in message_text.lower()])

	# Проверяем, есть ли ответ на сообщение бота:
	if msg.reply_to_message and not is_triggered:
		is_triggered = msg.reply_to_message.from_user.id == BOT.id

	# Рандомный шанс.
	if random.randint(1, 100) > (80 if is_triggered else 8):
		return


	# Сам процесс генерации нового сообщения.
	# Используется Цепь Маркова.

	# Создаём модель текста.
	# TODO: Есть ли какой-то метод *добавлять* новые сообщения в модель, что бы
	# каждый раз не нагружать бота, заставляя его загружать одну и ту же модель?
	model = markovify.NewlineText("\n".join(USER_BASE[str(msg.chat.id)]["Messages"]).lower())

	# Генерируем сообщение.
	# С шансом 33% будет "длинное" сообщение, с шансом 66% - "короткое" (<=50 символов).
	msg_generated = model.make_sentence(tries=10) if (random.randint(0, 2) == 2) else model.make_short_sentence(50, tries=100)

	# Если ничего не удалось сгенерировать, то с шансом 50% бот попробует достать случайное
	# сообщение из базы.
	if not msg_generated and random.randint(0, 1):
		msg_generated = random.choice(USER_BASE[str(msg.chat.id)]["Messages"])

	if msg_generated:
		# Сообщение было успешно сгенерировано. Фильтруем, удаляем упоминания:
		msg_generated = re.sub(r"@(\w*)", "<i><a href=\"https://t.me/\\1\">@\\1</a></i>", msg_generated)

		# Отправляем сгенерированное сообщение :)

		await asyncio.sleep(random.uniform(0, 1))

		await msg.bot.send_chat_action(msg.chat.id, "typing")
		await asyncio.sleep(random.uniform(1, 3))

		# С шансом 50% будет reply, с шансом 50% - обычное сообщение.
		if random.randint(0, 1):
			await msg.answer(msg_generated, disable_notification=True, allow_sending_without_reply=True, disable_web_page_preview=True)
		else:
			await msg.reply(msg_generated, disable_notification=True, allow_sending_without_reply=True, disable_web_page_preview=True)


if __name__ == "__main__":
	loop = asyncio.new_event_loop()
	asyncio.set_event_loop(loop)

	# Создаём папку, в которой будут храниться будущие сообщения:
	os.makedirs("db", exist_ok=True)

	# Регистрируем Middlware:
	DP.middleware.setup(
		BotMessagesMiddleware(populate_base)
	)

	# Создаём фоновую задачу для сохранения базы:
	loop.create_task(bg_saver())

	# Запускаем бота:
	aiogram.utils.executor.start_polling(
		dispatcher=DP,
		on_startup=onBotStart,
		skip_updates=True,
		loop=loop,
	)
