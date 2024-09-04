from celery import Celery
import os
import requests
from apps.shopwareapi import ShopWareAPI
from apps.dailyreports import DailyReports
from apps.weeklyreports import WeeklyReports
from utils.utils import send_email
from celery.exceptions import MaxRetriesExceededError

# Initialize Celery app
app = Celery('tasks', broker='redis://localhost:6379/0')

# Load Celery configuration
app.config_from_object('celeryconfig')

@app.task(bind=True, max_retries=3, default_retry_delay=300)  # 5 minutes delay
def generate_daily_shopware_reports(self):
    api = ShopWareAPI(
        base_url='https://api.shop-ware.com',
    )

    daily_reports = DailyReports(api)
    try:
        daily_html = daily_reports.generate_html_report()
        daily_reports.save_html_report(daily_html)
        send_email("Shop Ware Daily Report", daily_html)
    except requests.exceptions.RequestException as e:
        try:
            raise self.retry(exc=e)
        except MaxRetriesExceededError:
            print(f"Failed to generate daily report after 3 retries: {e}")

@app.task(bind=True, max_retries=3, default_retry_delay=600)  # 10 minutes delay
def generate_weekly_shopware_reports(self):
    api = ShopWareAPI(
        base_url='https://api.shop-ware.com',
    )

    weekly_reports = WeeklyReports(api)
    try:
        weekly_html = weekly_reports.generate_html_report()
        weekly_reports.save_html_report(weekly_html)
        send_email("Shop Ware Weekly Report", weekly_html, True)
    except requests.exceptions.RequestException as e:
        try:
            raise self.retry(exc=e)
        except MaxRetriesExceededError:
            print(f"Failed to generate weekly report after 3 retries: {e}")

if __name__ == "__main__":
    generate_daily_shopware_reports.delay()
    generate_weekly_shopware_reports.delay()