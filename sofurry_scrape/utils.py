import signal
import logging
import pathlib
import json

import yarl
import arrow
import attr

logger = logging.getLogger(__name__)


def register_ctrl_c_signal_handler(func_to_run):

    def inner_ctrl_c_signal_handler(sig, frame):

        logger.info("SIGINT caught!")
        func_to_run()

    signal.signal(signal.SIGINT, inner_ctrl_c_signal_handler)
    signal.signal(signal.SIGTERM, inner_ctrl_c_signal_handler)

class ArrowLoggingFormatter(logging.Formatter):
    ''' logging.Formatter subclass that uses arrow, that formats the timestamp
    to the local timezone (but its in ISO format)
    '''

    def formatTime(self, record, datefmt=None):
        return arrow.get("{}".format(record.created), "X").to("local").isoformat()

@attr.define
class ProfileFolderCollection:
    username:str
    uid:str
    root_dir:pathlib.Path
    profile_json:pathlib.Path
    stories_dir:pathlib.Path
    # artwork_dir:pathlib.Path
    # music_dir:pathlib.Path
    # photos_dir:pathlib.Path
    # journals_dir:pathlib.Path
    # characters_dir:pathlib.Path

def ensure_link_is_https(maybe_bad_link) -> str:
    '''toumal why do you do this to me
    the links returned in the api responses are http which doesn't work with http/2 which for some reason is required
    so if i don't convert these to https , it won't download
    '''

    url = yarl.URL(maybe_bad_link)
    https_url = url.with_scheme("https")
    return str(https_url)


def make_safe_filename(s):
    def safe_char(c):
        if c.isalnum():
            return c
        else:
            return "_"
    return "".join(safe_char(c) for c in s).rstrip("_")

def escape_and_parse_json_omg(maybe_naughty_json_str:str) -> dict:
    '''i swear toumal i will slap you with a fish

    newlines are not escaped in json responses, from what i've seen in user profile json
    '''

    escaped_json = maybe_naughty_json_str.replace("\n", "\\n")

    json_dict = json.loads(escaped_json)
    return json_dict

def create_necessary_output_directories(root_path, username:str, uid:str ) -> ProfileFolderCollection:

    root_dir_for_user = root_path / f"{username}_[{uid}]"


    if not root_path.exists():
        root_path.mkdir(parents=True)
        logger.info("creating output directory `%s`", root_path)

    if not root_dir_for_user.exists():
        root_dir_for_user.mkdir(parents=True)

    profile_json = root_dir_for_user / "profile.json"

    stories_dir = root_dir_for_user / "stories"
    stories_dir.mkdir(exist_ok=True)


    return ProfileFolderCollection(
        username=username,
        uid=uid,
        root_dir = root_dir_for_user,
        profile_json = profile_json,
        stories_dir = stories_dir)


def get_headers():

    headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": "https://www.sofurry.com",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Sec-GPC": "1",
    "Priority": "u=0, i",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache"}

    return headers

def get_login_post_data(username:str,password:str):

    payload = {
        "YII_CSRF_TOKEN": "",
        "yt0": "Login",
        "LoginForm[sfLoginUsername]": username,
        "LoginForm[sfLoginPassword]": password}

    return payload

