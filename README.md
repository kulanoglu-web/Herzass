# Pokerherz (Spielgeld)

Walzen-Kartenspiel: fünf Karten, Walzen halten, einmal nachziehen. Gewinne kann man
nehmen oder bei "Risiko" wagen: Das Lauflicht entscheidet zwischen NULL (alles weg)
und MEHR (Gewinn verdoppelt sich, Leiter x1 bis x64).

## Am PC testen
    pip install kivy==2.2.1
    python main.py
    python -m unittest test_logic

## APK bauen
GitHub Actions starten ("APK bauen"). Die fertige APK liegt danach im Branch `apk-build`
(Datei `app.apk`) und als Artifact des Laufs.

## Quellen
- Kartenbilder: Byron Knoll, "vector-playing-cards" (gemeinfrei), Sammlung von
  github.com/notpeter/vector-playing-cards (Public Domain / WTFPL).
- Klänge: selbst synthetisiert (`tools/make_sounds.py`). Hintergrund: `tools/make_bg.py`.
- Kartenbilder neu erzeugen: `python tools/make_cards.py <Ordner mit SVGs> 240`
