# Hertel Grillgenuss Standortsuche – Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/v/release/DHansel91/hertel-grillgenuss)](https://github.com/DHansel91/hertel-grillgenuss/releases)
[![Validate](https://img.shields.io/github/actions/workflow/status/DHansel91/hertel-grillgenuss/validate.yml?branch=main&label=validate)](https://github.com/DHansel91/hertel-grillgenuss/actions/workflows/validate.yml)

Eine Home Assistant HACS-Integration, die die Standortsuche von [Hertel Grillgenuss](https://hertel-grillgenuss.de) abfragt und als Sensor bereitstellt.

## Features

- Fragt die Standorte per **POST-Request** ab
- Konfigurierbare **Latitude / Longitude**
- Optionaler **PLZ-Filter** (nur Standorte einer bestimmten Postleitzahl)
- Konfigurierbares **Aktualisierungsintervall**
- Alle gefundenen Standorte als Sensor-Attribute (Name, Adresse, PLZ, Tag, Uhrzeit, Entfernung, Koordinaten)

## Installation via HACS

1. HACS öffnen → *Integrationen* → Drei-Punkte-Menü → *Benutzerdefinierte Repositories*
2. Repository-URL eintragen: `https://github.com/DHansel91/hertel-grillgenuss`
3. Typ: **Integration** → Hinzufügen
4. Integration suchen und installieren
5. Home Assistant neu starten

## Einrichtung

1. *Einstellungen* → *Geräte & Dienste* → *Integration hinzufügen*
2. „Hertel Grillgenuss" suchen
3. Koordinaten eintragen (Breitengrad / Längengrad)
4. Optional: PLZ-Filter angeben

## Sensor

| Attribut | Beschreibung |
|---|---|
| `state` | Anzahl der gefundenen Standorte |
| `locations` | Liste aller Standorte mit Details |
| `search_latitude` | Verwendeter Breitengrad |
| `search_longitude` | Verwendeter Längengrad |
| `search_zipcode` | PLZ-Filter (falls gesetzt) |

### Beispiel: Lovelace-Karte

```yaml
type: markdown
title: Hertel Grillgenuss Standorte
content: >
  {% set locs = state_attr('sensor.hertel_grillgenuss_standorte', 'locations') %}
  {% for loc in locs %}
  **{{ loc.name }}**
  {{ loc.address }} {{ loc.zipcode }} {{ loc.city }}
  🗓 {{ loc.day }} ⏰ {{ loc.time }}
  📍 {{ loc.distance }}
  ---
  {% endfor %}
```

### Beispiel: Automation (neue Standorte > 0)

```yaml
trigger:
  - platform: numeric_state
    entity_id: sensor.hertel_grillgenuss_standorte
    above: 0
action:
  - service: notify.mobile_app
    data:
      message: "{{ states('sensor.hertel_grillgenuss_standorte') }} Hertel-Standorte in deiner Nähe!"
```

## Technische Details

Die Integration sendet einen **HTTP POST** an:
```
https://hertel-grillgenuss.de/standortsuche?latitude=...&longitude=...&searchopt=All
```

Mit dem Form-Body:
```
latitude=49.6744&longitude=12.1489&searchopt=All[&zipcode=95XXX]
```

Die zurückgegebene HTML-Seite wird mit **BeautifulSoup** geparst. Ausgewertet werden
die `div.locationshape`-Elemente inkl. ihrer `data-*`-Attribute (Koordinaten, PLZ,
Stadt, Tag, Uhrzeit, Entfernung). Die Ergebnisse werden nach Wochentag (Mo→So) und
anschließend nach Entfernung sortiert.

## Troubleshooting

- **Keine Standorte gefunden**: Eventuell hat die Website ihr Markup geändert
  (es werden keine `.locationshape`-Elemente mehr gefunden) – dann muss `api.py`
  angepasst werden. Auch ein zu enger PLZ-Filter kann die Ursache sein.
- **Verbindungsfehler**: Prüfe die HA-Logs unter *Einstellungen → System → Protokolle*
- **Debug-Logging aktivieren**:
  ```yaml
  logger:
    logs:
      custom_components.hertel_grillgenuss: debug
  ```

## Icon / Logo

Das Entity-Icon (`mdi:food-drumstick`) wird über `icons.json` gesetzt. Für ein eigenes
**Integrations-Logo** in der Integrationsübersicht siehe Abschnitt „Icons ändern" in der
übergeordneten Repo-Dokumentation (Brands-Repository von Home Assistant).
