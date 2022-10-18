from html import escape
from secrets import choice
from Powers.vars import Config
from traceback import format_exc
from Powers.bot_class import Gojo
from pyrogram.errors import RPCError
from Powers.utils.kbhelpers import ikb
from Powers.utils.msg_types import Types
from Powers.database.chats_db import Chats
from Powers.database.notes_db import Notes
from Powers.database.rules_db import Rules
from Powers.utils.cmd_senders import send_cmd
from Powers import LOGGER, HELP_COMMANDS, SUPPORT_GROUP
from pyrogram.types import Message, CallbackQuery, InlineKeyboardButton
from Powers.utils.string import (
    parse_button, build_keyboard, escape_mentions_using_curly_brackets)


# Initialize
notes_db = Notes()


async def gen_cmds_kb(m: Message or CallbackQuery):
    """Generate the keyboard"""
    if isinstance(m, CallbackQuery):
        m = m.message

    cmds = sorted(list(HELP_COMMANDS.keys()))
    kb = [cmd.lower() for cmd in cmds]

    return [kb[i : i + 3] for i in range(0, len(kb), 3)]


async def gen_start_kb(q: Message or CallbackQuery):
    """Generate keyboard with start menu options."""
    return ikb(
        [
            [
                (
                    "➕ Add me to a chat!",
                    f"https://t.me/{Config.BOT_USERNAME}?startgroup=new",
                    "url",
                ),
                (
                    "Support 👥",
                    f"https://t.me/{SUPPORT_GROUP}",
                    "url",
                ),
            ],
            [("📚 Commands & Help", "commands")],
            [
                (
                    "🗃️ Source Code",
                    "https://github.com/Gojo-Bots/Gojo_Satarou",
                    "url",
                ),
                (
                    "Owner ❤️",
                    f"https://t.me/iamgojoof6eyes",
                    "url",
                ),
            ],
            [
                (
                    "Join for GFx work",
                    "https://t.me/psy_Logos",
                    "url",
                ),
            ],
        ],
    )


async def get_private_note(c: Gojo, m: Message, help_option: str):
    """Get the note in pm of user, with parsing enabled."""
    help_lst = help_option.split("_")
    if len(help_lst) == 2:
        chat_id = int(help_lst[1])

        all_notes = notes_db.get_all_notes(chat_id)
        chat_title = Chats.get_chat_info(chat_id)["chat_name"]
        rply = f"Notes in {chat_title}:\n\n"
        note_list = [
            f"- [{note[0]}](https://t.me/{Config.BOT_USERNAME}?start=note_{chat_id}_{note[1]})"
            for note in all_notes
        ]
        rply = "\n".join(note_list)
        rply += "You can retrieve these notes by tapping on the notename."
        await m.reply_text(rply, disable_web_page_preview=True, quote=True)
        return

    if len(help_lst) != 3:
        return

    note_hash = help_option.split("_")[2]
    getnotes = notes_db.get_note_by_hash(note_hash)
    if not getnotes:
        await m.reply_text("Note does not exist", quote=True)
        return

    msgtype = getnotes["msgtype"]
    if not msgtype:
        await m.reply_text(
            "<b>Error:</b> Cannot find a type for this note!!",
            quote=True,
        )
        return

    try:
        # support for random notes texts
        splitter = "%%%"
        note_reply = getnotes["note_value"].split(splitter)
        note_reply = choice(note_reply)
    except KeyError:
        note_reply = ""

    parse_words = [
        "first",
        "last",
        "fullname",
        "username",
        "id",
        "chatname",
        "mention",
    ]
    text = await escape_mentions_using_curly_brackets(m, note_reply, parse_words)

    if msgtype == Types.TEXT:

        teks, button = await parse_button(text)
        button = await build_keyboard(button)
        button = ikb(button) if button else None
        if button:
            try:
                await m.reply_text(
                    teks,
                    reply_markup=button,
                    disable_web_page_preview=True,
                    quote=True,
                )
                return
            except RPCError as ef:
                await m.reply_text(
                    "An error has occured! Cannot parse note.",
                    quote=True,
                )
                LOGGER.error(ef)
                LOGGER.error(format_exc())
                return
        else:
            await m.reply_text(teks, quote=True, disable_web_page_preview=True)
            return
    elif msgtype in (
        Types.STICKER,
        Types.VIDEO_NOTE,
        Types.CONTACT,
        Types.ANIMATED_STICKER,
    ):
        await (await send_cmd(c, msgtype))(m.chat.id, getnotes["fileid"])
    else:
        if getnotes["note_value"]:
            teks, button = await parse_button(getnotes["note_value"])
            button = await build_keyboard(button)
            button = ikb(button) if button else None
        else:
            teks = ""
            button = None
        if button:
            try:
                await (await send_cmd(c, msgtype))(
                    m.chat.id,
                    getnotes["fileid"],
                    caption=teks,
                    reply_markup=button,
                )
                return
            except RPCError as ef:
                await m.reply_text(
                    teks,
                    quote=True,
                    reply_markup=button,
                    disable_web_page_preview=True,
                )
                LOGGER.error(ef)
                LOGGER.error(format_exc())
                return
        else:
            await (await send_cmd(c, msgtype))(
                m.chat.id,
                getnotes["fileid"],
                caption=teks,
            )
    LOGGER.info(
        f"{m.from_user.id} fetched privatenote {note_hash} (type - {getnotes}) in {m.chat.id}",
    )
    return


async def get_private_rules(_, m: Message, help_option: str):
    chat_id = int(help_option.split("_")[1])
    rules = Rules(chat_id).get_rules()
    chat_title = Chats.get_chat_info(chat_id)["chat_name"]
    if not rules:
        await m.reply_text(
            "The Admins of that group have not setup any rules, that dosen't mean you break the decorum of the chat!",
            quote=True,
        )
        return ""
    await m.reply_text(
        f"""The rules for <b>{escape(chat_title)} are</b>:\n
{rules}
""",
        quote=True,
        disable_web_page_preview=True,
    )
    return ""


async def get_help_msg(m: Message or CallbackQuery, help_option: str):
    """Helper function for getting help_msg and it's keyboard."""
    help_msg = None
    help_kb = None
    help_cmd_keys = sorted(
        k
        for j in [HELP_COMMANDS[i]["alt_cmds"] for i in list(HELP_COMMANDS.keys())]
        for k in j
    )

    if help_option in help_cmd_keys:
        help_option_name = next(
            HELP_COMMANDS[i]
            for i in HELP_COMMANDS
            if help_option in HELP_COMMANDS[i]["alt_cmds"]
        )
        help_option_value = help_option_name["help_msg"]
        help_kb = next(
            HELP_COMMANDS[i]["buttons"]
            for i in HELP_COMMANDS
            if help_option in HELP_COMMANDS[i]["alt_cmds"]
        ) + [[("« " + "Back", "commands")]]
        help_msg = f"**{(help_option_value)}:**"
        LOGGER.info(
            f"{m.from_user.id} fetched help for {help_option} in {m.chat.id}",
        )
    else:
        help_msg = """
Hey There! My name is Gojo.
I'm here to help you manage your groups!
Commands available:
* /start: Start the bot
* /help: Give's you this message.
        """
        help_kb = [
            *(await gen_cmds_kb(m)),
            [
                InlineKeyboardButton(
                    "« Back",
                    callback_data="start_back",
                ),
            ],
        ]

    return help_msg, help_kb
