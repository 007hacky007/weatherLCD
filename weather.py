#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2014-17 Richard Hull and contributors
# See LICENSE.rst for details.
# PYTHON_ARGCOMPLETE_OK

from __future__ import unicode_literals

import json
import re
import time
from datetime import datetime, timedelta
from pprint import pprint
from RPLCD.i2c import CharLCD
import requests
import unidecode
import os

insideWeather = ''
outsideWeather = ['', '']
forecast = ''


def loop_string(string, lcd, framebuffer, row, num_cols, delay=0.1):
    padding = ' ' * (num_cols / 4)
    s = padding + string + padding
    for i in range(len(s) - num_cols):
        framebuffer[row] = s[i:i + num_cols]
        write_to_lcd(lcd, framebuffer, num_cols)
        time.sleep(delay)


def write_to_lcd(lcd, framebuffer, num_cols):
    """Write the framebuffer out to the specified LCD."""
    lcd.home()
    for row in framebuffer:
        lcd.write_string(row.ljust(num_cols)[:num_cols])
        lcd.write_string("\r\n")


def get_forecast():
    global forecast
    try:
        result = ''
        response = requests.get(
            "http://api.openweathermap.org/data/2.5/forecast?id=" +
            os.environ['WEATHER_ID'] +
            "&appid=" +
            os.environ['WEATHER_APPID'] +
            "&units" +
            "=metric&lang=cz",
            timeout=20)
        data = json.loads(response.text)
        dictionary = {'Mon': 'Po', 'Tue': 'Ut', 'Wed': 'St', 'Thu': 'Ct', 'Fri': 'Pa', 'Sat': 'So', 'Sun': 'Ne'}
        for delta_day in range(1, 3):
            date = (datetime.today() + timedelta(days=delta_day)).strftime("%Y-%m-%d")
            pattern = re.compile("^" + date + ".*$")
            temp = -99
            for item in data['list']:
                if pattern.match(item['dt_txt']) and item['main']['temp_max'] > temp:
                    temp = item['main']['temp_max']

            if temp == -99:
                result = result + dictionary[
                    (datetime.today() + timedelta(days=delta_day)).strftime("%a")] + ": N/A "
            else:
                result = result + dictionary[
                    (datetime.today() + timedelta(days=delta_day)).strftime("%a")] + ": " + str(
                    round(temp)) + "\x00C "

        forecast = result
    except Exception as e:
        print(e)
        result = "\x03" + forecast

    return result


def get_indoor_temp():
    global insideWeather
    try:
        r = requests.get('http://127.0.0.1:8080/get', timeout=20)
        temp_indoor = r.text.split(":")
        line = insideWeather = 'IN: ' + temp_indoor[0] + "\x00C " + temp_indoor[1] + "%"
    except Exception as e:
        print(e)
        line = "\x03" + insideWeather
    return line.ljust(20)


def get_current_weather():
    global outsideWeather
    try:
        response = requests.get(
            "http://api.openweathermap.org/data/2.5/weather?id=" +
            os.environ['WEATHER_ID'] +
            "&appid=" +
            os.environ['WEATHER_APPID'] +
            "&units" +
            "=metric&lang=cz",
            timeout=20)
        weather = json.loads(response.text)
        outsideWeather[0] = 'OUT: ' + str(round(float(weather['main']['temp']), 1)) + "\x00C (" + str(
            round(float(weather['main']['feels_like']), 1)) + "\x00C)"
        second_line = (unidecode.unidecode(weather['weather'][0]['description']) +
                       " \x01\x02" +
                       time.strftime("%H:%M", time.localtime(int(weather['sys']['sunset']))))
        outsideWeather[1] = second_line
        return [outsideWeather[0], outsideWeather[1]]
    except Exception as e:
        print(e)
        return [outsideWeather[0], "\x03 " + outsideWeather[1]]


def main():
    try:
        if os.environ['WEATHER_ID'] == "" or os.environ['WEATHER_APPID'] == "":
            print("Please set 'WEATHER_ID' and 'WEATHER_APPID' ENV variables")

    except KeyError as e:
        print("ENV variable", e, "is not set")

    forecast_line = get_forecast()
    forecast_cache = time.time() + 60 * 60 * 2
    weather = get_current_weather()
    weather_cache = time.time() + 60 * 15
    while True:
        if time.time() > forecast_cache:
            forecast_line = get_forecast()
        if time.time() > weather_cache:
            weather = get_current_weather()
        framebuffer = [
            get_indoor_temp(),
            weather[0],
            weather[1],
            forecast_line,
        ]
        pprint(framebuffer)
        write_to_lcd(device2, framebuffer, 20)
        time.sleep(120)
        # t_end = time.time() + 60 * 2


#      while time.time() < t_end:
#    	loop_string(forecast, device2, framebuffer, 3, 20)


if __name__ == "__main__":
    try:
        device2 = CharLCD('PCF8574', 0x3f, auto_linebreaks=False, rows=4, cols=20)
        degree = (
            0b00000,
            0b00110,
            0b00110,
            0b00000,
            0b00000,
            0b00000,
            0b00000,
            0b00000,
        )
        sunL = (
            0b01001,
            0b00100,
            0b00001,
            0b11011,
            0b00011,
            0b00001,
            0b01000,
            0b10001,
        )
        sunR = (
            0b01001,
            0b00010,
            0b10000,
            0b11000,
            0b11011,
            0b10000,
            0b00010,
            0b01001,
        )
        plug = (
            0b01010,
            0b01010,
            0b01010,
            0b11111,
            0b11111,
            0b01110,
            0b01110,
            0b00100,
        )
        device2.create_char(0, degree)
        device2.create_char(1, sunL)
        device2.create_char(2, sunR)
        device2.create_char(3, plug)
        main()
    except KeyboardInterrupt:
        pass
