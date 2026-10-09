"""
CinetPay Payment Service for EasyTravel
Integrates CinetPay API Checkout v2 for Mobile Money (MTN, Orange) and Credit Cards in Cameroon & CEMAC.
"""

import os
import uuid
import logging
import requests
from django.conf import settings
from django.utils import timezone
from bookings.models import Booking

logger = logging.getLogger(__name__)

CINETPAY_BASE_URL = "https://api-checkout.cinetpay.com/v2"


class CinetPayService:
    def __init__(self):
        self.site_id = getattr(settings, 'CINETPAY_SITE_ID', '') or os.getenv('CINETPAY_SITE_ID', '')
        self.api_key = getattr(settings, 'CINETPAY_API_KEY', '') or os.getenv('CINETPAY_API_KEY', '')
        self.currency = getattr(settings, 'CINETPAY_CURRENCY', 'XAF') or os.getenv('CINETPAY_CURRENCY', 'XAF')
        self.base_url = CINETPAY_BASE_URL

    def is_configured(self):
        """Returns True if the required credentials are provided."""
        return bool(self.site_id and self.api_key)

    def initiate_payment(self, booking=None, cart=None, return_url=None, notify_url=None):
        """
        Creates a payment session with CinetPay Checkout v2.
        Returns:
            (success: bool, result: dict, transaction_id: str)
        """
        if not self.is_configured():
            logger.warning("CinetPay is not fully configured (missing CINETPAY_SITE_ID or CINETPAY_API_KEY).")
            return False, {"message": "Passerelle CinetPay non configurée sur le serveur."}, ""

        # Determine context (Cart or Single Booking)
        if cart:
            tx_id = f"ET-CRT-{cart.reference}-{uuid.uuid4().hex[:4].upper()}"
            cart.transaction_id = tx_id
            cart.save(update_fields=['transaction_id'])
            first_booking = cart.bookings.first()
            amount = int(cart.total_amount)
            description = f"Panier EasyTravel Ref {cart.reference}"
            
            # Link all bookings in cart to this operator & tx_id
            cart.bookings.update(transaction_id=tx_id, payment_operator="cinetpay")
            
        elif booking:
            tx_id = f"ET-TX-{booking.id}-{uuid.uuid4().hex[:8].upper()}"
            booking.transaction_id = tx_id
            booking.payment_operator = "cinetpay"
            booking.save(update_fields=['transaction_id', 'payment_operator'])
            first_booking = booking
            amount = int(booking.total_amount)
            description = f"Billet EasyTravel Ref {booking.reference} - {booking.traveler_name}"
        else:
            return False, {"message": "Aucune réservation fournie."}, ""

        # Format traveler names
        parts = (first_booking.traveler_name or "Passager").strip().split(maxsplit=1)
        name = parts[0]
        surname = parts[1] if len(parts) > 1 else parts[0]

        # Sanitize phone number (e.g. +237 699... -> 237699...)
        phone = (first_booking.traveler_phone or "").replace(' ', '').replace('+', '').replace('-', '')
        if not phone.startswith('237') and len(phone) == 9:
            phone = f"237{phone}"

        city_name = "Douala"
        if first_booking.departure_stop and first_booking.departure_stop.city:
            city_name = first_booking.departure_stop.city.name

        payload = {
            "apikey": self.api_key,
            "site_id": str(self.site_id),
            "transaction_id": tx_id,
            "amount": amount,
            "currency": self.currency,
            "description": description,
            "notify_url": notify_url,
            "return_url": return_url,
            "channels": "ALL",
            "customer_name": name[:30],
            "customer_surname": surname[:30],
            "customer_email": first_booking.traveler_email or "client@easytravel.cm",
            "customer_phone_number": phone[:20],
            "customer_address": "Cameroun",
            "customer_city": city_name[:30],
            "customer_country": "CM",
            "customer_state": "CM",
            "customer_zip_code": "00237",
        }

        try:
            url = f"{self.base_url}/payment"
            resp = requests.post(url, json=payload, timeout=25)
            data = resp.json()

            code = str(data.get('code', ''))
            # CinetPay v2 returns code '201' on successful creation
            if resp.status_code == 200 and (code == '201' or data.get('status') == 'SUCCESS'):
                payment_url = data.get('data', {}).get('payment_url')
                return True, {"payment_url": payment_url, "raw": data}, tx_id
            else:
                msg = data.get('message') or data.get('description') or "Erreur lors de la création du paiement CinetPay."
                logger.error(f"CinetPay payment initiation error: {data}")
                return False, {"message": msg, "raw": data}, tx_id

        except requests.exceptions.RequestException as e:
            logger.exception("Network error while connecting to CinetPay API.")
            return False, {"message": f"Erreur de communication avec CinetPay : {str(e)}"}, tx_id

    def check_payment(self, transaction_id):
        """
        Direct server-to-server check of a transaction status on CinetPay.
        Returns:
            (success: bool, data: dict)
        """
        if not self.is_configured():
            return False, {"message": "CinetPay non configuré."}

        payload = {
            "apikey": self.api_key,
            "site_id": str(self.site_id),
            "transaction_id": transaction_id,
        }

        try:
            url = f"{self.base_url}/payment/check"
            resp = requests.post(url, json=payload, timeout=20)
            data = resp.json()
            code = str(data.get('code', ''))

            # Code '00' is the official success code for CinetPay check
            if code == '00':
                return True, data
            return False, data
        except requests.exceptions.RequestException as e:
            logger.exception("Error checking transaction on CinetPay.")
            return False, {"message": str(e)}

    def verify_and_update_booking(self, transaction_id):
        """
        Verifies transaction status directly with CinetPay and updates Booking or BookingCart accordingly.
        Returns:
            (updated: bool, obj: Booking | BookingCart | None, message: str)
        """
        from bookings.models import BookingCart
        
        from django.db import transaction
        is_cart = transaction_id.startswith('ET-CRT-')

        with transaction.atomic():
            if is_cart:
                obj = BookingCart.objects.select_for_update().filter(transaction_id=transaction_id).first()
                if not obj:
                    logger.warning(f"Cart not found for transaction_id={transaction_id}")
                    return False, None, "Panier introuvable."
                if obj.payment_status == 'paid':
                    return True, obj, "Panier déjà réglé et confirmé."
            else:
                obj = Booking.objects.select_for_update().filter(transaction_id=transaction_id).first()
                if not obj:
                    logger.warning(f"Booking not found for transaction_id={transaction_id}")
                    return False, None, "Réservation introuvable."
                if obj.payment_status == 'paid':
                    return True, obj, "Réservation déjà réglée et confirmée."

            success, check_data = self.check_payment(transaction_id)
            if success:
                data_info = check_data.get('data', {})
                status = str(data_info.get('status', '')).upper()
                operator = data_info.get('operator_id') or data_info.get('payment_method') or 'cinetpay'
                
                # Verify amount and currency
                pay_amount = int(data_info.get('amount', 0))
                pay_currency = data_info.get('currency', '')
                expected_amount = int(obj.total_amount)
                
                if status == 'ACCEPTED':
                    if pay_amount < expected_amount or pay_currency != self.currency:
                        logger.error(f"Montant/Devise invalide pour {transaction_id}. Reçu: {pay_amount} {pay_currency}, Attendu: {expected_amount} {self.currency}")
                        obj.payment_status = 'failed'
                        obj.save(update_fields=['payment_status'])
                        if is_cart:
                            obj.bookings.update(payment_status='failed')
                        return False, obj, "Le montant ou la devise du paiement ne correspondent pas."
                        
                    obj.payment_status = 'paid'
                    if not is_cart:
                        obj.payment_method = 'online'
                        obj.payment_operator = str(operator)
                        obj.status = 'confirmed'
                        obj.paid_at = timezone.now()
                        obj.save(update_fields=['payment_status', 'payment_method', 'payment_operator', 'status', 'paid_at'])
                    else:
                        obj.save(update_fields=['payment_status'])
                        # Update all bookings in cart
                        for b in obj.bookings.all():
                            b.payment_status = 'paid'
                            b.payment_method = 'online'
                            b.payment_operator = str(operator)
                            b.status = 'confirmed'
                            b.paid_at = timezone.now()
                            b.save(update_fields=['payment_status', 'payment_method', 'payment_operator', 'status', 'paid_at'])

                    logger.info(f"Payment {transaction_id} successfully marked as PAID via CinetPay ({operator}).")
                    return True, obj, "Paiement validé avec succès."
                    
                elif status in ('REFUSED', 'FAILED', 'CANCELLED'):
                    obj.payment_status = 'failed'
                    obj.save(update_fields=['payment_status'])
                    if is_cart:
                        obj.bookings.update(payment_status='failed')
                    return False, obj, f"Paiement refusé ou annulé ({status})."
                else:
                    return False, obj, f"Paiement en attente de confirmation ({status})."
            else:
                return False, obj, "Impossible de vérifier le statut auprès de CinetPay."
