# Agentflow Productivity Assistant

![License](https://img.shields.io/badge/license-Apache%202.0-blue) ![Language](https://img.shields.io/badge/language-Python-informational) ![Docker](https://img.shields.io/badge/docker-ready-2496ed)


## 📌 Overview

AgentFlow — A multi-agent AI productivity assistant built with Google ADK and MCP. Coordinates sub-agents to manage tasks, schedules, and notes. Deployed on Google Cloud Run.

## 🏗️ Architecture

```text
Browser / UI
     │   HTTP
     ▼
FastAPI app
     │
     ├──▶ Database — PostgreSQL
     └──▶ External services — Google Gemini
```

## 🧰 Tech Stack

- **Language:** Python
- **Backend:** FastAPI
- **Database:** PostgreSQL
- **Integrations:** Google Gemini
- **Deployment:** Docker container

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Docker (optional, for container runs)

### 1. Clone

```bash
git clone https://github.com/SabarishR08/agentflow-productivity-assistant.git
cd agentflow-productivity-assistant
```

### 2. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env   # then fill in values
```

Environment variables used: `ENV`, `DATABASE_URL`, `GOOGLE_API_KEY`, `GEMINI_MODEL`, `MCP_TODOIST_URL`, `MCP_TODOIST_TOKEN`, `TODOIST_API_TOKEN`, `MCP_CALENDAR_URL`, `MCP_CALENDAR_TOKEN`, `PORT`.

External services involved: Google Gemini.

### 4. Run

```bash
python main.py
```

### (Alternative) Run with Docker

```bash
docker build -t agentflow-productivity-assistant .
docker run -p 5000:5000 agentflow-productivity-assistant
```


---

![License](https://img.shields.io/badge/license-Apache%202.0-blue) ![Language](https://img.shields.io/badge/language-Python-informational) ![Docker](https://img.shields.io/badge/docker-ready-2496ed)


## 📌 Overview

AgentFlow — A multi-agent AI productivity assistant built with Google ADK and MCP. Coordinates sub-agents to manage tasks, schedules, and notes. Deployed on Google Cloud Run.

## 🏗️ Architecture

```text
Browser / UI
     │   HTTP
     ▼
FastAPI app
     │
     ├──▶ Database — PostgreSQL
     └──▶ External services — Google Gemini
```

## 🧰 Tech Stack

- **Language:** Python
- **Backend:** FastAPI
- **Database:** PostgreSQL
- **Integrations:** Google Gemini
- **Deployment:** Docker container

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Docker (optional, for container runs)

### 1. Clone

```bash
git clone https://github.com/SabarishR08/agentflow-productivity-assistant.git
cd agentflow-productivity-assistant
```

### 2. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env   # then fill in values
```

Environment variables used: `ENV`, `DATABASE_URL`, `GOOGLE_API_KEY`, `GEMINI_MODEL`, `MCP_TODOIST_URL`, `MCP_TODOIST_TOKEN`, `TODOIST_API_TOKEN`, `MCP_CALENDAR_URL`, `MCP_CALENDAR_TOKEN`, `PORT`.

External services involved: Google Gemini.

### 4. Run

```bash
python main.py
```

### (Alternative) Run with Docker

```bash
docker build -t agentflow-productivity-assistant .
docker run -p 5000:5000 agentflow-productivity-assistant
```

## 📁 Project Structure

```text
agentflow-productivity-assistant/
├── Dockerfile
├── README.md
├── agentflow-frontend.html
├── agents/
├── cloudbuild.yaml
├── db/
├── main.py
├── mcp/
├── models/
├── orchestrator/
├── requirements.txt
├── tests/
├── tools/
```

## ☁️ Deployment

Containerized via Dockerfile — deployable to any container platform (Render, Railway, Cloud Run, …).

## 📄 License

[Apache-2.0](LICENSE) — © 2026 Sabarish R.

---

## 📄 License

[Apache-2.0](LICENSE) — © 2026 Sabarish R.
