#!/usr/bin/env python

import requests

# Exit with status code >0 on non-200 response
requests.get("http://127.0.0.1:8080/api/health/").raise_for_status()
