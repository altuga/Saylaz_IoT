import datetime
import json
import logging
import os.path
import time

import requests
import serial
from serial.serialutil import SerialException

from subprocess import PIPE, Popen

from logging.handlers import TimedRotatingFileHandler

from threading import Thread

debug = False
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

baudrate = 38400
ip = "http://172.104.227.59"
# ip = "http://localhost"
port = "8080"
raspberry_key = "54e0c173-8253-485e-a9e8-a75bdd23f81b"
rest_url = ip + ":" + port + "/log/save/" + raspberry_key
# rest_url = ip + ":" + port + "/log/save"
rest_url_mock = "http://httpbin.org/post"
serial_port = "/dev/ttyUSB0"
date_format = "{0:%Y-%m-%d %H:%M:%S}"
serial_port_timeout_seconds = 10

#script_path = os.path.abspath(os.path.dirname(__file__))
#path = os.path.join(script_path, "serial_read_laser.txt")

read_sleep_time = 10
read_send_check = 6

consistent_data_length = 638


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
        if debug==True:
            logger.info("Temp: " + str(float_temp))
    except ValueError:
        logger.error("Temp value is not float")

    return float_temp


def get_formatted_date():
    return date_format.format(datetime.datetime.now())


def is_serial_data_consistent(serial_data):
    length = 0
    consistent_data_length = 638

    for serial_element in serial_data:
        length = length + len(serial_element)
    if debug==True:
      logger.info("Data Length: " + str(length))

    if length == consistent_data_length:
        # #if 'pls' in str_data:
        #     count_serial_pls = str_data[str_data.index('pls=') + 4: str_data.rindex("lamp")]
        #     logger.info("Cons Check : Date: " + get_formatted_date() + ", pls: " + str(count_serial_pls))
        #     try:
        #         count_serial_pls = int(count_serial_pls)
        #     except ValueError as verr:
        #         logger.error("Cons Check : Pls ValueError Cons Check Failed")
        #         return False
        #     except Exception as ex:
        #         logger.error("Cons Check : Pls Exception Cons Check Failed")
        #         return False
        return True
    else:
        logger.error("Serial data corrupt : " + str(length) + " Target length : " + str(consistent_data_length))
        return False


def send_data(serial_data, cnt_array):
    url = rest_url
    if debug==True:
      logger.info("Sending data begins with :")

    data = {
        "output": serial_data,
        "time": get_formatted_date(),
        "temp": get_cpu_temperature(),
        # "cntArray": cnt_array
    }

    data_json = json.dumps(data)
    headers = {'Content-type': 'application/json'}
    # response = requests.post(url, data=data_json, headers=headers)
    response = None

    try:
        response = requests.post(url, data=data_json, headers=headers)
    except requests.exceptions.Timeout:
        logger.error("Send data : Timeout exception")
    except requests.exceptions.TooManyRedirects:
        logger.error("Send data : Too many redirects")
    except requests.exceptions.RequestException as e:
        logger.error("Send data : Request exception")
        logger.error(e)

    if response is None or response.status_code != 200:
      if debug==True:
        logger.info("Send data : Internet problem")
    elif response.status_code == 200:
      if debug==True:
        logger.info("Api Response: " + response.text)


def write_to_file(serial_data):
    file = open(path, 'a')
    file.write(serial_data + "\n")
    file.close()


def read_serial_every_5_mins():
    ser = serial.Serial()
    ser.baudrate = baudrate
    ser.port = serial_port
    ser.timeout = serial_port_timeout_seconds
    logger.info(ser)

    in_loop = True
    sleep = False
    is_read_data = False

    exception_count = 1
    file_not_found_error_count = 1
    # read_count = 1

    read_send_count = 0
    cnt_array = []
    pls_array = []
    lines = []

    sleep_exception_message = True
    send_empty_data = True
    while in_loop:
        if sleep:
            sleep = False
            if sleep_exception_message:
              if debug==True:
                logger.info("sleeping on exception for 5 seconds")
                sleep_exception_message = False
            time.sleep(5)

        try:
            if not ser.is_open:
                ser.open()

            if read_send_count == read_send_check:
              if debug==True:
                logger.info("reading data started")

            line = ser.readline()
            # line = b'pct and Cnt'
            # read_count_string = str(read_count)
            str_data = str(line).encode("utf-8")

            if str_data == "":
                if send_empty_data:
                  if debug==True:
                    logger.info("Could'nt read any data from serial port")
                is_read_data = False
            else:
                is_read_data = True

            # print(read_count_string + " : " + str_data)
            # read_count = read_count + 1
            # send_data(str_data)
            # write_to_file(read_count_string + "@ " + str_data)

            # seri porttan veri okundu mu okunmadi mi
            if is_read_data:

                # read_send_check = 30
                # read_send_count = 0
                # 10snde bir cnt kontrolu
                if read_send_count < read_send_check:
                    if 'pls' in str_data:
                        count_serial_pls = str_data[str_data.index('pls=') + 4: str_data.rindex("lamp")]
                        if debug==True:
                          logger.info("Date: " + get_formatted_date() + ", pls: " + str(count_serial_pls))
                        try:
                            count_serial_pls = int(count_serial_pls)
                            pls_array.append(count_serial_pls)
                        except ValueError as verr:
                            logger.error("Pls value is not integer - ValueError : Reading serial again ...")
                        except Exception as ex:
                            logger.error("Pls value is not integer - Exception : Reading serial again ...")

                    if 'pct' in str_data and 'Cnt' in str_data:
                        count_serial_cnt = str_data[str_data.index('Cnt=') + 4: str_data.rindex("\r")]
                        if debug==True:
                          logger.info("Cnt: " + str(count_serial_cnt))
                        try:
                            count_serial_cnt = int(count_serial_cnt)
                            cnt_array.append(count_serial_cnt)
                        except ValueError as verr:
                            logger.error("Cnt value is not integer - ValueError")
                        except Exception as ex:
                            logger.error("Cnt value is not integer - Exception")
                            
                        read_send_count = read_send_count + 1
                        time.sleep(read_sleep_time)

                else:
                    # son satir mi degil mi kontrolu
                    if 'pct' in str_data and 'Cnt' in str_data:
                        if debug==True:
                          logger.info("reading data finished")
                          logger.info(lines)
                          logger.info("sending data to api")
                        lines.append(str_data)


                        if is_serial_data_consistent(lines):
                          if debug==True:
                            logger.info("Sending data to thread finished")
                          thread1 = Thread(target=send_data, args=(lines, cnt_array))
                          thread1.daemon = True
                          thread1.start()
                        else:
                          logger.error("Broken data : Restarting serial read")
                          read_serial_every_5_mins()

                        # thread2 = Thread(target=sertac_hoca_send_data, args=(lines, cnt_array))
                        # thread2.daemon = True
                        # thread2.start()

                        # send_data(lines, cnt_array)
                        # sertac_hoca_send_data(cnt_array)

                        read_send_count = 0
                        lines = []
                        cnt_array = []
                        pls_array = []
                        send_empty_data = True
                        sleep_exception_message = True
                        if debug==True:
                          logger.info("sleeping after data read")
                        time.sleep(read_sleep_time)
                        if debug==True:
                          logger.info("sleeping finished")
                    elif '[' in str_data:
                        # eski datayi sil
                        if debug==True:
                          logger.info("Waiting for last data (starts with '[')")
                          logger.info("Old data was removed")
                        lines = [str_data]
                    else:
                        lines.append(str_data)
            else:
                if send_empty_data:
                    if debug==True:
                      logger.info("sending empty array to service")

                    thread1 = Thread(target=send_data, args=([], []))
                    thread1.daemon = True
                    thread1.start()

                    # thread2 = Thread(target=sertac_hoca_send_data, args=([], []))
                    # thread2.daemon = True
                    # thread2.start()

                    # send_data([], [])
                    if debug==True:
                      logger.info("sleeping after empty array")
                    send_empty_data = False
                    time.sleep(read_sleep_time)
                    if debug==True:
                      logger.info("sleeping finished for empty array")

        except SerialException as e:
            sleep = True
            if debug==True:
              logger.info("Serial Exception: " + str(e.strerror))
            exception_count = exception_count + 1

        except Exception as e:
            sleep = True
            # logger.error("Exception: ", e)
            # logger.error(e)


if __name__ == '__main__':
    read_serial_every_5_mins()
