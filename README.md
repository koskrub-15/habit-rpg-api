# ⚔️ Habit RPG API

[![CI](https://github.com/koskrub-15/habit_api__bevz_konstantin__main/actions/workflows/ci.yml/badge.svg)](https://github.com/koskrub-15/habit_api__bevz_konstantin__main/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/koskrub-15/habit_api__bevz_konstantin__main/branch/main/graph/badge.svg)](https://codecov.io/gh/koskrub-15/habit_api__bevz_konstantin__main)

A gamified habit tracking and task management API built with FastAPI. Transform your daily routine into an RPG adventure!

---

## 🚀 Overview

**Habit RPG API** is a robust backend service designed to help users build better habits and manage tasks through gamification. Earn gold, gain experience, unlock achievements, and equip items by completing your real-life goals.

### ✨ Key Features

- **🔐 Secure Authentication**: JWT-based auth with Access/Refresh token rotation and Argon2 password hashing.
- **🛒 Dynamic Shop**: Automated shop rotation, stock management, and time-based item availability.
- **🏆 Achievement System**: Automated and manual achievement unlocking based on user progress and streaks.
- **🤝 Social Integration**: Friend request system (send, accept, decline, remove).
- **📜 Activity History**: Automatic logging of every important action (tasks, habits, purchases).
- **🔄 Daily Reset**: Automated resetting of daily tasks and habits to keep your routine fresh.
- **🛠️ Generic Router Factory**: High-speed development with a custom factory for CRUD operations.

### 🛠️ Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Database**: PostgreSQL with [SQLAlchemy](https://www.sqlalchemy.org/) (Async)
- **Migrations**: [Alembic](https://alembic.sqlalchemy.org/)
- **Validation**: [Pydantic V2](https://docs.pydantic.dev/)
- **Environment**: [uv](https://github.com/astral-sh/uv) & [Docker](https://www.docker.com/)

---

## ⚡ Quick Start

### ▶️ Run the App

Build and run everything from zero, including configuration and database setup:

```shell
just app-i-docker-i-run
```

### 🚮 Purge Data

Wipe all application data and start clean:

```shell
just app-i-docker-i-purge
```

---

## 🛠️ Development

### Install just

You must have [just] installed on your system to run different commands.

- [just.just](just/dev/just.just)

After installing [just], you can see all available commands with:

```bash
just --list
```

[just]: https://github.com/casey/just

### Initialize development environment

Create venv, register pre-commit hooks, and install dependencies:

```bash
just init-i-dev
```

### Run Tests

```bash
just test-i-run
```

---

## 🐳 Docker

Use services via Docker Compose.

### ▶️ Run

```shell
just d-run
```

### 🚮 Purge

Purge all data related to services:

```shell
just d-purge
```
