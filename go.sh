# add this line in the end of the file ~/.bashrc:
# ./git/jeroen256/aiy-voice-kit/go.sh

vncserver :1 -geometry 1366x715

# export LC_ALL=C is for preventing this error:
# File "/home/pi/AIY-voice-kit-python/env/lib/python3.4/site-packages/mps_youtube/main.py", line 44, in <module>
#     locale.setlocale(locale.LC_ALL, "")  # for date formatting
#   File "/home/pi/AIY-voice-kit-python/env/lib/python3.4/locale.py", line 592, in setlocale
#     return _setlocale(category, locale)
# locale.Error: unsupported locale setting
export LC_ALL=C

