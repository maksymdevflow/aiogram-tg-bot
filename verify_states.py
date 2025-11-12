#!/usr/bin/env python3
"""
Скрипт для автоматичної перевірки відповідності станів, обробників та реєстрацій.
Запускайте цей скрипт після змін у коді для перевірки актуальності.
"""

import re
import ast
from pathlib import Path
from typing import Set, Dict, List, Tuple

# Шляхи до файлів
BASE_DIR = Path(__file__).parent
STAGE_RESUME_FILE = BASE_DIR / "app" / "build_resume" / "stage_resume.py"
BOT_FILE = BASE_DIR / "app" / "bot.py"
CONSTANTS_FILE = BASE_DIR / "app" / "constants.py"


def extract_states_from_file(file_path: Path) -> Set[str]:
    """Витягує всі стани з ResumeForm."""
    states = set()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Шукаємо клас ResumeForm та всі стани
        pattern = r'class ResumeForm\(StatesGroup\):.*?(?=\n\n|\nclass|\Z)'
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            class_content = match.group(0)
            # Шукаємо всі рядки з = State()
            state_pattern = r'(\w+)\s*=\s*State\(\)'
            for state_match in re.finditer(state_pattern, class_content):
                states.add(state_match.group(1))
    
    except FileNotFoundError:
        print(f"[WARN] Файл не знайдено: {file_path}")
    except Exception as e:
        print(f"[ERROR] Помилка при читанні {file_path}: {e}")
    
    return states


def extract_handlers_from_file(file_path: Path) -> Dict[str, str]:
    """Витягує всі обробники (process_* та toggle_*) з файлу."""
    handlers = {}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Шукаємо async def process_* або toggle_*
        pattern = r'async def (process_\w+|toggle_\w+)'
        for match in re.finditer(pattern, content):
            handler_name = match.group(1)
            # Визначаємо тип (Message або Callback)
            handler_type = "Unknown"
            # Шукаємо параметри функції
            func_pattern = rf'async def {re.escape(handler_name)}\s*\((.*?)\)'
            func_match = re.search(func_pattern, content, re.DOTALL)
            if func_match:
                params = func_match.group(1)
                if 'Message' in params:
                    handler_type = "Message"
                elif 'CallbackQuery' in params:
                    handler_type = "Callback"
            
            handlers[handler_name] = handler_type
    
    except FileNotFoundError:
        print(f"[WARN] Файл не знайдено: {file_path}")
    except Exception as e:
        print(f"[ERROR] Помилка при читанні {file_path}: {e}")
    
    return handlers


def extract_registrations_from_file(file_path: Path) -> Dict[str, str]:
    """Витягує всі реєстрації обробників з bot.py."""
    registrations = {}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Шукаємо dp.message.register або dp.callback_query.register
        # Патерн: dp.message.register(handler_name, ResumeForm.state_name)
        message_pattern = r'dp\.message\.register\s*\(\s*(\w+)\s*,\s*ResumeForm\.(\w+)\s*\)'
        for match in re.finditer(message_pattern, content):
            handler_name = match.group(1)
            state_name = match.group(2)
            registrations[handler_name] = ("Message", state_name)
        
        # Патерн для callback: dp.callback_query.register(handler_name, lambda...)
        callback_pattern = r'dp\.callback_query\.register\s*\(\s*(\w+)\s*'
        for match in re.finditer(callback_pattern, content):
            handler_name = match.group(1)
            # Для callback важче визначити стан, тому просто позначаємо як Callback
            registrations[handler_name] = ("Callback", "Unknown")
    
    except FileNotFoundError:
        print(f"[WARN] Файл не знайдено: {file_path}")
    except Exception as e:
        print(f"[ERROR] Помилка при читанні {file_path}: {e}")
    
    return registrations


def extract_constants_from_file(file_path: Path) -> Set[str]:
    """Витягує всі константи ask_* з constants.py."""
    constants = set()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Шукаємо ask_* = "..."
        pattern = r'(ask_\w+)\s*='
        for match in re.finditer(pattern, content):
            constants.add(match.group(1))
    
    except FileNotFoundError:
        print(f"[WARN] Файл не знайдено: {file_path}")
    except Exception as e:
        print(f"[ERROR] Помилка при читанні {file_path}: {e}")
    
    return constants


def map_state_to_handler(state_name: str) -> Tuple[str, str]:
    """Визначає очікуваний обробник для стану."""
    # Конвертуємо snake_case в camelCase для обробника
    parts = state_name.split('_')
    
    # Спеціальні випадки
    if state_name == 'place_of_living_region':
        return ('process_place_of_region_callback', 'Callback')
    elif state_name == 'place_of_living_city':
        return ('process_place_of_city', 'Message')
    elif state_name == 'driving_categories':
        return ('toggle_driving_categories', 'Callback')
    elif state_name == 'driving_exp_per_category':
        return ('process_driving_exp_per_category', 'Message')
    elif state_name == 'driving_semi_trailer_types':
        return ('process_driving_semi_trailer_types', 'Callback')
    elif state_name == 'type_of_work':
        return ('toggle_type_of_work', 'Callback')
    elif state_name == 'is_adr_license':
        return ('process_adr_license', 'Callback')
    elif state_name == 'race_duration_preference':
        return ('toggle_race_duration', 'Callback')
    
    # Загальне правило: process_ + snake_case
    handler_name = 'process_' + state_name
    return (handler_name, 'Message')


def main():
    """Основна функція перевірки."""
    import sys
    import io
    
    # Налаштування для коректного виводу в Windows
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    print("=" * 60)
    print("[CHECK] Перевірка відповідності станів, обробників та реєстрацій")
    print("=" * 60)
    print()
    
    # Витягуємо дані
    states = extract_states_from_file(STAGE_RESUME_FILE)
    handlers = extract_handlers_from_file(STAGE_RESUME_FILE)
    registrations = extract_registrations_from_file(BOT_FILE)
    constants = extract_constants_from_file(CONSTANTS_FILE)
    
    print(f"[INFO] Знайдено:")
    print(f"   - Станів: {len(states)}")
    print(f"   - Обробників: {len(handlers)}")
    print(f"   - Реєстрацій: {len(registrations)}")
    print(f"   - Констант: {len(constants)}")
    print()
    
    # Перевірка 1: Стани без обробників
    print("=" * 60)
    print("[1] Перевірка станів без обробників")
    print("=" * 60)
    missing_handlers = []
    for state in sorted(states):
        expected_handler, _ = map_state_to_handler(state)
        if expected_handler not in handlers:
            missing_handlers.append((state, expected_handler))
            print(f"[ERROR] {state} -> очікується обробник: {expected_handler}")
    
    if not missing_handlers:
        print("[OK] Всі стани мають обробники")
    print()
    
    # Перевірка 2: Обробники без реєстрації
    print("=" * 60)
    print("[2] Перевірка обробників без реєстрації")
    print("=" * 60)
    missing_registrations = []
    for handler_name in sorted(handlers.keys()):
        if handler_name not in registrations:
            missing_registrations.append(handler_name)
            print(f"[ERROR] {handler_name} -> не зареєстровано в bot.py")
    
    if not missing_registrations:
        print("[OK] Всі обробники зареєстровані")
    print()
    
    # Перевірка 3: Реєстрації без обробників
    print("=" * 60)
    print("[3] Перевірка реєстрацій без обробників")
    print("=" * 60)
    orphan_registrations = []
    for handler_name in sorted(registrations.keys()):
        if handler_name not in handlers:
            orphan_registrations.append(handler_name)
            print(f"[WARN] {handler_name} -> зареєстровано, але обробник не знайдено")
    
    if not orphan_registrations:
        print("[OK] Всі реєстрації мають обробники")
    print()
    
    # Перевірка 4: Константи без використання
    print("=" * 60)
    print("[4] Перевірка констант питань")
    print("=" * 60)
    # Перевіряємо використання констант у файлах
    used_constants = set()
    for file_path in [STAGE_RESUME_FILE, BOT_FILE]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                for const in constants:
                    if const in content:
                        used_constants.add(const)
        except:
            pass
    
    unused_constants = constants - used_constants
    if unused_constants:
        print(f"[WARN] Константи, які не використовуються напряму:")
        for const in sorted(unused_constants):
            print(f"   - {const}")
    else:
        print("[OK] Всі константи використовуються")
    print()
    
    # Підсумок
    print("=" * 60)
    print("[SUMMARY] Підсумок")
    print("=" * 60)
    
    total_issues = len(missing_handlers) + len(missing_registrations) + len(orphan_registrations)
    
    if total_issues == 0:
        print("[SUCCESS] Всі перевірки пройдені успішно!")
        print("   Код відповідає всім вимогам.")
    else:
        print(f"[WARN] Знайдено проблем: {total_issues}")
        print()
        if missing_handlers:
            print(f"   - Станів без обробників: {len(missing_handlers)}")
        if missing_registrations:
            print(f"   - Обробників без реєстрації: {len(missing_registrations)}")
        if orphan_registrations:
            print(f"   - Реєстрацій без обробників: {len(orphan_registrations)}")
        print()
        print("   Перегляньте деталі вище та виправте проблеми.")
    
    print()
    print("=" * 60)
    
    return total_issues == 0


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

