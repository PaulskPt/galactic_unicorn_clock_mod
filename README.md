# Galactic Unicorn MicroPython Example <!-- omit in toc -->
 
- [About Galactic Unicorn](#about-galactic-unicorn)
- [Galactic Unicorn and PicoGraphics](#galactic-unicorn-and-picographics)
- [Example](#example)
  - [Clock (modified version)](#clock-modified-version)


## About Galactic Unicorn

Galactic Unicorn offers 53x11 bright RGB LEDs driven by Pico W's PIO in addition to a 1W amplifier + speaker, a collection of system and user buttons, and two Qw/ST connectors for adding external sensors and devices. Woha!

- :link: [Galactic Unicorn store page](https://shop.pimoroni.com/products/galactic-unicorn)

Galactic Unicorn ships with MicroPython firmware pre-loaded, but you can download the most recent version at the link below (you'll want the  `galactic-unicorn` image).

- [MicroPython releases](https://github.com/pimoroni/pimoroni-pico/releases)
- [Installing MicroPython](../../../setting-up-micropython.md)

## Galactic Unicorn and PicoGraphics

The easiest way to start displaying cool stuff on Galactic Unicorn is using our Galactic Unicorn module (which contains a bunch of helpful functions for interacting with the buttons, adjusting brightness and suchlike) and our PicoGraphics library, which is chock full of useful functions for drawing on the LED matrix.

- [Galactic Unicorn function reference](../../modules/galactic_unicorn/README.md)
- [PicoGraphics function reference](../../modules/picographics/README.md)

## Example


### Clock (modified version)

[clock_mod.py](clock_mod.py)


Modified clock example by @PaulskPt, using timed NTP synchronization. You can adjust the brightness with LUX + and -. Resync of the time is now done at intervals determined by the value of the variable 'interval_secs' in main(), line 648, default 600 seconds. Button A re-arranged. Buttons B, C and D added. Button A: increase hours; button B: decrease hours; button C: increase minutes; button D: decrease minutes. When you change hours and/or minutes, using buttons A thru D, the NTP syncing will be halted. This is done to prevent that a next NTP sync will undo your time alteration.

Added Global variables: 
- 'classic': (default False) If True: the color scheme of the the original Pimoroni clock script version for the
   Galactic Universe device is used. If False you have an option: see 'use_fixed_color' below.
- 'use_fixed_color: (default: False) (line 96). If True, set your favorite color with variable 'clr_idx' (line 171), e.g.: 'clr_idx = pink_'. 
   If True. One color (defaults: foreground: red, background: black) is used. If False: color change at intervals.
   The color changes after an NTP sync moment. All foreground colors go with a black background color, except when foregrond color is black, the background will be white.
- 'my_debug': (default False) If True more information will be printed to the REPL.
- 'do_sync': (default True) this boolean variable is used to inhibit NTP sync after an hour/minute change by the user.
  
- The following global variables are taken from the file 'clock_mod_secrets.py':
```
 +------------------+---------------------------+---------------------------------------------------------------------+
 | Global           | value from key ...        |                                                                     |
 | variable:        | in 'clock_mod_secrets.py' |  use:                                                               |
 +------------------+---------------------------+---------------------------------------------------------------------+
 | country          |    COUNTRY                |  to replace decimal '.' by ',' if country != "USA"                  |
 +------------------+---------------------------+---------------------------------------------------------------------+
 | utc_offset       |    TZ_OFFSET              |  to calculate the localtime. Offet in hours e.g. N.Y should be -5   |
 +------------------+---------------------------+---------------------------------------------------------------------+
 | ntp_server       |    NTP_SERVER             |  define here your NTP server. Default is set to "pool.ntp.org"      |
 +------------------+---------------------------+---------------------------------------------------------------------+
 ```

This example uses different character definitions. The characters are defined in the file 'clock_mod_digits.py'. At the end of this file is defined a 'img_dict', which contains info about the defined characters, all except one are digits, as well as the 'width' each of them occupies. The use of a different character set in combination with other color schemes gives you a more 'quiet' view experience. The original version is very nice, colorful and adjusted to ambient light, however that example gives a 'nervous' experience because pixels of the background colours surrounding and in between the digits are frequently moving. This 'effect' I didn't like. It was one of the reasons for me to write the 'clock_mod' example script. I also didn't like the way the 'colon' character was defined' (too much shifted upwards). I made the colon also wider.

Removed function:
- adjust_utc_offset()

Added functions:
- play_tone();
- double_tone();
- my_dev(): collects the os.uname() into global 'dev_dict' dictionary. Data as: 'machine', (micropython) release and version;
- blink(): blinks a 2x2 pixel square in the top-left corner to indicate WiFi connected (green), WiFi disconnected (red). sync_time (blue).
- is_connected: prints to REPL info about the WiFi connection status (connected/disconnected);
- epoch(): returns number of seconds derived from: time.time() + (utc_offset * 3600) value. It is used in main() for time-controlled actions.
- adjust_hour(): self evident;
- adjust_minute(): same;
- hdg(): prints a header to the REPL. Prints also clock, time_to_sync and percent_to_midday values.
- main(): contains the main loop

Modified functions:
- outline_text();
- sync_time();
- redraw_display_if_reqd():

Compared to the original clock.py example, this example prints more info to the REPL. Info like 'WiFi connected/disconnected'. Other info to REPL as: 'NTP sync in... secs', Clock time and '% to midday' are printed in a table format. Added a main() function with a try...except KeyboardInterrupt block, so the user can interrupt the running script by typing 'Ctrl+C'.


