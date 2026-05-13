# Платформа управління парком роботів — RobotOps

Користувачі можуть реєструватися, додавати роботів до флоту, призначати їм місії та відстежувати
статус виконання в реальному часі.

---

## API Gateway (nginx)

- Єдина точка входу для клієнтського додатку (SPA на HTML/JS)
- Маршрутизує всі вхідні HTTP-виклики до відповідних мікросервісів (Auth, Robot, Mission)
- Балансує навантаження між двома інстансами Auth Service (round-robin)

---

## Auth Service (FastAPI + PostgreSQL + Redis)

- Реєстрація (`POST /auth/register`) — зберігає `username`, `email`, bcrypt-хеш пароля у PostgreSQL
- Логін (`POST /auth/login`) — перевіряє пароль, генерує JWT, зберігає токен у Redis з TTL
- Логаут (`POST /auth/logout`) — видаляє токен з Redis, сесія миттєво анулюється
- Профіль (`GET /auth/me`) — перевіряє валідність JWT та наявність токена в Redis

**Відмовостійкість:** два інстанси сервісу (`auth-service-1`, `auth-service-2`) за nginx.
Redis — спільне сховище токенів для обох інстансів. Якщо один інстанс падає, другий продовжує
працювати, бо стан сесії зберігається не в пам'яті сервісу, а в Redis.

**Схема БД:**
```
users: id (UUID), username, email, password_hash, role, created_at
```

---

## Robot Service (FastAPI + MongoDB Replica Set, 3 ноди)

- Реєстрація робота (`POST /robots/`) — назва, тип, модель, capabilities, локація
- Список флоту (`GET /robots/`)
- Деталі робота (`GET /robots/{id}`)
- Оновлення статусу (`PATCH /robots/{id}`) — `online` / `offline` / `busy` / `maintenance`
- Видалення (`DELETE /robots/{id}`)

**MongoDB Replica Set:** 3 ноди (`mongo1` primary з priority=2, `mongo2`, `mongo3` secondary).
Сервіс підключається через URI з усіма нодами: `mongodb://mongo1,mongo2,mongo3/?replicaSet=rs0`.
При втраті кворуму (залишилась 1 нода з 3) запис стає недоступним, читання залишається.

**Приклад документа:**
```json
{
  "_id": "uuid",
  "name": "Wall-E",
  "type": "mobile",
  "model": "WE-2024",
  "status": "online",
  "capabilities": ["navigate", "pick", "place"],
  "location": {"x": 0.0, "y": 0.0, "z": 0.0},
  "assigned_mission_id": null,
  "owner_id": "uuid",
  "created_at": "...",
  "updated_at": "..."
}
```

---

## Mission Service (FastAPI + PostgreSQL + Hazelcast Queue)

- Створити місію (`POST /missions/`) — назва, опис, прив'язка до робота, пріоритет
- Список місій (`GET /missions/`)
- Деталі місії (`GET /missions/{id}`)

**Асинхронна обробка (CQRS + Event Queue):**

Після `POST /missions/` сервіс:
1. Зберігає місію у PostgreSQL зі статусом `queued`
2. Кладе повідомлення в **Hazelcast Distributed Queue** (`mission-queue`)
3. Повертає `202 Accepted` — не чекає завершення обробки

Фоновий `MissionProcessor` (daemon thread з власним event loop):
- Читає повідомлення з черги (Hazelcast Queue consumer)
- Оновлює статус місії: `queued` → `active` → `completed`

Write side (через чергу) відділений від read side (прямий SELECT з PostgreSQL) — реалізація
підходу CQRS.

**Схема БД:**
```
missions: id (UUID), title, description, robot_id, status, priority, created_by, created_at, started_at, completed_at
```

---

## Hazelcast Cluster (3 ноди)

Три ноди (`hazelcast1`, `hazelcast2`, `hazelcast3`) утворюють кластер `robotops-hz`.
Mission Service підключається як клієнт до всіх трьох нод.
При падінні однієї ноди черга залишається доступною через дві інші.

---

## Усі сервіси — 3-рівневі

```
api/routes.py       ← API layer     (HTTP endpoints, валідація вхідних даних)
service/*.py        ← Service layer (бізнес-логіка, оркестрація)
repository/*.py     ← Repository layer (робота з БД, абстракція доступу до даних)
```

---

## Схема взаємодії мікросервісів та баз даних

```
                    Клієнтський додаток (SPA)
                             │ HTTP
                             ▼
                        API Gateway (nginx :80)
                    ┌────────┼────────┐
                    │        │        │
              HTTP  │  HTTP  │  HTTP  │
           /auth/*  │ /robots│/missions
                    ▼        ▼        ▼
               Auth Svc  Robot Svc  Mission Svc
              (×2 HA)                │
                │    │        │      ├── PostgreSQL (missions)
                │    │        │      └── Hazelcast Queue
                │    │        │               │
          PostgreSQL Redis  MongoDB         MissionProcessor
           (users) (JWT) Replica Set     (async consumer)
                          (3 ноди)
```

---

## Технологічний стек

| Компонент         | Технологія                        |
|-------------------|-----------------------------------|
| API Framework     | Python 3.11, FastAPI 0.115        |
| Auth DB           | PostgreSQL 15 + SQLAlchemy async  |
| Session Store     | Redis 7 (JWT токени з TTL)        |
| Robot DB          | MongoDB 6 Replica Set (Motor)     |
| Mission DB        | PostgreSQL 15 + SQLAlchemy async  |
| Message Queue     | Hazelcast 5.3 Distributed Queue   |
| API Gateway       | nginx (load balancer + static)    |
| Frontend          | HTML/JS SPA + Bootstrap 5         |
| Контейнеризація   | Docker + Docker Compose           |
