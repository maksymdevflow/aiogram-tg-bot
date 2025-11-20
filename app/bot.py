import asyncio
import logging
import sys
from os import getenv
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    Message,
    ReplyKeyboardRemove,
)
from build_resume.stage_resume import (
    ResumeForm,
    convert_firebase_resume_to_display_format,
    format_resume_display,
)
from constants import (
    ask_name,
    button_create_resume,
    button_my_resume,
    msg_bot_greeting,
    msg_bot_greeting_with_resume,
    msg_my_resume_title,
    msg_no_resume,
    msg_resume_deleted,
    msg_resume_start,
)
from dotenv import load_dotenv
from edit_resume import (
    handle_edit_field,
    handle_edit_resume_menu,
    process_adr_license_wrapper,
    process_age_wrapper,
    process_description_wrapper,
    process_desired_salary_wrapper,
    process_driving_exp_per_category_wrapper,
    process_driving_semi_trailer_types_wrapper,
    process_military_booking_wrapper,
    process_name_wrapper,
    process_phone_wrapper,
    process_place_of_city_wrapper,
    process_place_of_region_callback_wrapper,
    process_types_of_cars_wrapper,
    skip_description_wrapper,
    toggle_docs_for_driving_abroad_wrapper,
    toggle_driving_categories_wrapper,
    toggle_race_duration_wrapper,
    toggle_type_of_work_wrapper,
)
from functions import safe_callback_answer
from keyboards import (
    delete_resume_keyboard,
    get_main_menu_keyboard,
)
from logging_config import get_user_info, log_error, log_info, setup_logging
from security_middleware import SecurityMiddleware

from firebase_db.crud import delete_resume, get_resume

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

setup_logging(log_level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from firebase_db import config  # noqa: F401

    logger.info("Firebase initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Firebase: {str(e)}", exc_info=True)
    raise

TOKEN = getenv("BOT_TOKEN")

dp = Dispatcher()

# Initialize security middleware
security_middleware = SecurityMiddleware(
    # Rate limiting - allow normal survey completion
    max_requests_per_minute=30,  # Enough for normal survey flow
    max_requests_per_hour=200,
    max_requests_per_day=1000,
    # Spam detection
    max_identical_messages=5,
    identical_message_window=60,
    min_message_interval=0.5,  # 500ms between messages
    # DDoS protection
    burst_threshold=10,  # 10 requests in 2 seconds = suspicious
    burst_window=2.0,
    # Survey protection - allow up to 1 hour for completion
    max_survey_duration=3600,
    max_state_changes_per_minute=20,  # Allow rapid navigation
    # Blocking
    initial_block_duration=300,  # 5 minutes
    max_block_duration=86400,  # 24 hours
)

# Register security middleware (applies to all updates)
dp.update.middleware(security_middleware)


@dp.message(Command("start"))
async def command_start_handler(message: Message, state: FSMContext) -> None:
    try:
        user_info = get_user_info(message)
        log_info(
            logger,
            action="user_started_bot",
            user_id=user_info["user_id"],
            username=user_info["username"],
        )
        await state.clear()

        # Check if user has a resume
        has_resume = False
        if user_info["user_id"]:
            resume_data = await get_resume(user_info["user_id"])
            has_resume = resume_data is not None

        keyboard = get_main_menu_keyboard(has_resume=has_resume)
        greeting = msg_bot_greeting_with_resume if has_resume else msg_bot_greeting
        await message.answer(greeting, reply_markup=keyboard)
    except Exception as e:
        user_info = get_user_info(message)
        log_error(
            logger,
            action="start_command_failed",
            error=str(e),
            user_id=user_info["user_id"],
            username=user_info["username"],
            exc_info=True,
        )


@dp.message(lambda message: message.text == button_create_resume)
async def handle_create_resume_button(message: Message, state: FSMContext) -> None:
    """Handle 'Create Resume' button press from main menu."""
    try:
        user_info = get_user_info(message)

        # Check if user already has a resume
        if user_info["user_id"]:
            resume_data = await get_resume(user_info["user_id"])
            if resume_data:
                # User has a resume, show it instead
                display_data = convert_firebase_resume_to_display_format(resume_data)
                resume_text = format_resume_display(display_data)
                # Replace title with "My Resume"
                resume_text = resume_text.replace(
                    "📋 <b>Ваше резюме</b>", msg_my_resume_title.strip()
                )
                await message.answer(
                    resume_text, parse_mode="HTML", reply_markup=delete_resume_keyboard
                )
                return

        # No resume found, start creation
        log_info(
            logger,
            action="user_started_resume_creation",
            user_id=user_info["user_id"],
            username=user_info["username"],
        )
        await message.answer(msg_resume_start)
        await state.set_state(ResumeForm.name)
        log_info(logger, action="asking_for_name", user_id=user_info["user_id"])
        await message.answer(
            ask_name,
            reply_markup=ReplyKeyboardRemove(),
        )
    except Exception as e:
        user_info = get_user_info(message)
        log_error(
            logger,
            action="create_resume_button_failed",
            error=str(e),
            user_id=user_info["user_id"],
            username=user_info["username"],
            exc_info=True,
        )


@dp.message(lambda message: message.text == button_my_resume)
async def handle_my_resume_button(message: Message, state: FSMContext) -> None:
    """Handle 'My Resume' button press from main menu."""
    try:
        user_info = get_user_info(message)
        log_info(
            logger,
            action="user_viewed_resume",
            user_id=user_info["user_id"],
            username=user_info["username"],
        )

        if not user_info["user_id"]:
            await message.answer(msg_no_resume)
            return

        resume_data = await get_resume(user_info["user_id"])
        if resume_data:
            display_data = convert_firebase_resume_to_display_format(resume_data)
            resume_text = format_resume_display(display_data)
            # Replace title with "My Resume"
            resume_text = resume_text.replace("📋 <b>Ваше резюме</b>", msg_my_resume_title.strip())
            await message.answer(
                resume_text, parse_mode="HTML", reply_markup=delete_resume_keyboard
            )
        else:
            await message.answer(msg_no_resume)
            # Update keyboard to show "Create Resume"
            keyboard = get_main_menu_keyboard(has_resume=False)
            await message.answer(msg_bot_greeting, reply_markup=keyboard)  # No resume, show create message
    except Exception as e:
        user_info = get_user_info(message)
        log_error(
            logger,
            action="my_resume_button_failed",
            error=str(e),
            user_id=user_info["user_id"],
            username=user_info["username"],
            exc_info=True,
        )


@dp.callback_query(lambda c: c.data == "delete_resume_confirm")
async def handle_delete_resume(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle delete resume confirmation."""
    try:
        user_info = get_user_info(callback)
        log_info(
            logger,
            action="user_deleting_resume",
            user_id=user_info["user_id"],
            username=user_info["username"],
        )

        if not user_info["user_id"]:
            await safe_callback_answer(callback, "Помилка: не вдалося визначити користувача")
            return

        success = await delete_resume(user_info["user_id"])
        if success:
            await safe_callback_answer(callback, "Резюме видалено")
            
            # Remove inline keyboard and show reply keyboard with "Create Resume" button
            keyboard = get_main_menu_keyboard(has_resume=False)
            try:
                await callback.message.edit_reply_markup(reply_markup=None)
            except Exception:
                pass  # Keyboard might already be removed
            await callback.message.answer(msg_resume_deleted, reply_markup=keyboard)
        else:
            await safe_callback_answer(callback, "Помилка при видаленні резюме")
    except Exception as e:
        user_info = get_user_info(callback)
        log_error(
            logger,
            action="delete_resume_failed",
            error=str(e),
            user_id=user_info["user_id"],
            username=user_info["username"],
            exc_info=True,
        )
        await safe_callback_answer(callback, "Помилка при видаленні резюме")


# Register edit resume handlers
dp.callback_query.register(handle_edit_resume_menu, lambda c: c.data == "edit_resume_menu")
dp.callback_query.register(handle_edit_field, lambda c: c.data.startswith("edit_field_"))


async def main() -> None:
    try:
        bot = Bot(token=TOKEN)
        log_info(logger, action="bot_initialized", data={"status": "starting_polling"})
        await dp.start_polling(bot)
    except Exception as e:
        log_error(logger, action="bot_execution_failed", error=str(e), exc_info=True)
        raise


if __name__ == "__main__":
    log_info(logger, action="bot_application_starting")
    try:
        dp.message.register(process_name_wrapper, ResumeForm.name)
        dp.message.register(process_phone_wrapper, ResumeForm.phone)
        dp.message.register(process_age_wrapper, ResumeForm.age)
        dp.message.register(process_place_of_city_wrapper, ResumeForm.place_of_living_city)
        dp.message.register(
            process_driving_exp_per_category_wrapper, ResumeForm.driving_exp_per_category
        )
        dp.message.register(process_types_of_cars_wrapper, ResumeForm.types_of_cars)
        dp.message.register(process_desired_salary_wrapper, ResumeForm.desired_salary)
        dp.message.register(process_description_wrapper, ResumeForm.description)

        dp.callback_query.register(
            process_place_of_region_callback_wrapper, lambda c: c.data.startswith("region_")
        )
        dp.callback_query.register(
            toggle_driving_categories_wrapper, lambda c: c.data.startswith("driver_categories_")
        )
        dp.callback_query.register(
            process_driving_semi_trailer_types_wrapper, lambda c: c.data.startswith("semi_trailer_")
        )
        dp.callback_query.register(
            toggle_type_of_work_wrapper, lambda c: c.data.startswith("type_of_work_")
        )
        dp.callback_query.register(
            process_adr_license_wrapper, lambda c: c.data in ["adr_yes", "adr_no"]
        )
        dp.callback_query.register(
            toggle_race_duration_wrapper, lambda c: c.data.startswith("race_duration_")
        )
        dp.callback_query.register(
            toggle_docs_for_driving_abroad_wrapper, lambda c: c.data.startswith("docs_abroad_")
        )
        dp.callback_query.register(
            process_military_booking_wrapper, lambda c: c.data in ["military_yes", "military_no"]
        )
        dp.callback_query.register(skip_description_wrapper, lambda c: c.data == "skip_description")

        log_info(logger, action="handlers_registered", data={"status": "success"})
        asyncio.run(main())
    except KeyboardInterrupt:
        log_info(logger, action="bot_stopped", data={"reason": "user_interrupt"})
    except Exception as e:
        log_error(logger, action="fatal_error", error=str(e), exc_info=True)
        raise
