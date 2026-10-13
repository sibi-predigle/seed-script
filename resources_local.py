"""Maps the bucket URLs found in the source DB to the local `resources/assets/...` paths.

A bot/connection source stored as `https://storage.googleapis.com/dev-precog-bucket-1/resources/connections/...`
only works with `GCP_CLOUD_BUCKET=True`: in local mode the storage layer `open()`s the string as a file path and
fails with `OSError: [Errno 22] Invalid argument`. `resources/assets/<Sample>/<file>` is a path under the precog
repo that works as-is locally, and is the layout the earlier (v2) seed used.

The files behind these paths are bundled in this directory's `resources/` and copied into precog's `resources/`
by seed_client.py. Add a line here when a new source/mapping file is introduced.
"""
BUCKET_URL_PREFIX = "https://storage.googleapis.com/dev-precog-bucket-1/"

# bucket key (URL minus prefix) -> local path
LOCAL_PATHS = {
    "resources/connections/6a60c51eb9fbeb4b73133954/FiservDNA_sample_data.txt": "resources/assets/FiservDNA_sample/FiservDNA_sample_data.txt",
    "resources/connections/6a60c51eb9fbeb4b73133954/adapter/FiservDNA_mapping.xml": "resources/assets/FiservDNA_sample/FiservDNA_mapping.xml",
    "resources/connections/notice-of-transfer-letter-masking/NoticeOfTransfer_sample_data.txt": "resources/assets/NoticeOfTransferLetter/NoticeOfTransfer_sample_data.txt",
    "resources/connections/notice-of-transfer-letter-masking/adapter/mapping.xml": "resources/assets/NoticeOfTransferLetter/mapping.xml",
}


def localize(value):
    """Recursively rewrites mapped bucket URLs in a dict/list/str; everything else passes through."""
    if isinstance(value, str):
        if value.startswith(BUCKET_URL_PREFIX):
            key = value[len(BUCKET_URL_PREFIX):]
            return LOCAL_PATHS.get(key, value)  # unmapped URLs are left alone rather than guessed
        return value
    if isinstance(value, dict):
        return {k: localize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [localize(v) for v in value]
    return value
