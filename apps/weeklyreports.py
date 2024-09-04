from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import base64
import io
import seaborn as sns


class WeeklyReports:
    def __init__(self, api):
        self.api = api

    def get_next_2_weeks_appointments(self):
        today = datetime.now().date()
        end_date = today + timedelta(days=14)  # Look ahead 14 days for 2 weeks

        updated_after = today - timedelta(days=30)  # Fetch appointments updated in the last 30 days

        appointment_counts = {}
        page = 1
        while True:
            appointments = self.api.get_appointments(updated_after, page=page)

            for appointment in appointments['results']:
                start_at = datetime.fromisoformat(appointment['start_at'].rstrip('Z')).date()

                if today <= start_at < end_date and start_at.weekday() < 5:
                    appointment_counts[start_at] = appointment_counts.get(start_at, 0) + 1

            if page >= appointments['total_pages']:
                break
            page += 1

        return self._create_appointments_dataframe(today, end_date, appointment_counts)

    def _create_appointments_dataframe(self, start_date, end_date, appointment_counts):
        data = []
        current_date = start_date

        while current_date < end_date:
            if current_date.weekday() < 5:  # Only include weekdays
                data.append({
                    'Date': current_date.strftime("%Y-%m-%d"),
                    'Day of Week': current_date.strftime("%A"),
                    'Appointment Count': appointment_counts.get(current_date, 0)
                })
            current_date += timedelta(days=1)

        return pd.DataFrame(data)

    def get_tech_billable_hours(self, start_date, end_date):
        repair_orders = []
        page = 1
        while True:
            response = self.api.get_repair_orders(
                page=page,
                per_page=100,
                closed_after=start_date.isoformat(),
                closed_before=end_date.isoformat(),
            )

            repair_orders.extend(response['results'])

            if page >= response['total_pages']:
                break
            page += 1

        tech_hours = {}
        for ro in repair_orders:
            for service in ro.get('services', []):
                for labor in service.get('labors', []):
                    tech_id = labor.get('technician_id')
                    if labor.get('hours', 0):
                        hours = labor.get('hours', 0)
                        if tech_id:
                            if tech_id not in tech_hours:
                                tech_hours[tech_id] = 0
                            tech_hours[tech_id] += hours

        df = pd.DataFrame([(tech_id, hours) for tech_id, hours in tech_hours.items()],
                          columns=['Technician ID', 'Billable Hours'])
        df = df.sort_values('Billable Hours', ascending=False).reset_index(drop=True)

        return df

    def get_weekly_tech_billable_hours(self, num_weeks=8):
        today = datetime.now().date()
        end_dates = [today - timedelta(days=i * 7) for i in range(num_weeks)]
        start_dates = [end_date - timedelta(days=6) for end_date in end_dates]

        weekly_data = []
        for start_date, end_date in zip(start_dates[::-1], end_dates[::-1]):
            df = self.get_tech_billable_hours(start_date, end_date)
            total_hours = df['Billable Hours'].sum()
            weekly_data.append({
                'Week': f"{start_date.strftime('%m/%d')} - {end_date.strftime('%m/%d')}",
                'Total Hours': total_hours
            })

        df_weekly = pd.DataFrame(weekly_data)
        return df_weekly

    def get_closed_sales_of_day(self, specific_date=None):
        specific_date = specific_date or (datetime.now() - timedelta(days=3)).date().isoformat()
        total_revenue = 0
        total_cost = 0
        closed_ros = []

        page = 1
        while True:
            response = self.api.get_repair_orders(
                page=page,
                per_page=100,
                closed_after=f"{specific_date}T00:00:00Z",
                closed_before=f"{specific_date}T23:59:59Z"
            )

            for ro in response['results']:
                ro_revenue, ro_cost = self._calculate_ro_financials(ro)
                total_revenue += ro_revenue
                total_cost += ro_cost
                closed_ros.append({
                    'RO Number': ro['number'],
                    'Revenue': ro_revenue,
                    'Cost': ro_cost,
                    'Gross Profit': ro_revenue - ro_cost,
                    'GP%': (ro_revenue - ro_cost) / ro_revenue * 100 if ro_revenue > 0 else 0
                })

            if page >= response['total_pages']:
                break
            page += 1

        gross_profit = total_revenue - total_cost
        gp_percentage = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0

        return {
            'Total Revenue': total_revenue,
            'Total Cost': total_cost,
            'Gross Profit': gross_profit,
            'GP%': gp_percentage,
            'Closed ROs': closed_ros
        }

    def _calculate_ro_financials(self, ro):
        revenue = 0
        cost = 0

        for service in ro.get('services', []):
            # Labor rate in cents
            labor_rate_cents = service.get('labor_rate_cents', 0)

            # Parts
            for part in service.get('parts', []):
                quoted_price = part.get('quoted_price_cents', 0)
                quantity = part.get('quantity', 0)
                cost_cents = part.get('cost_cents', 0)

                revenue += quoted_price * quantity
                cost += cost_cents * quantity

            # Labor
            for labor in service.get('labors', []):
                if labor.get('hours', 0):
                    hours = labor.get('hours', 0)
                    revenue += hours * labor_rate_cents
                # Assuming labor cost is 50% of revenue, adjust if you have actual labor cost data
                # cost += hours * labor_rate_cents * 0.5

            # Sublet
            for sublet in service.get('sublets', []):
                if sublet.get('price_cents', 0) and sublet.get('cost_cents', 0):
                    revenue += sublet.get('price_cents', 0)
                    cost += sublet.get('cost_cents', 0)

            # Hazmat and Supply Fees (100% GP)
            for hazmat in service.get('hazmats', []):
                if hazmat.get('fee_cents', 0) and hazmat.get('quantity', 0):
                    fee = hazmat.get('fee_cents', 0)
                    quantity = hazmat.get('quantity', 0)
                    revenue += fee * quantity

        # Add supply fee to revenue
        if ro.get('supply_fee_cents', 0):
            revenue += ro.get('supply_fee_cents', 0)

        # Apply discounts
        if ro.get('part_discount_cents', 0):
            revenue -= ro.get('part_discount_cents', 0)

        if ro.get('labor_discount_cents', 0):
            revenue -= ro.get('labor_discount_cents', 0)

        return revenue / 100, cost / 100  # Convert cents to dollars

    def get_weekly_closed_sales_and_profit(self, num_weeks=8):
        today = datetime.now().date()
        end_dates = [today - timedelta(days=i * 7) for i in range(num_weeks)]
        start_dates = [end_date - timedelta(days=6) for end_date in end_dates]

        weekly_data = []
        for start_date, end_date in zip(start_dates[::-1], end_dates[::-1]):
            total_revenue = 0
            total_cost = 0

            # Retrieve data for the current week
            for single_date in pd.date_range(start_date, end_date):
                daily_sales_data = self.get_closed_sales_of_day(single_date)
                total_revenue += daily_sales_data['Total Revenue']
                total_cost += daily_sales_data['Total Cost']

            gross_profit = total_revenue - total_cost
            gp_percentage = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0

            weekly_data.append({
                'Week': f"{start_date.strftime('%m/%d')} - {end_date.strftime('%m/%d')}",
                'Total Revenue': total_revenue,
                'Total Cost': total_cost,
                'Gross Profit': gross_profit,
                'GP%': gp_percentage
            })

        df_weekly = pd.DataFrame(weekly_data)
        return df_weekly

    def generate_html_report(self):
        appointments_df = self.get_next_2_weeks_appointments()
        billable_hours_df = self.get_weekly_tech_billable_hours()
        weekly_closed_sales_df = self.get_weekly_closed_sales_and_profit(num_weeks=8)

        # Plot Total Revenue over the past 8 weeks
        revenue_plot = self.generate_plot(
            weekly_closed_sales_df,
            x_column='Week',
            y_column='Total Revenue',
            title='Total Revenue Over the Past 8 Weeks',
            x_label='Week',
            y_label='Total Revenue ($)',
            plot_type='line'
        )

        # Plot Gross Profit over the past 8 weeks
        profit_plot = self.generate_plot(
            weekly_closed_sales_df,
            x_column='Week',
            y_column='Gross Profit',
            title='Gross Profit Over the Past 8 Weeks',
            x_label='Week',
            y_label='Gross Profit ($)',
            plot_type='line'
        )

        # Generate the plot using the generic function
        tech_billable_hours_plot = self.generate_plot(
            data=billable_hours_df,
            x_column='Week',
            y_column='Total Hours',
            title='Weekly Tech Billable Hours (Last 8 Weeks)',
            x_label='Week',
            y_label='Total Billable Hours',
            plot_type='bar'
        )

        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Shop-Ware Reports</title>
            <style type="text/css">
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                h1, h2, h3 {{
                    color: #2c3e50;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 20px;
                }}
                th, td {{
                    padding: 10px;
                    text-align: left;
                    border-bottom: 1px solid #dddddd;
                }}
                th {{
                    background-color: #f2f2f2;
                }}
                .plot-container {{
                    text-align: center;
                    margin-bottom: 20px;
                }}
                .plot-container img {{
                    max-width: 100%;
                    height: auto;
                }}
            </style>
        </head>
        <body>
            <h1>Shop-Ware Reports</h1>

            <h2>Appointments coming up in next 2 weeks</h2>
            {appointments_df.to_html(index=False)}

            <h2>Total Revenue over the past 8 weeks</h2>
            <div class="plot-container">
                <img src="data:image/png;base64,{revenue_plot}" alt="Total Revenue Over the Past 8 Weeks">
            </div>
            <p>This plot shows the total revenue generated over the past 8 weeks, helping to identify trends and patterns in revenue.</p>

            <h2>Gross Profit over the past 8 weeks</h2>
            <div class="plot-container">
                <img src="data:image/png;base64,{profit_plot}" alt="Gross Profit Over the Past 8 Weeks">
            </div>
            <p>This plot displays the gross profit for the past 8 weeks, offering insights into profitability trends.</p>

            <h2>Weekly Tech Billable Hours</h2>
            <div class="plot-container">
                <img src="data:image/png;base64,{tech_billable_hours_plot}" alt="Weekly Tech Billable Hours">
            </div>
            <p>The bar chart represents the total billable hours recorded by technicians over the last 8 weeks.</p>

        </body>
        </html>
        """

        return html_content

    def generate_plot(self, data, x_column, y_column, title, x_label, y_label, plot_type='bar', figsize=(12, 6)):
        """
        Generate a plot based on the given data and parameters.

        :param data: DataFrame containing the data to plot
        :param x_column: Name of the column to use for x-axis
        :param y_column: Name of the column to use for y-axis
        :param title: Title of the plot
        :param x_label: Label for x-axis
        :param y_label: Label for y-axis
        :param plot_type: Type of plot ('bar' or 'line')
        :param figsize: Size of the figure as a tuple (width, height)
        :return: Base64 encoded string of the plot image
        """
        # Set the style
        sns.set(style="whitegrid")

        plt.figure(figsize=figsize)

        # Plot based on the specified type
        if plot_type == 'bar':
            sns.barplot(x=data[x_column], y=data[y_column], palette='coolwarm')
        elif plot_type == 'line':
            sns.lineplot(x=data[x_column], y=data[y_column], marker='o', color='b')
        else:
            raise ValueError("Unsupported plot type. Use 'bar' or 'line'.")

        # Enhance plot aesthetics
        plt.title(title, fontsize=16, fontweight='bold')
        plt.xlabel(x_label, fontsize=14)
        plt.ylabel(y_label, fontsize=14)
        plt.xticks(rotation=45, ha='right')
        plt.yticks(fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.6)

        # Optimize layout
        plt.tight_layout()

        # Save the plot to a base64 encoded string
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=300)  # Higher DPI for better resolution
        buffer.seek(0)
        plot_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()

        return plot_base64

    def save_html_report(self, html_content, filename='weekly_appointment_report.html'):
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"HTML report saved as {filename}")
