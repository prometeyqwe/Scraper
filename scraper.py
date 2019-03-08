import json
from itertools import chain
from datetime import datetime, timedelta

import argparse
import requests
from lxml import html


class Scraper(object):
    path = "http://www.flybulgarien.dk"

    def __init__(self, departure_iata, arrival_iata, departure_date, return_date=None, passengers=1):
        self.departure_iata = departure_iata
        self.arrival_iata = arrival_iata
        self.departure_date = departure_date
        self.return_date = return_date
        self.passengers = passengers

    def get_arrived_iata_codes(self):
        response = requests.get(self.path + "/script/getcity/2-" + self.departure_iata)
        return json.loads(response.text)

    def get_flight_dates(self):
        response = requests.post(
            self.path + "/script/getdates/2-departure",
            data={"code1": self.departure_iata, "code2": self.arrival_iata}
        )
        return response.text.split("-")

    @staticmethod
    def get_flight_duration(departure_time, arrival_time):
        departure_time = datetime.strptime(departure_time, "%H:%M")
        arrival_time = datetime.strptime(arrival_time, "%H:%M")
        if departure_time > arrival_time:
            arrival_time += timedelta(days=1)

        return str(arrival_time - departure_time)[:-3]

    def get_response(self):
        """Getting table of flights"""

        arr_of_params = {
            "lang": "2",
            "departure-city": self.departure_iata,
            "arrival-city": self.arrival_iata,
            "departure-date": self.departure_date.strftime("%d.%m.%Y"),
            "adults-children": self.passengers,
            "search": "Search%21",
        }

        if self.return_date:
            arr_of_params["arrival-date"] = self.return_date.strftime("%d.%m.%Y")

        main_response = requests.get(self.path + "/en/search", params=arr_of_params)
        root = html.fromstring(main_response.text)
        # get URL which returns a table with flights data
        url = root.xpath("//iframe/@src")[0]
        response = html.fromstring(requests.get(url).text)
        return response

    def print_result(self, result):
        """Print the result of scrape()"""
        outbound = [i for i in result if self.departure_iata in i[3]]
        outbound.sort(key=(lambda x: float(x[5].split(" ")[2].strip())))  # sorting by price increase
        print("Going Out: ")
        full_price = self.get_print(outbound, 0)
        final_price = full_price[0] if full_price else 0
        currency = full_price[1] if full_price else "EUR"
        if self.return_date:
            inbound = [i for i in result if self.arrival_iata in i[3]]
            inbound.sort(key=(lambda x: float(x[5].split(" ")[2].strip())))  # sorting by price increase
            print("Coming Back: ")
            printed_value = self.get_print(inbound, 1)
            if printed_value:
                final_price += printed_value[0]
        print("Final price: {} {}".format(final_price, currency))

    @staticmethod
    def convert_date(date):
        """convert from "Mon, 15 Jul 19" to datetime: 2019-07-15 00:00:00"""
        return datetime.strptime(date.strip(), '%a, %d %b %y')

    def get_print(self, result, ind):
        """Print the list"""
        flag = self.return_date if ind else self.departure_date
        try:
            flight = next(f for f in result if self.convert_date(f[0]) == flag)
        except StopIteration:
            print 'flight not found'
        else:
            print("{0}:".format(flight[0]))
            print("\tDeparture: {0}".format(flight[1]))
            print("\tArrival: {0}".format(flight[2]))
            print("\tFlight duration: {0} hours".format(self.get_flight_duration(flight[1], flight[2])))
            print("\tCabin class: economy")
            print("\t{0}".format(flight[5]))
            print("\n"),
            return float(flight[5].split()[1]), flight[5].split()[2]

    @staticmethod
    def parse_response(response):
        rows = iter(response.xpath("//table[@id='flywiz_tblQuotes']/tr[count(td)>1]"))
        raw_flights = zip(rows, rows)
        return [
            [
                td.text_content()
                for td in chain(flight_row.xpath('./td'), prices_row.xpath('./td'))
                if td.text_content()
            ] for flight_row, prices_row in raw_flights
        ]

    def validate_input_data(self):
        """Validate user input"""
        current_date = datetime.today()
        if not self.departure_iata.isalpha() or len(self.departure_iata) != 3:
            print("The departure is not correct. Example, LHR")
        elif not self.arrival_iata.isalpha() or len(self.arrival_iata) != 3:
            print("The arrival is not correct. Example, CGN")
        elif self.departure_date < current_date:
            print("The departure date is not correct: less than current date.")
        elif self.return_date and self.return_date < self.departure_date:
            print("The return date is not correct: less than outbound date.")
        else:
            return True
        return False

    def check_flights_possibility(self):
        """Check schedule to confirm that there are flights for given route/date(s)."""
        if self.arrival_iata not in self.get_arrived_iata_codes():
            print("There are no flights on this route.")
            return False

        outbound_dates, inbound_dates = self.get_flight_dates()
        try:
            # unix format
            formatted_departure_date = self.departure_date.strftime("[%Y,%-m,%-d]")
            formatted_return_date = self.return_date.strftime("[%Y,%-m,%-d]") if self.return_date else ""
        except ValueError:
            # Windows format
            formatted_departure_date = self.departure_date.strftime("[%Y,%#m,%#d]")
            formatted_return_date = self.return_date.strftime("[%Y,%#m,%#d]") if self.return_date else ""

        if formatted_departure_date not in outbound_dates:
            print("There are no flights on this departure date.")
        elif formatted_return_date and formatted_return_date not in inbound_dates:
            print("There are no flights on this arrival date.")
        else:
            return True

        return False

    def scrape(self):
        """Main method with scraper methods calls"""
        if self.validate_input_data() and self.check_flights_possibility():
            response = self.get_response()
            result = self.parse_response(response)
            if result:
                self.print_result(result)


def parse_user_arguments():
    """Parse user search arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument("departure", help="Departure airport IATA code")
    parser.add_argument("arrival", help="Arrival airport IATA code")
    parser.add_argument("departure_date", type=lambda s: datetime.strptime(s, '%Y-%m-%d'),
                        help="Departure date. Correct date format: %Y-%m-%d")
    parser.add_argument("return_date", nargs="?", default="", type=lambda s: check_return_date(s),
                        help="Return date. Correct date format: %Y-%m-%d")

    return parser.parse_args()


def check_return_date(return_date):
    if return_date:
        return datetime.strptime(return_date, "%Y-%m-%d")


if __name__ == "__main__":
    args = parse_user_arguments()
    scraper = Scraper(args.departure, args.arrival, args.departure_date, args.return_date)
    scraper.scrape()
