"""
Views for CinetPay Payment Processing in EasyTravel.
Handles payment initiation, CinetPay IPN webhook notification, and customer return redirection.
"""

import json
import logging
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.conf import settings

from bookings.models import Booking
from .services.cinetpay import CinetPayService

logger = logging.getLogger(__name__)


def initiate_booking_payment(request, booking_id):
    """
    Initiates online payment with CinetPay (Orange Money, MTN MoMo, Carte Bancaire)
    and redirects user to the CinetPay hosted checkout page.
    """
    booking = get_object_or_404(Booking, id=booking_id)

    # If already paid, take directly to confirmed ticket
    if booking.payment_status == 'paid':
        messages.info(request, "Cette réservation a déjà été entièrement réglée.")
        return redirect('bookings:confirmation', reference=booking.reference)

    # Build callback URLs
    return_url = getattr(settings, 'CINETPAY_RETURN_URL', '') or request.build_absolute_uri(reverse('payments:return'))
    notify_url = getattr(settings, 'CINETPAY_NOTIFY_URL', '') or request.build_absolute_uri(reverse('payments:notification'))

    # Store transaction context in session for return fallback
    request.session['last_payment_booking_ref'] = booking.reference

    service = CinetPayService()
    if not service.is_configured():
        messages.warning(
            request, 
            "Le service de paiement en ligne CinetPay est en cours de configuration. "
            "Vous pourrez effectuer votre règlement au guichet de l'agence."
        )
        return redirect('bookings:confirmation', reference=booking.reference)

    success, result, tx_id = service.initiate_payment(
        booking=booking,
        return_url=return_url,
        notify_url=notify_url,
    )

    if success and result.get('payment_url'):
        request.session['current_payment_tx_id'] = tx_id
        return redirect(result['payment_url'])
    else:
        error_msg = result.get('message', "Une erreur est survenue lors de l'initialisation du paiement.")
        messages.error(request, f"Paiement en ligne indisponible : {error_msg}")
        return redirect('bookings:confirmation', reference=booking.reference)


@csrf_exempt
@require_POST
def cinetpay_notification(request):
    """
    Instant Payment Notification (IPN) webhook called by CinetPay.
    Performs server-to-server validation to avoid spoofing and securely updates Booking.
    """
    # CinetPay can send data as JSON or form-encoded POST
    data = {}
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            return HttpResponseBadRequest("Invalid JSON")
    else:
        data = request.POST.dict()

    # Extract transaction identifier
    tx_id = (
        data.get('cpm_trans_id') or 
        data.get('transaction_id') or 
        data.get('trans_id')
    )

    if not tx_id:
        logger.warning(f"CinetPay IPN received without transaction identifier: {data}")
        return HttpResponseBadRequest("Missing transaction_id")

    logger.info(f"Received CinetPay IPN for transaction_id: {tx_id}")
    service = CinetPayService()
    updated, booking, message = service.verify_and_update_booking(tx_id)

    # CinetPay expects HTTP 200 with JSON or text
    return JsonResponse({
        "status": "success" if updated else "pending_or_failed",
        "message": message,
        "transaction_id": tx_id,
    }, status=200)


def cinetpay_return(request):
    """
    User landing page when redirected back from CinetPay Checkout.
    Verifies transaction status and redirects to official boarding pass.
    """
    tx_id = (
        request.GET.get('transaction_id') or 
        request.GET.get('cpm_trans_id') or 
        request.POST.get('transaction_id') or 
        request.session.get('current_payment_tx_id')
    )

    booking = None
    if tx_id:
        service = CinetPayService()
        updated, booking, message = service.verify_and_update_booking(tx_id)
        if booking:
            if booking.payment_status == 'paid':
                messages.success(request, "🎉 Votre paiement a été validé avec succès ! Votre billet est confirmé.")
            elif booking.payment_status == 'failed':
                messages.error(request, "Le paiement a été interrompu ou refusé par l'opérateur. Vous pouvez réessayer.")
            else:
                messages.info(request, "Votre transaction est en cours de finalisation par votre opérateur Mobile Money.")
            return redirect('bookings:confirmation', reference=booking.reference)

    # Fallback to session reference if available
    ref = request.session.get('last_payment_booking_ref')
    if ref:
        booking = Booking.objects.filter(reference=ref).first()
        if booking:
            return redirect('bookings:confirmation', reference=booking.reference)

    messages.info(request, "Transaction terminée. Consultez vos réservations ci-dessous.")
    return redirect('accounts:my_bookings')
