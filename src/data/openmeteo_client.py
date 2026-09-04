import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import pandas as pd
import numpy as np
import xarray as xr
from datetime import datetime, timedelta
import logging
import json
import hashlib
from pathlib import Path

logger = logging.getLogger("aether.openmeteo")

class OpenMeteoClient:
    def __init__(self, cache_dir: Path):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.session = requests.Session()
        # Equivalent to retry-requests
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[ 429, 500, 502, 503, 504 ])
        self.session.mount('https://', HTTPAdapter(max_retries=retries))

    def _get_cache_path(self, url, params):
        # Equivalent to requests-cache
        key_str = url + json.dumps(params, sort_keys=True)
        h = hashlib.md5(key_str.encode('utf-8')).hexdigest()
        return self.cache_dir / f"om_cache_{h}.json"

    def fetch(self, url, params):
        cache_path = self._get_cache_path(url, params)
        if cache_path.exists():
            with open(cache_path, 'r') as f:
                return json.load(f)
                
        logger.info(f"Open-Meteo API URL: {url} Params: {params}")
        response = self.session.get(url, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        with open(cache_path, 'w') as f:
            json.dump(data, f)
        return data

def get_open_meteo_client(cache_dir):
    return OpenMeteoClient(cache_dir)
