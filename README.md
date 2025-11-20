# Driver Resume Bot - Telegram Bot for Ukrainian Drivers

## 📋 Project Overview

**Driver Resume Bot** is a professional Telegram bot designed to help drivers of any category in Ukraine create comprehensive, structured resumes and connect with potential employers. The bot guides users through an intuitive multi-step form using a state machine pattern, collecting essential information about driving experience, qualifications, and preferences.

### Key Value Proposition
- **Streamlined Resume Creation**: Interactive, step-by-step process that ensures all critical information is captured
- **Professional Format**: Structured data collection suitable for automated job matching
- **User-Friendly Interface**: Native Telegram interface with inline keyboards and validation
- **Data Persistence**: Secure storage in Firebase Firestore for future job matching

---

## 🏗️ Architecture Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Telegram Bot API                          │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    aiogram                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Dispatcher  │  │  FSM Context │  │   Handlers   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        │                               │
        ▼                               ▼
┌───────────────┐              ┌───────────────┐
│  Bot Logic    │              │  Data Layer   │
│               │              │               │
│ • State Mgmt  │              │ • Firebase    │
│ • Validation  │              │ • Firestore   │
│ • UI Flow     │              │ • CRUD Ops    │
└───────────────┘              └───────────────┘
```

### Component Breakdown

**1. Presentation Layer (`app/bot.py`)**
- Entry point for the application
- Handler registration and routing
- Bot initialization and lifecycle management

**2. Business Logic Layer (`app/build_resume/`)**
- **FSM States**: Manages multi-step form flow using `ResumeForm` StatesGroup
- **Process Handlers**: Validates input, processes data, and manages state transitions
- **State Flow**: 15+ sequential states collecting driver information

**3. Data Layer (`firebase_db/`)**
- **Firestore Integration**: Async CRUD operations for resumes and user data
- **Data Models**: Structured storage with timestamps and user associations

**4. Configuration Layer**
- **Constants** (`app/constants.py`): All user-facing text and data (language-specific)
- **Keyboards** (`app/keyboards.py`): UI components (Reply and Inline keyboards)
- **Utilities** (`app/functions.py`): Reusable functions for keyboard generation and data processing

**5. Infrastructure**
- **Logging** (`app/logging_config.py`): Structured logging with data sanitization
- **Security** (`app/security_middleware.py`): Rate limiting and spam protection
- **Docker**: Containerization support for deployment

### Architecture Principles

- **Separation of Concerns**: Clear boundaries between presentation, business logic, and data layers
- **State Machine Pattern**: FSM for managing complex multi-step forms
- **Configuration-Driven**: All user-facing text in constants, no hardcoded strings
- **Async-First**: Full async/await pattern for scalability
- **Security-First**: Data sanitization in logs, rate limiting, input validation

---

## ✨ Current Features

### Resume Creation Flow
1. **Personal Information**
   - Name and contact details
   - Age and location (region and city)

2. **Driving Qualifications**
   - Multiple driving categories selection (B, C, C1, C1E, CE)
   - Experience years per category
   - Semi-trailer types (for relevant categories)

3. **Work Preferences**
   - Type of work (Ukraine, International, Abroad)
   - Desired salary
   - Race duration preferences
   - Types of vehicles worked with

4. **Additional Qualifications**
   - ADR license for dangerous goods
   - International driving documents
   - Military booking status

5. **Personal Description**
   - Optional detailed description
   - Previous experience and special skills

### Technical Features
- ✅ **Multi-step Form Validation**: Input validation at each stage
- ✅ **Dynamic Inline Keyboards**: Toggle-based selection for multiple choices
- ✅ **State Persistence**: Resume creation can be interrupted and resumed
- ✅ **Comprehensive Logging**: All actions logged with user tracking
- ✅ **Error Handling**: Graceful error messages and recovery
- ✅ **Data Sanitization**: Sensitive data protection in logs
- ✅ **Firebase Integration**: Secure cloud storage

---

## 🚀 Future Features

### Phase 1: Job Matching Engine (Q2 2024)
- **Automated Job Matching**: AI-powered algorithm matching driver profiles with job postings
- **Job Database**: Integration with job boards and employer systems
- **Smart Notifications**: Real-time job alerts based on preferences
- **Match Scoring**: Relevance scoring for job recommendations

---

## 🌍 Language Support

The bot currently supports multiple languages through separate codebase branches:

### Current Languages
- ✅ **Ukrainian** (`tg_bot_v1_ukraine` branch) - Fully implemented
- 🔄 **English** (`tg_bot_v1_eng` branch) - Planned

### Branch Structure
- **`tg_bot_v1_ukraine`**: Ukrainian language version (current main branch)
- **`tg_bot_v1_eng`**: English language version (future implementation)

Each language branch contains:
- Language-specific constants in `app/constants.py`
- Localized keyboard texts in `app/keyboards.py`
- Language-appropriate validation messages

**Note**: Language switching within a single bot instance is planned for future releases.

---

## 🛠️ Tech Stack

### Core Technologies
- **Python 3.11+**: Main programming language
- **aiogram 3.22.0**: Modern async Telegram Bot framework
- **Firebase Firestore**: NoSQL database for resume storage
- **python-dotenv**: Environment variable management

### Development Tools
- **Docker**: Containerization
- **Ruff**: Code linting and formatting
- **Structured Logging**: Custom logging configuration

### Infrastructure
- **Firebase Admin SDK**: Server-side Firebase operations
- **Telegram Bot API**: Official Telegram Bot interface

---

## 📦 Installation & Setup

### Prerequisites
- Python 3.11 or higher
- Firebase project with Firestore enabled
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd aiogram-tg-bot
   ```
   
   **For specific language version:**
   ```bash
   # Ukrainian version (default)
   git checkout tg_bot_v1_ukraine
   
   # English version (when available)
   git checkout tg_bot_v1_eng
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   - Copy your Firebase service account JSON to project root
   - Create `.env` file:
     ```env
     BOT_TOKEN=your_telegram_bot_token
     ```

5. **Run the bot**
   ```bash
   python app/bot.py
   ```

### Docker Deployment

```bash
docker-compose up -d
```

---

## 📁 Project Structure

```
aiogram-tg-bot/
├── app/
│   ├── bot.py                 # Main entry point, handler registration
│   ├── constants.py           # All user-facing text and data
│   ├── keyboards.py           # UI keyboard definitions
│   ├── functions.py           # Reusable utility functions
│   ├── logging_config.py      # Logging configuration
│   ├── security_middleware.py # Rate limiting and security
│   └── build_resume/
│       └── stage_resume.py    # FSM states and process handlers
├── firebase_db/
│   ├── config.py              # Firebase initialization
│   └── crud.py                # Database operations
├── logs/                      # Application logs
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

---

## 🔒 Security & Privacy

- **Data Sanitization**: Sensitive information (names, phones) is sanitized in logs
- **Rate Limiting**: Security middleware prevents spam and abuse
- **Input Validation**: All user inputs are validated before processing
- **Secure Storage**: Firebase Firestore with proper access controls
- **No Hardcoded Secrets**: All sensitive data via environment variables

---

## 📊 Project Status

**Current Version**: 1.0.0  
**Status**: ✅ Production Ready (Resume Creation)  
**Next Milestone**: Job Matching Engine

### Completed
- ✅ Multi-step resume creation flow
- ✅ Firebase integration
- ✅ Comprehensive logging
- ✅ Input validation
- ✅ Security middleware

### In Progress
- 🔄 Job matching algorithm design
- 🔄 Job database integration
- 🔄 English language support (`tg_bot_v1_eng` branch)

### Planned
- 📋 Automated job notifications
- 📋 Multi-language support in single bot instance

---

### Key Rules
- All user-facing text must be in `constants.py`
- Handlers must be registered in `bot.py`
- Use FSM for multi-step flows
- Log all important actions with proper sanitization

---

## 👨‍💻 Development & AI Assistance

### Core Development
**Important**: The core architecture, business logic, design patterns, and project structure were developed manually by the project author. This includes:
- **Architecture Design**: Complete system architecture, layer separation, and component structure
- **FSM Implementation**: State machine patterns and flow design for multi-step forms
- **Business Logic**: All process handlers, validation logic, and state transitions
- **Project Structure**: File organization, module separation, and code organization principles
- **Design Patterns**: Application of architectural patterns and best practices

### AI Agent Assistance
During development, various AI coding assistants were used to accelerate specific tasks:

#### Documentation & Project Management
- **README.md & Documentation**: AI assistants helped structure and write comprehensive project documentation, architecture diagrams, and setup instructions
- **ARCHITECTURE.md**: Assistance with documenting architectural principles and development guidelines
- **Code Comments**: Help with writing clear code comments and docstrings

#### Code Quality & Refactoring
- **Code Review**: AI agents assisted in reviewing code for potential improvements and consistency
- **Refactoring**: Help with refactoring repetitive code into reusable functions
- **Linting & Formatting**: Assistance with code style improvements and formatting

#### Feature Implementation Support
- **Firebase Integration**: AI assistance with Firebase Admin SDK integration and CRUD operations
- **Logging System**: Help with implementing structured logging with data sanitization
- **Security Middleware**: Assistance with rate limiting and security implementation
- **Error Handling**: Help with implementing comprehensive error handling patterns

#### Debugging & Testing
- **Bug Fixes**: AI agents helped identify and fix bugs, especially import issues and syntax errors
- **Testing Scenarios**: Assistance with creating test scenarios and validation logic
- **Error Messages**: Help with user-friendly error message implementation

#### Utility Functions
- **Helper Functions**: AI assistance with creating utility functions in `functions.py` for keyboard generation and data processing
- **Validation Logic**: Help with input validation patterns and error handling

### Development Philosophy
While AI agents provided valuable assistance with implementation details, documentation, and code quality improvements, all architectural decisions, core logic, and design patterns were created manually. The project maintains a clear, maintainable structure that reflects careful planning and understanding of the system requirements.

---

## 📝 License

See [LICENSE](LICENSE) file for details.

---

## 📧 Contact & Support

For questions, issues, or feature requests, please open an issue in the repository.

---

**Built with ❤️ for Ukrainian drivers**
