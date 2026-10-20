# Kartenwalzen (Spielgeld)

Eigenes Walzen-Kartenspiel: Karten ziehen, Walzen halten, einmal nachziehen,
Gewinn nehmen oder auf der Risikoleiter (x1 bis x64) auf Rot/Schwarz verdoppeln.

## Am PC testen
    pip install kivy==2.3.1
    python main.py
    python -m unittest test_logic

## APK bauen
Variante A (einfach, kostenlos): Ordner in ein GitHub-Repository hochladen,
unter "Actions" den Workflow "APK bauen" starten, danach unter
"Artifacts" die Datei kartenwalzen-apk herunterladen (dauert ca. 20-40 Minuten).

Variante B: Auf Linux/WSL/Colab `pip install buildozer` und
`buildozer android debug` im Projektordner. Die APK liegt dann in `bin/`.
