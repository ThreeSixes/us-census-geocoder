# US Census Geocoder

## Background

This project is a CLI application designed to take a CSV file any column named `address` and to create a second `.csv` file with those address fields deocoded using the [US Census Bureau](https://www.census.gov/) address geocoding and geographies [APIs](https://www.census.gov/data/developers/data-sets.html). For Python devs, etc. you may also import this as a class in your own project by importing `*` from the `geocode.py` file.

The default configuration of the application uses the 2020 US census data. This may be changed or overridden using command line options.

## Setup

### Prereqisites

The following must be installed for the installation process and application to work.

* Python 3.13 (Might work with a newer version as well)
* [Pyenv](https://github.com/pyenv/pyenv) installed.
* [Pipenv](https://pipenv.pypa.io/en/latest/installation.html) installed.

### Initial installation (MacOS, Linux, _maybe_ Windows?)

1) Change directories into the location where this project is cloned or saved.
2) Run `pipenv install`.

## Using the application

The application is a command line utility that takes two optional parameters and a mandatory CSV file as arguments to geocode addresses. A description is available by running the script with `--help` as an argument.

Useage:

```text
usage: geocode.py [-h] [--benchmark BENCHMARK] [--vintage VINTAGE] csvfile

Geocode addresses in the "address" field of a CSV file.

positional arguments:
  csvfile               Name of the CSV file to geocode.

options:
  -h, --help            show this help message and exit
  --benchmark BENCHMARK
                        Census benchmark to use.
  --vintage VINTAGE     Census vintage to use.

See https://geocoding.geo.census.gov/geocoder/Geocoding_Services_API.pdf for more details.
```

Example usage with a file called `interesting-addresses.csv` that contains one column called `address`.

```shell
pipenv run ./geocode.py interesting-addresses.csv
```

The script will output a file called `interesting-adddresses-geocoded.csv`. It will contain the following columns:

* `address`: The original address from the input of the spreadsheet. Example `175 5th Ave, New York, NY`
* `resolved_address`: The address recognized by the address geocoding API. Example: `175 5TH AVE, NEW YORK, NY, 10010`
* `census_tract`: The census tract from the geographies API. Example: `5600`
* `census_block_group`: The census block group from the geographies API. Example: `2`
* `census_block`: The census block from the geographies API. Example: `2002`
* `latitude`: The latitude of the address returned by the address geocoding API. Example: `40.74101396005`
* `longitude`: The longitude of the address returned by the address geocoding API. Example: `-73.989882415116`
* `result`: A message indicating whether or not the retrieval of the geocoding or geographies data was successful. Example: `Success`

If any of those columns contain empty values that information could not be retrieved and the `result` column should tell you why.

### Example input and output

The input file `notable-buildings.csv` contains:

```csv
name,address
"Flatiron building","175 5th Ave, New York, NY"
"Empire state building","20 W 34th St., New York, NY"
"Ghostbusters HQ","14 N Moore St, New York, NY"
```

The command run to process the `notable-buildings.csv` file:

```shell
pipenv run ./geocoder.py
```

Exmple shell output:

```text
$ pipenv run ./geocode.py notable-buildings.csv
Loading CSV file: notable-buildings.csv
Processing address: 175 5th Ave, New York, NY
Processing address: 20 W 34th St., New York, NY
Processing address: 14 N Moore St, New York, NY
Results written to: notable-buildings-geocoded.csv
```

The output generated in `notable-buildings-geocoded.csv`:

```csv
address,resolved_address,census_tract,census_block_group,census_block,latitude,longitude,result
"175 5th Ave, New York, NY","175 5TH AVE, NEW YORK, NY, 10010",5600,2,2002,40.74101396005,-73.989882415116,Success
"20 W 34th St., New York, NY","20 W 34TH ST, NEW YORK, NY, 10118",7600,1,1001,40.748653379015,-73.985242583802,Success
"14 N Moore St, New York, NY","14 N MOORE ST, NEW YORK, NY, 10013",3300,2,2013,40.719749553446,-74.007085029146,Success
```

## Known issues and limitations

* This may not work for addresses outside the 50 states - specifically addresses that have urbanizations. That hasn't yet been tested.
* The application has only been tested on MacOS, but should work on Linux and Windows assuming the prerequisites are already set up.
