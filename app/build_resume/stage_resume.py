import logging
import re
import sys
from pathlib import Path

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

# Add project root to path for firebase_db imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Initialize logger first
logger = logging.getLogger(__name__)

# Initialize Firebase before importing crud
try:
    import firebase_db.config  # noqa: F401
except Exception as e:
    logger.warning(f"Firebase config not initialized: {str(e)}")

from constants import (
    DOCS_FOR_DRIVING_ABROAD,
    DRIVING_CATEGORIES,
    DRIVING_CATEGORIES_ADDITIONAL_INFO,
    RACE_DURATION_OPTIONS,
    REGIONS,
    SEMI_TRAILERS_TYPES,
    TYPES_OF_WORK,
    ask_age,
    ask_description,
    ask_desired_salary,
    ask_docs_for_driving_abroad,
    ask_driving_categories,
    ask_driving_exp_template,
    ask_is_adr_license,
    ask_military_booking,
    ask_phone,
    ask_place_of_living_region,
    ask_race_duration,
    ask_semi_trailer_types,
    ask_type_of_work,
    ask_types_of_cars,
    button_adr_no,
    button_adr_yes,
    button_military_no,
    button_military_yes,
    button_skip_description,
    error_age_empty,
    error_age_has_spaces,
    error_city_empty,
    error_city_only_digits,
    error_city_too_long,
    error_city_too_short,
    error_description_too_long,
    error_invalid_age,
    error_invalid_index,
    error_invalid_phone,
    error_invalid_years,
    error_name_empty,
    error_name_invalid_format,
    error_name_single_word,
    error_name_too_long,
    error_name_too_short,
    error_no_selection,
    error_no_semi_trailer,
    error_not_numeric,
    error_processing,
    error_salary_empty,
    error_salary_invalid_format,
    error_salary_too_high,
    error_salary_too_low,
    error_types_of_cars_cyrillic_template,
    error_types_of_cars_empty,
    error_types_of_cars_invalid_chars,
    error_types_of_cars_invalid_format,
    error_types_of_cars_no_letters,
    error_types_of_cars_too_long,
    error_types_of_cars_too_short,
    hint_place_of_living_city,
    msg_adr_no,
    msg_adr_yes,
    msg_all_data_collected,
    msg_bot_greeting,
    msg_military_no,
    msg_military_yes,
    msg_resume_saved,
    msg_selected_template,
    resume_display_adr_license,
    resume_display_age,
    resume_display_description,
    resume_display_docs_abroad,
    resume_display_driving_categories,
    resume_display_driving_experience,
    resume_display_location,
    resume_display_military_booking,
    resume_display_name,
    resume_display_phone,
    resume_display_race_duration,
    resume_display_salary,
    resume_display_semi_trailer_types,
    resume_display_title,
    resume_display_type_of_work,
    resume_display_types_of_cars,
)
from functions import get_updated_keyboard, toggle_selection
from keyboards import get_main_menu_keyboard, keyboard_place_of_living, phone_keyboard
from logging_config import (
    get_user_info,
    log_error,
    log_info,
    log_warning,
    sanitize_name,
    sanitize_phone,
    sanitize_text,
)

from firebase_db.crud import add_resume


class ResumeForm(StatesGroup):
    name = State()
    phone = State()
    age = State()
    place_of_living_region = State()
    place_of_living_city = State()
    driving_categories = State()
    driving_exp_per_category = State()
    driving_semi_trailer_types = State()
    type_of_work = State()
    desired_salary = State()
    types_of_cars = State()
    is_adr_license = State()
    race_duration_preference = State()

    docs_for_driving_abroad = State()
    military_booking = State()

    description = State()


async def process_name(message: Message, state: FSMContext) -> None:
    """Process the user's name with validation and move to the next state."""
    try:
        user_info = get_user_info(message)
        name = message.text.strip()

        if not name:
            log_warning(
                logger,
                action="name_validation_failed",
                reason="empty_input",
                user_id=user_info["user_id"],
                username=user_info["username"]
            )
            await message.answer(error_name_empty)
            return

        if len(name) < 2:
            log_warning(
                logger,
                action="name_validation_failed",
                reason="too_short",
                user_id=user_info["user_id"],
                username=user_info["username"],
                length=len(name)
            )
            await message.answer(error_name_too_short)
            return

        if len(name) > 100:
            log_warning(
                logger,
                action="name_validation_failed",
                reason="too_long",
                user_id=user_info["user_id"],
                username=user_info["username"],
                length=len(name)
            )
            await message.answer(error_name_too_long)
            return

        if not all(char.isalpha() or char.isspace() or char == "-" for char in name):
            sanitized_name = sanitize_name(name)
            log_warning(
                logger,
                action="name_validation_failed",
                reason="invalid_format",
                user_id=user_info["user_id"],
                username=user_info["username"],
                name=sanitized_name
            )
            await message.answer(error_name_invalid_format, parse_mode="HTML")
            return

        name_words = [word for word in name.split() if word.strip()]
        if len(name_words) < 2:
            sanitized_name = sanitize_name(name)
            log_warning(
                logger,
                action="name_validation_failed",
                reason="single_word",
                user_id=user_info["user_id"],
                username=user_info["username"],
                name=sanitized_name
            )
            await message.answer(error_name_single_word, parse_mode="HTML")
            return

        sanitized_name = sanitize_name(name)
        await state.update_data(name=name)
        log_info(
            logger,
            action="name_collected",
            user_id=user_info["user_id"],
            username=user_info["username"],
            name=sanitized_name
        )
        await state.set_state(ResumeForm.phone)
        log_info(
            logger,
            action="asking_for_phone",
            user_id=user_info["user_id"]
        )
        await message.answer(
            ask_phone,
            reply_markup=phone_keyboard,
        )
    except Exception as e:
        user_info = get_user_info(message)
        log_error(
            logger,
            action="name_processing_failed",
            error=str(e),
            user_id=user_info["user_id"],
            username=user_info["username"],
            exc_info=True
        )


async def process_phone(message: Message, state: FSMContext) -> None:
    """Process the user's phone number and move to the next state."""
    try:
        user_info = get_user_info(message)
        phone_number = None

        if message.contact and message.contact.phone_number:
            phone_number = message.contact.phone_number
            sanitized_phone = sanitize_phone(phone_number)
            logger.info(
                "Collected phone number via button - user_id: %s, username: %s, phone: %s",
                user_info["user_id"],
                user_info["username"],
                sanitized_phone,
            )
        else:
            phone_number = message.text
            valid_numb = re.match(r"^\+380\d{9}$", phone_number)
            if not valid_numb:
                sanitized_phone = sanitize_phone(phone_number)
                logger.warning(
                    "Invalid phone format - user_id: %s, input: %s",
                    user_info["user_id"],
                    sanitized_phone,
                )
                await message.answer(error_invalid_phone)
                return

        await state.update_data(phone=phone_number)
        sanitized_phone = sanitize_phone(phone_number)
        logger.info(
            "Collected phone number - user_id: %s, phone: %s", user_info["user_id"], sanitized_phone
        )
        await state.set_state(ResumeForm.age)
        logger.info("Asking for age - user_id: %s", user_info["user_id"])
        await message.answer(ask_age)
    except Exception as e:
        user_info = get_user_info(message)
        logger.error(
            "Error processing phone - user_id: %s, error: %s",
            user_info["user_id"],
            str(e),
            exc_info=True,
        )


async def process_age(message: Message, state: FSMContext) -> None:
    """Process the user's age with validation and move to the next state."""
    try:
        user_info = get_user_info(message)
        age_text = message.text.strip()

        if not age_text:
            logger.warning("Empty age input - user_id: %s", user_info["user_id"])
            await message.answer(error_age_empty)
            return

        if " " in age_text:
            logger.warning(
                "Age contains spaces - user_id: %s, input: %s", user_info["user_id"], age_text
            )
            await message.answer(error_age_has_spaces, parse_mode="HTML")
            return

        if not age_text.isdigit() or not (18 <= int(age_text) <= 100):
            logger.warning(
                "Invalid age input - user_id: %s, input: %s", user_info["user_id"], age_text
            )
            await message.answer(error_invalid_age)
            return

        await state.update_data(age=int(age_text))
        logger.info(
            "Collected age - user_id: %s, username: %s, age: %s",
            user_info["user_id"],
            user_info["username"],
            age_text,
        )

        await state.set_state(ResumeForm.place_of_living_region)
        logger.info("Asking for place of living region - user_id: %s", user_info["user_id"])

        await message.answer(ask_place_of_living_region, reply_markup=keyboard_place_of_living)
    except Exception as e:
        user_info = get_user_info(message)
        logger.error(
            "Error processing age - user_id: %s, error: %s",
            user_info["user_id"],
            str(e),
            exc_info=True,
        )


async def process_place_of_region_callback(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        user_info = get_user_info(callback)
        region = callback.data.replace("region_", "")
        sanitized_region = sanitize_text(region)

        await state.update_data(place_of_living_region=region)
        logger.info(
            "Collected place of living region - user_id: %s, username: %s, region: %s",
            user_info["user_id"],
            user_info["username"],
            sanitized_region,
        )

        await state.set_state(ResumeForm.place_of_living_city)
        await callback.message.edit_reply_markup()
        logger.info("Asking for place of living city - user_id: %s", user_info["user_id"])

        await callback.message.answer(hint_place_of_living_city)
    except Exception as e:
        user_info = get_user_info(callback)
        logger.error(
            "Error processing place of region - user_id: %s, error: %s",
            user_info["user_id"],
            str(e),
            exc_info=True,
        )


async def process_place_of_city(message: Message, state: FSMContext) -> None:
    """Process the user's city with validation and move to the next state."""
    try:
        user_info = get_user_info(message)
        city = message.text.strip()

        if not city:
            logger.warning("Empty city input - user_id: %s", user_info["user_id"])
            await message.answer(error_city_empty, parse_mode="HTML")
            return

        if len(city) < 2:
            logger.warning(
                "City too short - user_id: %s, length: %s", user_info["user_id"], len(city)
            )
            await message.answer(error_city_too_short, parse_mode="HTML")
            return

        if len(city) > 100:
            logger.warning(
                "City too long - user_id: %s, length: %s", user_info["user_id"], len(city)
            )
            await message.answer(error_city_too_long, parse_mode="HTML")
            return

        # Validation 4: Check that city name is not only digits
        if city.isdigit():
            logger.warning(
                "City contains only digits - user_id: %s, city: %s",
                user_info["user_id"],
                city,
            )
            await message.answer(error_city_only_digits, parse_mode="HTML")
            return

        sanitized_city = sanitize_text(city)
        await state.update_data(place_of_living_city=city)
        logger.info(
            "Collected place of living city - user_id: %s, username: %s, city: %s",
            user_info["user_id"],
            user_info["username"],
            sanitized_city,
        )

        await state.set_state(ResumeForm.driving_categories)
        logger.info("Asking for driving categories - user_id: %s", user_info["user_id"])

        keyboard = await get_updated_keyboard(
            selected=set(), categories=DRIVING_CATEGORIES, prefix="driver_categories_"
        )
        await message.answer(ask_driving_categories, reply_markup=keyboard)
    except Exception as e:
        user_info = get_user_info(message)
        logger.error(
            "Error processing place of city - user_id: %s, error: %s",
            user_info["user_id"],
            str(e),
            exc_info=True,
        )


async def toggle_driving_categories(callback: CallbackQuery, state: FSMContext) -> None:
    """Toggle driving categories selection and handle submit."""
    data = await state.get_data()
    selected = set(data.get("selected_driver_categories", []))

    is_submit = callback.data == "driver_categories_submit"

    await toggle_selection(
        callback=callback,
        state=state,
        prefix="driver_categories_",
        field_name="selected_driver_categories",
        options=DRIVING_CATEGORIES,
        next_state=None,
    )

    if is_submit:
        updated_data = await state.get_data()
        selected = list(updated_data.get("selected_driver_categories", []))

        if selected:
            await state.update_data(
                selected_driver_categories=selected, current_category_index=0, driving_experience={}
            )

            await state.set_state(ResumeForm.driving_exp_per_category)

            current_cat = selected[0]
            user_info = get_user_info(callback)
            logger.info(
                "Asking for driving experience - user_id: %s, category: %s",
                user_info["user_id"],
                current_cat,
            )
            await callback.message.answer(
                ask_driving_exp_template.format(category=current_cat), parse_mode="HTML"
            )


async def process_driving_exp_by_category(message: Message, state: FSMContext) -> None:
    """Process driving experience for each category sequentially with validation."""
    user_info = get_user_info(message)
    data = await state.get_data()
    selected_categories = data.get("selected_driver_categories", [])
    current_index = data.get("current_category_index", 0)
    experience_dict = data.get("driving_experience", {})

    years_text = message.text.strip()

    if not years_text:
        logger.warning("Empty years input - user_id: %s", user_info["user_id"])
        await message.answer(error_not_numeric)
        return

    if " " in years_text:
        logger.warning(
            "Years input contains spaces - user_id: %s, input: %s",
            user_info["user_id"],
            years_text,
        )
        await message.answer(error_not_numeric)
        return

    try:
        years = float(years_text)
        if years < 0 or years > 100:
            logger.warning(
                "Invalid years input - user_id: %s, input: %s", user_info["user_id"], years_text
            )
            await message.answer(error_invalid_years)
            return
    except ValueError:
        logger.warning(
            "Non-numeric input for years - user_id: %s, input: %s",
            user_info["user_id"],
            years_text,
        )
        await message.answer(error_not_numeric)
        return

    current_cat = selected_categories[current_index]
    experience_dict[current_cat] = years
    await state.update_data(driving_experience=experience_dict)
    logger.info(
        "Collected experience - user_id: %s, category: %s, years: %s",
        user_info["user_id"],
        current_cat,
        years,
    )

    next_index = current_index + 1

    if next_index < len(selected_categories):
        await state.update_data(current_category_index=next_index)
        next_cat = selected_categories[next_index]
        logger.info(
            "Asking for driving experience - user_id: %s, category: %s",
            user_info["user_id"],
            next_cat,
        )
        await message.answer(ask_driving_exp_template.format(category=next_cat), parse_mode="HTML")
    else:
        selected_set = set(selected_categories)
        needs_additional_survey = any(
            cat in selected_set for cat in DRIVING_CATEGORIES_ADDITIONAL_INFO
        )

        if needs_additional_survey:
            keyboard = await get_updated_keyboard(
                selected=set(), categories=SEMI_TRAILERS_TYPES, prefix="semi_trailer_"
            )
            logger.info("Asking for semi-trailer types - user_id: %s", user_info["user_id"])
            await message.answer(ask_semi_trailer_types, parse_mode="HTML", reply_markup=keyboard)
            await state.set_state(ResumeForm.driving_semi_trailer_types)
        else:
            await state.set_state(ResumeForm.type_of_work)
            logger.info(
                "All driving categories processed, moving to type_of_work - user_id: %s",
                user_info["user_id"],
            )


async def process_driving_semi_trailer_types(callback: CallbackQuery, state: FSMContext) -> None:
    """Process semi-trailer types selection (single survey for C1E/CE categories)."""
    prefix = "semi_trailer_"

    if callback.data == f"{prefix}submit":
        current_data = await state.get_data()
        selected_types = list(current_data.get("semi_trailer_selection", []))

        if not selected_types:
            user_info = get_user_info(callback)
            logger.warning("No semi-trailer types selected - user_id: %s", user_info["user_id"])
            await callback.answer(error_no_semi_trailer, show_alert=True)
            return

        user_info = get_user_info(callback)
        await state.update_data(semi_trailer_types=selected_types)
        logger.info(
            "Collected semi-trailer types - user_id: %s, username: %s, types: %s",
            user_info["user_id"],
            user_info["username"],
            len(selected_types),
        )

        await state.set_state(ResumeForm.type_of_work)
        logger.info(
            "Semi-trailer types survey completed, moving to type_of_work - user_id: %s",
            user_info["user_id"],
        )

        await callback.message.edit_reply_markup()
        await callback.message.answer(msg_all_data_collected)

        keyboard = await get_updated_keyboard(
            selected=set(), categories=TYPES_OF_WORK, prefix="type_of_work_"
        )
        logger.info("Asking for type of work - user_id: %s", user_info["user_id"])
        await callback.message.answer(ask_type_of_work, parse_mode="HTML", reply_markup=keyboard)
    else:
        await toggle_selection(
            callback=callback,
            state=state,
            prefix=prefix,
            field_name="semi_trailer_selection",
            options=SEMI_TRAILERS_TYPES,
            next_state=None,
        )


async def process_driving_categories(message: Message, state: FSMContext) -> None:
    """Process the user's driving categories and move to the next state."""
    pass


async def process_driving_exp_per_category(message: Message, state: FSMContext) -> None:
    """Process the user's driving experience per category with validation and move to the next state."""
    user_info = get_user_info(message)
    data = await state.get_data()
    selected_categories = data.get("selected_driver_categories", [])
    current_index = data.get("current_category_index", 0)
    experience_dict = data.get("driving_experience", {})

    years_text = message.text.strip()

    if not years_text:
        logger.warning("Empty years input - user_id: %s", user_info["user_id"])
        await message.answer(error_not_numeric)
        return

    if " " in years_text:
        logger.warning(
            "Years input contains spaces - user_id: %s, input: %s",
            user_info["user_id"],
            years_text,
        )
        await message.answer(error_not_numeric)
        return

    try:
        years = float(years_text)
        if years < 0 or years > 100:
            logger.warning(
                "Invalid years input - user_id: %s, input: %s", user_info["user_id"], years_text
            )
            await message.answer(error_invalid_years)
            return
    except ValueError:
        logger.warning(
            "Non-numeric input for years - user_id: %s, input: %s",
            user_info["user_id"],
            years_text,
        )
        await message.answer(error_not_numeric)
        return

    current_cat = selected_categories[current_index]
    experience_dict[current_cat] = years
    await state.update_data(driving_experience=experience_dict)
    logger.info(
        "Collected experience - user_id: %s, category: %s, years: %s",
        user_info["user_id"],
        current_cat,
        years,
    )

    next_index = current_index + 1

    if next_index < len(selected_categories):
        await state.update_data(current_category_index=next_index)
        next_cat = selected_categories[next_index]
        logger.info(
            "Asking for driving experience - user_id: %s, category: %s",
            user_info["user_id"],
            next_cat,
        )
        await message.answer(ask_driving_exp_template.format(category=next_cat), parse_mode="HTML")
    else:
        selected_set = set(selected_categories)
        needs_additional_survey = any(
            cat in selected_set for cat in DRIVING_CATEGORIES_ADDITIONAL_INFO
        )

        if needs_additional_survey:
            keyboard = await get_updated_keyboard(
                selected=set(), categories=SEMI_TRAILERS_TYPES, prefix="semi_trailer_"
            )
            logger.info("Asking for semi-trailer types - user_id: %s", user_info["user_id"])
            await message.answer(ask_semi_trailer_types, parse_mode="HTML", reply_markup=keyboard)
            await state.set_state(ResumeForm.driving_semi_trailer_types)
        else:
            await state.set_state(ResumeForm.type_of_work)
            logger.info(
                "All driving categories processed, moving to type_of_work - user_id: %s",
                user_info["user_id"],
            )

            keyboard = await get_updated_keyboard(
                selected=set(), categories=TYPES_OF_WORK, prefix="type_of_work_"
            )
            logger.info("Asking for type of work - user_id: %s", user_info["user_id"])
            await message.answer(ask_type_of_work, parse_mode="HTML", reply_markup=keyboard)


async def toggle_type_of_work(callback: CallbackQuery, state: FSMContext) -> None:
    """Process type of work selection."""
    is_submit = callback.data == "type_of_work_submit"

    await toggle_selection(
        callback=callback,
        state=state,
        prefix="type_of_work_",
        field_name="selected_types_of_work",
        options=TYPES_OF_WORK,
        next_state=None,
    )

    if is_submit:
        updated_data = await state.get_data()
        selected = list(updated_data.get("selected_types_of_work", []))

        if selected:
            user_info = get_user_info(callback)
            await state.update_data(types_of_work=selected)
            logger.info(
                "Collected types of work - user_id: %s, username: %s, types: %s",
                user_info["user_id"],
                user_info["username"],
                len(selected),
            )

            await state.set_state(ResumeForm.types_of_cars)
            logger.info(
                "Types of work selected, moving to types_of_cars - user_id: %s",
                user_info["user_id"],
            )

            await callback.message.answer(ask_types_of_cars, parse_mode="HTML")


async def process_types_of_cars(message: Message, state: FSMContext) -> None:
    """Process the user's car brands and models with validation (English only, format: Brand Model)."""
    text = message.text.strip()

    user_info = get_user_info(message)

    if not text:
        logger.warning("Empty car types input - user_id: %s", user_info["user_id"])
        await message.answer(error_types_of_cars_empty, parse_mode="HTML")
        return

    if len(text) < 3:
        logger.warning(
            "Car types too short - user_id: %s, length: %s", user_info["user_id"], len(text)
        )
        await message.answer(error_types_of_cars_too_short, parse_mode="HTML")
        return

    if len(text) > 500:
        logger.warning(
            "Car types too long - user_id: %s, length: %s", user_info["user_id"], len(text)
        )
        await message.answer(error_types_of_cars_too_long, parse_mode="HTML")
        return

    has_cyrillic = any("\u0400" <= char <= "\u04ff" for char in text)
    if has_cyrillic:
        sanitized_text = sanitize_text(text)
        logger.warning(
            "Cyrillic characters in car types - user_id: %s, text: %s",
            user_info["user_id"],
            sanitized_text,
        )
        await message.answer(error_types_of_cars_cyrillic_template, parse_mode="HTML")
        return

    allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ,-.")
    if not all(char in allowed_chars for char in text):
        sanitized_text = sanitize_text(text)
        logger.warning(
            "Invalid characters in car types - user_id: %s, text: %s",
            user_info["user_id"],
            sanitized_text,
        )
        await message.answer(error_types_of_cars_invalid_chars, parse_mode="HTML")
        return

    if not any(char.isalpha() for char in text):
        logger.warning("No letters in car types - user_id: %s", user_info["user_id"])
        await message.answer(error_types_of_cars_no_letters, parse_mode="HTML")
        return

    entries = [entry.strip() for entry in text.split(",")]
    valid_entries = []

    for entry in entries:
        words = entry.split()
        if len(words) >= 2 and any(any(c.isalpha() for c in word) for word in words):
            valid_entries.append(entry)

    if not valid_entries:
        sanitized_text = sanitize_text(text)
        logger.warning(
            "Invalid format in car types - user_id: %s, text: %s",
            user_info["user_id"],
            sanitized_text,
        )
        await message.answer(error_types_of_cars_invalid_format, parse_mode="HTML")
        return

    sanitized_text = sanitize_text(text)
    await state.update_data(types_of_cars=text)
    logger.info(
        "Collected car types - user_id: %s, username: %s, text: %s",
        user_info["user_id"],
        user_info["username"],
        sanitized_text,
    )

    await state.set_state(ResumeForm.is_adr_license)
    logger.info("Car types collected, moving to is_adr_license - user_id: %s", user_info["user_id"])

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=button_adr_yes, callback_data="adr_yes")],
            [InlineKeyboardButton(text=button_adr_no, callback_data="adr_no")],
        ]
    )

    await message.answer(ask_is_adr_license, reply_markup=keyboard)


async def process_adr_license(callback: CallbackQuery, state: FSMContext) -> None:
    """Process ADR license selection (Yes/No)."""
    user_info = get_user_info(callback.message)

    if callback.data == "adr_yes":
        has_adr = True
        response_text = msg_adr_yes
    elif callback.data == "adr_no":
        has_adr = False
        response_text = msg_adr_no
    else:
        logger.warning(
            "Invalid ADR callback data - user_id: %s, data: %s", user_info["user_id"], callback.data
        )
        await callback.answer(error_processing, show_alert=True)
        return

    await state.update_data(is_adr_license=has_adr)
    logger.info(
        "Collected ADR license - user_id: %s, username: %s, has_adr: %s",
        user_info["user_id"],
        user_info["username"],
        has_adr,
    )

    await callback.message.edit_reply_markup()
    await callback.message.answer(response_text)

    await state.set_state(ResumeForm.race_duration_preference)
    logger.info(
        "ADR license collected, moving to race_duration_preference - user_id: %s",
        user_info["user_id"],
    )

    keyboard = await get_updated_keyboard(
        selected=set(), categories=RACE_DURATION_OPTIONS, prefix="race_duration_"
    )

    logger.info("Asking for race duration - user_id: %s", user_info["user_id"])
    await callback.message.answer(ask_race_duration, reply_markup=keyboard)


async def toggle_race_duration(callback: CallbackQuery, state: FSMContext) -> None:
    """Process race duration preference selection."""
    is_submit = callback.data == "race_duration_submit"

    await toggle_selection(
        callback=callback,
        state=state,
        prefix="race_duration_",
        field_name="selected_race_durations",
        options=RACE_DURATION_OPTIONS,
        next_state=None,
    )

    if is_submit:
        updated_data = await state.get_data()
        selected = list(updated_data.get("selected_race_durations", []))

        if selected:
            user_info = get_user_info(callback)
            await state.update_data(race_duration_preference=selected)
            logger.info(
                "Collected race durations - user_id: %s, username: %s, count: %s",
                user_info["user_id"],
                user_info["username"],
                len(selected),
            )

            await state.set_state(ResumeForm.desired_salary)
            logger.info(
                "Race duration collected, moving to desired_salary - user_id: %s",
                user_info["user_id"],
            )

            await callback.message.answer(ask_desired_salary)


async def process_desired_salary(message: Message, state: FSMContext) -> None:
    """Process the user's desired salary with validation and move to the next state."""
    try:
        user_info = get_user_info(message)
        salary_text = message.text.strip()

        if not salary_text:
            logger.warning("Empty salary input - user_id: %s", user_info["user_id"])
            await message.answer(error_salary_empty, parse_mode="HTML")
            return

        salary_clean = salary_text.replace(" ", "").replace(",", "").replace(".", "")
        if not re.match(r"^\d+$", salary_clean):
            sanitized_salary = sanitize_text(salary_text)
            logger.warning(
                "Invalid salary format - user_id: %s, input: %s",
                user_info["user_id"],
                sanitized_salary,
            )
            await message.answer(error_salary_invalid_format, parse_mode="HTML")
            return

        try:
            salary = int(salary_clean)
        except ValueError:
            sanitized_salary = sanitize_text(salary_text)
            logger.warning(
                "Salary conversion failed - user_id: %s, input: %s",
                user_info["user_id"],
                sanitized_salary,
            )
            await message.answer(error_salary_invalid_format, parse_mode="HTML")
            return

        if salary < 1000:
            logger.warning("Salary too low - user_id: %s, salary: %s", user_info["user_id"], salary)
            await message.answer(error_salary_too_low, parse_mode="HTML")
            return

        if salary > 1000000:
            logger.warning(
                "Salary too high - user_id: %s, salary: %s", user_info["user_id"], salary
            )
            await message.answer(error_salary_too_high, parse_mode="HTML")
            return

        await state.update_data(desired_salary=salary)
        logger.info(
            "Collected desired salary - user_id: %s, username: %s, salary: %s",
            user_info["user_id"],
            user_info["username"],
            salary,
        )

        await state.set_state(ResumeForm.docs_for_driving_abroad)
        logger.info(
            "Desired salary collected, moving to docs_for_driving_abroad - user_id: %s",
            user_info["user_id"],
        )

        keyboard = await get_updated_keyboard(
            selected=set(), categories=DOCS_FOR_DRIVING_ABROAD, prefix="docs_abroad_"
        )
        logger.info("Asking for docs for driving abroad - user_id: %s", user_info["user_id"])
        await message.answer(ask_docs_for_driving_abroad, parse_mode="HTML", reply_markup=keyboard)
    except Exception as e:
        user_info = get_user_info(message)
        logger.error(
            "Error processing desired salary - user_id: %s, error: %s",
            user_info["user_id"],
            str(e),
            exc_info=True,
        )


async def toggle_docs_for_driving_abroad(callback: CallbackQuery, state: FSMContext) -> None:
    """Process documents for driving abroad selection with special logic for 'Не маю'."""
    prefix = "docs_abroad_"

    is_submit = callback.data == f"{prefix}submit"

    if not is_submit:
        data = await state.get_data()
        selected = set(data.get("selected_docs_abroad", []))

        if not callback.data.startswith(prefix):
            user_info = get_user_info(callback)
            logger.warning(
                "Invalid callback data - user_id: %s, data: %s", user_info["user_id"], callback.data
            )
            await callback.answer(error_processing, show_alert=True)
            return

        item_id = callback.data[len(prefix) :]

        try:
            idx = int(item_id)
            if 0 <= idx < len(DOCS_FOR_DRIVING_ABROAD):
                item = DOCS_FOR_DRIVING_ABROAD[idx]
            else:
                user_info = get_user_info(callback)
                logger.warning("Invalid index - user_id: %s, index: %s", user_info["user_id"], idx)
                await callback.answer(error_invalid_index, show_alert=True)
                return
        except ValueError:
            user_info = get_user_info(callback)
            logger.warning(
                "Invalid callback data - user_id: %s, data: %s", user_info["user_id"], callback.data
            )
            await callback.answer(error_processing, show_alert=True)
            return

        no_docs_option = "❌ Не маю"

        if item == no_docs_option:
            selected = {no_docs_option}
        else:
            if no_docs_option in selected:
                selected.remove(no_docs_option)

            if item in selected:
                selected.remove(item)
            else:
                selected.add(item)

        await state.update_data(selected_docs_abroad=list(selected))

        keyboard = await get_updated_keyboard(
            selected=selected, categories=DOCS_FOR_DRIVING_ABROAD, prefix=prefix
        )
        await callback.message.edit_reply_markup(reply_markup=keyboard)
        await callback.answer()
    else:
        updated_data = await state.get_data()
        selected = list(updated_data.get("selected_docs_abroad", []))

        if not selected:
            user_info = get_user_info(callback)
            logger.warning(
                "No docs for driving abroad selected - user_id: %s", user_info["user_id"]
            )
            await callback.answer(error_no_selection, show_alert=True)
            return

        user_info = get_user_info(callback)
        await state.update_data(docs_for_driving_abroad=selected)
        logger.info(
            "Collected docs for driving abroad - user_id: %s, username: %s, count: %s",
            user_info["user_id"],
            user_info["username"],
            len(selected),
        )

        await callback.message.edit_reply_markup()
        await callback.message.answer(
            msg_selected_template.format(items=", ".join(sorted(selected)))
        )

        await state.set_state(ResumeForm.military_booking)
        logger.info(
            "Docs for driving abroad collected, moving to military_booking - user_id: %s",
            user_info["user_id"],
        )

        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=button_military_yes, callback_data="military_yes")],
                [InlineKeyboardButton(text=button_military_no, callback_data="military_no")],
            ]
        )

        await callback.message.answer(ask_military_booking, reply_markup=keyboard)


async def process_military_booking(callback: CallbackQuery, state: FSMContext) -> None:
    """Process military booking selection (Yes/No)."""
    try:
        user_info = get_user_info(callback)

        if callback.data == "military_yes":
            has_military_booking = True
            response_text = msg_military_yes
        elif callback.data == "military_no":
            has_military_booking = False
            response_text = msg_military_no
        else:
            logger.warning(
                "Invalid military booking callback data - user_id: %s, data: %s",
                user_info["user_id"],
                callback.data,
            )
            await callback.answer(error_processing, show_alert=True)
            return

        await state.update_data(military_booking=has_military_booking)
        logger.info(
            "Collected military booking - user_id: %s, username: %s, has_booking: %s",
            user_info["user_id"],
            user_info["username"],
            has_military_booking,
        )

        await callback.message.edit_reply_markup()
        await callback.message.answer(response_text)

        await state.set_state(ResumeForm.description)
        logger.info(
            "Military booking collected, moving to description - user_id: %s", user_info["user_id"]
        )

        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=button_skip_description, callback_data="skip_description"
                    )
                ]
            ]
        )

        await callback.message.answer(ask_description, reply_markup=keyboard)
    except Exception as e:
        user_info = get_user_info(callback)
        logger.error(
            "Error processing military booking - user_id: %s, error: %s",
            user_info["user_id"],
            str(e),
            exc_info=True,
        )


async def process_description(message: Message, state: FSMContext) -> None:
    """Process user's description about themselves with validation."""
    try:
        user_info = get_user_info(message)
        description = message.text.strip()

        if len(description) > 2000:
            logger.warning(
                "Description too long - user_id: %s, length: %s",
                user_info["user_id"],
                len(description),
            )
            await message.answer(error_description_too_long, parse_mode="HTML")
            return

        sanitized_description = sanitize_text(description)
        await state.update_data(description=description)
        logger.info(
            "Collected description - user_id: %s, username: %s, length: %s, text: %s",
            user_info["user_id"],
            user_info["username"],
            len(description),
            sanitized_description,
        )

        await finalize_resume(message, state)
    except Exception as e:
        user_info = get_user_info(message)
        logger.error(
            "Error processing description - user_id: %s, error: %s",
            user_info["user_id"],
            str(e),
            exc_info=True,
        )


async def skip_description(callback: CallbackQuery, state: FSMContext) -> None:
    """Skip description step."""
    try:
        # Get user info from callback (the user who clicked the button)
        user_info = get_user_info(callback)

        # Validate user_id
        if user_info["user_id"] is None:
            logger.error("Cannot skip description: user_id is None")
            await callback.answer("Помилка: не вдалося ідентифікувати користувача.", show_alert=True)
            return

        await state.update_data(description="")
        logger.info(
            "Description skipped - user_id: %s, username: %s",
            user_info["user_id"],
            user_info["username"],
        )

        await callback.message.edit_reply_markup()

        # IMPORTANT: Pass user_id and username explicitly to finalize_resume
        # This is critical because callback.message.from_user might not match callback.from_user
        # The user who clicked the button is the one who should own the resume
        if callback.message.from_user and callback.message.from_user.id != user_info["user_id"]:
            logger.warning(
                "User ID mismatch in skip_description - callback.from_user.id: %s, "
                "callback.message.from_user.id: %s. Using callback.from_user.id.",
                user_info["user_id"],
                callback.message.from_user.id,
            )

        # Pass explicit user_id and username to ensure correct user
        await finalize_resume(
            callback.message,
            state,
            explicit_user_id=user_info["user_id"],
            explicit_username=user_info["username"]
        )
    except Exception as e:
        user_info = get_user_info(callback)
        logger.error(
            "Error skipping description - user_id: %s, error: %s",
            user_info["user_id"],
            str(e),
            exc_info=True,
        )


def format_resume_display(data: dict) -> str:
    """Format all collected resume data into a readable display string."""
    lines = [resume_display_title]

    if name := data.get("name"):
        lines.append(resume_display_name.format(name=name))
    if phone := data.get("phone"):
        lines.append(resume_display_phone.format(phone=phone))
    if age := data.get("age"):
        lines.append(resume_display_age.format(age=age))

    region_key = data.get("place_of_living_region")
    city = data.get("place_of_living_city")
    if region_key and city:
        region_name = REGIONS.get(region_key, region_key)
        lines.append(resume_display_location.format(region=region_name, city=city))

    categories = data.get("selected_driver_categories", [])
    if categories:
        categories_str = ", ".join(categories)
        lines.append(resume_display_driving_categories.format(categories=categories_str))

    experience = data.get("driving_experience", {})
    if experience:
        exp_lines = []
        for category, years in sorted(experience.items()):
            years_str = f"{years:.1f}" if isinstance(years, float) else str(years)
            exp_lines.append(f"  • {category}: {years_str} років")
        if exp_lines:
            lines.append(resume_display_driving_experience.format(experience="\n".join(exp_lines)))

    semi_trailer_types = data.get("semi_trailer_types", [])
    if semi_trailer_types:
        types_str = ", ".join(semi_trailer_types)
        lines.append(resume_display_semi_trailer_types.format(types=types_str))

    types_of_work = data.get("types_of_work", [])
    if types_of_work:
        work_str = ", ".join(types_of_work)
        lines.append(resume_display_type_of_work.format(types=work_str))

    types_of_cars = data.get("types_of_cars")
    if types_of_cars:
        lines.append(resume_display_types_of_cars.format(cars=types_of_cars))

    has_adr = data.get("is_adr_license")
    if has_adr is not None:
        adr_status = "✅ Так" if has_adr else "❌ Ні"
        lines.append(resume_display_adr_license.format(status=adr_status))

    race_durations = data.get("race_duration_preference", [])
    if race_durations:
        duration_str = ", ".join(race_durations)
        lines.append(resume_display_race_duration.format(duration=duration_str))

    docs_abroad = data.get("docs_for_driving_abroad", [])
    if docs_abroad:
        docs_str = ", ".join(docs_abroad)
        lines.append(resume_display_docs_abroad.format(docs=docs_str))

    has_military = data.get("military_booking")
    if has_military is not None:
        military_status = "✅ Так" if has_military else "❌ Ні"
        lines.append(resume_display_military_booking.format(status=military_status))

    salary = data.get("desired_salary")
    if salary:
        lines.append(resume_display_salary.format(salary=salary))

    description = data.get("description")
    if description:
        lines.append(resume_display_description.format(description=description))

    return "\n".join(lines)


def convert_firebase_resume_to_display_format(firebase_data: dict) -> dict:
    """
    Convert resume data from Firebase format to format expected by format_resume_display.
    
    Args:
        firebase_data: Dictionary with resume data from Firebase
        
    Returns:
        Dictionary in format expected by format_resume_display
    """
    display_data = {}

    # Copy simple fields
    for field in ["name", "phone", "age", "driving_experience", "semi_trailer_types",
                  "types_of_work", "race_duration_preference", "is_adr_license",
                  "docs_for_driving_abroad", "military_booking", "desired_salary", "description"]:
        if field in firebase_data:
            display_data[field] = firebase_data[field]

    # Convert place_of_living dict to separate fields
    place_of_living = firebase_data.get("place_of_living", {})
    if place_of_living:
        display_data["place_of_living_region"] = place_of_living.get("region_key")
        display_data["place_of_living_city"] = place_of_living.get("city")

    # Convert driving_categories to selected_driver_categories
    if "driving_categories" in firebase_data:
        display_data["selected_driver_categories"] = firebase_data["driving_categories"]

    # Convert types_of_cars from list to string if needed
    types_of_cars = firebase_data.get("types_of_cars")
    if types_of_cars:
        if isinstance(types_of_cars, list):
            display_data["types_of_cars"] = ", ".join(types_of_cars)
        else:
            display_data["types_of_cars"] = types_of_cars

    return display_data


def remove_emojis(text: str) -> str:
    """
    Remove emojis and other Unicode symbols from text.
    
    Removes emojis, symbols, and pictographs that are commonly used in Telegram.
    Also cleans up extra spaces left after emoji removal.
    """
    if not text:
        return text

    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF"
        "\U0001FA00-\U0001FA6F"
        "\U0001FA70-\U0001FAFF"
        "\U00002600-\U000026FF"
        "\U00002700-\U000027BF"
        "]+",
        flags=re.UNICODE,
    )

    cleaned = emoji_pattern.sub("", text)

    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def clean_data_for_firebase(value):
    """
    Recursively clean data structure removing emojis from strings.
    
    Handles strings, lists, dicts, and other types.
    Preserves data structure while cleaning text content.
    """
    if isinstance(value, str):
        return remove_emojis(value)
    elif isinstance(value, list):
        return [clean_data_for_firebase(item) for item in value]
    elif isinstance(value, dict):
        return {key: clean_data_for_firebase(val) for key, val in value.items()}
    else:
        return value


def _convert_car_types_to_list(car_types) -> list:
    """
    Convert car types from string to list by splitting on comma.
    
    Handles:
    - String input: splits by comma, strips whitespace, filters empty strings
    - List input: returns as-is
    - None/empty: returns empty list
    
    Args:
        car_types: String (comma-separated) or list of car types
        
    Returns:
        List of car type strings
    """
    if car_types is None:
        return []

    if isinstance(car_types, list):
        return car_types

    if isinstance(car_types, str):
        car_list = [item.strip() for item in re.split(r',', car_types) if item.strip()]
        return car_list

    return [str(car_types).strip()] if str(car_types).strip() else []


def prepare_resume_data_for_firebase(data: dict, user_id: int | None, username: str | None) -> dict:
    """
    Prepare resume data in a structured format for Firebase storage.
    
    Args:
        data: Dictionary with resume data from FSM state
        user_id: Telegram user ID (must be int, not None for saving)
        username: Telegram username (can be None)
    
    Returns:
        Dictionary with all resume data organized for database storage.
        All emojis and Telegram symbols are removed from text fields.
    
    Raises:
        ValueError: If user_id is None (required for saving to Firebase)
    """
    # Validate user_id - it's required for saving
    if user_id is None:
        raise ValueError("user_id is required for saving resume to Firebase")

    # Ensure user_id is int (not string or other type)
    if not isinstance(user_id, int):
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            raise ValueError(f"user_id must be an integer, got: {type(user_id)}")

    # username can be None, but if it exists, ensure it's a string
    if username is not None and not isinstance(username, str):
        username = str(username) if username else None

    region_key = data.get("place_of_living_region")
    region_name = REGIONS.get(region_key, region_key) if region_key else None

    firebase_data = {
        "user_id": user_id,  # Always int, never None
        "username": username,  # str or None
        "name": data.get("name"),
        "phone": data.get("phone"),
        "age": data.get("age"),
        "place_of_living": {
            "region_key": region_key,
            "region_name": region_name,
            "city": data.get("place_of_living_city"),
        },
        "driving_categories": data.get("selected_driver_categories", []),
        "driving_experience": data.get("driving_experience", {}),
        "semi_trailer_types": data.get("semi_trailer_types", []),
        "types_of_work": data.get("types_of_work", []),
        "types_of_cars": _convert_car_types_to_list(data.get("types_of_cars")),
        "race_duration_preference": data.get("race_duration_preference", []),
        "is_adr_license": data.get("is_adr_license", False),
        "docs_for_driving_abroad": data.get("docs_for_driving_abroad", []),
        "military_booking": data.get("military_booking", False),
        "desired_salary": data.get("desired_salary"),
        "description": data.get("description", ""),
    }

    # Store original user_id and username before cleaning (they should not be modified)
    original_user_id = user_id
    original_username = username

    # Clean emojis from text fields (user_id and username are preserved)
    firebase_data = clean_data_for_firebase(firebase_data)

    # Ensure user_id and username are never modified by clean_data_for_firebase
    firebase_data["user_id"] = original_user_id
    firebase_data["username"] = original_username

    return firebase_data


async def finalize_resume(
    message: Message,
    state: FSMContext,
    explicit_user_id: int | None = None,
    explicit_username: str | None = None
) -> None:
    """
    Finalize resume creation, display all data, and show thank you message.
    
    Args:
        message: Message object (can be from callback.message)
        state: FSM context with resume data
        explicit_user_id: Optional user_id to use instead of message.from_user
        explicit_username: Optional username to use instead of message.from_user
    """
    try:
        # Use explicit user_id/username if provided (e.g., from callback.from_user)
        # Otherwise, get from message
        if explicit_user_id is not None:
            user_info = {
                "user_id": explicit_user_id,
                "username": explicit_username,
            }
            logger.debug(
                "Using explicit user_id: %s, username: %s (instead of message.from_user)",
                explicit_user_id,
                explicit_username,
            )
        else:
            # Get user info directly from message (never from state data)
            user_info = get_user_info(message)

            # Additional validation: log warning if message.from_user seems incorrect
            if message.from_user:
                logger.debug(
                    "Finalizing resume - message.from_user.id: %s, message.from_user.username: %s",
                    message.from_user.id,
                    message.from_user.username,
                )

        # Validate user_id before proceeding
        if user_info["user_id"] is None:
            logger.error("Cannot finalize resume: user_id is None")
            await message.answer("Помилка: не вдалося ідентифікувати користувача. Будь ласка, спробуйте ще раз.")
            return

        data = await state.get_data()
        logger.info(
            "Resume finalized - user_id: %s, username: %s, fields_count: %s",
            user_info["user_id"],
            user_info["username"],
            len(data),
        )

        # Prepare Firebase data with validated user_id (always from message, never from state)
        firebase_data = prepare_resume_data_for_firebase(
            data=data,
            user_id=user_info["user_id"],  # Always from message.from_user
            username=user_info["username"],  # Always from message.from_user
        )
        logger.info(
            "Resume data prepared for Firebase - user_id: %s, username: %s",
            user_info["user_id"],
            user_info["username"],
        )

        try:
            resume_key = await add_resume(firebase_data)
            if resume_key:
                logger.info(
                    "Resume saved to Firebase - user_id: %s, resume_key: %s",
                    user_info["user_id"],
                    resume_key,
                )
            else:
                logger.warning(
                    "Failed to save resume to Firebase - user_id: %s",
                    user_info["user_id"],
                )
        except Exception as e:
            logger.error(
                "Error saving resume to Firebase - user_id: %s, error: %s",
                user_info["user_id"],
                str(e),
                exc_info=True,
            )

        resume_display = format_resume_display(data)
        await message.answer(resume_display, parse_mode="HTML")

        await message.answer(msg_resume_saved)

        await state.clear()
        logger.info("State cleared - user_id: %s", user_info["user_id"])

        # Use dynamic keyboard - resume was just created, so show "My Resume" button
        keyboard = get_main_menu_keyboard(has_resume=True)
        await message.answer(msg_bot_greeting, reply_markup=keyboard)
    except Exception as e:
        user_info = get_user_info(message)
        logger.error(
            "Error finalizing resume - user_id: %s, error: %s",
            user_info["user_id"],
            str(e),
            exc_info=True,
            )
