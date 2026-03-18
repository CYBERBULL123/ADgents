# Deployment & PyPI Packaging

ADgents is designed to easily be self-hosted, scalable, and fully distributable.

---

## 🐳 Docker Deployment

The fastest way to deploy the ADgents platform inside cloud services (like AWS, GCP, Heroku, or unRAID) is using our pre-built official Docker configurations.

We included a multi-stage `Dockerfile` and a 1-click `docker-compose.yml`.

### Quick Start
To launch the API layer, database dependencies, and the Studio Web-App seamlessly onto your machine, simply run:

```bash
docker compose up -d
```
All persistent memory, agent states, logs, and configuration values are securely mapped to local `/data` and `/.env` mounts.

### Manual Configuration
If you prefer running standalone, you can build and expose it directly:
```bash
docker build -t adgents_server .
docker run -p 8000:8000 --env-file .env adgents_server
```

---

## 📦 PyPI (Pip) Packaging

You can effortlessly compile, distribute, or import ADgents core functions inside other massive monolith backends by turning it into a Python package via PyPI.

This project uses `pyproject.toml` and `MANIFEST.in` out-of-the-box.

### 1. Build the Binary Wheel
From the project root:
```bash
python -m pip install build twine

python -m build
```
This automatically compiles the dependencies and produces `.whl` and `.tar.gz` artifacts inside `dist/`.

### 2. Install Your Built Package Locally
If you want to use the framework structure outside of the source code directory, you can install the exact `.whl` file you compiled:
```bash
python -m pip install dist/adgents-1.0.0-py3-none-any.whl
```

### 3. Uploading to PyPI.org
To publish your build so others can `pip install adgents`:

```bash
twine upload dist/*
```
*(Requires a free account and API Token at [pypi.org](https://pypi.org/)).*
