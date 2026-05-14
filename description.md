# Платформа управління парком роботів — RobotOps

Користувачі можуть реєструватися, додавати роботів до флоту, призначати їм місії та відстежувати
статус виконання в реальному часі.

---

## API Gateway (nginx + consul-template)

- Єдина точка входу для клієнтського додатку (SPA на HTML/JS)
- Маршрутизує всі вхідні HTTP-виклики до відповідних мікросервісів (Auth, Robot, Mission)
- Балансує навантаження між двома інстансами Auth Service (round-robin)
- Upstreams формуються **динамічно** через consul-template — nginx не містить жодних hardcoded адрес чи портів. При зміні кількості інстансів або їх адрес конфігурація nginx оновлюється автоматично

---

## Service Discovery — Consul

- Кожен мікросервіс при старті **самостійно реєструється** у Consul з IP, портом та HTTP health check
- При зупинці сервіс **дереєструється** з Consul; якщо сервіс впав — Consul автоматично знімає його з ротації після `DeregisterCriticalServiceAfter: 30s`
- Robot Service та Mission Service знаходять Auth Service через Consul (`discover("auth-service")`) — без hardcoded адрес
- Порти сервісів визначаються виключно у `.env` і передаються до Consul при реєстрації
- **Consul KV** використовується як Config Server: налаштування Hazelcast (members, cluster name, queue name) зберігаються у Consul KV і зчитуються Mission Service при старті

---

## Auth Service (FastAPI + PostgreSQL + Redis)

- Реєстрація (`POST /auth/register`) — зберігає `username`, `email`, bcrypt-хеш пароля у PostgreSQL
- Логін (`POST /auth/login`) — перевіряє пароль, генерує JWT, зберігає токен у Redis з TTL, встановлює **HttpOnly cookie** (`robotops_token`) — токен недоступний через JavaScript
- Логаут (`POST /auth/logout`) — видаляє токен з Redis, очищає cookie; сесія миттєво анулюється на всіх інстансах
- Профіль (`GET /auth/me`) — перевіряє валідність JWT та наявність токена в Redis

**Відмовостійкість:** два інстанси сервісу (`auth-service-1`, `auth-service-2`) за nginx.
Redis — спільне сховище токенів для обох інстансів. Якщо один інстанс падає, другий продовжує
працювати, бо стан сесії зберігається не в пам'яті сервісу, а в Redis.

**Авторизація в інших сервісах:** Robot Service та Mission Service валідують сесію, викликаючи
`GET /auth/me` на Auth Service через Consul. JWT secret зберігається лише в Auth Service —
інші сервіси не мають до нього доступу. Це також означає, що logout миттєво інвалідує сесію
для всіх сервісів, оскільки Redis перевіряється при кожному запиті.

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

**Конфігурація Hazelcast** зчитується з Consul KV при старті сервісу:
- `config/hazelcast/members` — адреси нод кластера
- `config/hazelcast/cluster-name` — назва кластера
- `config/hazelcast/queue-name` — назва черги

**Схема БД:**
```
missions: id (UUID), title, description, robot_id, status, priority, created_by, created_at, started_at, completed_at
```

---

## Hazelcast Cluster (3 ноди)

Три ноди (`hazelcast1`, `hazelcast2`, `hazelcast3`) утворюють кластер `robotops-hz`.
Mission Service підключається як клієнт до всіх трьох нод.
При падінні однієї ноди черга залишається доступною через дві інші.
Налаштування кластера (members, cluster name, queue name) зберігаються у Consul KV і
заповнюються автоматично при першому запуску через `consul-seed` контейнер.

---

## Усі сервіси — 3-рівневі

```
api/routes.py       ← API layer     (HTTP endpoints, валідація вхідних даних)
service/*.py        ← Service layer (бізнес-логіка, оркестрація)
repository/*.py     ← Repository layer (робота з БД, абстракція доступу до даних)
```

---

## Спільний модуль — common/

```
common/consul_client.py  ← register, deregister, discover, kv_get, kv_put
```

Єдина реалізація Consul-інтеграції, що імпортується всіма сервісами через спільний
build context Docker. Жоден сервіс не дублює логіку реєстрації чи discovery.

---

## Схема взаємодії мікросервісів та баз даних

```
                    Клієнтський додаток (SPA)
                             │ HTTP + HttpOnly Cookie
                             ▼
                        API Gateway (nginx :80)
                     consul-template динамічно
                     оновлює upstreams з Consul
                    ┌────────┼────────┐
                    │        │        │
              HTTP  │  HTTP  │  HTTP  │
           /auth/*  │ /robots│/missions
                    ▼        ▼        ▼
               Auth Svc  Robot Svc  Mission Svc
              (×2 HA)       │            │
                │    │      │ validates  │ validates
                │    │      └──/auth/me──┘
                │    │      (via Consul discover)
                │    │                  │
          PostgreSQL Redis  MongoDB     ├── PostgreSQL (missions)
           (users) (JWT) Replica Set    └── Hazelcast Queue
                          (3 ноди)            │
                                         MissionProcessor
                                         (async consumer)

                        ┌─────────────────────┐
                        │       Consul        │
                        │  Service Registry   │
                        │  Health Checking    │
                        │  KV Config Store    │
                        └─────────────────────┘
```

---

## Технологічний стек

| Компонент           | Технологія                                      |
|---------------------|-------------------------------------------------|
| API Framework       | Python 3.11, FastAPI 0.115                      |
| Auth DB             | PostgreSQL 15 + SQLAlchemy async                |
| Session Store       | Redis 7 (JWT токени з TTL, HttpOnly cookie)     |
| Robot DB            | MongoDB 6 Replica Set (Motor)                   |
| Mission DB          | PostgreSQL 15 + SQLAlchemy async                |
| Message Queue       | Hazelcast 5.3 Distributed Queue                 |
| Service Discovery   | Consul 1.18 (Registry + Health + KV Config)     |
| API Gateway         | nginx + consul-template (dynamic upstreams)     |
| Frontend            | HTML/JS SPA + Bootstrap 5                       |
| Контейнеризація     | Docker + Docker Compose                         |