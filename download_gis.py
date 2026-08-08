#!/usr/bin/env python3
"""Download all GIS Report files from ERCOT MIS API."""
import json, time, sys
from pathlib import Path
from urllib.request import urlretrieve, urlopen
from urllib.error import URLError

LIST_URL = "https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=15933"
FETCH_URL = "https://www.ercot.com/misdownload/servlets/mirDownload?mimic_duns=&doclookupId={}"
OUT_DIR = Path("data/raw")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def fetch_list():
    with urlopen(LIST_URL) as r:
        data = json.load(r)
    return [d["Document"] for d in data["ListDocsByRptTypeRes"]["DocumentList"]]

def main():
    print("Fetching document list...")
    docs = fetch_list()
    gis = [d for d in docs if "GIS_Report" in d["FriendlyName"]]
    gis.sort(key=lambda d: d["PublishDate"])
    print(f"Found {len(gis)} GIS reports (Dec 2018 – present)")

    ok = skip = fail = 0
    for d in gis:
        name = d["FriendlyName"] + "." + d["Extension"]
        dest = OUT_DIR / name
        if dest.exists() and dest.stat().st_size > 0:
            print(f"  skip  {name}")
            skip += 1
            continue
        url = FETCH_URL.format(d["DocID"])
        try:
            urlretrieve(url, dest)
            size_kb = dest.stat().st_size // 1024
            print(f"  ok    {name}  ({size_kb} KB)")
            ok += 1
            time.sleep(0.3)  # polite crawl delay
        except Exception as e:
            print(f"  FAIL  {name}: {e}", file=sys.stderr)
            fail += 1

    print(f"\nDone. {ok} downloaded, {skip} already existed, {fail} failed.")

if __name__ == "__main__":
    main()
