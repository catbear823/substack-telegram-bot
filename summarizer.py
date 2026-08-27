import asyncio
from openai import OpenAI

from config import OPENROUTER_API_KEY, LLM_MODEL, LLM_FALLBACK_MODEL, GLM_API_KEY, GLM_MODEL

SYSTEM_PROMPT = """你是一個專業的 Substack 文章摘要助手。你的工作是：
1. 為文章生成簡潔、有重點的中文摘要
2. 根據已抓取的文章內容回答使用者問題
3. 摘要應包含：核心觀點、關鍵數據、結論

回答規則：
- 使用繁體中文
- 摘要要簡潔有力，控制在 200-300 字
- 使用條列式呈現要點
- 如果問題與文章無關，誠實告知
- 引用文章時標明出處"""


def _get_openrouter_client():
    return OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
    )


def _get_glm_client():
    return OpenAI(
        api_key=GLM_API_KEY,
        base_url="https://open.bigmodel.cn/api/paas/v4/",
    )


def _chat_sync(messages: list[dict], model: str, temperature: float = 0.3, max_tokens: int = 1024, use_glm: bool = False) -> str:
    if use_glm:
        client = _get_glm_client()
    else:
        client = _get_openrouter_client()

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    content = response.choices[0].message.content.strip()

    if not content or "User Safety" in content or "safety" in content.lower():
        return ""

    return content


async def _chat(messages: list[dict], temperature: float = 0.3, max_tokens: int = 1024) -> str:
    if GLM_API_KEY:
        try:
            result = await asyncio.to_thread(
                _chat_sync, messages, GLM_MODEL, temperature, max_tokens, True
            )
            if result:
                return result
        except Exception as e:
            print(f"GLM error: {e}")

    try:
        result = await asyncio.to_thread(
            _chat_sync, messages, LLM_MODEL, temperature, max_tokens, False
        )
        if result:
            return result
    except Exception as e:
        print(f"OpenRouter error: {e}")

    try:
        result = await asyncio.to_thread(
            _chat_sync, messages, LLM_FALLBACK_MODEL, temperature, max_tokens, False
        )
        if result:
            return result
    except Exception as e:
        print(f"OpenRouter fallback error: {e}")

    return ""


async def summarize_article(title: str, content: str, max_length: int = 1000) -> str:
    if not content or len(content.strip()) < 50:
        return "文章內容不足，無法生成摘要。"

    truncated = content[:15000]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"請為以下文章生成一個詳細的中文摘要（約{max_length}字，使用條列式，包含主要觀點、關鍵數據、結論）：\n\n標題：{title}\n\n內容：\n{truncated}",
        },
    ]

    result = await _chat(messages, temperature=0.3, max_tokens=2048)
    if not result:
        return f"⚠️ 無法生成摘要（AI 服務暫時不可用）\n\n📄 標題：{title}\n🔗 請點擊「閱讀全文」查看原文"
    return result


async def answer_question(
    question: str, context_articles: list[dict], chat_history: list[dict] = None
) -> str:
    context_parts = []
    for i, article in enumerate(context_articles, 1):
        summary = article.get("summary") or article.get("content", "")[:3000]
        context_parts.append(
            f"[文章{i}] {article.get('title', '未知')}\n來源：{article.get('url', '')}\n摘要/內容：\n{summary}\n"
        )

    context_str = "\n---\n".join(context_parts) if context_parts else "（目前沒有已抓取的文章）"

    history_str = ""
    if chat_history:
        history_lines = []
        for msg in chat_history[-6:]:
            role = "使用者" if msg["role"] == "user" else "助手"
            history_lines.append(f"{role}：{msg['message'][:200]}")
        history_str = "\n".join(history_lines)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"""基於以下已抓取的 Substack 文章，回答使用者的問題。

===已抓取的文章===
{context_str}

===對話歷史===
{history_str}

===使用者問題===
{question}

請用繁體中文詳細回答。如果問題與提供的文章相關，請引用具體文章內容。""",
        },
    ]

    result = await _chat(messages, temperature=0.5, max_tokens=1500)
    if not result:
        return "⚠️ 無法生成回答（AI 服務暫時不可用），請稍後再試"
    return result


async def generate_digest(articles: list[dict]) -> str:
    if not articles:
        return "目前沒有新文章。"

    summaries = []
    for i, article in enumerate(articles[:5], 1):
        summary = article.get("summary", "尚無摘要")
        summaries.append(
            f"{i}. **{article.get('title', 'Untitled')}**\n"
            f"   作者：{article.get('author', 'Unknown')}\n"
            f"   摘要：{summary[:500]}\n"
            f"   連結：{article.get('url', '')}\n"
        )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"""為以下 Substack 文章生成一份簡潔的每日摘要：

{"".join(summaries)}

請用繁體中文生成一份結構化的摘要，包含：
1. 今日重點（1-2句總結）
2. 各文章簡述
3. 趨勢觀察（如果有）""",
        },
    ]

    result = await _chat(messages, temperature=0.4, max_tokens=1024)
    if not result:
        return "⚠️ 無法生成摘要（AI 服務暫時不可用）"
    return result
