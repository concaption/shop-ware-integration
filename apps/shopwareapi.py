import requests
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ShopWareAPI:
    def __init__(self, base_url):
        self.base_url = base_url
        self.api_partner_id = os.getenv('X-API-PARTNER-ID')
        self.api_secret = os.getenv('X-API-SECRET')
        self.tenant_id = os.getenv('TENANT_ID')

    def get_headers(self):
        return {
            'X-Api-Partner-Id': self.api_partner_id,
            'X-Api-Secret': self.api_secret,
            'Accept': 'application/json'
        }

    def get_appointments(self, updated_after, page=1, per_page=100):
        url = f"{self.base_url}/api/v1/tenants/{self.tenant_id}/appointments"
        params = {
            'updated_after': updated_after.isoformat(),
            'page': page,
            'per_page': per_page
        }
        response = requests.get(url, headers=self.get_headers(), params=params)
        response.raise_for_status()
        return response.json()

    def get_categories(self):
        url = f"{self.base_url}/api/v1/tenants/{self.tenant_id}/categories"
        response = requests.get(url, headers=self.get_headers())
        response.raise_for_status()
        return response.json()

    def get_payments_of_day(self,updated_after, page=1, per_page=100):
        url = f"{self.base_url}/api/v1/tenants/{self.tenant_id}/payments"
        params = {
            "page": page,
            "per_page": per_page,
            "updated_after": updated_after.isoformat()
        }
        response = requests.get(url, headers=self.get_headers(), params=params)
        response.raise_for_status()
        return response.json()

    def get_repair_orders(self, page=1, per_page=100, **kwargs):
        url = f"{self.base_url}/api/v1/tenants/{self.tenant_id}/repair_orders"
        params = {
            'page': page,
            'per_page': per_page,
            **kwargs
        }
        response = requests.get(url, headers=self.get_headers(), params=params)
        response.raise_for_status()
        return response.json()

    def get_staff_member(self, staff_id):
        url = f"{self.base_url}/api/v1/tenants/{self.tenant_id}/staffs/{staff_id}"
        response = requests.get(url, headers=self.get_headers())
        response.raise_for_status()
        return response.json()

    def get_inventory(self, inventory_item_id):
        url = f"{self.base_url}/api/v1/tenants/{self.tenant_id}/inventories/{inventory_item_id}"
        response = requests.get(url, headers=self.get_headers())
        response.raise_for_status()
        return response.json()
    
    def is_tyre(self,inventory_item_id):
        inventory_item=self.get_inventory(inventory_item_id)
        if inventory_item.get("part_type","None") == "Tire" or inventory_item.get("reporting_category","None") == "Tires":
            return True
        return False