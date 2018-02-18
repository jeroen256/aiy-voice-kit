#!/home/pi/AIY-voice-kit-python/env/bin/python3
"""Run a recognizer using the Google Assistant Library with button support.

The Google Assistant Library has direct access to the audio API, so this Python
code doesn't need to record audio. Hot word detection "OK, Google" is supported.

The Google Assistant Library can be installed with:
    env/bin/pip install google-assistant-library==0.0.2

It is available for Raspberry Pi 2/3 only; Pi Zero is not supported.
"""


import logging
import sys, os, re
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
        self.mpsyt_stop()

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

    def _on_button_pressed(self):
        # Check if we can start a conversation. 'self._can_start_conversation'
        # is False when either:
        # 1. The assistant library is not yet ready; OR
        # 2. The assistant library is already in a conversation.
        if self._can_start_conversation:
            self._assistant.start_conversation()

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
            if self.mpsyt_has_player() and self.mpsyt_pause_level == 0:
                self.mpsyt_pause(1) # auto pause player
            status_ui.status('listening')
        elif event.type == EventType.ON_END_OF_UTTERANCE:
            status_ui.status('thinking')

        elif event.type == EventType.ON_CONVERSATION_TURN_FINISHED:
            status_ui.status('ready')
            self._can_start_conversation = True
            if self.mpsyt_has_player() and self.mpsyt_pause_level == 1:
                self.mpsyt_pause(0) # auto resume player   

        elif event.type == EventType.ON_ASSISTANT_ERROR and event.args and event.args['is_fatal']:
            self.mpsyt_stop()
            sys.exit(1)

        elif event.type == EventType.ON_RECOGNIZING_SPEECH_FINISHED and event.args:
            print('You said:', event.args['text'])
            text = event.args['text'].lower()
            words = text.split(" ")
            first = text.split(" ")[0]
            if text=='continue' or text=='play':
                self._assistant.stop_conversation()
                self.mpsyt_pause(0)
            if text=='pause':
                self._assistant.stop_conversation()
                self.mpsyt_pause(2)
            elif first=='play': self.mpsyt_play(text)
            elif text=='stop': 
                self._assistant.stop_conversation()
                self.mpsyt_stop()
            elif "volume" in text: self.volume(words)
            elif text == 'ip address': self.say_ip()                 
            elif text == 'shut down' or text=='power off': self.power_off_pi()                 
            elif text == 'restart' or text=='reboot': self.reboot_pi()                
            elif text == 'quit': self.quit()                
            elif text == 'speak dutch': self.translate()

    def mpsyt_volume(self, change: int):
        if change > 0: 
            for x in range(0, change, 2): os.system('screen -X stuff "0"')
            aiy.audio.say('music volume up {} percent'.format(change))
        if change < 0: 
            for x in range(0, change, -2): os.system('screen -X stuff "9"')
            aiy.audio.say('music volume down {} percent'.format(-1 * change))

    #def volume(self, words: List[str]): python 3.5
    def volume(self, words: list):
        self._assistant.stop_conversation()
        percent = self.get_int(words)
        if 'music' in words: # change music volume
            if 'up' in words:
                if 'little' in words: self.mpsyt_volume(5)
                elif 'lot' in words: self.mpsyt_volume(20)
                elif percent == None or percent == 0: self.mpsyt_volume(10)
                else: self.mpsyt_volume(percent)
            elif 'down' in words:
                if 'little' in words: self.mpsyt_volume(-5)
                elif 'lot' in words: self.mpsyt_volume(-20)
                elif percent == None or percent == 0: self.mpsyt_volume(-10)
                else: self.mpsyt_volume(-1 * percent)
        else: # set master volume
            if percent == None: aiy.audio.say("Could not hear what percentage to set the volume to!")
            else:
                subprocess.call('amixer set Master {}%'.format(percent), shell=True)
                aiy.audio.say("Volume to {} percent.".format(percent))

    def get_int(self, words: list) -> int:
        r = None
        try:
            for word in words:
                t = re.sub('[^0-9]','', word) # remove for example % sign
                if t != '':
                    r = int(t)
                    return r
        except: pass
        return r
    # uses: https://github.com/mps-youtube/mps-youtube
    #
    # setup:
    # /home/pi/AIY-voice-kit-python/env/bin/python3 -m pip install mps-youtube
    # /home/pi/AIY-voice-kit-python/env/bin/python3 -m pip install youtube-dl
    # sudo apt update; sudo apt upgrade; sudo apt install mpv
    # run /home/pi/AIY-voice-kit-python/env/bin/mpsyt and configure mpv as default player
    # sudo apt install screen
    #
    # error? sudo dpkg-reconfigure locales (install locale en_US.UTF-8 and set as default, check with locale -a)
    def mpsyt_play(self, text):
        self._assistant.stop_conversation()
        track = text.replace("play","")
        #os.system('export LC_ALL=C')#https://askubuntu.com/questions/205378/unsupported-locale-setting-fault-by-command-not-found
        os.putenv('LC_ALL', 'C')
        self.mpsyt_stop()
        #https://serverfault.com/questions/178457/can-i-send-some-text-to-the-stdin-of-an-active-process-running-in-a-screen-sessi
        os.system('screen -d -m /home/pi/AIY-voice-kit-python/env/bin/mpsyt')
        os.system('screen -X stuff "/' + track + '\n1\n"')
        aiy.audio.say('One moment, Playing' + track)
    def mpsyt_has_player(self) -> bool:
        #https://stackoverflow.com/questions/4760215/running-shell-command-from-python-and-capturing-the-output
        # ps aux | grep -i [m]pv
        #t = subprocess.run('ps aux | grep -i [m]pv', shell=True, stdout=subprocess.PIPE).stdout.decode('utf-8') # requires python 3.5
        try:
            t = subprocess.check_output(['ps aux | grep -i [m]pv'], shell=True).decode('utf-8')
        except subprocess.CalledProcessError:
            t = '' # returned non-zero exit status 1 just means that nothing was found by grep
        #print('mpsyt_has_player:', t, ', mpsyt_pauzed_auto: ', self.mpsyt_pauzed_auto, ', mpsyt_pauzed_user: ', self.mpsyt_pauzed_user)
        if t == '': return False
        else: return True
    mpsyt_pause_level = 0 # 0: not pauzed, 1: auto pauzed, 2: pauzed by user
    def mpsyt_pause(self, level: int):
        if (self.mpsyt_pause_level == 0 and level > 0) or (self.mpsyt_pause_level > 0 and level == 0):
            os.system('screen -X stuff " "')
        self.mpsyt_pause_level = level
    def mpsyt_stop(self):
        self.mpsyt_pause_level = 0
        os.system('pkill screen') # os.system('pkill mpsyt') os.system('pkill mpv')
    
    def say_ip(self):
        self._assistant.stop_conversation()
        ip_address = subprocess.check_output("hostname -I | cut -d' ' -f1", shell=True)
        aiy.audio.say('My IP address is %s' % ip_address.decode('utf-8'))

    def power_off_pi(self):
        self._assistant.stop_conversation()
        aiy.audio.say('shutting down')
        subprocess.call('sudo shutdown now', shell=True)

    def reboot_pi(self):
        self._assistant.stop_conversation()
        aiy.audio.say('See you in a bit!')
        subprocess.call('sudo reboot', shell=True)

    def quit(self):
        self._assistant.stop_conversation()
        self.mpsyt_stop()
        aiy.audio.say('Quitting assistant application')
        sys.exit()

    def translate(self):
        self._assistant.stop_conversation()
        self._assistant.stop_conversation()
        aiy.audio.say('goedemorgen', 'nl-NL')

def main(): MyAssistant().start()
if __name__ == '__main__':
    main()
