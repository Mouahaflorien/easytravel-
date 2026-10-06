from .models import Agency

def get_current_agency(request):
    """
    Retourne l'agence exclusive de l'utilisateur connecté.
    Garantit l'étanchéité absolue et le cloisonnement strict des données :
    chaque utilisateur est strictement rattaché à son agence et ne peut
    en aucun cas basculer vers une agence concurrente.
    """
    if not request.user.is_authenticated:
        return None
    
    # 1. L'agence à laquelle l'utilisateur est rattaché (employé ou manager)
    agency = getattr(request.user, 'agency', None)
    
    # 2. S'il n'est rattaché à aucune agence, on vérifie s'il en est le créateur/propriétaire initial
    if not agency:
        agency = request.user.agencies_owned.first()
    
    # 3. Si super-administrateur global de la plateforme (sans agence en propre)
    if not agency and (request.user.is_superuser or request.user.is_staff):
        agency_id = request.session.get('current_agency_id')
        if agency_id:
            agency = Agency.objects.filter(id=agency_id).first()
        if not agency:
            agency = Agency.objects.first()
        
    return agency

def agency_context(request):
    """
    Injecte l'agence exclusive et les notifications dans tous les templates du portail.
    Aucun sélecteur de permutation n'est exposé : chaque utilisateur est cantonné à son agence.
    """
    if not request.user.is_authenticated:
        return {
            'current_agency': None,
            'unread_notifications_count': 0,
            'pending_anomalies_count': 0,
            'recent_notifications': [],
        }
        
    current_agency = get_current_agency(request)
    
    unread_notifications_count = 0
    pending_anomalies_count = 0
    recent_notifications = []

    if current_agency:
        from .models import AuditAnomaly, AgencyNotification
        unread_notifications_count = AgencyNotification.objects.filter(agency=current_agency, is_read=False).count()
        pending_anomalies_count = AuditAnomaly.objects.filter(agency=current_agency, status='pending').count()
        recent_notifications = AgencyNotification.objects.filter(agency=current_agency).select_related('anomaly').order_by('-created_at')[:6]

    return {
        'current_agency': current_agency,
        'unread_notifications_count': unread_notifications_count,
        'pending_anomalies_count': pending_anomalies_count,
        'recent_notifications': recent_notifications,
    }


