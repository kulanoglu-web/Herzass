import os
import platform
import sys

import kivy
from kivy.app import App
from kivy.uix.label import Label


class Test(App):
    def build(self):
        info = "Kivy laeuft!\n\nKivy %s\nPython %s\nCPU %s\nOrdner %s" % (
            kivy.__version__, sys.version.split()[0], platform.machine(),
            os.environ.get("ANDROID_PRIVATE"))
        return Label(text=info, font_size="20sp", halign="center")


Test().run()
