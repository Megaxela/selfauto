import typing as tp
import logging
import traceback
import dataclasses
import asyncio

from selfauto.components.basic_component import BasicComponent

import telegram
import telegram.ext
import telegram.error

logger = logging.getLogger(__name__)

DEFAULT_ERROR_NOTIFY_TEXT = """
⚙️ Internal error occured
```
{error_details}
```
"""


class ApplicationRunner:
    def __init__(self, app, error_cb):
        self._app = app
        self._error_cb = error_cb

    async def __aenter__(self, *args):
        await self._app.initialize()
        if self._app.post_init:
            self._app.post_init(self._app)

        await self._app.updater.start_polling(error_callback=self._error_cb)

        await self._app.start()

        return self

    async def __aexit__(self, *args):
        await self._app.stop()
        await self._app.updater.stop()
        await self._app.shutdown()


class TelegramComponent(BasicComponent):
    NAME = "telegram"

    @dataclasses.dataclass()
    class Config:
        bot_token: str

        @staticmethod
        def make_default():
            return Config(bot_token="<telegram_bot_token>")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._app: tp.Optional[telegram.ext.Application] = None
        self._error_notify_text = DEFAULT_ERROR_NOTIFY_TEXT

    @staticmethod
    def __dummy_escape(text: str):
        return text.replace(".", "\.")

    async def __error_handler(
        self,
        update: telegram.Update,
        context: telegram.ext.ContextTypes.DEFAULT_TYPE,
    ):
        logger.error("Error occured, during bot execution", exc_info=context.error)

        traceback_list = traceback.format_exception(
            None, context.error, context.error.__traceback__
        )
        traceback_str = "".join(traceback_list)
        print(traceback_str)

        text = self._error_notify_text.format(error_details=traceback_str[:3500])
        print(text)

        if update is None:
            await self.notify(
                text=text,
                parse_mode=telegram.constants.ParseMode.MARKDOWN_V2,
            )
            return

        await self._app.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            parse_mode=telegram.constants.ParseMode.MARKDOWN_V2,
        )

    def __run_error_callback(self, exc: telegram.error.TelegramError):
        try:
            self._app.create_task(self._app.process_error(error=exc, update=None))
        except Exception as e:
            logger.error(f"Internal error during error processing", exc_info=e)

    @property
    def application(self) -> telegram.ext.Application:
        return self._app

    def add_handler(self, handler):
        self._app.add_handler(handler)

    async def notify(self, *args, **kwargs):
        for chat_id in self._app.chat_data:
            try:
                await self._app.bot.send_message(*args, chat_id=chat_id, **kwargs)
            except Exception as e:
                logger.error("Unable to notify %s chat", str(chat_id), exc_info=e)

    async def on_initialize(self, config: Config):
        self._app = telegram.ext.Application.builder().token(config.bot_token).build()
        self._app.add_error_handler(self.__error_handler)
        self._app.add_handler(telegram.ext.CommandHandler("test", self.__test))

    async def __test(
        self, update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE
    ):
        await notify(text="Hello")

    async def run(self):
        async with ApplicationRunner(self._app, self.__run_error_callback):
            while 1:
                await asyncio.sleep(1)
