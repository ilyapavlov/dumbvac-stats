"""DumbVac's other-players table, rebuilt from Amplitude once a day.

For every level: how many players started it (unique users of Level Started)
and how many wins took how many moves (Level Completed, by its "moves").
Only these counts are published; no user, device or event is.
Needs AMPLITUDE_API_KEY and AMPLITUDE_SECRET_KEY (repository secrets).
"""
import base64
import datetime
import json
import os
import sys
import urllib.parse
import urllib.request

API = "https://amplitude.com/api/2/events/segmentation"
SINCE = "20261101"


def query(event: dict, metric: str) -> dict:
    today = datetime.date.today().strftime("%Y%m%d")
    params = {"e": json.dumps(event), "m": metric, "start": SINCE, "end": today, "i": "30", "limit": "1000"}
    request = urllib.request.Request(API + "?" + urllib.parse.urlencode(params))
    key = os.environ["AMPLITUDE_API_KEY"] + ":" + os.environ["AMPLITUDE_SECRET_KEY"]
    request.add_header("Authorization", "Basic " + base64.b64encode(key.encode()).decode())
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)["data"]


def by_label(data: dict) -> dict:
    """Each group-by value with its count over the whole range."""
    out = {}
    for label, collapsed in zip(data.get("seriesLabels", []), data.get("seriesCollapsed", [])):
        name = label[-1] if isinstance(label, list) else label
        value = collapsed[0]["value"] if collapsed else 0
        out[str(name).strip()] = int(value)
    return out


def main() -> int:
    levels = {}
    started = by_label(query({"event_type": "Level Started", "group_by": [{"type": "event", "value": "level"}]}, "uniques"))
    for level, players in started.items():
        if not level.isdigit():
            continue
        wins = by_label(query({
            "event_type": "Level Completed",
            "filters": [{"subprop_type": "event", "subprop_key": "level", "subprop_op": "is", "subprop_value": [level]}],
            "group_by": [{"type": "event", "value": "moves"}],
        }, "totals"))
        levels[level] = {"players": players, "wins": {m: n for m, n in wins.items() if m.isdigit() and n > 0}}
    table = {"updated": datetime.date.today().isoformat(), "levels": levels}
    with open("ranks.json", "w") as file:
        json.dump(table, file, sort_keys=True)
    print(f"{len(levels)} levels")
    return 0


if __name__ == "__main__":
    sys.exit(main())
