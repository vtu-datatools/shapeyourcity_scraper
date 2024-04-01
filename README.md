# ShapeYourCity Webscraper

To make the data easier to analyze, this webscraper uses selenium to pull down data on development and rezoning permits and any community engagement data available. It stores copies of each html page under data/pages and the parsed data under data/shapeyourcity.ACCESS_DATE.jsonl.

## Getting Started

Using python 3.12 (you may need to make some minor adjustments to the poetry file to use other version of python) poetry, setup and install is simple

```bash
poetry install
```

To collect/parse data, simply run the data collection script

```bash
poetry run python src/shapeyourcity/get_data.py
```

The current processing script makes a plot of the approval status of each application but it is intended for users to do their own analysis so this is simply an exaple script

```bash
poetry run python src/shapeyourcity/process_data.py
```
