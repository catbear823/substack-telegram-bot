TELEGRAM_MAX_LENGTH = 4096


def split_message(text: str, max_length: int = TELEGRAM_MAX_LENGTH) -> list[str]:
    if len(text) <= max_length:
        return [text]

    parts = []
    while text:
        if len(text) <= max_length:
            parts.append(text)
            break

        split_pos = text.rfind("\n", 0, max_length)
        if split_pos == -1:
            split_pos = text.rfind("。", 0, max_length)
        if split_pos == -1:
            split_pos = text.rfind("，", 0, max_length)
        if split_pos == -1:
            split_pos = max_length

        parts.append(text[:split_pos + 1])
        text = text[split_pos + 1:].lstrip("\n")

    return parts


async def send_long_message(message, text: str, reply_markup=None, parse_mode="Markdown", disable_web_page_preview=True):
    parts = split_message(text)

    for i, part in enumerate(parts):
        if i == 0:
            try:
                await message.answer(part, reply_markup=reply_markup, parse_mode=parse_mode, disable_web_page_preview=disable_web_page_preview)
            except Exception:
                await message.answer(part, reply_markup=reply_markup, disable_web_page_preview=disable_web_page_preview)
        else:
            try:
                await message.answer(part, parse_mode=parse_mode, disable_web_page_preview=disable_web_page_preview)
            except Exception:
                await message.answer(part, disable_web_page_preview=disable_web_page_preview)
