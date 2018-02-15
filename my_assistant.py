#!/home/pi/AIY-voice-kit-python/env/bin/python3
"""Run a recognizer using the Google Assistant Library with button support.

The Google Assistant Library has direct access to the audio API, so this Python
code doesn't need to record audio. Hot word detection "OK, Google" is supported.

The Google Assistant Library can be installed with:
    env/bin/pip install google-assistant-library==0.0.2

It is available for Raspberry Pi 2/3 only; Pi Zero is not supported.
"""

import logging
import sys
import threading
import subprocess

#sys.path.append('/home/pi/AIY-voice-kit-python/src/aiy')
sys.path.insert(0, '/home/pi/AIY-voice-kit-python/env/lib/python3.4/site-packages')
sys.path.insert(0, '/home/pi/AIY-voice-kit-python/src')
import aiy.assistant.auth_helpers
import aiy.audio
import aiy.voicehat
from google.assistant.library import Assistant
from google.assistant.library.event import EventType
import RPi.GPIO as gpio
import time
import locale
locale.setlocale(locale.LC_ALL, 'en_GB.utf8')

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
)
        
class MyAssistant(object):
    """An assistant that runs in the background.

    The Google Assistant Library event loop blocks the running thread entirely.
    To support the button trigger, we need to run the event loop in a separate
    thread. Otherwise, the on_button_pressed() method will never get a chance to
    be invoked.
    """
    def __init__(self):
        self._task = threading.Thread(target=self._run_task)
        self._can_start_conversation = False
        self._assistant = None

    def start(self):
        """Starts the assistant.

        Starts the assistant event loop and begin processing events.
        """
        self._task.start()

    def _run_task(self):
        credentials = aiy.assistant.auth_helpers.get_assistant_credentials()
        with Assistant(credentials) as assistant:
            self._assistant = assistant
            for event in assistant.start():
                self._process_event(event)

    def _process_event(self, event):
        status_ui = aiy.voicehat.get_status_ui()
        if event.type == EventType.ON_START_FINISHED:
            status_ui.status('ready')
            self._can_start_conversation = True
            # Start the voicehat button trigger.
            aiy.voicehat.get_button().on_press(self._on_button_pressed)
            if sys.stdout.isatty():
                print('Say "OK, Google" or press the button, then speak. '
                      'Press Ctrl+C to quit...')

        elif event.type == EventType.ON_CONVERSATION_TURN_STARTED:
            self._can_start_conversation = False
            status_ui.status('listening')

        elif event.type == EventType.ON_RECOGNIZING_SPEECH_FINISHED and event.args:
            print('You said:', event.args['text'])
            text = event.args['text'].lower()
            words = text.split(" ")
            first = text.split(" ")[0]
            if self.playshell != None: self.stop_playing()
            elif text=='stop playing': self.stop_playing()
            elif first=='play': self.play(text)
            elif "volume" in text: self.change_volume(words)
            elif text == 'ip address': self.say_ip()                 
            elif text == 'catch you on the flip side' or text=='shut down' or text=='power off': self.power_off_pi()                 
            elif text == 'restart' or text=='reboot': self.reboot_pi()                
            elif text == 'quit': self.quit()                
            elif text == 'speak dutch': self.translate()               


        elif event.type == EventType.ON_END_OF_UTTERANCE:
            status_ui.status('thinking')

        elif event.type == EventType.ON_CONVERSATION_TURN_FINISHED:
            status_ui.status('ready')
            self._can_start_conversation = True

        elif event.type == EventType.ON_ASSISTANT_ERROR and event.args and event.args['is_fatal']:
            sys.exit(1)

    def _on_button_pressed(self):
        # Check if we can start a conversation. 'self._can_start_conversation'
        # is False when either:
        # 1. The assistant library is not yet ready; OR
        # 2. The assistant library is already in a conversation.
        if self.playshell != None: self.stop_playing()
        if self._can_start_conversation:
            self._assistant.start_conversation()

    def change_volume(self, words):
        self._assistant.stop_conversation()
        for word in words:
            try:
                volume = int(word.replace("%", ""))
                subprocess.call('amixer set Master {}%'.format(volume), shell=True)
                aiy.audio.say("Volume changed to {} percent.".format(volume))
                return
            except ValueError:
                print("{} is not a number".format(word))
        aiy.audio.say("Could not hear what percentage to change the volume to!")

    def say_ip(self):
        self._assistant.stop_conversation()
        ip_address = subprocess.check_output("hostname -I | cut -d' ' -f1", shell=True)
        aiy.audio.say('My IP address is %s' % ip_address.decode('utf-8'))
    
    def power_off_pi(self):
        self._assistant.stop_conversation()
        aiy.audio.say('Catch you on the flippity flip!')
        subprocess.call('sudo shutdown now', shell=True)

    def reboot_pi(self):
        self._assistant.stop_conversation()
        aiy.audio.say('See you in a bit!')
        subprocess.call('sudo reboot', shell=True)

    def quit(self):
        self._assistant.stop_conversation()
        aiy.audio.say('Quitting assistant application')
        sys.exit()

    playshell = None
    # uses: https://github.com/mps-youtube/mps-youtube
    # /home/pi/AIY-voice-kit-python/env/bin/python3 -m pip install mps-youtube
    # /home/pi/AIY-voice-kit-python/env/bin/python3 -m pip install youtube-dl
    # sudo apt update; sudo apt upgrade; sudo apt install mpv
    # run /home/pi/AIY-voice-kit-python/env/bin/mpsyt and configure mpv as default player
    #
    # or (this does not seem to work for me at the moment): 
    # install: sudo apt install mps-youtube
    # error? sudo dpkg-reconfigure locales (install locale en_US.UTF-8 and set as default, check with locale -a)
    # still error? https://askubuntu.com/questions/205378/unsupported-locale-setting-fault-by-command-not-found
    # still error? https://askubuntu.com/questions/205378/unsupported-locale-setting-fault-by-command-not-found
    def play(self, text):
        self._assistant.stop_conversation()
        track = text.replace("play","")
        aiy.audio.say('OK, one moment, Playing' + track)
        #global playshell
        if (self.playshell == None):
            subprocess.call('export LC_ALL=C', shell=True)
            #self.playshell = subprocess.Popen(["/usr/bin/mpsyt",""],stdin=subprocess.PIPE ,stdout=subprocess.PIPE)
            self.playshell = subprocess.Popen(["/home/pi/AIY-voice-kit-python/env/bin/mpsyt",""],stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        self.playshell.stdin.write(bytes('/' + track + '\n1\n', 'utf-8'))
        self.playshell.stdin.flush()
        #gpio.setmode(gpio.BCM)
        #gpio.setup(23, gpio.IN)
        #while gpio.input(23):
        #        time.sleep(1)
        #pkill = subprocess.Popen(["/usr/bin/pkill","vlc"],stdin=subprocess.PIPE)
        #aiy.audio.say('Finished playing' + track)
        #self._task.start()

    def stop_playing(self):
        self._assistant.stop_conversation()
        pkill = subprocess.Popen(["/usr/bin/pkill","mpv"],stdin=subprocess.PIPE)
        self.playshell = None
        aiy.audio.say('Finished playing')
    
    def translate(self):
        self._assistant.stop_conversation()
        aiy.audio.say('goedemorgen', 'nl-NL')

def main():
    MyAssistant().start()


if __name__ == '__main__':
    main()

