# Homework 9

---

## 🏠 Homework

Homework related actions.

### ▶️ Run

Make all actions needed for run homework from zero. Including configuration.

```shell
just homework-i-docker-i-run
```

### 🚮 Purge

Make all actions needed for run homework from zero.

```shell
just homework-i-docker-i-purge
```

---

## 🛠️ Development

### Install just

You must have [just] installed on your system for run different commands.

If you don't have [just] installed, you can find commands for installation here:

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

---

## 🐳 Docker

Use services in dockers.

### ▶️ Run

Just run

```shell
just d-run
```

### 🚮 Purge

Purge all data related to services

```shell
just d-purge
```
