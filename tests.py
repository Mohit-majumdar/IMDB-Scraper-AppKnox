import unittest
from unittest.mock import patch, MagicMock
import asyncio
from scrapping import ScrapingData


class TestScrapingData(unittest.TestCase):
    def setUp(self):
        self.scraper = ScrapingData("action", "genres")

    @patch("scrapping.webdriver.Chrome")
    def test_create_url(self, mock_chrome):
        # Mock the Chrome WebDriver
        mock_chrome.return_value.page_source = "<html><head></head><body></body></html>"

        self.scraper._create_url()

        # Run the _create_url method in an event loop
        # Assert the URL is correctly constructed
        self.assertEqual(
            self.scraper.url, "https://www.imdb.com/search/title/?genres=action"
        )

    @patch("scrapping.webdriver.Chrome")
    @patch("scrapping.WebDriverWait")
    @patch("scrapping.EC")
    def test_get_paginated_data(self, mock_ec, mock_wait, mock_chrome):
        mock_chrome.return_value.page_source = "<html><head></head><body></body></html>"
        mock_wait.return_value.until.return_value = MagicMock()
        mock_ec.element_to_be_clickable.return_value = MagicMock()

        async def test_coroutine():
            await self.scraper._get_paginated_data(self.scraper.url)

        asyncio.run(test_coroutine())

        mock_chrome.return_value.get.assert_called_once_with(self.scraper.url)

    @patch("scrapping.ScrapingData._get_paginated_data")
    @patch("scrapping.ScrapingData.extract_parent")
    def test_get_data_from_imdb(self, mock_extract_parent, mock_get_paginated_data):
        # Mock the _get_paginated_data method to return a dummy response
        mock_get_paginated_data.return_value = "<html><body></body></html>"

        async def test_coroutine():
            # Run the get_data_from_imdb method
            await self.scraper.get_data_from_imdb()

        asyncio.run(test_coroutine())
        # Assert that extract_parent was called with the expected argument
        mock_extract_parent.assert_called_once_with("<html><body></body></html>")


if __name__ == "__main__":
    unittest.main()
