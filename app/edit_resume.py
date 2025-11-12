"""Module for handling resume editing functionality."""

import logging
import re

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from build_resume.stage_resume import (
    ResumeForm,
    convert_firebase_resume_to_display_format,
    format_resume_display,
    process_adr_license,
    process_age,
    process_description,
    process_desired_salary,
    process_driving_exp_per_category,
    process_driving_semi_trailer_types,
    process_military_booking,
    process_name,
    process_phone,
    process_place_of_city,
    process_place_of_region_callback,
    process_types_of_cars,
    skip_description,
    toggle_docs_for_driving_abroad,
    toggle_driving_categories,
    toggle_race_duration,
    toggle_type_of_work,
)
from constants import (
    DOCS_FOR_DRIVING_ABROAD,
    DRIVING_CATEGORIES,
    DRIVING_CATEGORIES_ADDITIONAL_INFO,
    RACE_DURATION_OPTIONS,
    REGIONS,
    TYPES_OF_WORK,
    ask_age,
    ask_description,
    ask_desired_salary,
    ask_docs_for_driving_abroad,
    ask_driving_categories,
    ask_driving_exp_template,
    ask_is_adr_license,
    ask_military_booking,
    ask_name,
    ask_phone,
    ask_place_of_living_region,
    ask_race_duration,
    ask_type_of_work,
    ask_types_of_cars,
    button_adr_no,
    button_adr_yes,
    button_edit_field_adr,
    button_edit_field_age,
    button_edit_field_description,
    button_edit_field_docs_abroad,
    button_edit_field_driving_categories,
    button_edit_field_location,
    button_edit_field_military,
    button_edit_field_name,
    button_edit_field_phone,
    button_edit_field_race_duration,
    button_edit_field_salary,
    button_edit_field_type_of_work,
    button_edit_field_types_of_cars,
    button_military_no,
    button_military_yes,
    button_skip_description,
    error_age_empty,
    error_age_has_spaces,
    error_edit_data_not_found,
    error_edit_field_failed,
    error_edit_menu_failed,
    error_invalid_age,
    error_invalid_phone,
    error_name_empty,
    error_name_invalid_format,
    error_name_single_word,
    error_name_too_long,
    error_name_too_short,
    error_processing,
    error_resume_not_found,
    error_resume_update_failed,
    error_user_not_found,
    msg_adr_no,
    msg_adr_yes,
    msg_edit_resume_menu,
    msg_military_no,
    msg_military_yes,
    msg_my_resume_title,
    msg_resume_updated,
    msg_selected_template,
)
from functions import get_updated_keyboard
from keyboards import delete_resume_keyboard, keyboard_place_of_living, phone_keyboard
from logging_config import (
    get_user_info,
    log_error,
    log_info,
    log_warning,
    sanitize_name,
    sanitize_phone,
    sanitize_text,
)

from firebase_db.crud import get_resume, update_resume

logger = logging.getLogger(__name__)


def get_edit_resume_menu_keyboard() -> InlineKeyboardMarkup:
    """Create inline keyboard for edit resume menu."""
    keyboard = [
        [InlineKeyboardButton(text=button_edit_field_name, callback_data="edit_field_name")],
        [InlineKeyboardButton(text=button_edit_field_phone, callback_data="edit_field_phone")],
        [InlineKeyboardButton(text=button_edit_field_age, callback_data="edit_field_age")],
        [
            InlineKeyboardButton(
                text=button_edit_field_location, callback_data="edit_field_location"
            )
        ],
        [
            InlineKeyboardButton(
                text=button_edit_field_driving_categories,
                callback_data="edit_field_driving_categories",
            )
        ],
        [
            InlineKeyboardButton(
                text=button_edit_field_type_of_work, callback_data="edit_field_type_of_work"
            )
        ],
        [
            InlineKeyboardButton(
                text=button_edit_field_types_of_cars, callback_data="edit_field_types_of_cars"
            )
        ],
        [InlineKeyboardButton(text=button_edit_field_adr, callback_data="edit_field_adr")],
        [
            InlineKeyboardButton(
                text=button_edit_field_race_duration, callback_data="edit_field_race_duration"
            )
        ],
        [InlineKeyboardButton(text=button_edit_field_salary, callback_data="edit_field_salary")],
        [
            InlineKeyboardButton(
                text=button_edit_field_docs_abroad, callback_data="edit_field_docs_abroad"
            )
        ],
        [
            InlineKeyboardButton(
                text=button_edit_field_military, callback_data="edit_field_military"
            )
        ],
        [
            InlineKeyboardButton(
                text=button_edit_field_description, callback_data="edit_field_description"
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def handle_edit_resume_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle edit resume menu button press."""
    try:
        user_info = get_user_info(callback)
        log_info(
            logger,
            action="user_opened_edit_menu",
            user_id=user_info["user_id"],
            username=user_info["username"],
        )

        await callback.message.edit_text(
            msg_edit_resume_menu,
            parse_mode="HTML",
            reply_markup=get_edit_resume_menu_keyboard(),
        )
        await callback.answer()
    except Exception as e:
        user_info = get_user_info(callback)
        log_error(
            logger,
            action="edit_menu_failed",
            error=str(e),
            user_id=user_info["user_id"],
            username=user_info["username"],
            exc_info=True,
        )
        await callback.answer(error_edit_menu_failed)


async def handle_edit_field(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle field edit selection."""
    try:
        user_info = get_user_info(callback)
        field = callback.data.replace("edit_field_", "")

        if not user_info["user_id"]:
            await callback.answer(error_user_not_found)
            return

        # Get current resume data
        resume_data = await get_resume(user_info["user_id"])
        if not resume_data:
            await callback.answer(error_resume_not_found)
            return

        # Convert to display format for easier handling
        display_data = convert_firebase_resume_to_display_format(resume_data)

        # Store resume data in state for editing
        # IMPORTANT: Store user_id and username explicitly to avoid issues with callback.message.from_user
        await state.update_data(
            editing_resume=resume_data,
            editing_field=field,
            editing_user_id=user_info["user_id"],  # Store correct user_id
            editing_username=user_info["username"],  # Store username for logging
        )

        log_info(
            logger,
            action="user_editing_field",
            user_id=user_info["user_id"],
            field=field,
        )

        # Handle each field type
        if field == "name":
            await callback.message.edit_text(ask_name)
            await state.set_state(ResumeForm.name)
            await callback.answer()

        elif field == "phone":
            await callback.message.edit_text(ask_phone, reply_markup=phone_keyboard)
            await state.set_state(ResumeForm.phone)
            await callback.answer()

        elif field == "age":
            await callback.message.edit_text(ask_age)
            await state.set_state(ResumeForm.age)
            await callback.answer()

        elif field == "location":
            await callback.message.edit_text(
                ask_place_of_living_region, reply_markup=keyboard_place_of_living
            )
            await state.set_state(ResumeForm.place_of_living_region)
            await callback.answer()

        elif field == "driving_categories":
            # Load current categories - ensure it's a list
            current_categories = display_data.get("selected_driver_categories", [])
            if not isinstance(current_categories, list):
                current_categories = []
            # Show all options as unselected (no checkmarks) when editing
            keyboard = await get_updated_keyboard(
                selected=set(),  # Empty set - no checkmarks shown
                categories=DRIVING_CATEGORIES,
                prefix="driver_categories_",
            )
            await callback.message.edit_text(
                ask_driving_categories, parse_mode="HTML", reply_markup=keyboard
            )
            await state.set_state(ResumeForm.driving_categories)
            # Store current categories in state but don't show them as selected
            await state.update_data(selected_driver_categories=current_categories)
            await callback.answer()

        elif field == "type_of_work":
            # Ensure it's a list
            current_types = display_data.get("types_of_work", [])
            if not isinstance(current_types, list):
                current_types = []
            # Show all options as unselected (no checkmarks) when editing
            keyboard = await get_updated_keyboard(
                selected=set(),  # Empty set - no checkmarks shown
                categories=TYPES_OF_WORK,
                prefix="type_of_work_",
            )
            await callback.message.edit_text(
                ask_type_of_work, parse_mode="HTML", reply_markup=keyboard
            )
            await state.set_state(ResumeForm.type_of_work)
            # Store current types in state but don't show them as selected
            await state.update_data(types_of_work=current_types)
            await callback.answer()

        elif field == "types_of_cars":
            current_cars = display_data.get("types_of_cars", "")
            await callback.message.edit_text(ask_types_of_cars, parse_mode="HTML")
            await state.set_state(ResumeForm.types_of_cars)
            await state.update_data(types_of_cars=current_cars)
            await callback.answer()

        elif field == "adr":
            current_adr = display_data.get("is_adr_license", False)
            # Don't show checkmarks when editing - show clean options
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=button_adr_yes, callback_data="adr_yes")],
                    [InlineKeyboardButton(text=button_adr_no, callback_data="adr_no")],
                ],
            )
            await callback.message.edit_text(ask_is_adr_license, reply_markup=keyboard)
            await state.set_state(ResumeForm.is_adr_license)
            # Store current value in state but don't show it as selected
            await state.update_data(is_adr_license=current_adr)
            await callback.answer()

        elif field == "race_duration":
            # Ensure it's a list
            current_durations = display_data.get("race_duration_preference", [])
            if not isinstance(current_durations, list):
                current_durations = []
            # Show all options as unselected (no checkmarks) when editing
            keyboard = await get_updated_keyboard(
                selected=set(),  # Empty set - no checkmarks shown
                categories=RACE_DURATION_OPTIONS,
                prefix="race_duration_",
            )
            await callback.message.edit_text(
                ask_race_duration, parse_mode="HTML", reply_markup=keyboard
            )
            await state.set_state(ResumeForm.race_duration_preference)
            # Store current durations in state but don't show them as selected
            await state.update_data(race_duration_preference=current_durations)
            await callback.answer()

        elif field == "salary":
            current_salary = display_data.get("desired_salary", "")
            await callback.message.edit_text(ask_desired_salary)
            await state.set_state(ResumeForm.desired_salary)
            await state.update_data(desired_salary=current_salary)
            await callback.answer()

        elif field == "docs_abroad":
            # Ensure it's a list
            current_docs = display_data.get("docs_for_driving_abroad", [])
            if not isinstance(current_docs, list):
                current_docs = []
            # Show all options as unselected (no checkmarks) when editing
            keyboard = await get_updated_keyboard(
                selected=set(),  # Empty set - no checkmarks shown
                categories=DOCS_FOR_DRIVING_ABROAD,
                prefix="docs_abroad_",
            )
            await callback.message.edit_text(
                ask_docs_for_driving_abroad, parse_mode="HTML", reply_markup=keyboard
            )
            await state.set_state(ResumeForm.docs_for_driving_abroad)
            # Store current docs in state but don't show them as selected
            await state.update_data(docs_for_driving_abroad=current_docs)
            await callback.answer()

        elif field == "military":
            current_military = display_data.get("military_booking", False)
            # Don't show checkmarks when editing - show clean options
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=button_military_yes, callback_data="military_yes")],
                    [InlineKeyboardButton(text=button_military_no, callback_data="military_no")],
                ],
            )
            await callback.message.edit_text(ask_military_booking, reply_markup=keyboard)
            await state.set_state(ResumeForm.military_booking)
            # Store current value in state but don't show it as selected
            await state.update_data(military_booking=current_military)
            await callback.answer()

        elif field == "description":
            current_desc = display_data.get("description", "")
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=button_skip_description, callback_data="skip_description"
                        )
                    ],
                ],
            )
            await callback.message.edit_text(ask_description, reply_markup=keyboard)
            await state.set_state(ResumeForm.description)
            await state.update_data(description=current_desc)
            await callback.answer()

    except Exception as e:
        user_info = get_user_info(callback)
        log_error(
            logger,
            action="edit_field_failed",
            error=str(e),
            user_id=user_info["user_id"],
            username=user_info["username"],
            exc_info=True,
        )
        await callback.answer(error_edit_field_failed)


async def save_edited_field(message: Message, state: FSMContext) -> None:
    """Save edited field and update resume in Firebase."""
    try:
        data = await state.get_data()
        editing_resume = data.get("editing_resume")
        editing_field = data.get("editing_field")
        # Use stored user_id from editing start, not from message (which might be from bot)
        editing_user_id = data.get("editing_user_id")
        
        if not editing_resume or not editing_field or not editing_user_id:
            await message.answer(error_edit_data_not_found)
            return
        
        # Use the stored user_id and username instead of getting from message
        # (message.from_user might be from bot, not the actual user)
        user_info = {
            "user_id": editing_user_id,
            "username": data.get("editing_username"),  # Use stored username
        }

        # Get updated field value from state
        field_updates = {}

        if editing_field == "name":
            field_updates["name"] = data.get("name")
        elif editing_field == "phone":
            field_updates["phone"] = data.get("phone")
        elif editing_field == "age":
            field_updates["age"] = data.get("age")
        elif editing_field == "location":
            region_key = data.get("place_of_living_region")
            city = data.get("place_of_living_city")
            if region_key and city:
                region_name = REGIONS.get(region_key, region_key)
                field_updates["place_of_living"] = {
                    "region_key": region_key,
                    "region_name": region_name,
                    "city": city,
                }
        elif editing_field == "driving_categories":
            # Handle interconnected: if categories change, may need to update experience and semi-trailer types
            # Use all_selected_categories if available (preserved from edit), otherwise use selected_driver_categories
            new_categories = data.get("all_selected_categories") or data.get("selected_driver_categories", [])
            field_updates["driving_categories"] = new_categories

            # Get existing experience from resume
            existing_experience = editing_resume.get("driving_experience", {})
            # Get new experience from state (if user provided it)
            new_experience = data.get("driving_experience", {})
            # Merge: keep existing for categories that still exist, add new experience
            merged_experience = {**existing_experience}
            merged_experience.update(new_experience)
            # Keep only experience for categories that still exist
            filtered_experience = {
                cat: exp for cat, exp in merged_experience.items() if cat in new_categories
            }
            if filtered_experience:
                field_updates["driving_experience"] = filtered_experience

            # Update semi-trailer types if needed
            selected_set = set(new_categories)
            needs_semi_trailer = any(
                cat in selected_set for cat in DRIVING_CATEGORIES_ADDITIONAL_INFO
            )
            if needs_semi_trailer:
                # Get existing semi-trailer types or new ones from state
                semi_trailer_types = data.get("semi_trailer_types") or editing_resume.get(
                    "semi_trailer_types", []
                )
                if semi_trailer_types:
                    field_updates["semi_trailer_types"] = semi_trailer_types
            else:
                # Remove semi_trailer_types if no longer needed
                field_updates["semi_trailer_types"] = []
        elif editing_field == "type_of_work":
            field_updates["types_of_work"] = data.get("types_of_work", [])
        elif editing_field == "types_of_cars":
            types_of_cars = data.get("types_of_cars", "")
            # Convert to list format for Firebase
            if isinstance(types_of_cars, str):
                field_updates["types_of_cars"] = [
                    t.strip() for t in types_of_cars.split(",") if t.strip()
                ]
            else:
                field_updates["types_of_cars"] = types_of_cars
        elif editing_field == "adr":
            field_updates["is_adr_license"] = data.get("is_adr_license", False)
        elif editing_field == "race_duration":
            field_updates["race_duration_preference"] = data.get("race_duration_preference", [])
        elif editing_field == "salary":
            field_updates["desired_salary"] = data.get("desired_salary")
        elif editing_field == "docs_abroad":
            field_updates["docs_for_driving_abroad"] = data.get("docs_for_driving_abroad", [])
        elif editing_field == "military":
            field_updates["military_booking"] = data.get("military_booking", False)
        elif editing_field == "description":
            field_updates["description"] = data.get("description", "")

        # Update resume in Firebase
        success = await update_resume(user_info["user_id"], field_updates)

        if success:
            await message.answer(msg_resume_updated)

            # Show updated resume
            updated_resume = await get_resume(user_info["user_id"])
            if updated_resume:
                display_data = convert_firebase_resume_to_display_format(updated_resume)
                resume_text = format_resume_display(display_data)
                resume_text = resume_text.replace(
                    "📋 <b>Ваше резюме</b>", msg_my_resume_title.strip()
                )
                await message.answer(
                    resume_text, parse_mode="HTML", reply_markup=delete_resume_keyboard
                )
        else:
            await message.answer(error_resume_update_failed)

        # Clear editing state
        await state.clear()

    except Exception as e:
        user_info = get_user_info(message)
        log_error(
            logger,
            action="save_edited_field_failed",
            error=str(e),
            user_id=user_info["user_id"],
            username=user_info["username"],
            exc_info=True,
        )
        await message.answer(error_resume_update_failed)


# Wrapper handlers for edit mode
async def process_name_wrapper(message: Message, state: FSMContext) -> None:
    """Wrapper for process_name that handles edit mode."""
    data = await state.get_data()
    if data.get("editing_field") == "name":
        # In edit mode, only validate and save, don't continue to next question
        user_info = get_user_info(message)
        name = message.text.strip()

        # Validate (same as process_name)
        if not name:
            log_warning(
                logger,
                action="name_validation_failed",
                reason="empty_input",
                user_id=user_info["user_id"],
                username=user_info["username"],
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
                length=len(name),
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
                length=len(name),
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
                name=sanitized_name,
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
                name=sanitized_name,
            )
            await message.answer(error_name_single_word, parse_mode="HTML")
            return

        # Validation passed, save
        sanitized_name = sanitize_name(name)
        await state.update_data(name=name)
        log_info(
            logger,
            action="name_collected_edit",
            user_id=user_info["user_id"],
            username=user_info["username"],
            name=sanitized_name,
        )
        await save_edited_field(message, state)
    else:
        await process_name(message, state)


async def process_phone_wrapper(message: Message, state: FSMContext) -> None:
    """Wrapper for process_phone that handles edit mode."""
    data = await state.get_data()
    if data.get("editing_field") == "phone":
        # In edit mode, only validate and save, don't continue to next question
        user_info = get_user_info(message)
        phone_number = None

        if message.contact and message.contact.phone_number:
            phone_number = message.contact.phone_number
        else:
            phone_number = message.text
            valid_numb = re.match(r"^\+380\d{9}$", phone_number)
            if not valid_numb:
                sanitized_phone = sanitize_phone(phone_number)
                log_warning(
                    logger,
                    action="phone_validation_failed",
                    user_id=user_info["user_id"],
                    input=sanitized_phone,
                )
                await message.answer(error_invalid_phone)
                return

        # Validation passed, save
        await state.update_data(phone=phone_number)
        sanitized_phone = sanitize_phone(phone_number)
        log_info(
            logger,
            action="phone_collected_edit",
            user_id=user_info["user_id"],
            phone=sanitized_phone,
        )
        await save_edited_field(message, state)
    else:
        await process_phone(message, state)


async def process_age_wrapper(message: Message, state: FSMContext) -> None:
    """Wrapper for process_age that handles edit mode."""
    data = await state.get_data()
    if data.get("editing_field") == "age":
        # In edit mode, only validate and save, don't continue to next question
        user_info = get_user_info(message)
        age_text = message.text.strip()

        # Validate (same as process_age)
        if not age_text:
            log_warning(
                logger, action="age_validation_failed", reason="empty", user_id=user_info["user_id"]
            )
            await message.answer(error_age_empty, parse_mode="HTML")
            return

        if " " in age_text:
            log_warning(
                logger,
                action="age_validation_failed",
                reason="has_spaces",
                user_id=user_info["user_id"],
            )
            await message.answer(error_age_has_spaces, parse_mode="HTML")
            return

        try:
            age = int(age_text)
            if age < 18 or age > 100:
                log_warning(
                    logger,
                    action="age_validation_failed",
                    reason="invalid_range",
                    user_id=user_info["user_id"],
                    age=age,
                )
                await message.answer(error_invalid_age)
                return
        except ValueError:
            log_warning(
                logger,
                action="age_validation_failed",
                reason="not_numeric",
                user_id=user_info["user_id"],
            )
            await message.answer(error_invalid_age)
            return

        # Validation passed, save
        await state.update_data(age=age)
        log_info(
            logger,
            action="age_collected_edit",
            user_id=user_info["user_id"],
            username=user_info["username"],
            age=age,
        )
        await save_edited_field(message, state)
    else:
        await process_age(message, state)


async def process_place_of_city_wrapper(message: Message, state: FSMContext) -> None:
    """Wrapper for process_place_of_city that handles edit mode."""
    data = await state.get_data()
    if data.get("editing_field") == "location":
        # In edit mode, only validate and save, don't continue to next question
        user_info = get_user_info(message)
        city = message.text.strip()

        # Validate (same as process_place_of_city)
        if not city:
            from logging_config import log_warning

            log_warning(
                logger,
                action="city_validation_failed",
                reason="empty",
                user_id=user_info["user_id"],
            )
            from constants import error_city_empty

            await message.answer(error_city_empty, parse_mode="HTML")
            return

        if len(city) < 2:
            from logging_config import log_warning

            log_warning(
                logger,
                action="city_validation_failed",
                reason="too_short",
                user_id=user_info["user_id"],
                length=len(city),
            )
            from constants import error_city_too_short

            await message.answer(error_city_too_short, parse_mode="HTML")
            return

        if len(city) > 100:
            from logging_config import log_warning

            log_warning(
                logger,
                action="city_validation_failed",
                reason="too_long",
                user_id=user_info["user_id"],
                length=len(city),
            )
            from constants import error_city_too_long

            await message.answer(error_city_too_long, parse_mode="HTML")
            return

        if city.isdigit():
            from logging_config import log_warning

            log_warning(
                logger,
                action="city_validation_failed",
                reason="only_digits",
                user_id=user_info["user_id"],
                city=city,
            )
            from constants import error_city_only_digits

            await message.answer(error_city_only_digits, parse_mode="HTML")
            return

        # Validation passed, save
        from logging_config import log_info, sanitize_text

        sanitized_city = sanitize_text(city)
        await state.update_data(place_of_living_city=city)
        log_info(
            logger,
            action="city_collected_edit",
            user_id=user_info["user_id"],
            username=user_info["username"],
            city=sanitized_city,
        )
        await save_edited_field(message, state)
    else:
        await process_place_of_city(message, state)


async def process_types_of_cars_wrapper(message: Message, state: FSMContext) -> None:
    """Wrapper for process_types_of_cars that handles edit mode."""
    data = await state.get_data()
    if data.get("editing_field") == "types_of_cars":
        # In edit mode, only validate and save, don't continue to next question
        text = message.text.strip()
        user_info = get_user_info(message)

        # Validate (same as process_types_of_cars)
        if not text:
            from logging_config import log_warning

            log_warning(
                logger,
                action="car_types_validation_failed",
                reason="empty",
                user_id=user_info["user_id"],
            )
            from constants import error_types_of_cars_empty

            await message.answer(error_types_of_cars_empty, parse_mode="HTML")
            return

        if len(text) < 3:
            from logging_config import log_warning

            log_warning(
                logger,
                action="car_types_validation_failed",
                reason="too_short",
                user_id=user_info["user_id"],
                length=len(text),
            )
            from constants import error_types_of_cars_too_short

            await message.answer(error_types_of_cars_too_short, parse_mode="HTML")
            return

        if len(text) > 500:
            from logging_config import log_warning

            log_warning(
                logger,
                action="car_types_validation_failed",
                reason="too_long",
                user_id=user_info["user_id"],
                length=len(text),
            )
            from constants import error_types_of_cars_too_long

            await message.answer(error_types_of_cars_too_long, parse_mode="HTML")
            return

        has_cyrillic = any("\u0400" <= char <= "\u04ff" for char in text)
        if has_cyrillic:
            from logging_config import log_warning, sanitize_text

            sanitized_text = sanitize_text(text)
            log_warning(
                logger,
                action="car_types_validation_failed",
                reason="cyrillic",
                user_id=user_info["user_id"],
                text=sanitized_text,
            )
            from constants import error_types_of_cars_cyrillic_template

            await message.answer(error_types_of_cars_cyrillic_template, parse_mode="HTML")
            return

        allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ,-.")
        if not all(char in allowed_chars for char in text):
            from logging_config import log_warning, sanitize_text

            sanitized_text = sanitize_text(text)
            log_warning(
                logger,
                action="car_types_validation_failed",
                reason="invalid_chars",
                user_id=user_info["user_id"],
                text=sanitized_text,
            )
            from constants import error_types_of_cars_invalid_chars

            await message.answer(error_types_of_cars_invalid_chars, parse_mode="HTML")
            return

        if not any(char.isalpha() for char in text):
            from logging_config import log_warning

            log_warning(
                logger,
                action="car_types_validation_failed",
                reason="no_letters",
                user_id=user_info["user_id"],
            )
            from constants import error_types_of_cars_no_letters

            await message.answer(error_types_of_cars_no_letters, parse_mode="HTML")
            return

        entries = [entry.strip() for entry in text.split(",")]
        valid_entries = []
        for entry in entries:
            words = entry.split()
            if len(words) >= 2 and any(any(c.isalpha() for c in word) for word in words):
                valid_entries.append(entry)

        if not valid_entries:
            from logging_config import log_warning, sanitize_text

            sanitized_text = sanitize_text(text)
            log_warning(
                logger,
                action="car_types_validation_failed",
                reason="invalid_format",
                user_id=user_info["user_id"],
                text=sanitized_text,
            )
            from constants import error_types_of_cars_invalid_format

            await message.answer(error_types_of_cars_invalid_format, parse_mode="HTML")
            return

        # Validation passed, save
        from logging_config import log_info, sanitize_text

        sanitized_text = sanitize_text(text)
        await state.update_data(types_of_cars=text)
        log_info(
            logger,
            action="car_types_collected_edit",
            user_id=user_info["user_id"],
            username=user_info["username"],
            text=sanitized_text,
        )
        await save_edited_field(message, state)
    else:
        await process_types_of_cars(message, state)


async def process_desired_salary_wrapper(message: Message, state: FSMContext) -> None:
    """Wrapper for process_desired_salary that handles edit mode."""
    data = await state.get_data()
    if data.get("editing_field") == "salary":
        # In edit mode, only validate and save, don't continue to next question
        import re

        user_info = get_user_info(message)
        salary_text = message.text.strip()

        # Validate (same as process_desired_salary)
        if not salary_text:
            from logging_config import log_warning

            log_warning(
                logger,
                action="salary_validation_failed",
                reason="empty",
                user_id=user_info["user_id"],
            )
            from constants import error_salary_empty

            await message.answer(error_salary_empty, parse_mode="HTML")
            return

        salary_clean = salary_text.replace(" ", "").replace(",", "").replace(".", "")
        if not re.match(r"^\d+$", salary_clean):
            from logging_config import log_warning, sanitize_text

            sanitized_salary = sanitize_text(salary_text)
            log_warning(
                logger,
                action="salary_validation_failed",
                reason="invalid_format",
                user_id=user_info["user_id"],
                input=sanitized_salary,
            )
            from constants import error_salary_invalid_format

            await message.answer(error_salary_invalid_format, parse_mode="HTML")
            return

        try:
            salary = int(salary_clean)
        except ValueError:
            from logging_config import log_warning, sanitize_text

            sanitized_salary = sanitize_text(salary_text)
            log_warning(
                logger,
                action="salary_validation_failed",
                reason="conversion_failed",
                user_id=user_info["user_id"],
                input=sanitized_salary,
            )
            from constants import error_salary_invalid_format

            await message.answer(error_salary_invalid_format, parse_mode="HTML")
            return

        if salary < 1000:
            from logging_config import log_warning

            log_warning(
                logger,
                action="salary_validation_failed",
                reason="too_low",
                user_id=user_info["user_id"],
                salary=salary,
            )
            from constants import error_salary_too_low

            await message.answer(error_salary_too_low, parse_mode="HTML")
            return

        if salary > 1000000:
            from logging_config import log_warning

            log_warning(
                logger,
                action="salary_validation_failed",
                reason="too_high",
                user_id=user_info["user_id"],
                salary=salary,
            )
            from constants import error_salary_too_high

            await message.answer(error_salary_too_high, parse_mode="HTML")
            return

        # Validation passed, save
        from logging_config import log_info

        await state.update_data(desired_salary=salary)
        log_info(
            logger,
            action="salary_collected_edit",
            user_id=user_info["user_id"],
            username=user_info["username"],
            salary=salary,
        )
        await save_edited_field(message, state)
    else:
        await process_desired_salary(message, state)


async def process_description_wrapper(message: Message, state: FSMContext) -> None:
    """Wrapper for process_description that handles edit mode."""
    data = await state.get_data()
    if data.get("editing_field") == "description":
        # Process description but don't call finalize_resume
        user_info = get_user_info(message)
        description = message.text.strip()

        if len(description) > 2000:
            from logging_config import log_warning

            log_warning(
                logger,
                action="description_too_long",
                user_id=user_info["user_id"],
                length=len(description),
            )
            from constants import error_description_too_long

            await message.answer(error_description_too_long, parse_mode="HTML")
            return

        sanitized_description = sanitize_text(description)
        await state.update_data(description=description)
        log_info(
            logger,
            action="description_collected_edit",
            user_id=user_info["user_id"],
            username=user_info["username"],
            length=len(description),
            description=sanitized_description,
        )
        await save_edited_field(message, state)
    else:
        await process_description(message, state)


# Wrapper for callback handlers
async def process_place_of_region_callback_wrapper(
    callback: CallbackQuery, state: FSMContext
) -> None:
    """Wrapper for process_place_of_region_callback that handles edit mode."""
    data = await state.get_data()
    if data.get("editing_field") == "location":
        await process_place_of_region_callback(callback, state)
        # Don't save yet, wait for city
    else:
        await process_place_of_region_callback(callback, state)


async def process_adr_license_wrapper(callback: CallbackQuery, state: FSMContext) -> None:
    """Wrapper for process_adr_license that handles edit mode."""
    data = await state.get_data()
    if data.get("editing_field") == "adr":
        # In edit mode, process ADR selection manually to prevent continuing to next question
        user_info = get_user_info(callback.message)
        
        if callback.data == "adr_yes":
            has_adr = True
            response_text = msg_adr_yes
        elif callback.data == "adr_no":
            has_adr = False
            response_text = msg_adr_no
        else:
            log_warning(
                logger,
                "Invalid ADR callback data - user_id: %s, data: %s",
                user_info["user_id"],
                callback.data,
            )
            await callback.answer(error_processing, show_alert=True)
            return
        
        await state.update_data(is_adr_license=has_adr)
        log_info(
            logger,
            action="adr_collected_edit",
            user_id=user_info["user_id"],
            username=user_info["username"],
            has_adr=has_adr,
        )
        
        # Try to remove keyboard, ignore if already removed
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass  # Keyboard already removed or doesn't exist
        await callback.message.answer(response_text)
        
        # Save and don't continue to next question
        await save_edited_field(callback.message, state)
    else:
        await process_adr_license(callback, state)


async def process_military_booking_wrapper(callback: CallbackQuery, state: FSMContext) -> None:
    """Wrapper for process_military_booking that handles edit mode."""
    data = await state.get_data()
    if data.get("editing_field") == "military":
        # In edit mode, process military booking manually to prevent continuing to next question
        user_info = get_user_info(callback.message)
        
        if callback.data == "military_yes":
            has_military_booking = True
            response_text = msg_military_yes
        elif callback.data == "military_no":
            has_military_booking = False
            response_text = msg_military_no
        else:
            log_warning(
                logger,
                action="military_validation_failed",
                reason="invalid_callback",
                user_id=user_info["user_id"],
                callback_data=callback.data,
            )
            from constants import error_processing
            await callback.answer(error_processing, show_alert=True)
            return
        
        await state.update_data(military_booking=has_military_booking)
        log_info(
            logger,
            action="military_collected_edit",
            user_id=user_info["user_id"],
            username=user_info["username"],
            has_military_booking=has_military_booking,
        )
        
        # Try to remove keyboard, ignore if already removed
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass  # Keyboard already removed or doesn't exist
        await callback.message.answer(response_text)
        
        # Save and don't continue to next question
        await save_edited_field(callback.message, state)
    else:
        await process_military_booking(callback, state)


async def toggle_driving_categories_wrapper(callback: CallbackQuery, state: FSMContext) -> None:
    """Wrapper for toggle_driving_categories that handles edit mode."""
    data = await state.get_data()
    if data.get("editing_field") == "driving_categories":
        # In edit mode, handle toggle manually to prevent original logic from running
        is_submit = callback.data == "driver_categories_submit"

        if is_submit:
            # Handle submit manually in edit mode
            from constants import DRIVING_CATEGORIES
            from functions import toggle_selection

            # Just update selection without triggering original logic
            await toggle_selection(
                callback=callback,
                state=state,
                prefix="driver_categories_",
                field_name="selected_driver_categories",
                options=DRIVING_CATEGORIES,
                next_state=None,
            )

            # Now handle the submit logic - get updated data after toggle_selection
            updated_data = await state.get_data()
            selected = list(updated_data.get("selected_driver_categories", []))

            if selected:
                # When editing, ask for experience for ALL selected categories (even if they have experience)
                # This allows user to update experience for existing categories or add for new ones
                editing_resume = data.get("editing_resume", {})
                existing_exp = editing_resume.get("driving_experience", {})
                
                # Process ALL selected categories, not just new ones
                categories_to_ask = selected  # Ask for all selected categories
                
                # Need to ask for experience - set up state
                # Keep existing experience as base, will update/add new
                # IMPORTANT: Save all selected categories to preserve them
                await state.update_data(
                    current_category_index=0,
                    categories_to_process=categories_to_ask,  # Process all selected categories
                    driving_experience=existing_exp.copy(),  # Keep existing as base, will update/add
                    all_selected_categories=selected,  # Save all selected categories
                )
                first_cat = categories_to_ask[0]
                # Try to remove keyboard, ignore if already removed
                try:
                    await callback.message.edit_reply_markup(reply_markup=None)
                except Exception:
                    pass  # Keyboard already removed or doesn't exist
                await callback.message.answer(
                    ask_driving_exp_template.format(category=first_cat), parse_mode="HTML"
                )
                await state.set_state(ResumeForm.driving_exp_per_category)
        else:
            # Not submit, just toggle selection
            from constants import DRIVING_CATEGORIES
            from functions import toggle_selection

            await toggle_selection(
                callback=callback,
                state=state,
                prefix="driver_categories_",
                field_name="selected_driver_categories",
                options=DRIVING_CATEGORIES,
                next_state=None,
            )
    else:
        await toggle_driving_categories(callback, state)


async def toggle_type_of_work_wrapper(callback: CallbackQuery, state: FSMContext) -> None:
    """Wrapper for toggle_type_of_work that handles edit mode."""
    data = await state.get_data()
    if data.get("editing_field") == "type_of_work":
        # In edit mode, handle toggle manually to prevent continuing to next question
        is_submit = callback.data == "type_of_work_submit"
        
        if is_submit:
            # Handle submit manually - don't call toggle_selection to avoid duplicate messages
            current_data = await state.get_data()
            selected = list(current_data.get("selected_types_of_work", []))
            
            if not selected:
                user_info = get_user_info(callback)
                from constants import error_no_selection
                await callback.answer(error_no_selection, show_alert=True)
                return
            
            # Get user info from state (stored during edit start)
            editing_user_id = current_data.get("editing_user_id")
            editing_username = current_data.get("editing_username")
            user_info = {"user_id": editing_user_id, "username": editing_username}
            
            await state.update_data(types_of_work=selected)
            log_info(
                logger,
                action="types_of_work_collected_edit",
                user_id=user_info["user_id"],
                username=user_info["username"],
                types=len(selected),
            )
            
            # Try to remove keyboard, ignore if already removed
            try:
                await callback.message.edit_reply_markup(reply_markup=None)
            except Exception:
                pass
            
            # Show confirmation and save (only once)
            await callback.message.answer(
                msg_selected_template.format(items=", ".join(sorted(selected)))
            )
            await save_edited_field(callback.message, state)
        else:
            # Not submit, just toggle selection
            from constants import TYPES_OF_WORK
            from functions import toggle_selection
            
            await toggle_selection(
                callback=callback,
                state=state,
                prefix="type_of_work_",
                field_name="selected_types_of_work",
                options=TYPES_OF_WORK,
                next_state=None,
            )
    else:
        await toggle_type_of_work(callback, state)


async def toggle_race_duration_wrapper(callback: CallbackQuery, state: FSMContext) -> None:
    """Wrapper for toggle_race_duration that handles edit mode."""
    data = await state.get_data()
    if data.get("editing_field") == "race_duration":
        # In edit mode, handle toggle manually to prevent continuing to next question
        is_submit = callback.data == "race_duration_submit"
        
        if is_submit:
            # Handle submit manually - don't call toggle_selection to avoid duplicate messages
            current_data = await state.get_data()
            selected = list(current_data.get("selected_race_durations", []))
            
            if not selected:
                user_info = get_user_info(callback)
                from constants import error_no_selection
                await callback.answer(error_no_selection, show_alert=True)
                return
            
            # Get user info from state (stored during edit start)
            editing_user_id = current_data.get("editing_user_id")
            editing_username = current_data.get("editing_username")
            user_info = {"user_id": editing_user_id, "username": editing_username}
            
            await state.update_data(race_duration_preference=selected)
            log_info(
                logger,
                action="race_duration_collected_edit",
                user_id=user_info["user_id"],
                username=user_info["username"],
                count=len(selected),
            )
            
            # Try to remove keyboard, ignore if already removed
            try:
                await callback.message.edit_reply_markup(reply_markup=None)
            except Exception:
                pass
            
            # Show confirmation and save (only once)
            await callback.message.answer(
                msg_selected_template.format(items=", ".join(sorted(selected)))
            )
            await save_edited_field(callback.message, state)
        else:
            # Not submit, just toggle selection
            from constants import RACE_DURATION_OPTIONS
            from functions import toggle_selection
            
            await toggle_selection(
                callback=callback,
                state=state,
                prefix="race_duration_",
                field_name="selected_race_durations",
                options=RACE_DURATION_OPTIONS,
                next_state=None,
            )
    else:
        await toggle_race_duration(callback, state)


async def toggle_docs_for_driving_abroad_wrapper(
    callback: CallbackQuery, state: FSMContext
) -> None:
    """Wrapper for toggle_docs_for_driving_abroad that handles edit mode."""
    data = await state.get_data()
    if data.get("editing_field") == "docs_abroad":
        # In edit mode, handle toggle manually to prevent continuing to next question
        prefix = "docs_abroad_"
        is_submit = callback.data == f"{prefix}submit"
        
        if not is_submit:
            # Handle toggle with special logic for "❌ Не маю"
            current_data = await state.get_data()
            selected = set(current_data.get("selected_docs_abroad", []))
            
            if not callback.data.startswith(prefix):
                user_info = get_user_info(callback)
                log_warning(
                    logger,
                    action="docs_abroad_validation_failed",
                    reason="invalid_callback",
                    user_id=user_info["user_id"],
                    callback_data=callback.data,
                )
                from constants import error_processing
                await callback.answer(error_processing, show_alert=True)
                return
            
            item_id = callback.data[len(prefix) :]
            
            try:
                idx = int(item_id)
                if 0 <= idx < len(DOCS_FOR_DRIVING_ABROAD):
                    item = DOCS_FOR_DRIVING_ABROAD[idx]
                else:
                    user_info = get_user_info(callback)
                    log_warning(
                        logger,
                        action="docs_abroad_validation_failed",
                        reason="invalid_index",
                        user_id=user_info["user_id"],
                        index=idx,
                    )
                    from constants import error_invalid_index
                    await callback.answer(error_invalid_index, show_alert=True)
                    return
            except ValueError:
                user_info = get_user_info(callback)
                log_warning(
                    logger,
                    action="docs_abroad_validation_failed",
                    reason="invalid_callback",
                    user_id=user_info["user_id"],
                    callback_data=callback.data,
                )
                from constants import error_processing
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
            # Handle submit
            current_data = await state.get_data()
            selected = list(current_data.get("selected_docs_abroad", []))
            
            if not selected:
                user_info = get_user_info(callback)
                log_warning(
                    logger,
                    action="docs_abroad_validation_failed",
                    reason="no_selection",
                    user_id=user_info["user_id"],
                )
                from constants import error_no_selection
                await callback.answer(error_no_selection, show_alert=True)
                return
            
            # Get user info from state (stored during edit start)
            editing_user_id = current_data.get("editing_user_id")
            editing_username = current_data.get("editing_username")
            user_info = {"user_id": editing_user_id, "username": editing_username}
            
            await state.update_data(docs_for_driving_abroad=selected)
            log_info(
                logger,
                action="docs_abroad_collected_edit",
                user_id=user_info["user_id"],
                username=user_info["username"],
                count=len(selected),
            )
            
            # Try to remove keyboard, ignore if already removed
            try:
                await callback.message.edit_reply_markup(reply_markup=None)
            except Exception:
                pass
            
            # Show confirmation and save
            await callback.message.answer(
                msg_selected_template.format(items=", ".join(sorted(selected)))
            )
            await save_edited_field(callback.message, state)
    else:
        await toggle_docs_for_driving_abroad(callback, state)


async def process_driving_exp_per_category_wrapper(message: Message, state: FSMContext) -> None:
    """Wrapper for process_driving_exp_per_category that handles edit mode."""
    data = await state.get_data()
    if data.get("editing_field") == "driving_categories":
        # When editing, we need to use categories_to_process instead of selected_categories
        categories_to_process = data.get("categories_to_process", [])
        if categories_to_process:
            # Get all selected categories from state (preserved during edit start)
            all_selected = data.get("all_selected_categories", [])
            if not all_selected:
                # Fallback: try to get from selected_driver_categories
                all_selected = data.get("selected_driver_categories", [])
            # Store all_selected in state to preserve it (in case it wasn't stored)
            await state.update_data(
                all_selected_categories=all_selected,
                selected_driver_categories=categories_to_process  # Temporarily set for processing
            )

            # Process experience (but intercept to prevent continuing to next question)
            user_info = get_user_info(message)
            current_index = data.get("current_category_index", 0)
            # Get experience dict - it should already contain existing experience
            experience_dict = data.get("driving_experience", {})
            # If empty, get from editing_resume
            if not experience_dict:
                editing_resume = data.get("editing_resume", {})
                experience_dict = editing_resume.get("driving_experience", {}).copy()
            years_text = message.text.strip()

            # Validate (same as process_driving_exp_per_category)
            if not years_text:
                from logging_config import log_warning

                log_warning(
                    logger,
                    action="experience_validation_failed",
                    reason="empty",
                    user_id=user_info["user_id"],
                )
                from constants import error_not_numeric

                await message.answer(error_not_numeric)
                return

            if " " in years_text:
                from logging_config import log_warning

                log_warning(
                    logger,
                    action="experience_validation_failed",
                    reason="has_spaces",
                    user_id=user_info["user_id"],
                )
                from constants import error_not_numeric

                await message.answer(error_not_numeric)
                return

            try:
                years = float(years_text)
                if years < 0 or years > 100:
                    from logging_config import log_warning

                    log_warning(
                        logger,
                        action="experience_validation_failed",
                        reason="invalid_range",
                        user_id=user_info["user_id"],
                    )
                    from constants import error_invalid_years

                    await message.answer(error_invalid_years)
                    return
            except ValueError:
                from logging_config import log_warning

                log_warning(
                    logger,
                    action="experience_validation_failed",
                    reason="not_numeric",
                    user_id=user_info["user_id"],
                )
                from constants import error_not_numeric

                await message.answer(error_not_numeric)
                return

            # Save experience for current category
            current_cat = categories_to_process[current_index]
            experience_dict[current_cat] = years
            await state.update_data(driving_experience=experience_dict)
            from logging_config import log_info

            log_info(
                logger,
                action="experience_collected_edit",
                user_id=user_info["user_id"],
                category=current_cat,
                years=years,
            )

            # Check if more categories to process
            next_index = current_index + 1
            if next_index < len(categories_to_process):
                await state.update_data(current_category_index=next_index)
                next_cat = categories_to_process[next_index]
                await message.answer(
                    ask_driving_exp_template.format(category=next_cat), parse_mode="HTML"
                )
            else:
                # All new categories processed
                # Restore all selected categories from state
                current_data = await state.get_data()
                all_selected = current_data.get("all_selected_categories", [])
                
                # Check if we need to ask for semi-trailer types
                selected_set = set(all_selected)
                needs_semi_trailer = any(
                    cat in selected_set for cat in DRIVING_CATEGORIES_ADDITIONAL_INFO
                )

                if needs_semi_trailer:
                    # Check if we already have semi-trailer types
                    editing_resume = data.get("editing_resume", {})
                    existing_semi_trailer = editing_resume.get("semi_trailer_types", [])
                    if existing_semi_trailer:
                        # Already have, just save
                        await state.update_data(semi_trailer_types=existing_semi_trailer)
                        # experience_dict already contains merged experience (existing + new)
                        await state.update_data(
                            driving_experience=experience_dict,
                            selected_driver_categories=all_selected,
                        )
                        await save_edited_field(message, state)
                    else:
                        # Need to ask for semi-trailer types
                        from constants import SEMI_TRAILERS_TYPES, ask_semi_trailer_types
                        from functions import get_updated_keyboard

                        keyboard = await get_updated_keyboard(
                            selected=set(), categories=SEMI_TRAILERS_TYPES, prefix="semi_trailer_"
                        )
                        await state.update_data(selected_driver_categories=all_selected)
                        await message.answer(
                            ask_semi_trailer_types, parse_mode="HTML", reply_markup=keyboard
                        )
                        await state.set_state(ResumeForm.driving_semi_trailer_types)
                else:
                    # No semi-trailer types needed, save experiences
                    # experience_dict already contains merged experience (existing + new)
                    await state.update_data(
                        driving_experience=experience_dict, selected_driver_categories=all_selected
                    )
                    await save_edited_field(message, state)
        else:
            # No new categories to process, just save
            await save_edited_field(message, state)
    else:
        await process_driving_exp_per_category(message, state)


async def process_driving_semi_trailer_types_wrapper(
    callback: CallbackQuery, state: FSMContext
) -> None:
    """Wrapper for process_driving_semi_trailer_types that handles edit mode."""
    data = await state.get_data()
    if data.get("editing_field") == "driving_categories":
        # In edit mode, process semi-trailer types and save
        prefix = "semi_trailer_"

        if callback.data == f"{prefix}submit":
            current_data = await state.get_data()
            selected_types = list(current_data.get("semi_trailer_selection", []))

            if not selected_types:
                user_info = get_user_info(callback)
                from logging_config import log_warning

                log_warning(
                    logger,
                    action="semi_trailer_validation_failed",
                    reason="no_selection",
                    user_id=user_info["user_id"],
                )
                from constants import error_no_semi_trailer

                await callback.answer(error_no_semi_trailer, show_alert=True)
                return

            user_info = get_user_info(callback)
            await state.update_data(semi_trailer_types=selected_types)
            from logging_config import log_info

            log_info(
                logger,
                action="semi_trailer_collected_edit",
                user_id=user_info["user_id"],
                username=user_info["username"],
                types=len(selected_types),
            )

            # experience_dict in state should already contain merged experience (existing + new)
            # Just ensure it's saved properly
            current_experience = data.get("driving_experience", {})
            if not current_experience:
                # Fallback: get from editing_resume if somehow lost
                editing_resume = data.get("editing_resume", {})
                current_experience = editing_resume.get("driving_experience", {})
            
            # Restore all selected categories from state before saving
            all_selected = current_data.get("all_selected_categories", [])
            if not all_selected:
                # Fallback: try to get from selected_driver_categories
                all_selected = current_data.get("selected_driver_categories", [])
            
            await state.update_data(
                driving_experience=current_experience,
                selected_driver_categories=all_selected
            )

            # Try to remove keyboard, ignore if already removed
            try:
                await callback.message.edit_reply_markup(reply_markup=None)
            except Exception:
                pass  # Keyboard already removed or doesn't exist
            await save_edited_field(callback.message, state)
        else:
            # Use toggle_selection for selection
            from constants import SEMI_TRAILERS_TYPES
            from functions import toggle_selection

            await toggle_selection(
                callback=callback,
                state=state,
                prefix=prefix,
                field_name="semi_trailer_selection",
                options=SEMI_TRAILERS_TYPES,
                next_state=None,
            )
    else:
        await process_driving_semi_trailer_types(callback, state)


async def skip_description_wrapper(callback: CallbackQuery, state: FSMContext) -> None:
    """Wrapper for skip_description that handles edit mode."""
    data = await state.get_data()
    if data.get("editing_field") == "description":
        await state.update_data(description="")
        await save_edited_field(callback.message, state)
    else:
        await skip_description(callback, state)
