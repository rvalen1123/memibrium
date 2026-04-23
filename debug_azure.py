import os
from urllib.parse import urlparse

FOUNDRY_BASE = os.environ.get('OPENAI_BASE_URL', '')
print('FOUNDRY_BASE:', FOUNDRY_BASE)
_foundry_parsed = urlparse(FOUNDRY_BASE) if FOUNDRY_BASE else None
_foundry_host = _foundry_parsed.hostname if _foundry_parsed else None
print('_foundry_host:', _foundry_host)
print('bool:', bool(_foundry_host))
if _foundry_host:
    print('endswith:', _foundry_host.endswith('.openai.azure.com'))

_azure_api_key = os.environ.get('AZURE_OPENAI_API_KEY', '')
print('AZURE_OPENAI_API_KEY:', repr(_azure_api_key))
_azure_env_enabled = bool(os.environ.get('AZURE_OPENAI_ENDPOINT')) and bool(_azure_api_key) and _azure_api_key != '***'
print('_azure_env_enabled:', _azure_env_enabled)
print('USE_AZURE would be:', _azure_env_enabled)
