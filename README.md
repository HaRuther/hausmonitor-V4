# Hausmonitor 3.1 mit Rissmonitoring

Diese Version behält das bestehende Nivellement-Monitoring und ergänzt ein unabhängiges Modul für Rissmessstellen.

## Rissmonitoring

- Messstellen mit Name, Ort und Beschreibung anlegen
- Je Messstelle beliebig viele Messungen erfassen
- Datum/Uhrzeit, Lufttemperatur, Messwert in mm, Notiz und Foto
- Verlauf des absoluten Messwerts und Änderung gegenüber der ersten Messung
- Vergleich von Rissänderung und Lufttemperatur
- CSV-Export aller Rissmessungen
- Fotos werden unter `data/uploads/cracks/` gespeichert

## Bestehende Installation aktualisieren

Die Datenbank wird beim ersten Start automatisch um die Tabellen `crack_points` und `crack_measurements` erweitert. Bestehende Nivellement-Daten bleiben erhalten.

```bash
cd /root/hausmonitor
docker-compose down
```

Ersetze anschließend die Projektdateien durch den Inhalt dieses Pakets. Die bestehende Datei `.env` und der Ordner `data/` müssen erhalten bleiben. Danach:

```bash
docker-compose up -d --build
docker ps
docker logs --tail=100 hausmonitor-v3
```

App: `http://IP-DES-LXC:8000`

## Backup vor dem Update

```bash
cd /root/hausmonitor
mkdir -p backup-vor-rissmonitoring
cp -a data backup-vor-rissmonitoring/
cp .env backup-vor-rissmonitoring/
```

Alternativ den gesamten Proxmox-LXC sichern.

## Frische Installation

```bash
cp .env.example .env
nano .env
docker-compose up -d --build
```

## Wichtige Backup-Daten

- `data/hausmonitor.db`
- `data/uploads/`
- `.env`

Das Skript `scripts/backup.sh` sichert Datenbank und Uploads. Voraussetzung ist das Paket `sqlite3` auf dem LXC.
