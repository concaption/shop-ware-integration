from celery.schedules import crontab

beat_schedule = {
    'generate-shopware-reports-daily': {
        'task': 'main.generate_daily_shopware_reports',
        'schedule': crontab(),  # Run daily at midnight
    },
    'generate-shopware-reports-weekly': {
        'task': 'main.generate_weekly_shopware_reports',
        'schedule': crontab(day_of_week=0, hour=1, minute=0),  # Run weekly on Sunday at 1:00 AM
    },
}

broker_url = 'redis://localhost:6379/0'
result_backend = 'redis://localhost:6379/0'