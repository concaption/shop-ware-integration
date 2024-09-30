import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio
import requests
from datetime import datetime
from apps.shopwareapi import ShopWareAPI
from apps.dailyreports import DailyReports
from apps.weeklyreports import WeeklyReports
from utils.utils import send_email
import pytz
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Initialize the scheduler
scheduler = AsyncIOScheduler()

async def generate_daily_shopware_reports():
    logger.info("Starting daily ShopWare report generation")
    api = ShopWareAPI(
        base_url='https://api.shop-ware.com',
    )

    daily_reports = DailyReports(api)
    try:
        daily_html = daily_reports.generate_html_report()
        daily_reports.save_html_report(daily_html)
        send_email("Shop Ware Daily Report", daily_html)
        logger.info("Daily ShopWare report generated and sent successfully")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to generate daily report: {e}", exc_info=True)

async def generate_weekly_shopware_reports():
    logger.info("Starting weekly ShopWare report generation")
    api = ShopWareAPI(
        base_url='https://api.shop-ware.com',
    )

    weekly_reports = WeeklyReports(api)
    try:
        weekly_html = weekly_reports.generate_html_report()
        weekly_reports.save_html_report(weekly_html)
        send_email("Shop Ware Weekly Report", weekly_html, True)
        logger.info("Weekly ShopWare report generated and sent successfully")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to generate weekly report: {e}", exc_info=True)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up the application")
    # EST Zone
    est = pytz.timezone("America/New_York")
    # Schedule daily report
    scheduler.add_job(generate_daily_shopware_reports, CronTrigger(hour=20, minute=0, day_of_week='mon-fri',timezone=est))
    # scheduler.add_job(generate_daily_shopware_reports, CronTrigger())
    logger.info("Scheduled daily report to run at 8 PM EST, Monday to Friday")
    
    # Schedule weekly report
    scheduler.add_job(generate_weekly_shopware_reports, CronTrigger(day_of_week=6, hour=1, minute=0,timezone=est))
    logger.info("Scheduled weekly report to run at 1:00 AM every Sunday")
    
    scheduler.start()
    logger.info("Scheduler started")  

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down the application")
    scheduler.shutdown()
    logger.info("Scheduler shut down")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.utcnow()
    response = await call_next(request)
    process_time = (datetime.utcnow() - start_time).total_seconds() * 1000
    logger.info(f"Request: {request.method} {request.url.path} - Status: {response.status_code} - Process Time: {process_time:.2f}ms")
    return response

@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "ShopWare Reports Scheduler is running"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting the application")
    uvicorn.run(app, host="0.0.0.0", port=8000)
