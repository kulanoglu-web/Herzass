"""Startpunkt der App. Faengt Fehler ab und zeigt sie auf dem Bildschirm an,
damit die App nicht wortlos verschwindet."""
import traceback


def _fehler_text(exc):
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))


def _fehler_widget(text):
    from kivy.uix.label import Label
    from kivy.uix.scrollview import ScrollView
    lab = Label(text="FEHLER - bitte Screenshot senden\n\n" + text, font_size="12sp",
                size_hint_y=None, halign="left", valign="top", color=(1, 1, 1, 1))
    lab.bind(width=lambda *_: setattr(lab, "text_size", (lab.width, None)))
    lab.bind(texture_size=lambda *_: setattr(lab, "height", lab.texture_size[1]))
    sv = ScrollView()
    sv.add_widget(lab)
    return sv


def _fehler_app(text):
    from kivy.app import App

    class FehlerApp(App):
        def build(self):
            return _fehler_widget(text)

    FehlerApp().run()


def _laufzeitfehler_anzeigen():
    """Fehler waehrend des Spiels als Fenster einblenden, App laeuft weiter."""
    from kivy.base import ExceptionHandler, ExceptionManager
    from kivy.clock import Clock

    class Anzeige(ExceptionHandler):
        gezeigt = False

        def handle_exception(self, inst):
            if not Anzeige.gezeigt:
                Anzeige.gezeigt = True
                text = _fehler_text(inst)

                def zeigen(dt):
                    from kivy.uix.popup import Popup
                    Popup(title="Fehler", content=_fehler_widget(text),
                          size_hint=(0.95, 0.9)).open()
                Clock.schedule_once(zeigen, 0)
            return ExceptionManager.PASS

    ExceptionManager.add_handler(Anzeige())


def start():
    try:
        _laufzeitfehler_anzeigen()
        import kartenapp
        kartenapp.run()
    except Exception as exc:  # noqa: BLE001
        text = _fehler_text(exc)
        print(text)
        try:
            _fehler_app(text)
        except Exception:  # noqa: BLE001
            raise exc


start()
