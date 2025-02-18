# sofurry_scrape

code and utilities to eventually come together to assist with point in time
or ongoing scraping of sofurry.com

## usage

```plaintext
$ python3 cli.py --help
usage: cli.py [-h] [--verbose] {single_user_scrape} ...

utilities for scraping sofurry.com

positional arguments:
  {single_user_scrape}

options:
  -h, --help            show this help message and exit
  --verbose             increase logging verbosity

Copyright 2025-02-17 - Mark Grandi

```

## commands

### single_user_scrape

a rough and ready script to do a point in time scrape of a single user

currently, as of 2025-02-17, only works for stories

note: `wget-path` is also known as [wget-lua](github.com/ArchiveTeam/wget-lua) , not normal wget.

```plaintext

$ python3 cli.py single_user_scrape --help
usage: cli.py single_user_scrape [-h] --username-to-scrape USERNAME_TO_SCRAPE --output-path OUTPUT_PATH --credentials-json-file CREDENTIALS_JSON_FILE
                                 [--wget-path WGET_PATH]

options:
  -h, --help            show this help message and exit
  --username-to-scrape USERNAME_TO_SCRAPE
                        the username of the sofurry user whom you want to scrape
  --output-path OUTPUT_PATH
                        the output path where you want to output the data to
  --credentials-json-file CREDENTIALS_JSON_FILE
                        json file that holds the credentials, two keys, 'username' and 'password'
  --wget-path WGET_PATH
                        path to the wget-at binary
```