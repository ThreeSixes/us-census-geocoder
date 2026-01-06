#!/usr/bin/env python
"""Search US census data for addresses using a CSV file.
Expected rows where street and ID are required.

Input CSV format example:
"address"
"555 Fake ave, 5, Placeville, IL"
"555 Bad ave, 5, Placeville, IL"

Output CSV format exmaple:
address,resolved_address,latitude,longitude,result
"555 Fake ave, 5, Placeville, IL","555 FAKE AVE, 5, PLACEVILLE, IL, 55555",0.0000000000,0.0000000000,Success
"555 Bad ave, 5, Placeville, IL",,,,Error: Address not found.
"""

from pprint import pprint
import ast
import csv

import requests


class AddressNotFound(BaseException):
    """The address could not be found."""


class AddressAmbiguous(BaseException):
    """More than one geocoded location was returned."""


class CensusDogGovAPIError(BaseException):
    """An API error besides 404 was reuturned."""


class GeogrpahyNotFound(BaseException):
    """The geogrpahy for the given address could not be found."""


class USCensusGeocoder:
    """Use the US Census Bureau's geocoding API.
    """

    def __init__(self,
                 base_url:str="https://geocoding.geo.census.gov/geocoder",
                 benchmark:str="Public_AR_Census2020", vintage:str="2020",
                 request_timeout:float=30.0
        ):
        """Use the US Census Bureau's geocoding API.

        Args:
            base_url (str, optional): census.gov API base URL. Defaults to 
                "https://geocoding.geo.census.gov/geocoder".
            benchmark (str, optional): _description_. Defaults to "Public_AR_Census2020".
            request_timeout (float, optional): _description_. Defaults to 30.0.
        """
        self.__base_url = base_url
        self.__benchmark = benchmark
        self.__request_timeout = request_timeout
        self.__vintage = vintage


    def __processing_pipeline(self, rows:csv.DictReader) -> tuple[list[str],list[dict]]:
        """Process addresses into a CSV file.

        Args:
            rows (csv.DictReader): DictReader object from the opened CSV file.

        Returns:
            tuple[list[str],list[dict]]: Column headers and a dictionary containing row contents.
        """

        # Set output order.
        output_csv_header = [
            'address',
            'resolved_address',
            'census_tract',
            'census_block_group',
            'census_block',
            'latitude',
            'longitude',
            'result'
        ]

        csv_records:list[dict] = []

        # Assume some sort of error unless we get a different one or succeed.
        result_string = "Error: unknown"

        # Iterate over each CSV row.
        for row in rows:
            # Look for the 'address' column in the sheet.
            if 'address' in row:
                raw_address = row['address']

                print(f"Processing address: {raw_address}")                

                this_entry = {
                    'address': raw_address,
                    'census_block': '',
                    'census_block_group': '',
                    'census_tract': '',
                    'latitude': '',
                    'longitude': '',
                    'resolved_address': '',
                    'result': result_string
                }

                try:
                    # Get the address and process fields we want in the results.
                    address_response = self.find_address(raw_address)
                    address_processed = self.__process_address_api_result(address_response)
                    this_entry.update(address_processed)

                    # Split the address up for the geographies API call.
                    resolved_address_parts = this_entry['resolved_address'].split(", ")
                    street_part = ", ".join(resolved_address_parts[:-3])
                    city_state_zip = resolved_address_parts[-3:]

                    # Get the geographies data for the adddress.
                    geographies_response = self.find_geographies(street_part, city_state_zip[0],
                                                             city_state_zip[1])
                    geograhpies_prcessed = \
                        self.__process_geographies_api_result(geographies_response)
                    this_entry.update(geograhpies_prcessed)

                    # Flag a successful run.
                    result_string = "Success"


                except AddressAmbiguous as e:
                    print(f"Error geocoding address: {str(e)}: {raw_address}")
                    result_string = "Error: The address is ambiguous."

                except AddressNotFound as e:
                    print(f"Address not found: {str(e)}: {raw_address}")
                    result_string = "Error: Address not found."

                except CensusDogGovAPIError as e:
                    print(f"{str(e)} for address {raw_address}")
                    result_string = str(e)

                except GeographyAmbiguous as e:
                    print(f"Error getting geopgraphy: {str(e)}: {raw_address}")
                    result_string = "Error: The geography is ambiguous."

                except GeogrpahyNotFound as e:
                    print(f"Error getting geopgraphy: {str(e)}: {raw_address}")
                    result_string = "Error: Geography not found."

                # Update the success flag for this row.
                this_entry.update({'result': result_string})

                # Add the row to the final output.
                csv_records.append(this_entry)

        return (output_csv_header, csv_records)


    def __process_address_api_result(self, api_result:dict) -> dict:
        """Get interesting address fields from the API response.

        Args:
            api_result (dict): API results as dictionary.

        Returns:
            dict: Interesting fields and their values.
        """

        processed_api_result = {
            'resolved_address': None,
            'latitude': None,
            'longitude': None
        }

        # Set lat and lon
        if 'coordinates' in api_result:
            processed_api_result['latitude'] = api_result['coordinates']['y']
            processed_api_result['longitude'] = api_result['coordinates']['x']

        # Set the address matched by the TIGER API.
        if 'matchedAddress' in api_result:
            processed_api_result['resolved_address'] = api_result['matchedAddress']

        return processed_api_result


    def __process_geographies_api_result(self, api_result:dict) -> dict:
        """Process interesting fields from the geographies API.

        Args:
            api_result (dict): Results for the geographies API as a dictionary.

        Raises:
            GeogrpahyNotFound: The geography couldn't be found given the inputted address.

        Returns:
            dict: Census block, block group, and tract data.
        """

        result:dict = {}

        if 'geographies' in api_result:
            if 'Census Blocks' in api_result['geographies']:
                blocks = api_result['geographies']['Census Blocks']

                if len(blocks) >= 1:
                    result.update({
                        'census_block': ast.literal_eval(blocks[0]['BLOCK'].lstrip('0')),
                        'census_block_group': ast.literal_eval(blocks[0]['BLKGRP'].lstrip('0')),
                        'census_tract': ast.literal_eval(blocks[0]['TRACT'].lstrip('0'))
                    })
            else:
                raise GeogrpahyNotFound("No geographies found for address")
        else:
            raise GeogrpahyNotFound("No geographies found for address")

        return result


    def find_address(self, address:str) -> dict:
        """Gelolocate address.

        Args:
            address (str): One line address as string.

        Raises:
            AddressAmbiguous: The query returned more than one matching address.
            AddressNotFound: The requested address was not found.
            CensusDogGovAPIError: An error occured when querying the census.gov API.

        Returns:
            dict: census.gov API response as dictionary.
        """

        result:dict = {}

        url = f"{self.__base_url}/locations/onelineaddress?benchmark={self.__benchmark}" \
            f"&format=json&address={address}"

        # Make the GET request
        response = requests.get(url, timeout=self.__request_timeout)

        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            json_response = response.json()

            if 'result' in json_response:
                result_data = json_response['result']

                if 'addressMatches' in result_data:
                    matches = result_data['addressMatches']

                    if len(matches) == 1:
                        result = matches[0]

                    elif len(matches) > 1:
                        raise AddressAmbiguous("More than one geocoded location was returned " \
                            "for address")

                    elif len(matches) == 0:
                        raise AddressNotFound("No geocoded location was returned for address")

                else:
                    raise AddressNotFound("No geocoded location was returned for address")

        elif response.status_code == 404:
            raise AddressNotFound("No geocoded location was returned for address")

        else:
            raise CensusDogGovAPIError(f"API request failed geocoding address: " \
                f"{response.status_code}/'{response.text}'")

        return result


    def find_geographies(self, street:str, city:str, state:str,
                         layers:list[int]|None=[10]) -> dict:
        """Get geography data related to an address including census tracks.

        Args:
            street (str): Street component of the address to get geographies for.
            city (str): City component of the address to get geographies for.
            state (str): State component of the address to get geographies for.
            layers (list[int] | None, optional): Census data layers to add. Defaults to [10].

        Raises:
            GeogrpahyNotFound: The geography for the address wasn't found.
            CensusDogGovAPIError: An error occurred calling the census.gov API.

        Returns:
            dict: Geogprhaies related to the specified address.
        """
        result:dict = {}

        layers_template = ""

        # If we have layers add them.
        if layers:
            layers_str:list[str] = []

            for layer in layers:
                layers_str.append(str(layer))

            layers_template = f"&layers={','.join(layers_str)}"

        url = f"{self.__base_url}/geographies/address?benchmark={self.__benchmark}" \
            f"&vintage={self.__vintage}{layers_template}&format=json&street={street}" \
            f"&city={city}&state={state}"

        # Make the GET request
        response = requests.get(url, timeout=self.__request_timeout)

        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            json_response = response.json()

            if 'result' in json_response:
                result_data = json_response['result']

                if 'addressMatches' in result_data:
                    matches = result_data['addressMatches']

                    # If we have at least one match...
                    if len(matches) >= 1:
                        # Use the first result.
                        result = matches[0]

                    elif len(matches) == 0:
                        raise GeogrpahyNotFound("No geocoded location was returned for address")

                    # Print a warning for multiple matches.
                    if len(matches) > 1:
                        print("WARNING: More than one geography returned. Using the first one " \
                            "in the list.")
                else:
                    raise GeogrpahyNotFound("No geocoded location was returned for address")

        elif response.status_code == 404:
            raise GeogrpahyNotFound("No geocoded location was returned for address")

        else:
            raise CensusDogGovAPIError(f"API request failed getting geography: " \
                f"{response.status_code}/'{response.text}'")

        return result


    def geocode_from_csv(self, file_name:str):
        """Geocode addresses from a CSV file.

        Args:
            file_name (str): Name of the file.
        """

        results_file = file_name.replace('.csv', '-geocoded.csv')
        results_header:list[str] = []

        results:list[dict] = []

        print(f"Loading CSV file: {file_name}")

        # Open the incoming CSV file.
        with open(file_name, newline='', encoding='utf8') as csvfile:
            reader = csv.DictReader(csvfile)

            # Get header and results.
            results_header, results = self.__processing_pipeline(reader)

        # Open the results CSV file.
        with open(results_file, 'w', newline='', encoding='utf8') as csvfile:
            # Create a DictWriter object
            writer = csv.DictWriter(csvfile, fieldnames=results_header)

            # Write the header row
            writer.writeheader()

            # Write the data rows
            writer.writerows(results)

        print(f"Results written to: {results_file}")


# If we were executed as a standalone script.
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        prog='geocode.py',
        description='Geocode addresses in the "address" field of a CSV file.',
        epilog='See https://geocoding.geo.census.gov/geocoder/Geocoding_Services_API.pdf ' \
            'for more details.'
    )

    parser.add_argument('csvfile', help="Name of the CSV file to geocode.")
    parser.add_argument('--benchmark', help='Census benchmark to use.',
                        default='Public_AR_Census2020')
    parser.add_argument('--vintage', help='Census vintage to use.',
                        default='2020')
    args = parser.parse_args()

    geocoder = USCensusGeocoder(benchmark=args.benchmark, vintage=args.vintage)
    geocoder.geocode_from_csv(args.csvfile)
