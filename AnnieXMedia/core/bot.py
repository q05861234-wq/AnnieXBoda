# Authored By Certified Coders © 2025
import sys
from pyrogram import Client, errors
from pyrogram.enums import ChatMemberStatus

import config
from ..logging import LOGGER


class MusicBotClient(Client):
    def __init__(self):
        super().__init__(
            name="AnnieXMusic",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            bot_token=config.BOT_TOKEN,
            workers=48,
            max_concurrent_transmissions=7,
        )
        LOGGER(__name__).info("تم تهيئة عميل البوت بنجاح وجاهز للاقلاع.")

    async def start(self, *args, **kwargs):
        await super().start()
        
        me = await self.get_me()
        self.username, self.id = me.username, me.id
        self.name = f"{me.first_name} {me.last_name or ''}".strip()
        self.mention = me.mention

        try:
            await self.send_message(
                config.LOGGER_ID,
                (
                    f"<u><b>» {self.mention} يـا عـزيـزي لـقـد بـدأ الـعـمـل :</b></u>\n\n"
                    f"الايـدي : <code>{self.id}</code>\n"
                    f"الاسـم : {self.name}\n"
                    f"الـمـعـرف : @{self.username}"
                ),
            )
        except (errors.ChannelInvalid, errors.PeerIdInvalid):
            LOGGER(__name__).error("البوت لا يستطيع الوصول لمجموعة السجل (Logger Group) - تاكد من اضافته ورفعه مشرفا!")
            sys.exit()
        except Exception as exc:
            LOGGER(__name__).error(f"فشل البوت في الاتصال بمجموعة السجل.\nالسبب: {type(exc).__name__}")
            sys.exit()

        try:
            member = await self.get_chat_member(config.LOGGER_ID, self.id)
            if member.status != ChatMemberStatus.ADMINISTRATOR:
                LOGGER(__name__).error("يرجى رفع البوت مشرفا (Admin) في مجموعة السجل ليعمل بشكل صحيح.")
                sys.exit()
        except Exception as e:
            LOGGER(__name__).error(f"فشل التحقق من صلاحيات المشرف: {e}")
            sys.exit()

        LOGGER(__name__).info(f"تم بدء تشغيل بوت الميوزك بنجاح باسم: {self.name} (@{self.username})")
