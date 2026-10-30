import asyncio
import logging

from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Envía alertas de GroupWatch a un chat de Telegram."""

    def __init__(self, token: str, chat_id: str):
        # Validación explícita de credenciales para fallar pronto y con claridad
        if not token:
            raise ValueError("El token de Telegram no puede estar vacío ni ser None")
        if not chat_id:
            raise ValueError("El chat_id de Telegram no puede estar vacío ni ser None")

        self.token = token
        self.chat_id = str(chat_id)
        self.bot = Bot(token=self.token)

    def send(self, message: str) -> bool:
        """Envía un mensaje Markdown al chat configurado.

        Devuelve True si el envío fue correcto y False si Telegram devolvió error.
        """
        try:
            asyncio.run(
                self.bot.send_message(
                    chat_id=self.chat_id,
                    text=message,
                    parse_mode="Markdown",
                )
            )
            logger.debug("Mensaje enviado a Telegram (chat_id=%s)", self.chat_id)
            return True
        except TelegramError as exc:
            logger.error("Error al enviar mensaje a Telegram: %s", exc)
            return False
        except Exception as exc:  # Red de seguridad ante fallos inesperados de red
            logger.error("Fallo inesperado enviando a Telegram: %s", exc)
            return False

    def test_connection(self) -> bool:
        """Envía un mensaje de prueba para verificar la configuración."""
        return self.send("GroupWatch conectado correctamente")
