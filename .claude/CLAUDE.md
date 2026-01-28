# Keuvi Project Context

## About Keuvi
Keuvi is a freemium SAT test prep app. The core philosophy is:

> "Keuvi doesn't feel like studying. It feels like a calm, slightly sarcastic tutor who's always on your side."

The Penguin mascot serves as coach + navigator + motivator + friction remover.

## Tech Stack
- **Backend**: Django REST Framework, PostgreSQL, Heroku
- **iOS App**: Swift/SwiftUI
- **Android App**: Kotlin, Jetpack Compose
- **Web**: React (if applicable)

## Key Principles
1. Low-pressure, encouraging UX
2. Penguin personality: Calm, light humor, never shaming, always optional
3. Mobile-first experience
4. Freemium model with soft paywalls

## Current Priorities
See the 2-Month Roadmap in Argos Control for active sprints and tasks.

---

# Repository Structure

## Project Repositories
| Role | Repo Path | Primary Folders |
|------|-----------|-----------------|
| @fullstack | `~/argosventures/keuvi` | `api/`, `satlingo/`, `core/` |
| @ios | `~/argosventures/keuvi_ios` | `Keuvi/`, `KeuviTests/` |
| @android | `~/argosventures/keuvi_android` | `app/src/main/`, `app/src/test/` |

## Key Folders by Role

### Backend (@fullstack)
```
keuvi/
├── api/                    # Django REST API endpoints
│   ├── views.py
│   ├── serializers.py
│   └── urls.py
├── core/                   # Core models and business logic
├── satlingo/               # Django settings
└── requirements.txt
```

### iOS (@ios)
```
keuvi_ios/
├── Keuvi/
│   ├── Views/              # SwiftUI views
│   ├── ViewModels/         # MVVM view models
│   ├── Models/             # Data models
│   ├── Services/           # API, storage services
│   └── Components/         # Reusable UI components
└── KeuviTests/
```

### Android (@android)
```
keuvi_android/
├── app/src/main/
│   ├── java/.../keuvi/
│   │   ├── ui/             # Compose screens
│   │   ├── viewmodel/      # ViewModels
│   │   ├── data/           # Repository, API
│   │   └── di/             # Hilt modules
│   └── res/                # Resources
└── app/src/test/
```

---

# Agent Roles

When fixing bugs or implementing features, Claude should adopt the appropriate role based on the task.

## Available Roles
1. `@fullstack` - Full Stack Engineer (coordinates all work)
2. `@ios` - iOS App Engineer  
3. `@android` - Android App Engineer

## How to Invoke a Role

**Option 1**: Reference the role file
```
@android.md Fix this bug: [description]
```

**Option 2**: Mention the role in your prompt
```
As the @android engineer, fix this bug: [description]
```

**Option 3**: Let @fullstack delegate
```
@fullstack.md Here are 5 bugs across iOS and Android. Triage and fix them.
```
