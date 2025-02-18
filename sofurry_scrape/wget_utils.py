import subprocess
import pathlib
import asyncio
import logging

import arrow

# seems to be a good compromise between what is actually needed and viewing pleasure
# i had to disable --page-requistes for this to work i guess? maybe the site is just weird or
# wget's algorithm kinda sucks for choosing what to download / isn't clear
WGET_ACCEPT_REGEX = "//www\\.sofurryfiles\\.com/std/.*|www\\.sofurryfiles\\.com/assets/.*|www\\.sofurry\\.com/static/.*|www\\.sofurry\\.com/std/.*"

logger = logging.getLogger(__name__)

def write_cookie_file(output_file:pathlib.Path, cookiejar_dict:dict):

    logger.debug("writing cookie file to `%s`", output_file)
    with open(output_file, "w", encoding="utf-8") as f:
        #f.write("# Netscape HTTP Cookie File\n")

        for k,v in cookiejar_dict.items():

            f.write(f".sofurry.com\tTRUE\t/\tTRUE\t2147483646\t{k}\t{v}\n")



async def run_command_and_wait(
    binary_to_run:pathlib.Path,
    argument_list:list[str],
    timeout:int,
    acceptable_return_codes:list[int],
    cwd=None) -> str:

    logger.debug("running `%s` process with arguments `%s` and cwd `%s`",
        binary_to_run.name,
        argument_list, cwd)

    process_obj:asyncio.subprocess.Process = await asyncio.create_subprocess_exec(
        binary_to_run,
        *argument_list,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=cwd)

    while True:
        try:
            logger.debug("Waiting for `%s` process to exit...", binary_to_run.name)

            await asyncio.wait_for(
                # wait_for will cancel the task if it times out
                # so wrap the `asyncio.subprocess.Process` object
                # in `shield()` so it doesn't get cancelled
                asyncio.shield(process_obj.wait()),
                timeout=timeout)

            break

        except Exception as e:
            logger.debug("command `%s` timed out, trying again", binary_to_run.name)

    stdout_result = await process_obj.stdout.read()
    stdout_output = stdout_result.decode("utf-8")
    logger.debug("the `%s` process exited: `%s`", binary_to_run.name, process_obj)
    logger.debug("stdout: `%s`", stdout_output)

    if process_obj.returncode not in acceptable_return_codes:

        logger.error("command `%s` with arguments `%s` 's return code of `%s` wasn't in the list of " +
                "acceptable return codes `%s`, stdout: `%s`",
                binary_to_run, argument_list, process_obj.returncode, acceptable_return_codes, stdout_output)
        raise Exception(f"Command `{binary_to_run}` with arguments `{argument_list}` 's return code " +
            f"`{process_obj.returncode}` was not in the list of acceptable return codes: `{acceptable_return_codes}`")

    return stdout_output



def get_wget_args(
    cookie_path:pathlib.Path,
    warc_path:pathlib.Path,
    tempdir:pathlib.Path,
    submission_json:dict,
    url:str) ->list[str]:

    cur_date = arrow.utcnow()

    submission_id = submission_json["id"]
    author_id = submission_json["authorID"]
    author_str = submission_json["author"]


    wget_args =  [
        #"--no-verbose",
        f"--load-cookies={cookie_path}",
        "-e",
        "robots=off",
        "--user-agent",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
        "--span-hosts",
        # disabled, was downloading too much
        #"--page-requisites",
        "--no-check-certificate",
        "--tries",
        "5",
        "--waitretry",
        "5",
        "--warc-tempdir",
        tempdir,
        "--warc-header",
        f"sofurry_submission_id: {submission_id}",
        "--warc-header",
        f"sofurry_author_id: {author_id}",
        "--warc-header",
        f"sofurry_author: {author_str}",
        "--warc-header",
        f"date: {cur_date.isoformat()}",
        "--warc-file",
        warc_path,
        "--recursive",
        "--level",
        "1",
        "--accept-regex",
        WGET_ACCEPT_REGEX,
        url
    ]
    return wget_args