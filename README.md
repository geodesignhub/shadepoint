![LOGO](images/logos/logo-D-white.jpg)

# Shadepoint
This plugin uses the [Geodesignhub API](https://www.geodesignhub.com/api) to download information about a design and / or diagrams to  analyze it to produce a variety of views around heat and shade impacts at a local level. 

### Adding your project
This plugin can be added to your project in the Administration interface or at the time of Geodesignhub project creation. 

### Details
This plugin provides analytical capability for any diagram and design from Geodesignhub as a one-click integration, we use the API to download all the data. 

## Setup

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) — install via `curl -LsSf https://astral.sh/uv/install.sh | sh`
- PostgreSQL with PostGIS extension
- Redis

### Install dependencies

```bash
uv sync
```

### Environment variables

Copy the sample env file and fill in your values:

```bash
cp .env.sample.txt .env
```

Key variables:

| Variable | Description |
|---|---|
| `DB_ENGINE` | Database engine (e.g. `postgresql`) |
| `DB_USERNAME` | Database user |
| `DB_PASSWORD` | Database password |
| `DB_NAME` | Database name |
| `DB_HOSTNAME` | Database host |
| `DB_PORT` | Database port (default `5432`) |
| `REDIS_URL` | Redis connection URL |
| `maptiler_key` | MapTiler API key |

## Initial Database setup

Create an initial database.

Log in to the database as user `postgres`, from command line:

```bash
psql -U postgres
```

Then create the new database via commands below.

```sql
CREATE DATABASE localclimateresponse;
ALTER DATABASE localclimateresponse SET search_path=public,postgis,contrib;
\connect localclimateresponse;
CREATE SCHEMA postgis;
CREATE EXTENSION postgis SCHEMA postgis;
CREATE USER localclimateresponse;
ALTER ROLE localclimateresponse WITH PASSWORD 'localclimateresponse';
GRANT all privileges ON DATABASE localclimateresponse TO localclimateresponse;
ALTER DATABASE localclimateresponse OWNER TO localclimateresponse;
```

### Run migrations

```bash
uv run flask --app app db upgrade
```

### Seed the database

```bash
uv run flask --app app seed-db
```

### Start the app

```bash
uv run flask --app app run
```

### Start the background worker

```bash
uv run python worker.py
```


### Motivation
The overall objective of this project is to develop a set of tools to focus on heat response at a local scale. This dashboard will be flexible and will be used as a plugin to Geodesignhub and will analyze data provided by Geodesignhub. In addition, it will connect to external data platforms to download layers and data. 

In addition to the metrics, a summary page would be generated for a design that presents a summary analysis of the metrics developed. 

### Shadow Analysis / Heat Response
We focus on heat / shadow and management response.

### Screenshots
Shadows and trees
![shadow-trees](images/shadow-analysis-trees.jpg)

Analysis of generated shadows
![shadow-analysis](images/shadow-analysis.jpg)

## Compatible with NBSAPI

<img src="images/nbsapi-logo.png" alt="nbsapi-logo" style="max-width: 200px;">

This application is fully compatible with NBSAPI, allowing seamless integration and data exchange. For more information, please visit the [NBSAPI website](https://nbsapi.org).
