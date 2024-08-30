import os
import requests
from apps.shopwareapi import ShopWareAPI
from apps.dailyreports import DailyReports

if __name__ == "__main__":
    api = ShopWareAPI(
        base_url='https://api.shop-ware.com',
    )

    daily_reports = DailyReports(api)

    try:
        html = daily_reports.generate_html_report()
        daily_reports.save_html_report(html)

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
