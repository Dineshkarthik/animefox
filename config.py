import os

BASIC_AUTH_USERNAME = os.environ["BASIC_AUTH_USERNAME"]
BASIC_AUTH_PASSWORD = os.environ["BASIC_AUTH_PASSWORD"]
DATABASE_URI = os.environ["DATABASE_URI"]
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"
}
TABLE_NAME = os.environ["TABLE_NAME"]
FROMADDR = os.environ["FROMADDR"]
SMTP_HOST = os.environ["SMTP_HOST"]
BCCADDR = os.environ["BCCADDR"].split(",")
PASSWORD = os.environ["PASSWORD"]
SECURITY_KEY = os.environ["SECURITY_KEY"]
ACTIVE_URL = "https://extendsclass.com/api/json-storage/bin/ccdfbed"
LIST_URL = "https://extendsclass.com/api/json-storage/bin/fcbdaca"
