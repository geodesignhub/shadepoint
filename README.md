# Local Climate Indicators
This plugin uses the [Geodesignhub API](https://www.geodesignhub.com/api) to download information about a design and / or diagrams to  analyze it to produce a variety of views around heat and flood impacts at a local level. 

### Adding your project
This plugin can be added to your project in the Administration interface or at the time of Geodesignhub project creation. 

### Details
This plugin provides analytical capability for any diagram and design from Geodesignhub as a one-click integration, we use the API to download all the data. 

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


### Motivation
The overall objective of this project is to develop a set of tools to focus on heat and flood response at a local scale. This dashboard will be flexible and will be used as a plugin to Geodesignhub and will analyze data provided by Geodesignhub. In addition, it will connect to external data platforms to download layers and data. 

In addition to the metrics, a summary page would be generated for a design that presents a summary analysis of the metrics developed. 

### Shadow Analysis / Heat Response
We focus on heat / shadow response first and then to flooding mitigation response.

### Screenshots
Shadows and trees
![shadow-trees](images/shadow-analysis-trees.jpg)

Analysis of generated shadows
![shadow-analysis](images/shadow-analysis.jpg)

### Local Flood analysis

TBC

## Compatible with NBSAPI

<img src="images/nbsapi-logo.png" alt="nbsapi-logo" style="max-width: 200px;">

This application is fully compatible with NBSAPI, allowing seamless integration and data exchange. For more information, please visit the [NBSAPI website](https://nbsapi.org).