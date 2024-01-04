import time
from mqtt import MQTTClient   # For use of MQTT protocol to talk to Adafruit IO
import ubinascii              # Conversions between binary data and various encodings
import machine                # Interfaces with hardware components
import micropython            # Needed to run any MicroPython code
from machine import Pin       # Define pin
import utime as time
from dht import DHT11
import wifi
from machine import I2C, Pin, ADC
from pico_i2c_lcd import I2cLcd


# BEGIN SETTINGS
i2c = I2C(0, sda=Pin(8), scl=Pin(9), freq=400000)
#minutes = 5
#INTERVAL = minutes * 60  # 300 seconds = 5 minutes
INTERVAL = 10
led = Pin("LED", Pin.OUT)   # led pin initialization for Raspberry Pi Pico W
soil_adc_pin1 = ADC(Pin(26))

# Adafruit IO (AIO) configuration
AIO_SERVER = "io.adafruit.com"
AIO_PORT = 1883
AIO_USER = "Paty_Marklund"
AIO_KEY = "aio_wJnh06AczerjJNM4vxgB03tEFY3z"
AIO_CLIENT_ID = ubinascii.hexlify(machine.unique_id()) 
AIO_LIGHTS_FEED = "Paty_Marklund/feeds/lights"
AIO_TEMP_FEED = "Paty_Marklund/feeds/temperature"
AIO_HUMID_FEED = "Paty_Marklund/feeds/humidity"
AIO_MESSAGE_FEED = "Paty_Marklund/feeds/message"
AIO_HELLO_FEED = "Paty_Marklund/feeds/hello"


# FUNCTIONS

# Callback Function to respond to messages from Adafruit IO
def sub_cb(topic, msg):          # sub_cb means "callback subroutine"    
    received = msg.decode()
    print((topic, received))              # Outputs the message that was received. Debugging use.
    message_1 = "Hello!"
    display_message(message_1, received)

# Method to get the temperature from the sensor and publish
def get_temperature():
    sensor = DHT11(machine.Pin(28))
    prev_temp = None
    prev_humid = None    
    
    while True:
        try:
            temp = sensor.temperature
            time.sleep(2)
            humid = sensor.humidity
        except:
            print("An exception occurred")  
            continue  
        
        if (prev_humid is None or prev_temp is None) or (temp != prev_temp and humid != prev_humid):
            prev_temp = temp
            prev_humid = humid
            message_1, message_2 = weather_report(temp, humid)
            publish_message = message_1 + " / " + message_2
            display_message(message_1, message_2)
            
        print("Publishing: {0} to {1} ... ".format(temp, AIO_TEMP_FEED), end='')
        print("Publishing: {0} to {1} ... ".format(humid, AIO_HUMID_FEED), end='')
        print("Publishing: {0} to {1} ... ".format(publish_message, AIO_MESSAGE_FEED), end='')
        
        pub_sub(temp, humid, publish_message)
        
# this function is called when auto wattering is ON
def do_auto_wattering():
    adc1 = soil_adc_pin1.read_u16()
    moisture_perc1 = rsd.get_soil_moisture_percentage(adc1, fully_dry, fully_wet)
    if moisture_perc1 <= 15:
        relay_pump_pin = Pin(15, Pin.OUT)
        print("WATER PUMP IS ON!")
        time.sleep(3)
        relay_pump_pin.init(Pin.IN)
        print("WATER PUMP IS OFF!")
        time.sleep(3)
    else:
        print("Soil moisture is above 10%, no need to water the plant!", moisture_perc1, adc1)
        time.sleep(3)
    
# Method to publish and subscribe to messages
def pub_sub(temp, humid, publish_message):
    try:
        client.publish(topic=AIO_TEMP_FEED, msg=str(temp))
        client.publish(topic=AIO_HUMID_FEED, msg=str(humid))
        client.publish(topic=AIO_MESSAGE_FEED, msg=str(publish_message))
        client.subscribe(AIO_HELLO_FEED)
        print("DONE")
    except Exception as e:
        print("FAILED")
    finally:
        time.sleep(INTERVAL)
            
# Method to calculate weather report
def weather_report(temp, humidity):
    temperature = int(temp)
    message_1 = " "
    message_2 = " "
    if temperature > 30 and humidity < 70:
        message_1 = str(temperature)+"C Too hot!"
        message_2 = "Shorts & flops!"
    elif temperature > 25 and humidity < 70:
        message_1 = str(temperature)+"C Warm weather"
        message_2 = "T-shirt & hat"
    elif temperature > 20 and humidity < 70:
        message_1 = str(temperature)+"C Nice weather"
        message_2 = "Light jacket"
    elif temperature > 10 and humidity < 70:
        message_1 = str(temperature)+"C Bit chill"
        message_2 = "Jacket"
    elif temperature > 0 and humidity > 70:
        message_1 = str(temperature)+"C Rainy day"
        message_2 = "Rain cloths"
    elif temperature > 0 and humidity < 70:
        message_1 = str(temperature)+"C Too cold"
        message_2 = "Overalls"
    elif temperature < 0 and humidity > 70:
        message_1 = str(temperature)+"C Snow day"
        message_2 = "Put everything"
    else:
        message_1 = str(temperature)+"C Too cold"
        message_2 = "Overalls"
        
    return message_1, message_2
    
# Method to display message on the LCD screen
def display_message(message_1, message_2):
    I2C_ADDR = i2c.scan()[0]
    lcd = I2cLcd(i2c, I2C_ADDR, 2, 16)
    print()
    lcd.move_to(0,0)
    lcd.putstr(message_1+"\n")
    lcd.move_to(0,1)
    lcd.putstr(message_2)

# Try WiFi Connection
try:
    ip = wifi.do_connect()
except KeyboardInterrupt:
    print("Keyboard interrupt")

# Use the MQTT protocol to connect to Adafruit IO
client = MQTTClient(AIO_CLIENT_ID, AIO_SERVER, AIO_PORT, AIO_USER, AIO_KEY)

# Subscribed messages will be delivered to this callback
client.set_callback(sub_cb)
client.connect()
client.subscribe(AIO_HELLO_FEED)
print("Connected to %s, subscribed to %s topic" % (AIO_SERVER, AIO_HELLO_FEED))

try:                      
    while 1:              
        client.check_msg()  # Action a message if one is received. Non-blocking.
        get_temperature()
finally:                  # If an exception is thrown ...
    client.disconnect()   # disconnect the client and clean up.
    client = None
    print("Disconnected from Adafruit IO.")
    