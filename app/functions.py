import logging

from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from constants import (
    button_confirm,
    error_invalid_index,
    error_no_selection,
    error_processing,
    msg_selected_template,
)

logger = logging.getLogger(__name__)


async def safe_callback_answer(
    callback: CallbackQuery, text: str | None = None, show_alert: bool = False
) -> None:
    """
    Safely answer a callback query, handling expired or invalid queries.
    
    Args:
        callback: The CallbackQuery to answer
        text: Optional text to show
        show_alert: Whether to show as alert
    """
    try:
        await callback.answer(text=text, show_alert=show_alert)
    except TelegramBadRequest as e:
        # Query is too old, already answered, or invalid - just log and ignore
        logger.debug(
            "Callback query answer failed (likely expired): %s", str(e), exc_info=False
        )
    except Exception as e:
        # Other unexpected errors - log but don't crash
        logger.warning(
            "Unexpected error answering callback query: %s", str(e), exc_info=True
        )


async def get_updated_keyboard(
    selected: set[str], categories: list[str], prefix: str
) -> InlineKeyboardMarkup:
    """
    Universal multiple button choosing func.
    Uses index-based callback_data to avoid exceeding 64-byte limit.
    """
    keyboard = []
    for idx, cat in enumerate(categories):
        text = f"{cat}{' ✔' if cat in selected else ''}"
        callback_data = f"{prefix}{idx}"
        if len(callback_data.encode("utf-8")) > 64:
            callback_data = f"{prefix}{cat[:20]}"
            if len(callback_data.encode("utf-8")) > 64:
                callback_data = callback_data[:60]

        keyboard.append([InlineKeyboardButton(text=text, callback_data=callback_data)])

    keyboard.append([InlineKeyboardButton(text=button_confirm, callback_data=f"{prefix}submit")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def toggle_selection(
    callback: CallbackQuery,
    state: FSMContext,
    prefix: str,
    field_name: str,
    options: list[str],
    next_state=None,
) -> None:
    """
    Universal toggle for inline-buttons.
    Handles both index-based and text-based callback_data for compatibility.
    """
    data = await state.get_data()
    selected = set(data.get(field_name, []))

    if not callback.data.startswith(prefix):
        await safe_callback_answer(callback, error_processing, show_alert=True)
        return

    item_id = callback.data[len(prefix) :]

    if item_id == "submit":
        if not selected:
            await safe_callback_answer(callback, error_no_selection, show_alert=True)
            return

        await callback.message.edit_reply_markup()
        await callback.message.answer(
            msg_selected_template.format(items=", ".join(sorted(selected)))
        )

        if next_state:
            await state.set_state(next_state)

        return

    try:
        idx = int(item_id)
        if 0 <= idx < len(options):
            item = options[idx]
        else:
            await safe_callback_answer(callback, error_invalid_index, show_alert=True)
            return
    except ValueError:
        item = item_id

    if item in selected:
        selected.remove(item)
    else:
        selected.add(item)

    await state.update_data(**{field_name: list(selected)})

    keyboard: InlineKeyboardMarkup = await get_updated_keyboard(
        selected=selected, categories=options, prefix=prefix
    )

    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await safe_callback_answer(callback)
