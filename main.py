import os
import requests
from apps.shopwareapi import ShopWareAPI
from apps.dailyreports import DailyReports
from apps.weeklyreports import WeeklyReports
from utils.utils import send_email

if __name__ == "__main__":
    api = ShopWareAPI(
        base_url='https://api.shop-ware.com',
    )

    daily_reports = DailyReports(api)
    # weekly_reports = WeeklyReports(api)
    try:
        daily_html = daily_reports.generate_html_report()
        daily_reports.save_html_report(daily_html)
        # send_email("Shop Ware Daily Report",daily_html)
        # weekly_html = weekly_reports.generate_html_report()
        # weekly_reports.save_html_report(weekly_html)
        # send_email("Shop Ware Weekly Report",weekly_html,True)
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
