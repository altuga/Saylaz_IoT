import datetime
import json
import logging
import os.path
import time
import serial
import requests
import traceback
from serial.serialutil import SerialException
from subprocess import PIPE, Popen
from logging.handlers import TimedRotatingFileHandler
from threading import Thread

# create logger with 'spam_application'
logger = logging.getLogger('saylaz_application')
logger.setLevel(logging.DEBUG)
# create file handler which logs even debug messages
# fh = logging.FileHandler('saylaz.log')
fh = logging.handlers.TimedRotatingFileHandler("saylaz.log", when="midnight", interval=1)
fh.setLevel(logging.DEBUG)
fh.suffix = "%Y%m%d"
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(fh)
logger.addHandler(ch)

ip = "http://172.104.227.59"
port = "8080"
raspberry_key = "54e0c173-8253-485e-a9e8-a75bdd23f81b"
rest_url = ip + ":" + port + "/log/save/" + raspberry_key
rest_url_mock = "http://httpbin.org/post"
date_format = "{0:%Y-%m-%d %H:%M:%S}"
cnt_array = []

def get_cpu_temperature():
    """get cpu temperature using vcgencmd"""

    output = ""

    try:
        process = Popen(['vcgencmd', 'measure_temp'], stdout=PIPE)
        output, _error = process.communicate()
        output = str(output)
    except Exception:
        logger.error("Exception while reading cpu temp")

    float_temp = 0

    try:
        float_temp = float(output[output.index('=') + 1:output.rindex("'")])
        #logger.info("Temp: " + str(float_temp))
    except ValueError:
        logger.error("Temp value is not float")

    return float_temp


def get_formatted_date():
    return date_format.format(datetime.datetime.now())


def send_data(serial_data,cnt_array):

    url = rest_url

    data = {
        "output": serial_data,
        "time": get_formatted_date(),
        "temp": get_cpu_temperature(),
    }

    data_json = json.dumps(data)
    headers = {'Content-type': 'application/json'}
    # response = requests.post(url, data=data_json, headers=headers)
    response = None

    try:
        response = requests.post(url, data=data_json, headers=headers)
    except requests.exceptions.Timeout:
        logger.error("Timeout exception")
    except requests.exceptions.TooManyRedirects:
        logger.error("Too many redirects")
    except requests.exceptions.RequestException as e:
        logger.error("Request exception")
        logger.error(e)

    if response is None or response.status_code != 200:
        logger.info("Sunucu erisiminde ya da sunucuda bir problem var"+str(response.status_code))
    elif response.status_code == 200:
        logger.info("Api Response: " + response.text)

while True:
    try:
        #os.system('clear')
        lines = 8
        num = 0
        data = []
        begin = 0
        emptyData = 0

        ser = serial.Serial('/dev/ttyS0', 38400)
        ser.flushInput()
        ser.flushOutput()
        ser.timeout = 10

        start_time = time.time()

        #ser.open()

        #logger.info("reading data started")

        while num < lines:
            ser_bytes = ser.readline()
            str_data = str(ser_bytes, "utf-8")
            if str_data =="":
                emptyData = 1
                num += 1
                data.append(str_data)
                #logger.info("Empty data")
            if '[' in str_data:
                data = [str_data]
                num = 0
                #print(str(num) + " : A")
                begin = 1
            else:
                if (str_data not in data) and (begin>0):
                    data.append(str_data)
                    #print(str(num) + " : +")
                    num += 1

        str_data = str(data);

        if emptyData < 1:

            count_serial_pls = str_data[str_data.index('pls=') + 4: str_data.rindex("lamp")]

            count_h20 = str_data[str_data.index('H2O=') + 4: str_data.rindex("bdte")]

            logger.info("Chk: " + str(len(str(data))) + " Pls: " + str(count_serial_pls) + " H2O: " + str(count_h20) + " Time: %s " % (time.time() - start_time))

        else :

            logger.info("Empty Data Send")

        thread1 = Thread(target=send_data, args=(data,cnt_array))
        thread1.daemon = True
        thread1.start()

        ser.close()

        time.sleep(60)

    except SerialException:
        logger.error("Serial Exception: Device Connection Problem")
        time.sleep(10)

    except Exception as e:
        print("Keyboard Interrupt :" + str(e))
        logger.error(e)
        traceback.print_exc()
        break
