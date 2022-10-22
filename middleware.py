# coding: utf-8

# Простой Middleware для бота, который будет выполняться перед
# любыми другими Handler'ами бота, если пользователь написал
# боту в ЛС.

from aiogram import Dispatcher
from aiogram.dispatcher.handler import CancelHandler, current_handler
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.types import Message as MessageType


class BotMessagesMiddleware(BaseMiddleware):
	"""
	Простой Middleware для бота, который будет выполняться перед другими Handler'ами бота, если пользователь написал боту в ЛС.
	Так же, этот Middleware добавляет базовую запись в базу данных, если такого чата в базе нет. 
	"""

	def __init__(self, func):
		self.db_func = func

		super(BotMessagesMiddleware, self).__init__()

	async def on_process_message(self, msg: MessageType, data: dict):
		handler = current_handler.get()
		DP 		= Dispatcher.get_current()

		# Проверяем, где было отправлено сообщение:
		
		if msg.chat.type == "private":
			await msg.answer("<b>Привет! 👋</b>\n\nЯ — простой бот для веселья, способный работать <b>только в беседах</b>.\nПожалуйста, добавь меня в беседу, что бы продолжить! 😌")

			raise CancelHandler()

		# В ином случае, просто добавляем базовую запись в БД:

		self.db_func(msg.chat.id)
