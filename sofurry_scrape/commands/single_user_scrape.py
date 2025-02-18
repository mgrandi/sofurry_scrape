import argparse
import logging
import json
import asyncio

import httpx



from sofurry_scrape.argparse_utils import isFolderType, isFileType
from sofurry_scrape import utils

logger = logging.getLogger(__name__)


class SingleUserScrape:

    @staticmethod
    def create_subparser_command(argparse_subparser):
        '''
        populate the argparse arguments for this module

        @param argparse_subparser - the object returned by ArgumentParser.add_subparsers()
        that we call add_parser() on to add arguments and such

        '''

        parser = argparse_subparser.add_parser("single_user_scrape")

        parser.add_argument(
            "--username-to-scrape",
            dest="username_to_scrape",
            type=str,
            help="the username of the sofurry user whom you want to scrape")

        parser.add_argument(
            "--output-path",
            dest="output_path",
            type=isFolderType(False),
            help="the output path where you want to output the data to")


        parser.add_argument(
            "--credentials-json-file",
            dest="credentials_json_file",
            type=isFileType(True),
            help="json file that holds the credentials, two keys, 'username' and 'password'")


        single_user_scrape_obj = SingleUserScrape()

        # set the function that is called when this command is used
        parser.set_defaults(func_to_run=single_user_scrape_obj.run)


    def __init__(self):

        self.config:model.Settings = None
        self.stop_event:asyncio.Event = None
        self.root_actor = None



    async def get_user_info(self, client:httpx.AsyncClient, username:str) -> dict:

        logger.debug("making http call for user info for username `%s`", username)
        resp = await client.get(f"https://api2.sofurry.com/std/getUserProfile?username={username}&format=json")

        resp.raise_for_status()

        unescaped_json:str = resp.text
        escaped_json_dict:dict = utils.escape_and_parse_json_omg(unescaped_json)

        return escaped_json_dict


    def write_profile_json(self, user_info:dict, folder_collection:utils.ProfileFolderCollection):

        logger.debug("writing profile json to `%s`", folder_collection.profile_json)
        with open(folder_collection.profile_json, "w", encoding="utf-8") as f:
            json.dump(user_info, f)


    async def scrape_stories_handle_paginated_api(self, url:str, params:dict, httpx_client:httpx.AsyncClient, uid:str, folder_collection:utils.ProfileFolderCollection, stop_event:asyncio.Event):


        ## need to cache since pagination is broken
        submission_id_cache = set()
        page_number = 1

        # add the page number
        params_updated = params.copy()
        params_updated.update({"stories-page": f"{page_number}"})

        # whether we have seen a duplicate page because when we go past the available pages it
        # just returns the first page again
        should_stop_while_loop = False
        while not should_stop_while_loop:

            if stop_event.is_set():
                logger.info("stopping scrape stories early, stop event is set!")
                return

            logger.info("on page `%s`", page_number)


            page_result_response = await httpx_client.get(url, params=params_updated)
            logger.debug("result from story api page `%s` was `%s`", page_number, page_result_response)
            page_result_response.raise_for_status()

            story_json_sanitized = utils.escape_and_parse_json_omg(page_result_response.text)

            item_collection = story_json_sanitized["items"]



            for iter_item in story_json_sanitized["items"]:
                if stop_event.is_set():
                    logger.info("stopping scrape stories early, stop event is set!")
                    should_stop_while_loop = True
                    return

                iter_submission_id = iter_item["id"]

                if iter_submission_id in submission_id_cache:
                    # break out of loop, we already have this page
                    # this will get called for every item in the page but whatever its fine,quick and dirty
                    logger.info("breaking out of loop, looks like we processed this page already")
                    should_stop_while_loop = True
                    # break out of for loop, and should_stop_while_loop should break out of the while loop
                    break

                # keep going

                logger.info("processing story submission `%s` - `%s`", iter_submission_id, iter_item["title"])
                await self.handle_story_iter_submission_json(iter_item, httpx_client, folder_collection)
                submission_id_cache.add(iter_submission_id)


            # increment page number
            page_number += 1


    async def scrape_stories(self, httpx_client:httpx.AsyncClient, uid:str, folder_collection:utils.ProfileFolderCollection, stop_event:asyncio.Event):

        story_api_url_template = "https://www.sofurry.com/browse/user/stories"


        #params_html = {"by": f"{uid}", "stories-page": f"{page_number}"}


        # get regular submissions

        # pass in the params without the page number which will be added in
        params_json = {"by": f"{uid}", "format": "json"}
        await self.scrape_stories_handle_paginated_api(
            url=story_api_url_template,
            params=params_json,
            httpx_client=httpx_client,
            uid=uid,
            folder_collection=folder_collection,
            stop_event=stop_event)

        logger.info("stories without a folder done")

        # now get the folders




    async def handle_story_iter_submission_json(self, submission_json:dict, httpx_client:httpx.AsyncClient, folder_collection:utils.ProfileFolderCollection):

        # make folder under stories folder
        safe_submission_name = utils.make_safe_filename(submission_json["title"])
        submission_id = submission_json["id"]

        iter_submission_folder = folder_collection.stories_dir / f"{safe_submission_name} [{submission_id}]"
        logger.debug("submission `%s`: creating submission folder at `%s`", submission_id, iter_submission_folder)
        iter_submission_folder.mkdir(exist_ok=True)


        # write profile json
        profile_json_path = iter_submission_folder / f"info.json"
        logger.debug("submission `%s`: creating submission json at `%s`", submission_id, profile_json_path)

        with open(profile_json_path, "w", encoding="utf-8") as f:
            json.dump(submission_json, f)

        # get thumbnail
        thumbnail_path = iter_submission_folder / "thumbnail.png"
        thumbnail_response = await httpx_client.get(submission_json["thumbnail"])
        logger.debug("submission `%s`, thumbnail response: `%s`", submission_id, thumbnail_response)
        thumbnail_response.raise_for_status()
        logger.debug("submission `%s`, writing thumbnail to `%s`", submission_id, thumbnail_path)
        with open(thumbnail_path, "wb") as f:
            f.write(thumbnail_response.read())

        # download html
        html_path = iter_submission_folder / f"{safe_submission_name} [{submission_id}].html"

        fixed_link = utils.ensure_link_is_https(submission_json["link"])
        html_response = await httpx_client.get(fixed_link)
        logger.debug("submission `%s`, html response: `%s`", submission_id, html_response)
        html_response.raise_for_status()
        logger.debug("submission `%s`, writing html to `%s`", submission_id, html_path)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_response.text)

        logger.debug("submission `%s` done")





    async def run(self, parsed_args, stop_event:asyncio.Event):


        # create output directory
        output_path:pathlib.Path = parsed_args.output_path
        user_to_scrape:str = parsed_args.username_to_scrape

        # load credential file
        credential_json = None
        with open(parsed_args.credentials_json_file, "r", encoding="utf-8") as f:
            credential_json = json.load(f)

        logger.info("loaded credential file from `%s`", parsed_args.credentials_json_file)

        logger.info("creating httpx client")


        headers = utils.get_headers()


        login_post_data = utils.get_login_post_data(credential_json["username"], credential_json["password"])

        # it HAS to be http2=True and http1=False or else the sofurry api refuses to work LOL
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, http1=False, http2=True) as httpx_client:

            logger.info("making initial calls to sofurry...")

            # hit the main page to get some headers and cookies
            homepage_resp = await httpx_client.get("https://www.sofurry.com")
            logger.debug("homepage response: `%s`", homepage_resp)
            homepage_resp.raise_for_status()

            login_pg_resp = await httpx_client.get("https://www.sofurry.com/user/login")
            logger.debug("login page get response: `%s`", login_pg_resp)
            login_pg_resp.raise_for_status()

            logger.info("logging in to sofurry...")
            login_post_resp = await httpx_client.post("https://www.sofurry.com/user/login", data=login_post_data)
            logger.debug("login page post response: `%s`", login_post_resp)
            login_post_resp.raise_for_status()
            logger.info("login successful")

            # fetch the user
            user_info = await self.get_user_info(httpx_client, user_to_scrape)

            real_username = user_info["useralias"]
            real_uid = user_info["userID"]

            # create initial directories
            folder_collection:ProfileFolderCollection = utils.create_necessary_output_directories(output_path, real_username, real_uid)

            # write profile json
            self.write_profile_json(user_info, folder_collection)

            # scrape stories
            await self.scrape_stories(httpx_client,real_uid, folder_collection, stop_event)



