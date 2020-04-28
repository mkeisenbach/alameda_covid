# Alameda County COVID Dashboard

Python script for data processing COVID-19 data for Alameda County Health Department.

## Requirements
Requires Python 3.6+

Additional libraries:
- pandas
- geopy
- geopandas

## Installation (Linux / MacOS)

1. Ensure python3 and pip3 are installed
2. Download alameda_covid source code
3. Run `bootstrap.sh`

## Installation (Windows - Anaconda)

1. Download alameda_covid source code
2. Install Anaconda (https://anaconda.com)
3. Launch *Anaconda PowerShell Prompt*
4. Run `bootstrap.bat` (Acknowledge all prompts)

## How to run
Call the script with yesterday's datafile and today's datafile
```sh
python covid.py <yesterday_file> <today_file>
```

## Output
- The generated output file `output.txt` is a tab separated file which contains the merged rows from yesterday's file with the new rows from today. 
- Longitude and Latitude are looked up using a concatenation of address, city, state, and zip fields.
