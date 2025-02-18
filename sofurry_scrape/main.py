import logging
import logging.config
import argparse
import sys
import asyncio
import logging_tree
import actorio

from sofurry_scrape import utils
from sofurry_scrape.commands import single_user_scrape

def start():
    '''
    cli entry point
    just creates main and runs it
    '''
    m = Main()
    asyncio.run(m.run(), debug=False)


class Main():

    def __init__(self):

        # DON'T CREATE THIS NOW
        # you have to create it once the event loop is running (aka asyncio.run() gets called with the `run` method below)
        # or else you get "got Future <Future pending> attached to a different loop" errors
        self.stop_event = None


    async def run(self):

        self.stop_event = asyncio.Event()

        parser = argparse.ArgumentParser(
            description="utilities for scraping sofurry.com",
            epilog="Copyright 2025-02-17 - Mark Grandi",
            fromfile_prefix_chars='@')

        parser.add_argument("--verbose",
            action="store_true",
            help="increase logging verbosity")

        # ScrapeUsers command
        subparsers = parser.add_subparsers()
        single_user_scrape.SingleUserScrape.create_subparser_command(subparsers)



        try:


            parsed_args = parser.parse_args()

            lg_handler = logging.StreamHandler(sys.stdout)
            lg_formatter = utils.ArrowLoggingFormatter("%(asctime)s %(name)-40s %(levelname)-8s: %(message)s")
            lg_handler.setFormatter(lg_formatter)

            root_logger = logging.getLogger()
            root_logger.addHandler(lg_handler)
            if parsed_args.verbose:
                root_logger.setLevel("DEBUG")
            else:
                root_logger.setLevel("INFO")

            hpack_logger = logging.getLogger("hpack")
            hpack_logger.setLevel("WARNING")

            httpcore_logger = logging.getLogger("httpcore")
            httpcore_logger.setLevel("WARNING")

            httpx_logger = logging.getLogger("httpx")
            httpx_logger.setLevel("WARNING")

            logging.captureWarnings(True) # capture warnings with the logging infrastructure

            root_logger.info("starting")

            root_logger.debug("Parsed arguments: %s", parsed_args)
            root_logger.debug("Logger hierarchy:\n%s", logging_tree.format.build_description(node=None))

            # register Ctrl+C/D/whatever signal
            def _please_stop_loop_func():
                root_logger.info("setting stop event: %s", self.stop_event)

                # this is complex now because it wasn't working before
                # see https://stackoverflow.com/questions/48836285/python-asyncio-event-wait-not-responding-to-event-set
                asyncio.get_running_loop().call_soon_threadsafe(self.stop_event.set)

            utils.register_ctrl_c_signal_handler(_please_stop_loop_func)

            # run the function associated with each sub command
            if "func_to_run" in parsed_args:
                await parsed_args.func_to_run(parsed_args, self.stop_event)

                # await to let aiohttp close its connection
                await asyncio.sleep(0.5)

            else:
                root_logger.info("no subcommand specified!")
                parser.print_help()
                sys.exit(0)

            root_logger.info("Done!")
        except Exception as e:
            root_logger.exception("Something went wrong!")
            sys.exit(1)

