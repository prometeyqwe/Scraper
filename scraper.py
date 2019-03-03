# -*- coding: utf-8 -*-

import requests
import sys
from lxml import html
import json
import datetime


class Scraper(object):
    path = "http://www.flybulgarien.dk"

    def __init__(self, depart_iata, arrived_iata, date_depart, date_arrived=None, adults_children=1):
        self.result = None
        self.depart_iata = depart_iata
        self.adults_children = adults_children
        self.date_arrived = date_arrived
        try:
            if arrived_iata in self.get_arrived_iata_codes():
                self.arrived_iata = arrived_iata
            else:
                print("There are no flights.")
                sys.exit()
            flight_dates = self.get_flight_dates()
            if "[{}]".format(date_depart) in flight_dates[0]:
                self.date_depart = ".".join([str.rjust(s, 2, '0') for s in date_depart.split(",")][::-1])

            else:
                print("There are no flights.")
                sys.exit()

            if date_arrived:
                if "[{}]".format(date_arrived) in flight_dates[1]:
                    self.date_arrived = ".".join([str.rjust(s, 2, '0') for s in date_arrived.split(",")][::-1])
                else:
                    print("There are no flights.")
                    sys.exit()

        except requests.exceptions.RequestException as e:
            print e
            sys.exit(1)

    def get_arrived_iata_codes(self):
        request = requests.get(self.path + "/script/getcity/2-" + self.depart_iata)
        return json.loads(request.text)

    def get_flight_dates(self):
        request = requests.post(self.path + "/script/getdates/2-departure", data={"code1": self.depart_iata,
                                                                                  "code2": self.arrived_iata})
        return request.text.split("-")

    def get_flight_duration(self, a, b):
        t1 = a.split(":")
        t2 = b.split(":")

        if t1[0] > '12' > t2[0]:
            t2 = datetime.datetime(1, 1, 2, int(t2[0]), int(t2[1]))
        else:
            t2 = datetime.datetime(1, 1, 1, int(t2[0]), int(t2[1]))

        t1 = datetime.datetime(1, 1, 1, int(t1[0]), int(t1[1]))

        return str(t2 - t1)[:-3]

    def get_response(self):
        """Getting table of flights"""
        try:
            arr_of_params = {"departure-city": self.depart_iata, "arrival-city": self.arrived_iata,
                             "departure-date": self.date_depart, "adults-children": self.adults_children}

            if self.date_arrived:
                arr_of_params["arrival-date"] = str(self.date_arrived)

            first_request = requests.get(self.path + "/en/search", params=arr_of_params)

            response = html.fromstring(first_request.text)
            url = response.xpath("//iframe/@src")[0]
            second_request = requests.get(url)
            response = html.fromstring(second_request.text)

        except requests.exceptions.RequestException as e:
            print e
            sys.exit(1)

        return response

    def print_result(self):
        """Print the result of scpare()"""
        res_arr1 = self.result
        going_out = [i for i in res_arr1 if self.depart_iata in i[3]]
        going_out.sort(key=(lambda x: float(x[5].split(" ")[2].strip())))  # sorting by price increase
        print("Going Out: \n")
        self.get_print(going_out)

        if self.date_arrived:
            coming_back = [i for i in res_arr1 if self.arrived_iata in i[3]]
            coming_back.sort(key=(lambda x: float(x[5].split(" ")[2].strip())))  # sorting by price increase
            print("Coming Back: \n")
            self.get_print(coming_back)

    def get_print(self, res_arr1):
        """Print the list"""
        for i in range(len(res_arr1)):
            print("{0}:".format(res_arr1[i][0]))
            print("\tDeparture: {0}".format(res_arr1[i][1]))
            print("\tArrival: {0}".format(res_arr1[i][2]))
            print("\tFlight duration: {0} hours".format(self.get_flight_duration(res_arr1[i][1], res_arr1[i][2])))
            print("\t{0}".format(res_arr1[i][5]))
            print("\n"),

    def parse_response(self, response):
        try:
            res_table = response.xpath("//table[@id='flywiz_tblQuotes']/tr[count(td)>1]")
        except AttributeError as e:
            print(e)
            sys.exit(1)

        res_arr1 = [[] for _ in range((len(res_table)) // 2)]
        for row in range(len(res_table) + 1):
            for i in response.xpath("//table[@id='flywiz_tblQuotes']/tr[count(td)>1][" + str(row) + "]/td"):
                if i.text_content():
                    res_arr1[(row - 3) // 2].append(i.text_content())

        for i in range(len(res_arr1)):  # recalculation of the amount of tickets for several people
            if self.adults_children > 1:
                res_arr1[i][5] = res_arr1[i][5].split()[0] + "  " + str(
                    float(res_arr1[i][5].split()[1].strip()) * self.adults_children) + " " + res_arr1[i][5].split()[2]

        return res_arr1

    def scrape(self):
        """Main method with scraper methods calls"""
        response = self.get_response()
        self.result = self.parse_response(response)
        print("count: {0}\n".format(len(self.result)))


if __name__ == "__main__":
    s1 = Scraper("BLL", "BOJ", "2019,7,8")
    s1.scrape()
    s1.print_result()
