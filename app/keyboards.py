from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from constants import (
    DRIVING_CATEGORIES,
    REGIONS,
    button_create_resume,
    button_delete_resume,
    button_edit_resume,
    button_my_resume,
    button_send_phone,
)

phone_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=button_send_phone, request_contact=True)]],
    resize_keyboard=True,
    one_time_keyboard=True,
)

keyboard_place_of_living = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text=f"{v}", callback_data=f"region_{k}")
            for k, v in REGIONS.items()
            if k in list(REGIONS.keys())[i : i + 2]
        ]
        for i in range(0, len(REGIONS), 2)
    ]
)


keyboard_driver_categories = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text=cat, callback_data=f"category_{cat}")]
        for cat in DRIVING_CATEGORIES
    ]
)


def get_main_menu_keyboard(has_resume: bool = False) -> ReplyKeyboardMarkup:
    """
    Get main menu keyboard based on whether user has a resume.

    Args:
        has_resume: True if user has a resume, False otherwise

    Returns:
        ReplyKeyboardMarkup with appropriate button
    """
    button_text = button_my_resume if has_resume else button_create_resume

    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=button_text)]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


main_menu_keyboard = get_main_menu_keyboard(has_resume=False)


delete_resume_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text=button_edit_resume, callback_data="edit_resume_menu"),
            InlineKeyboardButton(text=button_delete_resume, callback_data="delete_resume_confirm")
        ]
    ]
)
