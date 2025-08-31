# Django Connections & Notifications System

A Django-based social connection system with real-time notifications using Django Channels, Celery, and WebSocket push, with JWT authentication.

---

## Features

### User & Authentication

* User registration (`/api/register/`)
* User login with JWT sliding token (`/api/login/`)
* User profile retrieval & update (`/api/profile/`)
* Token refresh endpoint

### Connections

* Send, accept, and reject connection requests
* View all connections
* Remove existing connections
* Idempotent operations: multiple accepts/rejects handled gracefully
* Ensures atomic DB operations to avoid race conditions

### Notifications

* Real-time notifications for connection requests and responses
* Notifications stored in database
* Mark notifications as read (optional)
* Supports:

  * Actor (user who performed action)
  * Recipient
  * Verb (`accepted/rejected`)
  * Message text
  * Read flag
  * Timestamp

### Search Users

* Search by:

  * Full name
  * Company name
  * Username
  * Email
  * Contact
* Endpoint: `/api/search_users/?q=<query>`

### Real-Time Push

* Uses Django Channels with WebSocket support
* Consumers:

  * `NotificationConsumer` subscribes each user to `user_<user_id>` group
* Frontend receives notifications in real-time without external services

### Background Tasks

* Uses Celery for asynchronous processing
* Connection accept/reject triggers notification creation
* Task:

  * `send_connection_response_notification`

### Security & Permissions

* Endpoints protected with `IsAuthenticated`
* Object-level permission: `IsOwnerOrReadOnly`
* Only recipients can accept/reject connection requests

---

## System Flow Diagram

```
+-----------------+       +----------------+       +------------------+
|  Connection     |       |  Celery        |       |  Notifications   |
|  App / API      |-----> |  Worker Task   |-----> |  Database        |
+-----------------+       +----------------+       +------------------+
        |                                              |
        |                                              |
        |                                              v
        |                                    +------------------+
        |                                    |  Django Channels |
        |                                    |  WebSocket Layer |
        |                                    +------------------+
        |                                              |
        |                                              v
        |                                    +------------------+
        |                                    |  Frontend /      |
        |                                    |  Browser WS      |
        |                                    |  client          |
        |                                    +------------------+
```

Flow Explanation:

1. User accepts/rejects connection → `ConnectionRequestViewSet`.
2. Celery task `send_connection_response_notification` creates notification in DB.
3. Notification is sent via Channels group `user_<user_id>`.
4. Connected frontend receives notification in real-time via WebSocket.

---

## Installation & Setup

1. **Clone repository**

```bash
git clone <your-repo-url>
cd <repo-folder>
```

2. **Create virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Configure environment variables**

```
DJANGO_SECRET_KEY=<your-secret-key>
DJANGO_DEBUG=True
DATABASE_URL=postgres://user:password@localhost:5432/dbname
REDIS_URL=redis://localhost:6379/0
```

5. **Apply migrations**

```bash
python manage.py migrate
```

6. **Create superuser (optional)**

```bash
python manage.py createsuperuser
```

---

## Running the project

### 1. Start Redis

```bash
redis-server
```

### 2. Start Django development server (ASGI)

```bash
python manage.py runserver
```

### 3. Start Celery worker

```bash
celery -A <project_name> worker --loglevel=info
```

---

## API Endpoints

| Endpoint                                | Method          | Description                                        |
| --------------------------------------- | --------------- | -------------------------------------------------- |
| `/api/register/`                        | POST            | Register a new user                                |
| `/api/login/`                           | POST            | User login with JWT token                          |
| `/api/profile/`                         | GET, PUT, PATCH | Get or update user profile                         |
| `/api/token/refresh/`                   | POST            | Refresh JWT sliding token                          |
| `/api/search_users/`                    | GET             | Search users                                       |
| `/api/connection_requests/`             | GET, POST       | List/create connection requests                    |
| `/api/connection_requests/{id}/accept/` | POST            | Accept connection request                          |
| `/api/connection_requests/{id}/reject/` | POST            | Reject connection request                          |
| `/api/connections/`                     | GET             | List all connections                               |
| `/api/connections/{id}/`                | DELETE          | Remove a connection                                |
| `/api/notifications/`                   | GET, POST       | List notifications, create notification (optional) |

---

## WebSocket Endpoint

| Endpoint             | Description                 |
| -------------------- | --------------------------- |
| `/ws/notifications/` | Real-time notification feed |

**Frontend example**:

```js
const token = localStorage.getItem("token");
const ws = new WebSocket(`ws://${window.location.host}/ws/notifications/?token=${token}`);

ws.onmessage = (evt) => {
    const payload = JSON.parse(evt.data);
    console.log("Notification:", payload);
};
```

---

## Celery Task

```python
send_connection_response_notification(recipient_id, actor_id, action, request_id=None)
```

* Triggered automatically on connection accept/reject.
* Creates notification and pushes it via Channels.

---

## Notes

* `CHANNEL_LAYERS` + Redis must be configured.
* Custom `user_id` field is used in Channels group naming.
* Permissions: `IsAuthenticated` + `IsOwnerOrReadOnly`.
* Idempotent operations for accept/reject.
* WebSocket uses JWT token or session cookie for authentication.

---

## Recommended Packages (`requirements.txt`)

```
Django>=5.1
djangorestframework
channels
channels-redis
celery
redis
djangorestframework-simplejwt
python-dotenv
```
