from datetime import datetime, timedelta
import pandas as pd
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)


logger = logging.getLogger(__name__)



class DailyReports:
    def __init__(self, api):
        self.api = api

    def get_next_7_weekdays_appointments(self):
        try:
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
            logger.info(f"Got next 7 weekdays appointments")
            return self._create_dataframe(today, appointment_counts)
        except Exception as e:
            logger.error(f"Error getting next 7 weekdays appointments: {str(e)}")
            return pd.DataFrame()  # Return an empty DataFrame on error

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

    def get_categories(self):
        try:
            categories_data = self.api.get_categories()
            categories = [{'Category ID': cat['id'], 'Category Name': cat['text']} for cat in categories_data['results']]
            logger.info(f"Got categories")
            return pd.DataFrame(categories)
        except Exception as e:
            logger.error(f"Error getting categories: {str(e)}")
            return pd.DataFrame()  # Return an empty DataFrame on error

    def get_payments(self):
        try:
            updated_after = datetime.now().date() - timedelta(days=1)
            payments_data = self.api.get_payments_of_day(updated_after)
            payments = [{
                'Payment ID': payment['id'],
                'Repair Order ID': payment['repair_order_id'],
                'Payment Type': payment['payment_type'],
                'Amount in USD': payment['amount_cents'] / 100,  # Convert cents to dollars
            } for payment in payments_data['results']]
            logger.info(f"Got payments of today")
            if payments:
                return pd.DataFrame(payments)
            else:
                return pd.DataFrame([{"Message": "No payments received today."}])
        except Exception as e:
            logger.error(f"Error getting payments: {str(e)}")
            return pd.DataFrame()  # Return an empty DataFrame on error

    def get_tech_billable_hours(self, days=1):
        try:
            today = datetime.now().date()
            start_date = today - timedelta(days=days)

            repair_orders = []
            page = 1
            while True:
                response = self.api.get_repair_orders(
                    page=page,
                    per_page=100,
                    closed_after=start_date.isoformat(),
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
            tech_names = {}
            for tech_id in tech_hours.keys():
                try:
                    staff_member = self.api.get_staff_member(tech_id)
                    tech_names[tech_id] = f"{staff_member['first_name']} {staff_member['last_name']}"
                except Exception as e:
                    logger.error(f"Error fetching technician name for ID {tech_id}: {str(e)}")
                    tech_names[tech_id] = f"Unknown (ID: {tech_id})"

            df = pd.DataFrame([(tech_names[tech_id], hours) for tech_id, hours in tech_hours.items()],
                              columns=['Technician Name', 'Billable Hours'])
            df = df.sort_values('Billable Hours', ascending=False).reset_index(drop=True)
            logger.info(f"Got Tech Billable Hours")
            return df, start_date.strftime("%Y-%m-%d")
        except Exception as e:
            logger.error(f"Error getting tech billable hours: {str(e)}")
            return pd.DataFrame(), ""  # Return empty DataFrame and empty date on error


    def get_low_margin_services(self, days=1, margin_threshold=0.4):
        try:
            today = datetime.now().date()
            start_date = today - timedelta(days=days)

            low_margin_services = []
            page = 1
            while True:
                response = self.api.get_repair_orders(
                    page=page,
                    per_page=100,
                    closed_after=start_date.isoformat()
                )

                for ro in response['results']:
                    for service in ro.get('services', []):
                        service_low_margin_parts = []
                        for part in service.get('parts', []):
                            if not self.api.is_tyre(part['part_inventory_id']):  # Check for tire
                                cost = part['cost_cents'] / 100
                                price = part['quoted_price_cents'] / 100
                                if cost > 0:
                                    margin = (price - cost) / price
                                    if margin < margin_threshold:
                                        service_low_margin_parts.append({
                                            'part_number': part['number'],
                                            'description': part['description'],
                                            'cost': cost,
                                            'price': price,
                                            'margin': margin
                                        })

                        if service_low_margin_parts:
                            low_margin_services.append({
                                'ro_number': ro['number'],
                                'service_title': service['title'],
                                'low_margin_parts': service_low_margin_parts
                            })

                if page >= response['total_pages']:
                    break
                page += 1
            logger.info(f"Got low margin servces of today")
            return low_margin_services
        except Exception as e:
            logger.error(f"Error getting low margin services: {str(e)}")
            return []  # Return an empty list on error

    def get_car_count(self, closed_sales):
        try:
            today = (datetime.now() - timedelta(days=1)).date().isoformat()
            count = 0
            page = 1
            while True:
                response = self.api.get_repair_orders(
                    page=page,
                    per_page=100,
                    closed_after=f"{today}T00:00:00Z",
                )
                for car in response['results']:
                    count += 1

                if page >= response['total_pages']:
                    break
                page += 1
            logger.info(f"Got car count of today")
            return count
        except Exception as e:
            logger.error(f"Error getting car count: {str(e)}")
            return 0  # Return 0 on error

    def get_avg_ro (self,closed_sales,car_count):
        return closed_sales['Total Revenue']/car_count if car_count > 0 else 0

    def get_total_billable(self,tech_hours) :
        return tech_hours['Billable Hours'].sum()

    def get_labour_efficiency(self , tech_hours):
        return (tech_hours['Billable Hours'].sum() / 40 ) *100

    def get_closed_sales_of_day(self):
        try:
            today = (datetime.now() - timedelta(days=1)).date().isoformat()
            total_revenue = 0
            total_cost = 0
            total_parts_revenue = 0
            total_parts_cost = 0
            total_tire_revenue = 0
            total_tire_cost = 0
            closed_ros = []

            page = 1
            while True:
                response = self.api.get_repair_orders(
                    page=page,
                    per_page=100,
                    closed_after=f"{today}T00:00:00Z",
                    status='invoice'
                )

                for ro in response['results']:
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
                        'Parts + Tires Cost': ro_cost,
                        'Parts + Tires Margin': ro_revenue - ro_cost,
                        'Parts Margin %': (part_revenue - part_cost) / part_revenue * 100 if part_revenue > 0 else 0,
                        'Tires Margin %': (tire_revenue - tire_cost) / tire_revenue * 100 if tire_revenue > 0 else 0,
                        'RO Link':"https://bob-s-automotive-services.shop-ware.com/work_orders/" + str(ro['id'])
                    })

                if page >= response['total_pages']:
                    break
                page += 1
            part_n_tire_marg = (total_tire_revenue + total_parts_revenue) - (total_parts_cost+total_tire_cost)
            print(f"Total Parts Revenue: {total_parts_revenue} and Total Parts Cost : {total_parts_cost}")
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

    def generate_html_report(self):
        try:
            appointments_df = self.get_next_7_weekdays_appointments()
            # categories_df = self.get_categories()
            payments_df = self.get_payments()
            # repair_orders_df = self.get_recent_repair_orders()
            tech_hours_df, current_date = self.get_tech_billable_hours()
            low_margin_services = self.get_low_margin_services()
            low_margin_html = self._generate_low_margin_html(low_margin_services)
            closed_sales = self.get_closed_sales_of_day()

            closed_sales_html = self._generate_closed_sales_html(closed_sales,tech_hours_df)

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
                        max-width: 600px;
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
                    .closed-sales-summary {{
                        background-color: #f2f2f2;
                        padding: 15px;
                        margin-bottom: 20px;
                    }}
                    .closed-sales-summary h3 {{
                        margin-top: 0;
                        border-bottom: 2px solid #2c3e50;
                        padding-bottom: 10px;
                    }}
                    .highlight {{
                        font-weight: bold;
                        color: #27ae60;
                    }}
                    .closed-ro {{
                        background-color: #ffffff;
                        border: 1px solid #dddddd;
                        padding: 15px;
                        margin-bottom: 15px;
                    }}
                    .closed-ro h4 {{
                        margin-top: 0;
                        color: #2c3e50;
                        border-bottom: 1px solid #dddddd;
                        padding-bottom: 5px;
                    }}
                    .ro-gp {{
                        font-weight: bold;
                        color: #27ae60;
                    }}
                </style>
            </head>
            <body>
                <h1>Shop-Ware Reports</h1>

                <h2>Appointments for the Next 7 Weekdays</h2>
                {appointments_df.to_html(index=False)}

                <div class="section">
                    <h2>Closed Sales of the Day</h2>
                    {closed_sales_html}
                </div>
                
                <h2>Today's Payments</h2>
                {payments_df.to_html(index=False)}
                
                <h2>Technician Billable Hours (After {current_date})</h2>
                {tech_hours_df.to_html(index=False)}
                
                <div class="section">
                    <h2>Services with Low Parts Margin (&lt;40%)</h2>
                    {low_margin_html}
                </div>
                
            </body>
            </html>
            """
            return html_content
        except Exception as e:
            logger.error(f"An error occurred while generating the HTML report: {e}")


    def save_html_report(self, html_content, filename='appointment_report.html'):
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"HTML report saved as {filename}")
        except IOError as e:
            logger.error(f"IO error: {e}. Could not save the HTML report.")

    def _generate_low_margin_html(self, low_margin_services):
        html = ""
        for service in low_margin_services:
            html += f"""
            <div class="low-margin-service">
                <h4>RO #{service['ro_number']} - {service['service_title']}</h4>
                <ul>
            """
            for part in service['low_margin_parts']:
                html += f"""
                    <li class="low-margin-part">
                        {part['part_number']} - {part['description']}<br>
                        Cost: ${part['cost']:.2f}, Price: ${part['price']:.2f}, Margin: {part['margin']:.2%}
                    </li>
                """
            html += """
                </ul>
            </div>
            """
        return html

    def _generate_closed_sales_html(self, closed_sales,tech_hours_df):
        car_count= self.get_car_count(closed_sales)
        avg_ro= self.get_avg_ro(closed_sales,car_count)
        labor_efficiency=self.get_labour_efficiency(tech_hours_df)
        html = f"""
        <div class="closed-sales-summary">
            <h3>Closed Sales Summary</h3>
            <p>Total Revenue: <span class="highlight">${closed_sales['Total Revenue']:.2f}</span></p>
            <p>Parts + Tires Cost : ${closed_sales['Total Parts + Tires Cost']:.2f}</p>
            <p>Parts + Tires Margin ($): <span class="highlight">${closed_sales['Total Parts + Tires Margin']:.2f}</span></p>
            <p>Parts Margin %: <span class="highlight">{closed_sales['Total Parts Margin %']:.2f}%</span></p>
            <p>Tires Margin %: <span class="highlight">{closed_sales['Total Tires Margin %']:.2f}%</span></p>
            <p>Car Count: <span class="highlight">{car_count}</span></p>
            <p>Average RO: <span class="highlight">{avg_ro:.2f}</span></p>
            <p>Labor Efficeincy %: <span class="highlight">{labor_efficiency:.2f}%</span></p>

        </div>
        <h3>Closed Repair Orders:</h3>
        """

        for ro in closed_sales['Closed ROs']:
            html += f"""
            <div class="closed-ro">
                <h4>RO Number: <a href="{ro['RO Link']}">{ro['RO Number']}</a></h4>
                <p>Revenue: ${ro['Revenue']:.2f}</p>
                <p>Parts + Tires Cost ($): ${ro['Parts + Tires Cost']:.2f}</p>
                <p>Parts + Tires Margin ($): ${ro['Parts + Tires Margin']:.2f}</p>
                <p class="ro-gp">Parts Margin %: {ro['Parts Margin %']:.2f}%</p>
                <p class="ro-gp">Tires Margin %: {ro['Tires Margin %']:.2f}%</p>
            </div>
            """

        return html
