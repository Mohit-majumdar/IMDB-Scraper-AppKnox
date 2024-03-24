import logging.config
from pathlib import Path
import asyncio
from scrapping import ScrapingData
import sys
import threading
import time
import random

logging.config.fileConfig("logging.ini")


_NAMEMAP = {"1": "genres", "2": "keyword"}

MESSAGES = ["data loading......."]


async def _read_text_file():
    with open("messages.txt", "r") as f:
        global MESSAGES
        MESSAGES = [line.strip() for line in f.readlines()]


def create_required_folder():
    logs_path = Path(".").absolute() / "logs"
    logs_path.mkdir(exist_ok=True)

    out_folder = Path(".").absolute() / "out"
    out_folder.mkdir(exist_ok=True)


def typing_print(text):
    for character in text:
        sys.stdout.write(character)
        sys.stdout.flush()
        time.sleep(0.05)


def print_loading_message():
    while True:
        message = random.choice(MESSAGES)
        typing_print(message)
        time.sleep(2)
        sys.stdout.write("\r" + " " * len(message))
        sys.stdout.flush()

        # shift cursor to begging of the line
        sys.stdout.write("\r")
        sys.stdout.flush()


def get_input():
    typing_print("Hello There!!! Welcome to IMDB Scraper..")
    print()
    typing_print("what you want to search: \nFor genre Press 1\nFor keyword Press 2")
    print()
    while True:
        movie_type = input("Enter Your Choice: ")
        movie_type = _NAMEMAP.get(movie_type)
        if not movie_type:
            print("You have choose wrong option please choose correct one")
            continue

        movie_name = input(f"Please Enter Your {movie_type}: ")
        return movie_name, movie_type


async def main():
    movie_name, movie_type = get_input()

    scrapper = ScrapingData(movie_name, movie_type)
    await _read_text_file()
    loading_thread.start()

    await scrapper.get_data_from_imdb()

    loading_thread.join()


if __name__ == "__main__":
    create_required_folder()
    loading_thread = threading.Thread(target=print_loading_message)
    loading_thread.daemon = True
    asyncio.run(main())
