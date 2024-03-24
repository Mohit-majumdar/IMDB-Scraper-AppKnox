import asyncio
import sys
import pandas as pd
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import bs4
from aiohttp import ClientSession
import logging


logger = logging.getLogger(__name__)


class ScrapingData:
    def __init__(self, search_string, search_type="genres") -> None:
        self._type = search_type
        self._search_string = search_string
        # defining requests header for resolve 403 error
        self._header = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        self._url = "https://www.imdb.com"

        self._create_url()
        self._listmap = {
            "Title": [],
            "Release Year": [],
            "IMDB Rating": [],
            "Directors": [],
            "Cast": [],
            "Plot Summary": [],
        }

        # storing all CSS selectors in one place for reuse
        self._selector_map = {
            "load_more": "button.ipc-see-more__button",
            "genres": {"a_key": "a.ipc-title-link-wrapper"},
            "keyword": {"a_key": "a.ipc-metadata-list-summary-item__t"},
        }

    def _create_url(self):
        if self._type == "genres":
            self.url = self._url + f"/search/title/?genres={self._search_string}"
        else:
            self.url = self._url + f"/find/?q={self._search_string}"

    async def _get_paginated_data(self, url):
        """use selenium webdriver for get paginated data"""
        chrome_options = Options()
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument(f"user-agent={self._header.get('User-Agent')}")

        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=chrome_options
        )
        try:
            selector = self._selector_map.get("load_more", "")
            driver.get(url)
            wait = WebDriverWait(driver, 15)
            el = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))

            for _ in range(5):
                try:
                    driver.execute_script("arguments[0].click()", el)
                    el = wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    await asyncio.sleep(5)
                except Exception as E:
                    logger.warning(f"unable to get element {E}")
                    el = driver.find_element(By.CSS_SELECTOR, selector)
                    continue

            soup = driver.page_source
            return soup
        except Exception as E:
            logger.error("got error during get data from chrome error : %s",E)
            print(
                f"\nSorry, seems like we broke the imdb server or you have entered wrong {self._type}, Please Try again after 5 minute"
            )
            sys.exit(1)
        finally:
            driver.quit()

    async def get_data_from_imdb(self):
        """driver method which call all other methods"""
        res = await self._get_paginated_data(self.url)
        await self.extract_parent(res)

    async def _fetch(self, url):
        """call all requests to internet"""
        async with ClientSession() as session:
            try:
                async with session.get(url, headers=self._header) as res:
                    if res.status != 200:
                        logger.info(
                            f"Not able to get data for url:{url}, status code:{res.status}"
                        )
                        return None
                    return await res.text()
            except Exception as e:
                logger.error(f"unable to fetch {url} due to {e}")

    async def _create_soup(self, content):
        if not content:
            return None
        soup = bs4.BeautifulSoup(content, "html.parser")
        return soup

    async def _get_cast(self, soup):
        """return - movie cast in string formate"""
        cast_list = [
            i.get_text()
            for i in soup.find_all("a", {"data-testid": "title-cast-item__actor"})
        ]
        cast = ",".join(cast_list)
        return cast

    async def _get_summary(self, soup):
        summary = soup.find("span", {"data-testid": "plot-xl"})
        if not summary:
            summary = soup.find("span", {"data-testid": "plot"})
        if summary:
            return summary.text
        return None

    async def _create_out_file(self) -> None:
        """create csv file as output"""
        df = pd.DataFrame(self._listmap)
        df.to_csv(f"out/{self._search_string}.csv", index=False)

    async def extract_parent(self, content) -> None:
        """extract top level url for child detailed view"""
        try:
            soup = await self._create_soup(content)
            title_list = soup.select("li.ipc-metadata-list-summary-item")
            _list = []
            for li in title_list:
                selector = self._selector_map.get(self._type, {}).get("a_key")
                link = li.select_one(selector).get("href")
                _list.append(link)
            tasks = [self.extract_childs(title) for title in _list]
            await asyncio.gather(*tasks)
            await self._create_out_file()
            print()
            print(f"Congrats!!! your file is ready out/{self._search_string}.csv")
            sys.exit()
        except Exception as e:
            tb = sys.exc_info()[-1]
            logger.error(
                "got some error at line: %s and Error: %s",
                tb.tb_lineno,
                e,
                exc_info=sys.exc_info(),
            )
            print("sorry we run into some error please try again")
            sys.exit(1)

    async def _get_director(self, soup) -> str | None:
        director = soup.select("a[href*='tt_ov_dr']")
        if not director:
            director = soup.select('a[href*="tt_ov_wr"]:not([href*="tt_ov_wr_"])')

        if not director:
            return None
        director = [dr.text for dr in director]
        director = list(set(director))
        director = ",".join(director)
        return director

    async def extract_childs(self, child_url) -> None:
        """extract all data from node"""
        try:
            res = await self._fetch(f"{self._url}{child_url}")
            if not res:
                return
            soup = await self._create_soup(res)
            movie_title = soup.select_one("span.hero__primary-text").get_text()
            movie_summary = await self._get_summary(soup)
            movie_cast = await self._get_cast(soup)
            movie_release = (
                soup.select_one("a[href*='releaseinfo']").text
                if soup.select_one("a[href*='releaseinfo']")
                else None
            )
            movie_rating = (
                soup.find(
                    "div", {"data-testid": "hero-rating-bar__aggregate-rating__score"}
                ).span.text
                if soup.find(
                    "div", {"data-testid": "hero-rating-bar__aggregate-rating__score"}
                )
                else None
            )
            movie_director = await self._get_director(soup)

            # writing all data in dict for create file
            self._listmap.get("Title").append(movie_title)
            self._listmap.get("Cast").append(movie_cast)
            self._listmap.get("Directors").append(movie_director)
            self._listmap.get("Plot Summary").append(movie_summary)
            self._listmap.get("Release Year").append(movie_release)
            self._listmap.get("IMDB Rating").append(movie_rating)
        except Exception as e:
            tb = sys.exc_info()[-1]
            logger.error(
                "got some error at line: %s and Error: %s",
                tb.tb_lineno,
                e,
                exc_info=sys.exc_info(),
            )
