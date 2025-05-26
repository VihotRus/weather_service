# weather_service

## steps for local development

`pip install -r dev_requirements.txt`

`pre-commit install`

# 🌤️ Weather API Service

This is a simple and efficient weather API built using **FastAPI**. It allows clients to fetch the current weather for a specified city, with built-in caching support to reduce redundant external API calls.

---

## 🚀 Why FastAPI?

FastAPI was chosen for this project due to its excellent performance and developer-friendly design:

- **Blazing Fast** – One of the fastest Python web frameworks available (based on Starlette and Pydantic).
- **Easy to Use** – Automatic request validation, data parsing, and interactive API documentation.
- **Type-Safe** – Built around Python type hints for safer, cleaner code.
- **Asynchronous Support** – Fully async-capable for efficient I/O operations.

---

## 🧠 Caching Logic

This service uses `fastapi-cache2` with an **in-memory cache backend**:

- 🗃 **InMemoryBackend** is ideal for simple/local setups.
- 🔁 **Easily replaceable** with Redis for scalable, persistent caching.

---

## 📡 `/weather` Endpoint

**Endpoint**: `/weather`  
**Method**: `POST`  
**Content-Type**: `application/json`

### 🔧 Request Body

```json
{
  "city": "Kyiv",
  "cache_ttl": 1800,        // optional, in seconds
  "cache_bypass": false     // optional
}
```

### 📥 Supported Headers

| Header            | Type | Description                                 |
|-------------------|------|---------------------------------------------|
| `X-Cache-TTL`     | int  | Optional. Cache expiration time in seconds. |
| `X-Cache-Bypass`  | bool | Optional. Bypass cache if set to true.      |

#### 🧭 Prioritization

- `X-Cache-TTL` (header) **overrides** `cache_ttl` (JSON).
- `X-Cache-Bypass` (header) **overrides** `cache_bypass` (JSON).
- If neither TTL is provided, default cache expiration is **60 minutes**.
- Maximum cache TTL is a month.

#### 🔤 Bypass Header Values

Accepted values for `X-Cache-Bypass` (case-insensitive):

- **True**: `"1"`, `"true"`, `"yes"`, `"on"`
- **False**: `"0"`, `"false"`, `"no"`, `"off"`

#### 🧾 Response Headers

The response includes additional headers to inform clients about cache behavior:

- **`X-Cache-Status`**: Indicates whether the response was served from cache.  
  Possible values:  
  - `HIT` – The data was served from cache.  
  - `MISS` – Fresh data was fetched and stored in cache.

- **`X-Cache-TTL`**: Shows the current cache Time-To-Live (in seconds) for the returned data.

These headers help clients understand whether caching was used and how long the cached data remains valid.


---

## 🧑‍💻 Local Development

### 📦 Installation

1. Clone the repository and navigate to the project directory.
2. Create and activate a virtual environment (optional but recommended).
3. Install the development dependencies:

```bash
pip install -r requirements.txt
```

```bash
pip install -r dev_requirements.txt
```

```bash
pre-commit install
```

### 🚀 Running the App

Use `uvicorn` to run the app in development mode with auto-reload:

```bash
uvicorn main:app --reload
```

### 🐳 Docker

This service can also be containerized with Docker for consistent deployments.

Build the Docker image:

```bash
docker build -t weather-proxy-with-cache .
```

Run the container:

```bash
docker run -d --name weather-api -p 8000:8000 weather-proxy-with-cache
```

Using Docker Compose:
```bash
docker-compose up --build -d
```

The API will be available at http://localhost:8000.
