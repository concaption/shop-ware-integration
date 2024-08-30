from datetime import datetime, timedelta
import pandas as pd

class DailyReports:
    def __init__(self, api):
        self.api = api

    def get_next_7_weekdays_appointments(self):
        today = datetime.now().date()
        end_date = today + timedelta(days=13)  # Look ahead 13 days to ensure we get 7 weekdays

        # Get appointments updated in the last 30 days to ensure we have recent data
        updated_after = today - timedelta(days=30)

        appointment_counts = {}
        page = 1
        while True:
            appointments = self.api.get_appointments(updated_after, page=page)

            for appointment in appointments['results']:
                start_at = datetime.fromisoformat(appointment['start_at'].rstrip('Z')).date()

                # Check if the appointment is within our date range and on a weekday
                if today <= start_at <= end_date and start_at.weekday() < 5:
                    appointment_counts[start_at] = appointment_counts.get(start_at, 0) + 1

            # Check if we've processed all pages
            if page >= appointments['total_pages']:
                break
            page += 1

        return self._create_dataframe(today, appointment_counts)

    def _create_dataframe(self, start_date, appointment_counts):
        data = []
        current_date = start_date
        weekdays_count = 0

        while weekdays_count < 7:
            if current_date.weekday() < 5:  # If it's a weekday
                data.append({
                    'Date': current_date.strftime("%Y-%m-%d"),
                    'Day of Week': current_date.strftime("%A"),
                    'Appointment Count': appointment_counts.get(current_date, 0)
                })
                weekdays_count += 1
            current_date += timedelta(days=1)

        return pd.DataFrame(data)

    def generate_html_report(self):
        df = self.get_next_7_weekdays_appointments()

        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Appointments for the Next 7 Weekdays</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                h1 {{
                    color: #2c3e50;
                    text-align: center;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                }}
                th, td {{
                    padding: 12px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }}
                th {{
                    background-color: #2c3e50;
                    color: white;
                }}
                tr:nth-child(even) {{
                    background-color: #f2f2f2;
                }}
            </style>
        </head>
        <body>
            <h1>Appointments for the Next 7 Weekdays</h1>
            {df.to_html(index=False)}
        </body>
        </html>
        """

        return html_content

    def save_html_report(self,html_content, filename='appointment_report.html'):
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"HTML report saved as {filename}")