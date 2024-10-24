from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import base64
import io
import seaborn as sns
import logging


logger = logging.getLogger(__name__)


class WeeklyReports:
    def __init__(self, api,duration):
        self.api = api
        self.duration = duration
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

    def get_tech_billable_hours_complete(self, specific_date):
        specific_date = specific_date or (datetime.now() - timedelta(days=3)).date().isoformat()
        page = 1
        complete_response = {
            "results": [],
            "limit": 100,
            "limited": False,
            "total_count": 0,
            "current_page": 1,
            "total_pages": 0
        }
        try:
            while True:
                response = self.api.get_repair_orders(
                    page=page,
                    per_page=100,
                    closed_after=f"{specific_date}T00:00:00Z",
                    status='invoice'
                )
                
                # For first page, initialize the metadata
                if page == 1:
                    complete_response['total_pages'] = response.get('total_pages', 0)
                    complete_response['total_count'] = response.get('total_count', 0)
                    
                # Extend the results list with the current page's results
                if 'results' in response:
                    complete_response['results'].extend(response['results'])
                
                # Check if we've reached the last page
                if page >= response.get('total_pages', 0):
                    break
                    
                page += 1
                
            # Update final metadata
            complete_response['current_page'] = 1  # Always 1 since we're combining all pages
            complete_response['limit'] = len(complete_response['results'])
            complete_response['limited'] = False  # Since we're getting all results
                
            return complete_response
        
        except Exception as e:
            logger.error(f"Error getting Tech Billable hours of the day: {str(e)}")
            return None


    def get_tech_billable_hours(self, repair_orders, specific_date):
        tech_hours = {}
        df=pd.DataFrame([[0,0]], columns=['Technician ID', 'Billable Hours'])
        df = df.sort_values('Billable Hours', ascending=False).reset_index(drop=True)
        for ro in repair_orders['results']:
            # print (ro.get('closed_at'))
            if datetime.strptime(str(ro.get('closed_at')), "%Y-%m-%dT%H:%M:%SZ").date() == datetime.strptime(str(specific_date), "%Y-%m-%d %H:%M:%S").date() :
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
        # today= today - timedelta(days=3)
        num_weeks=self.duration
        start_date1=today - timedelta(days=num_weeks * 7)
        end_dates = [today - timedelta(days=i * 7) for i in range(num_weeks)]
        start_dates = [end_date - timedelta(days=6) for end_date in end_dates]
        response_tech_billable_hours=self.get_tech_billable_hours_complete(start_date1)
        weekly_data = []
        for start_date, end_date in zip(start_dates[::-1], end_dates[::-1]):
            total_hours=0
            for single_date in pd.date_range(start_date, end_date):
                df = self.get_tech_billable_hours(response_tech_billable_hours, single_date)
                total_hours = total_hours + df['Billable Hours'].sum()
                
            weekly_data.append({
                'Week': f"{start_date.strftime('%m/%d')} - {end_date.strftime('%m/%d')}",
                'Total Hours': total_hours
            })

        df_weekly = pd.DataFrame(weekly_data)
        return df_weekly

    def get_closed_sales_complete(self, specific_date=None):
        specific_date = specific_date or (datetime.now() - timedelta(days=3)).date().isoformat()
        page = 1
        complete_response = {
            "results": [],
            "limit": 100,
            "limited": False,
            "total_count": 0,
            "current_page": 1,
            "total_pages": 0
        }
        
        try:
            while True:
                response = self.api.get_repair_orders(
                    page=page,
                    per_page=100,
                    closed_after=f"{specific_date}T00:00:00Z",
                    status='invoice'
                )
                
                # For first page, initialize the metadata
                if page == 1:
                    complete_response['total_pages'] = response.get('total_pages', 0)
                    complete_response['total_count'] = response.get('total_count', 0)
                    
                # Extend the results list with the current page's results
                if 'results' in response:
                    complete_response['results'].extend(response['results'])
                
                # Check if we've reached the last page
                if page >= response.get('total_pages', 0):
                    break
                    
                page += 1
                
            # Update final metadata
            complete_response['current_page'] = 1  # Always 1 since we're combining all pages
            complete_response['limit'] = len(complete_response['results'])
            complete_response['limited'] = False  # Since we're getting all results
                
            return complete_response
            
        except Exception as e:
            logger.error(f"Error getting closed sales of the day: {str(e)}")
            return None


    def get_closed_sales_of_day(self,response, specific_date=None):
        # specific_date = specific_date or (datetime.now() - timedelta(days=3)).date().isoformat()
        total_revenue = 0
        total_cost = 0
        closed_ros = []

        try:
            total_revenue = 0
            total_cost = 0
            total_parts_revenue = 0
            total_parts_cost = 0
            total_tire_revenue = 0
            total_tire_cost = 0
            closed_ros = []

            for ro in response['results']:
                # print(f"Updated AT {datetime.strptime(str(ro['closed_at']), "%Y-%m-%dT%H:%M:%SZ").date()}")
                # print(datetime.strptime(str(specific_date), "%Y-%m-%d %H:%M:%S").date())
                if datetime.strptime(str(ro['closed_at']), "%Y-%m-%dT%H:%M:%SZ").date() == datetime.strptime(str(specific_date), "%Y-%m-%d %H:%M:%S").date() :
                    ro_revenue, ro_cost, part_revenue, part_cost, tire_revenue, tire_cost = self._calculate_ro_financials(ro)
                    total_revenue += ro_revenue
                    total_cost += ro_cost
                    total_parts_revenue += part_revenue
                    total_parts_cost += part_cost
                    total_tire_revenue += tire_revenue
                    total_tire_cost += tire_cost
                    closed_ros.append({
                        'RO Number': ro['number'],
                        'Revenue': ro_revenue,
                        'Parts + Tires Cost': part_cost + tire_cost,
                        'Parts + Tires Margin': (part_revenue + tire_revenue) - (part_cost + tire_cost),
                        'Parts Margin %': (part_revenue - part_cost) / part_revenue * 100 if part_revenue > 0 else 0,
                        'Tires Margin %': (tire_revenue - tire_cost) / tire_revenue * 100 if tire_revenue > 0 else 0,
                        'RO Link':"https://bob-s-automotive-services.shop-ware.com/work_orders/" + str(ro['id'])
                    })

            part_n_tire_marg = (total_tire_revenue + total_parts_revenue) - (total_parts_cost+total_tire_cost)
            # print(f"Total Parts Revenue: {total_parts_revenue} and Total Parts Cost : {total_parts_cost}")
            parts_margin = ((total_parts_revenue - total_parts_cost) / total_parts_revenue * 100) if total_parts_revenue > 0 else 0
            tire_margin  = ((total_tire_revenue - total_tire_cost) / total_tire_revenue * 100) if total_tire_revenue > 0 else 0

            return {
            'Total Revenue': total_revenue,
            'Total Parts + Tires Cost': total_cost,
            'Total Parts + Tires Margin': part_n_tire_marg,
            'Total Parts Margin %': parts_margin,
            'Total Tires Margin %': tire_margin,
            'Closed ROs': closed_ros
             }
        except Exception as e:
            logger.error(f"Error getting closed sales of the day: {str(e)}")
            return {
            'Total Revenue': 0,
            'Total Parts + Tires Cost': 0,
            'Total Parts + Tires Margin': 0,
            'Total Parts Margin %': 0,
            'Total Tires Margin %': 0,
            'Closed ROs': 0
             }  # Return zeros and empty list on error


    def _calculate_ro_financials(self, ro):
        revenue = 0
        cost = 0
        part_revenue=0
        part_cost=0
        tire_revenue=0
        tire_cost=0
        try: 
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
                    
                    if not self.api.is_tyre(part['part_inventory_id']):# check for tires
                        part_revenue+=quoted_price * quantity
                        part_cost+=cost_cents * quantity
                    else :                                             # tire calculation
                        tire_revenue += quoted_price * quantity
                        tire_cost+=cost_cents * quantity

                # Labor
                for labor in service.get('labors', []):
                    if labor.get('hours', 0):
                        hours = labor.get('hours', 0)
                        revenue += hours * labor_rate_cents
                    # Assuming labor cost is 50% of revenue, adjust if you have actual labor cost data
                        # cost += hours * labor_rate_cents * 0.4

                # Sublet
                for sublet in service.get('sublets', []):
                    if sublet.get('price_cents', 0) :
                        revenue += sublet.get('price_cents', 0)
                    if sublet.get('cost_cents', 0):
                        cost += sublet.get('cost_cents', 0)

                # Hazmat and Supply Fees (100% GP)
                for hazmat in service.get('hazmats', []):
                    if hazmat.get('fee_cents', 0) and hazmat.get('quantity', 0):
                        fee = hazmat.get('fee_cents', 0)
                        quantity = hazmat.get('quantity', 0)
                        revenue += fee * quantity
        except KeyError as e:
            logger.error(f"Key error: {e}. Check if the keys exist in the service data.")
        except TypeError as e:
            logger.error(f"Type error: {e}. Check data types for calculations.")
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            # Add supply fee to revenue
        try:
            if ro.get('supply_fee_cents', 0):
                revenue += ro.get('supply_fee_cents', 0)

            # Apply discounts
            if ro.get('part_discount_cents', 0):
                revenue -= float(ro.get('part_discount_cents', 0))

            if ro.get('labor_discount_cents', 0):
                revenue -= float(ro.get('labor_discount_cents', 0))

        except (KeyError, TypeError, ValueError) as e:
            logger.error(f"Error processing supply fees or discounts: {e}")
            
        return (revenue / 100,
            cost / 100,
            part_revenue / 100,
            part_cost / 100,
            tire_revenue / 100,
            tire_cost / 100)  # Convert cents to dollars

    def get_car_count(self,specific_date):
        specific_date = specific_date or (datetime.now() - timedelta(days=3)).date().isoformat()
        page = 1
        complete_response = {
            "results": [],
            "limit": 100,
            "limited": False,
            "total_count": 0,
            "current_page": 1,
            "total_pages": 0
        }
        
        try:
            while True:
                response = self.api.get_repair_orders(
                    page=page,
                    per_page=100,
                    closed_after=f"{specific_date}T00:00:00Z",
                )
                
                # For first page, initialize the metadata
                if page == 1:
                    complete_response['total_pages'] = response.get('total_pages', 0)
                    complete_response['total_count'] = response.get('total_count', 0)
                    
                # Extend the results list with the current page's results
                if 'results' in response:
                    complete_response['results'].extend(response['results'])
                
                # Check if we've reached the last page
                if page >= response.get('total_pages', 0):
                    break
                    
                page += 1
                
            # Update final metadata
            complete_response['current_page'] = 1  # Always 1 since we're combining all pages
            complete_response['limit'] = len(complete_response['results'])
            complete_response['limited'] = False  # Since we're getting all results
            
            logger.info(f"Got cars in of the day.")
            
            return complete_response
            
        except Exception as e:
            logger.error(f"Error getting cars in of the day: {str(e)}")
            return None

    def get_car_count_specific(self,response,specific_date):
        count=0
        for ro in response['results']:
            if datetime.strptime(str(ro['closed_at']), "%Y-%m-%dT%H:%M:%SZ").date() == datetime.strptime(str(specific_date), "%Y-%m-%d %H:%M:%S").date() :
                count = count + 1
        return count


    def get_avg_ro (self,closed_sales,car_count):
        return closed_sales['Total Revenue']/car_count if car_count > 0 else 0
    

    def get_weekly_closed_sales(self, num_weeks=8):
        today = datetime.now().date()
        # today= today - timedelta(days=3)
        start_date1=today - timedelta(days=16 * 7)
        response_closed_sales = self.get_closed_sales_complete(start_date1)
        response_car_count = self.get_car_count(start_date1)
        end_dates = [today - timedelta(days=i * 7) for i in range(num_weeks)]
        start_dates = [end_date - timedelta(days=6) for end_date in end_dates]
        weekly_data = []
        # Header for the report
        print("\n" + "="*50)
        print(f"Daily Metrics Summary Report")
        print("="*50 + "\n")
        for start_date, end_date in zip(start_dates[::-1], end_dates[::-1]):
            total_revenue = 0
            total_parts_margin = 0
            total_tires_margin = 0
            total_car_count = 0
            parts_day_count= 0
            tires_day_count= 0
            # Retrieve data for the current week
            for single_date in pd.date_range(start_date, end_date):
                print (f"Single Date {single_date}, Start Date {start_date} , End Date {end_date}")
                daily_sales_data = self.get_closed_sales_of_day(response_closed_sales,single_date)
                car_count= self.get_car_count_specific(response_car_count,single_date)
                # avg_ro= self.get_avg_ro(daily_sales_data,car_count)
                total_revenue += daily_sales_data['Total Revenue']
                if daily_sales_data['Total Parts Margin %'] > 0 :
                    parts_day_count += 1
                if daily_sales_data['Total Tires Margin %'] > 0 :
                    tires_day_count += 1                    
                total_parts_margin += daily_sales_data['Total Parts Margin %']
                total_tires_margin += daily_sales_data['Total Tires Margin %']
                total_car_count += car_count
                print(f"{'Car Count:':<25} {car_count:>8}")
                # print(f"{'Average RO:':<25} ${daily_sales_data['Total Revenue']/car_count:>7,.2f}")
                print(f"{'Daily Revenue:':<25} ${daily_sales_data['Total Revenue']:>7,.2f}")
                print(f"{'Parts Margin %:':<25} {daily_sales_data['Total Parts Margin %']:>7.1f}%")
                print(f"{'Tires Margin %:':<25} {daily_sales_data['Total Tires Margin %']:>7.1f}%")
                print("-" * 40 + "\n")                
                

            total_parts_margin = total_parts_margin / parts_day_count
            total_tires_margin = total_tires_margin / tires_day_count
            print (f"Week {start_date.strftime('%m/%d')} - {end_date.strftime('%m/%d')} , Total Revenue {total_revenue},Total Parts Margin % {total_parts_margin}, Total Tires Margin % {total_tires_margin}, Total Car {total_car_count}")
            weekly_data.append({
                'Week': f"{start_date.strftime('%m/%d')} - {end_date.strftime('%m/%d')}",
                'Total Revenue': total_revenue,
                'Total Parts Margin %': total_parts_margin,
                'Total Tires Margin %': total_tires_margin,
                'Total Avg RO': total_revenue/total_car_count if total_car_count > 0 else 0,
                'Total Car Count': total_car_count,
            })
            print("="*50)
            print("Summary Statistics")
            print("="*50)
            print(f"{'Total Cars Serviced:':<25} {total_car_count:>8}")
            print(f"{'Average RO Value:':<25} ${total_revenue/total_car_count if total_car_count > 0 else 0:>7,.2f}")
            print(f"{'Total Revenue:':<25} ${total_revenue}")
            print(f"{'Average Parts Margin:':<25} {total_parts_margin}%")
            print(f"{'Average Tires Margin:':<25} {total_tires_margin}%")
            print("="*50)

        df_weekly = pd.DataFrame(weekly_data)
        return df_weekly

    def generate_html_report(self):
        appointments_df = self.get_next_2_weeks_appointments()
        billable_hours_df = self.get_weekly_tech_billable_hours()
        weekly_closed_sales_df = self.get_weekly_closed_sales(num_weeks=self.duration)

        # Plot Total Revenue over the past 8 weeks
        revenue_plot = self.generate_plot(
            weekly_closed_sales_df,
            x_column='Week',
            y_column='Total Revenue',
            title='Total Revenue Over the Past' + str(self.duration)+' Weeks',
            x_label='Week',
            y_label='Total Revenue ($)',
            plot_type='line'
        )

        # Plot Car Count over the past 8 weeks
        car_count_plot = self.generate_plot(
            weekly_closed_sales_df,
            x_column='Week',
            y_column='Total Car Count',
            title='Car Count Over' + str(self.duration)+' Weeks',
            x_label='Week',
            y_label='Car Count',
            plot_type='line'
        )

        # Plot Avg ROs over the past 8 weeks
        avg_ro_plot = self.generate_plot(
            weekly_closed_sales_df,
            x_column='Week',
            y_column='Total Avg RO',
            title='Avg ROs Over' + str(self.duration)+' Weeks',
            x_label='Week',
            y_label='Avg ROs',
            plot_type='line'
        )

        # Plot Parts Margin % over the past 8 weeks
        parts_margin_plot = self.generate_plot(
            weekly_closed_sales_df,
            x_column='Week',
            y_column='Total Parts Margin %',
            title='Total Parts Margin % Over' + str(self.duration)+' Weeks',
            x_label='Week',
            y_label='Total Parts Margin %',
            plot_type='line'
        )

        # Plot Tires Margin % over the past 8 weeks
        tires_margin_plot = self.generate_plot(
            weekly_closed_sales_df,
            x_column='Week',
            y_column='Total Tires Margin %',
            title='Total Tires Margin % ' + str(self.duration)+' Weeks',
            x_label='Week',
            y_label='Total Tires Margin %',
            plot_type='line'
        )



        # Plot Tech billable Hours over the past 8 weeks
        tech_billable_hours_plot = self.generate_plot(
            data=billable_hours_df,
            x_column='Week',
            y_column='Total Hours',
            title='Weekly Tech Billable Hours (Last' + str(self.duration)+' Weeks)',
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

            <h2>Total Revenue over the past {self.duration} weeks</h2>
            <div class="plot-container">
                <img src="data:image/png;base64,{revenue_plot}" alt="Total Revenue Over the Past {self.duration} Weeks">
            </div>
            <p>This plot shows the total revenue generated over the past {self.duration} weeks, helping to identify trends and patterns in revenue.</p>

            <h2>Car Count over the past {self.duration} weeks</h2>
            <div class="plot-container">
                <img src="data:image/png;base64,{car_count_plot}" alt="Gross Profit Over the Past {self.duration} Weeks">
            </div>
            # <p>This plot displays the Car Count for the past {self.duration} weeks, offering insights into profitability trends.</p>

            <h2>Avg ROs over the past {self.duration} weeks</h2>
            <div class="plot-container">
                <img src="data:image/png;base64,{avg_ro_plot}" alt="Gross Profit Over the Past {self.duration} Weeks">
            </div>
            # <p>This plot displays the Avg ROs for the past {self.duration} weeks, offering insights into profitability trends.</p>

            <h2>Parts Margin % over the past {self.duration} weeks</h2>
            <div class="plot-container">
                <img src="data:image/png;base64,{parts_margin_plot}" alt="Gross Profit Over the Past {self.duration} Weeks">
            </div>
            # <p>This plot displays the Parts Margin % for the past {self.duration} weeks, offering insights into profitability trends.</p>            

            <h2>Tires Margin % over the past {self.duration} weeks</h2>
            <div class="plot-container">
                <img src="data:image/png;base64,{tires_margin_plot}" alt="Gross Profit Over the Past {self.duration} Weeks">
            </div>
            # <p>This plot displays the Tires Margin % for the past {self.duration} weeks, offering insights into profitability trends.</p>                        
            
            <h2>Weekly Tech Billable Hours</h2>
            <div class="plot-container">
                <img src="data:image/png;base64,{tech_billable_hours_plot}" alt="Weekly Tech Billable Hours">
            </div>
            <p>The bar chart represents the total billable hours recorded by technicians over the last {self.duration} weeks.</p>

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
