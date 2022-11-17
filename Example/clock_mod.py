# https://github.com/pimoroni/pimoroni-pico/blob/main/micropython/examples/galactic_unicorn/clock.py
# Clock example with NTP synchronization
#
# Create a secrets.py with your Wifi details to be able to get the time
# when the Galactic Unicorn isn't connected to Thonny.
#
# secrets.py should contain:
# WIFI_SSID = "Your WiFi SSID"
# WIFI_PASSWORD = "Your WiFi password"
#
# Clock synchronizes time on start, and resynchronizes if you press the A button
##############
# 2022-11-13 by @PaulskPt (Github)
# This is a modified version:
# The following changes have been done:
# Button A: increase hour
# Button B: decrease hour
# Button C: increase minute
# Button D: increase minute
# Instead of calling time_sync() by pressing Button A,
# time_sync() is now called at an interval set by global variable interval_secs
# Changing the minute:
# - will not change the hour;
# - roll-over >= 24 = 0. < 0 = 23)
# Changing the hour:
# - will not change the minute
# - roll-over >= 60 = 0. < 0 = 59)
#
# Global variable 'classic' :
# - if True: the classic clock algorithm is used
# - if False: the mmodified (@PaulskPt) algorithm is used
#             and loads the character definitions in digits.py
# Note:
# When the hour or minute has been changed, the global flag 'do_sync' will be set to False
# because we don't want this change of hour/minute be overruled by a next NTP sync.
# The 'do_sync' flag can only be switched back to True by restarting this script.
#
# Set the global variable 'my_debug' to True to see more details like os.uname() results.
# Global variable use_fixed_color:
# If True, the displayed foreground color is red
# If False, the displayed foreground color starts with red. After a NTP sync the color will change to
# one of the seven other defined colors. See color_dict.
# Added global variable 'use_sound'. If True a double tone will be played at NTP_sync.
# Added global variable 'vol'. Default vol = 10 which inhibits sound. After the user pressed button 'Vol +' and vol > 10,
# then a sound will be played at the NTP_sync interval events.
##############
import time, sys, os
import math
import machine
import network
import ntptime
from galactic import GalacticUnicorn, Channel
from picographics import PicoGraphics, DISPLAY_GALACTIC_UNICORN as DISPLAY

try:
    from clock_mod_secrets import WIFI_SSID, WIFI_PASSWORD, COUNTRY, TZ_OFFSET
    wifi_available = True
except ImportError:
    print("Create secrets.py with your WiFi credentials to get time from NTP")
    wifi_available = False

my_debug = False

id0 = machine.unique_id()
id = '{:02x}{:02x}{:02x}{:02x}'.format(id0[0], id0[1], id0[2], id0[3]) 

# used in main()
country = COUNTRY.upper()

# Classic means: the original Pimoroni clock script version for the Galactic Universe device
classic = False

do_sync = True # Built-in RTC will be updated at intervals by NTP datetime

# NTP synchronizes the time to UTC, this allows you to adjust the displayed time
# by one hour increments from UTC by pressing the volume up/down buttons
utc_offset = TZ_OFFSET

img_dict = {} # to prevent error. dictionary will be loaded from digits.py

use_sound = True

if not classic:
    from clock_mod_digits import *

use_fixed_color = False

vol_set = False

# constants for controlling the background colour throughout the day
MIDDAY_HUE = 1.1
MIDNIGHT_HUE = 0.8
HUE_OFFSET = -0.1

MIDDAY_SATURATION = 1.0
MIDNIGHT_SATURATION = 1.0

MIDDAY_VALUE = 0.8
MIDNIGHT_VALUE = 0.3

wlan = None

# create galactic object and graphics surface for drawing
gu = GalacticUnicorn()
#gr = PicoGraphics(DISPLAY)
gr = PicoGraphics(display=DISPLAY)

button_a = machine.Pin(gu.SWITCH_A, machine.Pin.IN, machine.Pin.PULL_UP)
button_b = machine.Pin(gu.SWITCH_B, machine.Pin.IN, machine.Pin.PULL_UP)
button_c = machine.Pin(gu.SWITCH_C, machine.Pin.IN, machine.Pin.PULL_UP)
button_d = machine.Pin(gu.SWITCH_D, machine.Pin.IN, machine.Pin.PULL_UP)
up_button = machine.Pin(gu.SWITCH_VOLUME_UP, machine.Pin.IN, machine.Pin.PULL_UP)
down_button = machine.Pin(gu.SWITCH_VOLUME_DOWN, machine.Pin.IN, machine.Pin.PULL_UP)

# create the rtc object
rtc = machine.RTC()

year, month, day, wd, hour, minute, second, _ = rtc.datetime()
last_second = second
clock = ''

ptm = 0.0 # percentage-to-midday

width = gu.WIDTH
height = gu.HEIGHT

# See: https://www.rapidtables.com/web/color/index.html
# set up some pens to use later
BLACK = gr.create_pen(0, 0, 0)
red_ = 0
green_ = 1
blue_ = 2
yellow_ = 3
orange_ = 4
pink_ = 5
white_ = 6
black_ = 7

clr_dict = {
    red_:    (255,0,0),
    green_:  (0,255,0),
    blue_:   (0,0,255),
    yellow_: (255,255,0),
    orange_: (255,140,0),
    pink_:   (255,20,147),
    white_:  (255,255,255),
    black_:  (0,0,0)
}

clr_dict_rev = {
    red_: 'RED',
    green_: 'GREEN',
    blue_: 'BLUE',
    yellow_: 'YELLOW',
    orange_: 'ORANGE',
    pink_: 'PINK',
    white_: 'WHITE',
    black_: 'BLACK'
}
#-----------------+
clr_idx = pink_ # | <<<=== Set here the fixed color
#-----------------+
max_clr_idx = len(clr_dict)-1

time_chgd = False
dev_dict = {}

if use_sound:
    timer = machine.Timer(-1)

    # The two frequencies to play
    tone_a = 1000
    tone_b = 900
    vol = 10  # initially no sound, only after user presses 'Vol +'
    min_vol = 10
    max_vol = 20000
    

    notes = [(1000, 900), (1000, 900)]
    channels = [gu.synth_channel(i) for i in range(len(notes))]

    def play_tone(tone):
        global vol
        if vol <= 10:
            return  # don't make sound
        if tone >= 0 and tone <=1000:
            # Stop synth (if running) and play Tone A
            timer.deinit()
            if tone == tone_a:
                channels[0].play_tone(tone, 0.06)
            if tone == tone_b:
                channels[1].play_tone(tone_b, 0.06, attack=0.5)

            gu.play_synth()

    def double_tone():
        global tone_a, tone_b
        TAG="double_tone(): "
        tone_a = 1000
        tone_b = 900
        ch_a = 0
        ch_b = 1
        tone = None
        ch = None

        for _ in range(2):
            timer.deinit() 
            tone = tone_a if _ == 0 else tone_b
            # print(TAG+f"playing tone {tone}")
            ch = ch_a if _ == 0 else ch_b
            if tone > 0:  # Zero means tone not playing
                play_tone(tone)
                time.sleep(0.3)
        gu.stop_playing()
        timer.deinit()
        tone_a = 0
        tone_b = 0

"""
    os.uname() result =
    (sysname='rp2',
    nodename='rp2',
    release='1.19.1',
    version='9dfabcd on 2022-10-19 (GNU 9.2.1 MinSizeRel)',
    machine='Raspberry Pi Pico W with RP2040')
"""
def my_dev():
    if my_debug:
        global dev_dict
    TAG= "my_dev(): "
    dev_lst = ['sysname', 'nodename', 'release', 'version', 'machine']
    
    dev_dict = {}
    s_tpl = os.uname()
    le = len(s_tpl)
    for i in range(le):
        dev_dict[dev_lst[i]] = s_tpl[i]
    if my_debug:
        print(TAG+f"dev_dict= {dev_dict}")

def clear():
    gr.set_pen(BLACK)
    gr.clear()
    gu.update(gr)

@micropython.native  # noqa: F821
def from_hsv(h, s, v):
    i = math.floor(h * 6.0)
    f = h * 6.0 - i
    v *= 255.0
    p = v * (1.0 - s)
    q = v * (1.0 - f * s)
    t = v * (1.0 - (1.0 - f) * s)

    i = int(i) % 6
    if i == 0:
        return int(v), int(t), int(p)
    if i == 1:
        return int(q), int(v), int(p)
    if i == 2:
        return int(p), int(v), int(t)
    if i == 3:
        return int(p), int(q), int(v)
    if i == 4:
        return int(t), int(p), int(v)
    if i == 5:
        return int(v), int(p), int(q)


# function for drawing a gradient background
def gradient_background(start_hue, start_sat, start_val, end_hue, end_sat, end_val):
    half_width = width // 2
    for x in range(0, half_width):
        hue = ((end_hue - start_hue) * (x / half_width)) + start_hue
        sat = ((end_sat - start_sat) * (x / half_width)) + start_sat
        val = ((end_val - start_val) * (x / half_width)) + start_val
        colour = from_hsv(hue, sat, val)
        if classic:
            gr.set_pen(gr.create_pen(int(colour[0]), int(colour[1]), int(colour[2])))
        else:
            gr.set_pen(gr.create_pen(0, 0, 0))  # mod by @PaulskPt
        for y in range(0, height):
            gr.pixel(x, y)
            gr.pixel(width - x - 1, y)

    colour = from_hsv(end_hue, end_sat, end_val)
    if classic:
        gr.set_pen(gr.create_pen(int(colour[0]), int(colour[1]), int(colour[2])))
    else:
        gr.set_pen(gr.create_pen(0, 0, 0))  # mod by @PaulskPt
    for y in range(0, height):
        gr.pixel(half_width, y)

# function for drawing outlined text

def outline_text(text, x: int=10, y: int=2, inv: int=0):
    # def draw(image, fg, bg, time_ms):
    TAG = "outline_text(): "
    my_classic = classic
    # print(TAG+f"text= \'{text}\'")
    t_lst = ["Res", "Vol"]
    if text[:3] in t_lst:
        my_classic = True

    if my_classic:
        if not inv:
            fg = clr_dict[black_]
        else:
            fg = clr_dict[white_]
        fg_pen = gr.create_pen(fg[0], fg[1], fg[2])
        gr.set_pen(fg_pen)
        gr.text(text, x - 1, y - 1, -1, 1)
        gr.text(text, x    , y - 1, -1, 1)
        gr.text(text, x + 1, y - 1, -1, 1)
        
        gr.text(text, x - 1, y    , -1, 1)
        gr.text(text, x + 1, y    , -1, 1)
        
        gr.text(text, x - 1, y + 1, -1, 1)
        gr.text(text, x    , y + 1, -1, 1)
        gr.text(text, x + 1, y + 1, -1, 1)
        
        if not inv:
            fg = clr_dict[white_]
        else:
            fg = clr_dict[black_]
        fg_pen = gr.create_pen(fg[0], fg[1], fg[2])
        gr.set_pen(fg_pen)
        gr.text(text, x, y, -1, 1)
        if vol_set:
            time.sleep(1)
    else:
        img = None
        fg = clr_dict[clr_idx]
        if clr_dict_rev[clr_idx] == 'BLACK':
            bg = clr_dict[white_]
            bg_pen = gr.create_pen(bg[0], bg[1], bg[2])
            for i in range(x):
                for j in range(height):
                    gr.set_pen(bg_pen)
                    gr.pixel(i, j)
        else:
            bg = clr_dict[black_]
        fg_pen = gr.create_pen(fg[0], fg[1], fg[2])
        bg_pen = gr.create_pen(bg[0], bg[1], bg[2])
        gr.set_pen(fg_pen)
        
        le=len(text)    
        col_ = x
        width_ = 0
        time_ms = time.time_ns()//1000000  # convert nanosecond to millisecond - added by @PaulskPt
        for _ in range(le):
            if text[_][0] in img_dict:
                img = img_dict[text[_]][0]
                width_ = img_dict[text[_]][1]
                #print(TAG+f"image= \'{text[_]}\'")
            else:
                if my_debug:
                    print(TAG+f"key \'{text[_]}\' not in img_dict")

            if img is None:
                return
            
            for y in range(len(img)):
                row = img[y]
                for z in range(len(row)):
                    pixel = row[z]
                    # draw the prompt text
                    if pixel == 'O':
                        gr.set_pen(fg_pen)

                    # draw the caret blinking
                    elif pixel == 'X' and (time_ms // 300) % 2:
                        gr.set_pen(fg_pen)
                    else:
                        gr.set_pen(bg_pen)                
                    gr.pixel(col_+z, y)
            col_ += width_+1
            
        if clr_dict_rev[clr_idx] == 'BLACK':
            le = width - col_
            bg = clr_dict[white_]
            bg_pen = gr.create_pen(bg[0], bg[1], bg[2])
            for i in range(le):
                for j in range(height):
                    gr.set_pen(bg_pen)
                    gr.pixel(col_+i, j)
        gu.update(gr)
        
# In the left-upper corner
# blink a 2x2 square
# to indicate:
# WiFi Connected:       green_
# WiFi disconnected:    red_
# sync_time successful: blue_
def blink(clr):
    if my_debug:
        TAG= "blink():     "
        print(TAG+f"param= {clr_dict_rev[clr]}")
    if clr in clr_dict.keys():
        fg = clr_dict[clr]
        bg = clr_dict[black_]
        fg_pen = gr.create_pen(fg[0], fg[1], fg[2])
        bg_pen = gr.create_pen(bg[0], bg[1], bg[2])
        for h in range(3): # blink 3 times
            for i in range(2):  # horzontal
                for j in range(2):  # vertical
                    gr.set_pen(fg_pen) # green or red
                    gr.pixel(i, j)
            gu.update(gr)
            time.sleep(0.2)
            for i in range(2):  # horizontal
                for j in range(2):  # vertical
                    gr.set_pen(bg_pen) # black
                    gr.pixel(i, j)
            gu.update(gr)
            time.sleep(0.2)

# wrapper for wlan.isconnected()
# Param TAG: the TAG from the calling function
# so this func is printing 'in name of' the calling function
def is_connected(TAG):
    global wlan
    if TAG is None:
        TAG="is_connected(): "
    s = '' if wlan.isconnected() else "dis"
    print(TAG+f"WiFi {s}connected")
    if wlan.isconnected():
        blink(green_)
    else:
        blink(red_)


# Connect to wifi and synchrnize the RTC time from NTP
def sync_time():
    global wlan, tone_a, tone_b
    if not do_sync:
        return
    if not wifi_available:
        return
    TAG="sync_time(): "
    msg_shown = False

    # Start connection
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    # Wait for connect success or failure
    max_wait = 100
    while max_wait > 0:
        wstat = wlan.status()
        if wstat < 0 or wstat >= 3:
            break
        max_wait -= 1
        if not msg_shown:
            msg_shown = True
            print(TAG+'waiting for connection...')
        time.sleep(0.2)

        redraw_display_if_reqd()
        gu.update(gr)

    if max_wait > 0:
        is_connected(TAG)
        try:
            ntptime.settime()
            if use_sound:
                double_tone()
            blink(blue_)
            print(TAG+"built-in RTC sync\'ed from NTP")
        except OSError as e:
            print(TAG+f"error: {e}")
            pass
    else:
        print(TAG+"NTP sync failed. Check WiFi Access Point")

    wlan.disconnect()
    cnt = 0
    while wlan.isconnected():
        machine.idle()  # save power while waiting
        cnt += 1
        if cnt >= 100:
            print(TAG+f"failed to disconnect from wlan during {cnt} tries")
            break
    is_connected(TAG)
    wlan.active(False)

#
# return a quasi unix epoch value
# to be used in main() to calculate the elapsed time in seconds
# 
def epoch():
    year, month, day, wd, hour, minute, second, _ = rtc.datetime()
    secs = (day*(24*3600))+(hour*3600)+(minute*60)+second
    if my_debug:
        print(f"epoch(): seconds= {secs}")
    return secs

def adjust_utc_offset(pin):
    global utc_offset
    if pin == up_button:
        utc_offset += 1
    if pin == down_button:
        utc_offset -= 1
        
def adjust_hour(pin):
    global hour, time_chgd, do_sync
    if time_chgd:
        return  # we don't want react on a button bounce
    if pin == button_a:
        time_chgd = True
        hour += 1
        if hour >= 24:
            hour = 0
    elif pin == button_b:
        time_chgd = True
        hour -= 1
        if hour < 0:
            hour = 23
    if time_chgd:
        print("Hour changed")
        if do_sync:
            do_sync = False  # We don't want the changed time to by overwritten by NTP sync
            print("adjust_hour(): NTP sync swtiched off")
            
def adjust_minute(pin):
    global minute, time_chgd, do_sync
    if time_chgd:
        return  # we don't want react on a button bounce
    if pin == button_c:
        time_chgd = True
        minute += 1
        if minute >= 60:
            minute = 0
    elif pin == button_d:
        time_chgd = True
        minute -= 1
        if minute < 0:
            minute = 59
    if time_chgd:
        print("Minute changed")
        if do_sync:
            do_sync = False  # We don't want the changed time to by overwritten by NTP sync
            print("adjust_minute(): NTP sync swtiched off")

# We use the IRQ method to detect the button presses to avoid incrementing/decrementing
# multiple times when the button is held.
button_a.irq(trigger=machine.Pin.IRQ_FALLING, handler=adjust_hour)
button_b.irq(trigger=machine.Pin.IRQ_FALLING, handler=adjust_hour)
button_c.irq(trigger=machine.Pin.IRQ_FALLING, handler=adjust_minute)
button_d.irq(trigger=machine.Pin.IRQ_FALLING, handler=adjust_minute)
#up_button.irq(trigger=machine.Pin.IRQ_FALLING, handler=adjust_utc_offset)
#down_button.irq(trigger=machine.Pin.IRQ_FALLING, handler=adjust_utc_offset)

# Check whether the RTC time has changed and if so redraw the display
def redraw_display_if_reqd():
    global clock, year, month, day, wd, hour, minute, second, last_second, old_secs, time_chgd, ptm, vol_set
    
    if time_chgd:
        rtc.datetime((year,month,day,wd,hour,minute,second,0))
        time.sleep(0.1)
    year, month, day, wd, hour, minute, second, _ = rtc.datetime()
    
    if second != last_second or time_chgd:
        if time_chgd:
            time_chgd = False
        hour += utc_offset
        time_through_day = (((hour * 60) + minute) * 60) + second
        percent_through_day = time_through_day / 86400
        percent_to_midday = 1.0 - ((math.cos(percent_through_day * math.pi * 2) + 1) / 2)
        if second*1000 % 10 == 0:
            #print(percent_to_midday) # we don't need to show this percentage every second
            ptm = percent_to_midday

        hue = ((MIDDAY_HUE - MIDNIGHT_HUE) * percent_to_midday) + MIDNIGHT_HUE
        sat = ((MIDDAY_SATURATION - MIDNIGHT_SATURATION) * percent_to_midday) + MIDNIGHT_SATURATION
        val = ((MIDDAY_VALUE - MIDNIGHT_VALUE) * percent_to_midday) + MIDNIGHT_VALUE

        gradient_background(hue, sat, val,
                            hue + HUE_OFFSET, sat, val)

        clock = "{:02}:{:02}:{:02}".format(hour, minute, second) # global var. Used sed in main() and hdg()

        # set the font
        gr.set_font("bitmap8")

        # calculate text position so that it is centred
        w = gr.measure_text(clock, 1)
        if classic:
            x = int(width / 2 - w / 2 + 1)
        else:
            x = 9
        y = 2

        outline_text(clock, x, y)
        if vol_set:
            vol_set = False  # clear

        last_second = second

def hdg(hdg, TAG, clock, time_to_sync, s,):
    ln = TAG+"+----------+-------------+--------------+"
    if clock is None:
        clock = '00:00:00'
    if isinstance(clock, str) and len(clock) == 8:
        if hdg:
            print()
            print(ln)
            print(TAG+"|          | NTP sync    |      %       |")
            print(TAG+"|  Clock   | in...  secs |  to midday   |")
            print(ln)
        print(TAG+f"| {clock} |     {time_to_sync}    |     {s}   |")
        print(ln)
    
def main():
    global dev_dict, clr_idx, tone_a, tone_b, vol_set, vol
    TAG="main():      "
    my_dev() # fill dev_dict with os.uname() keys and values
    if len(dev_dict) > 0:
        k = dev_dict.keys()
        if 'machine' in k:
            print(TAG+f"This script is running on a \'{dev_dict['machine']}\'")
        if my_debug:
            print(TAG+f"board id: \'{id}\'")
            if 'release' in k:
                print(TAG+f"MicroPython release: \'{dev_dict['release']}\'")
            if 'version' in k:
                print(TAG+f"Version: \'{dev_dict['version']}\'")
    gu.set_brightness(0.2)  # was: (0.5)
    #----------------------------------+
    interval_secs = 600 # 10 minutes # | <<<=== Set here the time_sync interval
    #----------------------------------+
    if do_sync:
        print(TAG+f"At intervals of {interval_secs//60} minutes the built-in RTC will be synchronized from NTP datetime server")
    else:
        print(TAG+"The built-in RTC will not by synchronized from NTP datetime server")
    
    sync_time()

    start_secs = epoch()
    if my_debug:
        print(TAG+"+----------+-------------+--------------+")
        print(TAG+"| mod_secs | start_secs  | elapsed_secs |")
        print(TAG+"+----------+-------------+--------------+")
    elapsed_old = -1
    pr_hdg = False
    print(TAG+f"Display color: {clr_dict_rev[clr_idx]}")
    stop = False
    while True:
        try:
            text = ''
            curr_secs = epoch()
            elapsed_secs = curr_secs - start_secs
            #print(TAG+f"elapsed_secs= {elapsed_secs}")
            if elapsed_old != elapsed_secs:
                elapsed_old = elapsed_secs
                mod_secs10 = elapsed_secs % 10
                mod_secs60 = elapsed_secs % 60
                #print(TAG+f"mod_secs60 = {mod_secs60}")
                mod_secs2 = elapsed_secs % interval_secs
                if elapsed_secs > 0 and mod_secs2 == 0:
                    start_secs = curr_secs
                    print("Going to sync built-in RTC with NTP date & time")
                    sync_time()
                    pr_hdg = True
                    if not use_fixed_color:
                        clr_idx += 1
                        if clr_idx > max_clr_idx:
                            clr_idx = 0  # not 0 (that's black)
                    print(TAG+f"Display color: {clr_dict_rev[clr_idx]}")
                if my_debug:
                    s = "| {:4d}     |  {:8d}   |  {:4d}        |".format(mod_secs10, start_secs, elapsed_secs)
                    print(TAG+s)
                if mod_secs10 == 0:
                    #s = "{:4d}".format(elapsed_secs)
                    time_to_sync = "{:4d}".format(interval_secs - elapsed_secs)
                    n = 100-ptm*100
                    s = "{:6.3f}".format(n)
                    #s = str(n)
                    if country.upper() == "PT":
                        s = s.replace('.',',')  # Don't do this if country == "USA"
                    if elapsed_secs == 0 or mod_secs60 == 0:
                        if not pr_hdg:
                            pr_hdg = True
                        hdg(pr_hdg, TAG, clock, time_to_sync, s)
                    else:
                        if pr_hdg:
                            pr_hdg = False
                        hdg(pr_hdg, TAG, clock, time_to_sync, s)

            if gu.is_pressed(gu.SWITCH_BRIGHTNESS_UP):
                gu.adjust_brightness(+0.01)

            if gu.is_pressed(gu.SWITCH_BRIGHTNESS_DOWN):
                gu.adjust_brightness(-0.01)
            
            if use_sound:
                if gu.is_pressed(gu.SWITCH_VOLUME_UP):
                    if vol > 0:  # Zero means tone not playing
                        # Increase Tone A
                        vol = min(vol + 10, 20000)
                        #channels[0].frequency(vol)

                if gu.is_pressed(gu.SWITCH_VOLUME_DOWN):
                    if vol > 0:  # Zero means tone not playing
                        # Decrease Tone A
                        vol = max(vol - 10, 10)
                        #channels[0].frequency(vol)
                    
                if gu.is_pressed(gu.SWITCH_VOLUME_UP):
                    text = "Vol Up"+' '+str(vol)
                    gr.set_pen(gr.create_pen(0, 0, 0))
                    clear()
                    outline_text(text, x=5)

                if gu.is_pressed(gu.SWITCH_VOLUME_DOWN):
                    text = "Vol Dn"+' '+str(vol)
                    gr.set_pen(gr.create_pen(0, 0, 0))
                    clear()
                    outline_text(text, x=5)

            if gu.is_pressed(gu.SWITCH_A):
                adjust_hour(gu.SWITCH_A)
            
            if gu.is_pressed(gu.SWITCH_B):
                adjust_hour(gu.SWITCH_B)
                
            if gu.is_pressed(gu.SWITCH_C):
                adjust_minute(gu.SWITCH_C)
                
            if gu.is_pressed(gu.SWITCH_D):
                adjust_minute(gu.SWITCH_D)
                
            if gu.is_pressed(gu.SWITCH_SLEEP):
                text = "Resetting..."
                print("Going to reset...")
                stop = True
                gr.set_pen(gr.create_pen(0, 0, 0))
                clear()
                outline_text(text)
    
            redraw_display_if_reqd()

            # update the display
            gu.update(gr)
            
            if stop:
                time.sleep(2)
                machine.reset()

            time.sleep(0.01)
        except KeyboardInterrupt:
            print("Keyboard interrupt. Exiting...")
            sys.exit()

# Call the main function
if __name__ == '__main__':
    main()
