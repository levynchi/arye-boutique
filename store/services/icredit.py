"""
iCredit Payment Gateway Service
שירות תשלומים באמצעות iCredit API
"""
import requests
import hashlib
import json
import logging
from decimal import Decimal
from django.conf import settings
from django.urls import reverse

logger = logging.getLogger(__name__)


class ICreditService:
    """
    Service class for iCredit payment gateway integration
    """
    
    def __init__(self):
        self.api_url = settings.ICREDIT_API_URL
        self.verify_url = settings.ICREDIT_VERIFY_URL
        self.group_private_token = settings.ICREDIT_GROUP_PRIVATE_TOKEN
        self.credit_box_token = settings.ICREDIT_CREDIT_BOX_TOKEN
        self.test_mode = settings.ICREDIT_TEST_MODE
    
    def create_payment_request(self, order, request):
        """
        יצירת בקשת תשלום ל-iCredit
        
        Args:
            order: Order model instance
            request: HTTP request for building absolute URLs
            
        Returns:
            dict: Response with payment URL or error
        """
        # Build callback URLs
        base_url = request.build_absolute_uri('/')[:-1]  # Remove trailing slash
        success_url = f"{base_url}{reverse('payment_success')}"
        fail_url = f"{base_url}{reverse('payment_fail')}"
        ipn_url = f"{base_url}{reverse('payment_ipn')}"
        
        # Prepare payment data
        payload = {
            "GroupPrivateToken": self.group_private_token,
            "CreditboxToken": self.credit_box_token,
            "CustomerLastName": order.guest_name.split()[-1] if order.guest_name else "",
            "CustomerFirstName": order.guest_name.split()[0] if order.guest_name else "",
            "PhoneNumber": order.guest_phone or "",
            "EmailAddress": order.guest_email or "",
            "FlexItem": True,
            "Items": [{
                "Quantity": 1,
                "UnitPrice": str(order.total_price),
                "Description": f"הזמנה #{order.id} - בוטיק אריה"
            }],
            "Currency": 1,  # 1 = ILS
            "Sale": {
                "SaleId": str(order.id),
                "Amount": str(order.total_price)
            },
            "RedirectURL": success_url,
            "FailRedirectURL": fail_url,
            "IPNURL": ipn_url,
            "HideItemList": True,
            "CustomFields": json.dumps({"order_id": order.id}),
            "DocumentType": 4,  # 4 = Invoice
        }
        
        logger.info(f"Creating iCredit payment for order #{order.id}, amount: {order.total_price}")
        
        try:
            response = requests.post(
                self.api_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            logger.debug(f"iCredit API response status: {response.status_code}")
            logger.debug(f"iCredit API response: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("Status") == 0:
                    # Success - return payment URL
                    payment_url = data.get("URL")
                    logger.info(f"Payment URL created for order #{order.id}: {payment_url}")
                    return {
                        "success": True,
                        "payment_url": payment_url,
                        "private_sale_token": data.get("PrivateSaleToken")
                    }
                else:
                    # API returned error
                    error_msg = data.get("StatusDescription", "Unknown error")
                    logger.error(f"iCredit API error for order #{order.id}: {error_msg}")
                    return {
                        "success": False,
                        "error": error_msg
                    }
            else:
                logger.error(f"iCredit API HTTP error: {response.status_code}")
                return {
                    "success": False,
                    "error": f"HTTP Error: {response.status_code}"
                }
                
        except requests.exceptions.Timeout:
            logger.error("iCredit API timeout")
            return {
                "success": False,
                "error": "Connection timeout"
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"iCredit API request error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def verify_payment(self, sale_id, private_sale_token):
        """
        אימות תשלום מול iCredit
        
        Args:
            sale_id: מזהה ההזמנה
            private_sale_token: טוקן פרטי שהתקבל מ-iCredit
            
        Returns:
            dict: פרטי התשלום או שגיאה
        """
        payload = {
            "GroupPrivateToken": self.group_private_token,
            "SaleId": str(sale_id),
            "PrivateSaleToken": private_sale_token
        }
        
        try:
            response = requests.post(
                self.verify_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": data.get("Status") == 0,
                    "data": data
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP Error: {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Payment verification error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def process_ipn(self, data):
        """
        עיבוד IPN (Instant Payment Notification) מ-iCredit
        
        Args:
            data: נתוני ה-IPN
            
        Returns:
            dict: תוצאת העיבוד
        """
        logger.info(f"Processing IPN: {json.dumps(data)}")
        
        try:
            sale_id = data.get("SaleId") or data.get("sale_id")
            status = data.get("TransStatus") or data.get("trans_status")
            transaction_id = data.get("TransactionId") or data.get("transaction_id")
            
            # Status codes:
            # 0 = Success
            # Other = Failed
            
            return {
                "sale_id": sale_id,
                "status": "approved" if str(status) == "0" else "failed",
                "transaction_id": transaction_id,
                "raw_data": data
            }
            
        except Exception as e:
            logger.error(f"IPN processing error: {str(e)}")
            return {
                "sale_id": None,
                "status": "error",
                "error": str(e)
            }


# Singleton instance
icredit_service = ICreditService()
