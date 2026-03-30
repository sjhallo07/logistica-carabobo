import os
import sys
url = "https://mcp.supabase.com/mcp?project_ref=picfkguawkzhbdvagcbi/mcp/health"
try:
    import httpx
    resp = httpx.get(url, timeout=10.0)
    print('status_code:', resp.status_code)
    print(resp.text)
except Exception as e:
    try:
        from urllib import request
        with request.urlopen(url, timeout=10) as r:
            print('status_code:', r.status)
            print(r.read().decode('utf-8'))
    except Exception as e2:
        print('error:', e)
        print('fallback error:', e2)
        sys.exit(1)
