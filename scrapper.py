# -*- coding: utf-8 -*-

import requests
import sys
import lxml.html as lh
import json
import datetime


class Scrapper:
    def __init__(self, path, depart_iata, arrived_iata, date_depart, date_arrived=None):
        self.path = "http://" + path
        self.result = None
        self.depart_iata = depart_iata
        if arrived_iata in self.get_arrived_iata():
            self.arrived_iata = arrived_iata
        else:
            print("По данному направдению самолетов не найдено. Выберите другой пункт назначения.")
            sys.exit()
        if "[" + date_depart + "]" in self.get_date()[0]:
            self.date_depart = ".".join([str.rjust(s, 2, '0') for s in date_depart.split(",")][::-1])

        else:
            print("На данную дату отправления самолетов не найдено. Выберите другую дату.")
            sys.exit()

        if date_arrived:
            if "[" + date_arrived + "]" in self.get_date()[1]:
                # print("date arrived done")
                self.date_arrived = ".".join([str.rjust(s, 2, '0') for s in date_arrived.split(",")][::-1])
            else:
                print("На данную дату возврата самолетов не найдено. Выберите другую дату.")
                sys.exit()
        else:
            self.date_arrived = None

    # надо добавить обработку исключений на методы requests!!!
    # сделать методы get и post

    def get_arrived_iata(self):
        r = requests.get(self.path + "/script/getcity/2-" + self.depart_iata)
        return json.loads(r.text)

    def get_date(self):
        r = requests.post(self.path + "/script/getdates/2-departure", data={"code1": self.depart_iata,
                                                                            "code2": self.arrived_iata})
        return r.text.split("-")

    def get_flight_duration(self, a, b):
        t1 = a.split(":")
        t2 = b.split(":")

        if t1[0] > '12' > t2[0]:
            t1 = datetime.datetime(1, 1, 1, int(t1[0]), int(t1[1]))
            t2 = datetime.datetime(1, 1, 2, int(t2[0]), int(t2[1]))
        else:
            t1 = datetime.datetime(1, 1, 1, int(t1[0]), int(t1[1]))
            t2 = datetime.datetime(1, 1, 1, int(t2[0]), int(t2[1]))
        return str(t2 - t1)[:-3]

    def get_root_of_page(self):
        if not self.date_arrived:

            r = requests.get(self.path + "/en/search?lang=2&departure-city=" + self.depart_iata + "&arrival-city=" +
                             self.arrived_iata + "&reserve-type=&"
                                                 "departure-date=" + self.date_depart + "&adults-children=1&"
                                                                                        "search=Search%21")
        else:
            r = requests.get(self.path + "/en/search?lang=2&departure-city=" + self.depart_iata + "&arrival-city=" +
                             self.arrived_iata + "&reserve-type=&"
                                                 "departure-date=" + self.date_depart + "&arrival-date=" +
                             self.date_arrived + "&adults-children=1&" + "search=Search%21")

        root = lh.fromstring(r.text)
        elt = root.xpath("//iframe")[0]
        url_data = elt.attrib.get("src")
        data = requests.get(url_data)
        root = lh.fromstring(data.text)

        return root

    def print_result(self, arr=None):

        res_arr1 = self.result
        going_out = [i for i in res_arr1 if self.depart_iata in i[3]]
        going_out.sort(key=(lambda x: float(x[5].split(" ")[2].strip())))  # сортирвка по возврастанию цена
        print("Going Out: \n")
        self.get_print(going_out)

        if self.date_arrived:
            coming_back = [i for i in res_arr1 if self.arrived_iata in i[3]]
            coming_back.sort(key=(lambda x: float(x[5].split(" ")[2].strip())))  # сортирвка по возврастанию цена
            print("Coming Back: \n")
            self.get_print(coming_back)

    def get_print(self, res_arr1):
        for i in range(len(res_arr1)):
            print("{0}:".format(res_arr1[i][0]))
            print("\tDeparture: {0}".format(res_arr1[i][1]))
            print("\tArrival: {0}".format(res_arr1[i][2]))
            print("\tFlight duration: {0} hours".format(self.get_flight_duration(res_arr1[i][1], res_arr1[i][2])))
            print("\t{0}".format(res_arr1[i][5]))
            # print(float(res_arr1[i][5].split(" ")[2].strip()))
            print("\n"),

    def parse(self):
        root = self.get_root_of_page()
        res_table = root.xpath("//table[@id='flywiz_tblQuotes']/tr[count(td)>1]")
        # for i in res_table:
        #     print(len(i), i.text_content())

        res_arr1 = [[] for _ in range((len(res_table)) // 2)]
        for row in range(len(res_table) + 1):
            # for column in range(2, len(root.xpath("//table[@id='flywiz_tblQuotes']/tr[" + str(row) + "]/td")) + 1):
            #     if column > 0:
            #         res = root.xpath("//table[@id='flywiz_tblQuotes']/tr[" + str(row) + "]/td[" + str(column) + "]")[0] \
            #             .text_content()
            #         if res != "":
            #             res_arr1[(row - 3) // 2].append(res)
            for i in root.xpath("//table[@id='flywiz_tblQuotes']/tr[count(td)>1][" + str(row) + "]/td"):
                # print(i.text_content())
                if i.text_content():
                    res_arr1[(row - 3) // 2].append(i.text_content())

        self.result = res_arr1
        # for i in res_arr1:
        #     print(i)
        print("count: {0}\n".format(len(res_arr1)))


s1 = Scrapper("www.flybulgarien.dk", "BLL", "BOJ", "2019,7,1", "2019,7,8")
s1.parse()
s1.print_result()
