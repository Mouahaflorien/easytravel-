import re
from django.core.exceptions import ValidationError
from django.core.validators import validate_email as django_validate_email

def validate_cameroon_phone(phone_raw):
    """
    Valide et normalise un numéro de téléphone avec détection intelligente de l'indicatif régional :
    - Cameroun (+237) : 9 chiffres débutant par 6 (mobile) ou 2 (fixe) -> +237 6XX XXX XXX
    - Allemagne / Europe (+49) : indicatif +49 ou format national 015x/016x/017x -> +49 1XX XXXX XXXX
    - France (+33) : indicatif +33 ou format national 06/07 -> +33 6 XX XX XX XX
    - International (+...) : norme E.164 (8 à 15 chiffres)
    """
    if not phone_raw:
        raise ValidationError("Le numéro de téléphone est obligatoire.")
    
    raw = str(phone_raw).strip()
    digits = re.sub(r'[^\d+]', '', raw)
    clean_pure_digits = re.sub(r'\D', '', digits)
    
    # 1. Cas Allemagne (+49, 0049 ou préfixe 01xx)
    if digits.startswith('+49') or digits.startswith('0049'):
        core = clean_pure_digits[2:] if digits.startswith('+49') else clean_pure_digits[4:]
        if len(core) < 9 or len(core) > 13:
            raise ValidationError("Numéro allemand invalide : doit comporter entre 9 et 12 chiffres après l'indicatif +49.")
        return f"+49 {core[:3]} {core[3:7]} {core[7:]}".strip()
    elif digits.startswith('01') and len(clean_pure_digits) in (11, 12):
        core = clean_pure_digits[1:]
        return f"+49 {core[:3]} {core[3:7]} {core[7:]}".strip()

    # 2. Cas France (+33, 0033 ou préfixe 06/07)
    if digits.startswith('+33') or digits.startswith('0033'):
        core = clean_pure_digits[2:] if digits.startswith('+33') else clean_pure_digits[4:]
        if len(core) != 9:
            raise ValidationError("Numéro français invalide : doit comporter 9 chiffres après l'indicatif +33.")
        return f"+33 {core[0]} {core[1:3]} {core[3:5]} {core[5:7]} {core[7:9]}"
    elif len(clean_pure_digits) == 10 and clean_pure_digits.startswith(('06', '07')):
        core = clean_pure_digits[1:]
        return f"+33 {core[0]} {core[1:3]} {core[3:5]} {core[5:7]} {core[7:9]}"

    # 3. Cas Cameroun (+237, 237, 00237, ou 9 chiffres locaux débutant par 6 ou 2)
    core_cmr = clean_pure_digits
    if core_cmr.startswith('00237'):
        core_cmr = core_cmr[5:]
    elif core_cmr.startswith('237') and len(core_cmr) == 12:
        core_cmr = core_cmr[3:]
        
    if len(core_cmr) == 9:
        if core_cmr[0] not in ['6', '2']:
            raise ValidationError("Numéro camerounais invalide : les numéros au Cameroun commencent par un 6 (Orange, MTN, Camtel, Nexttel) ou un 2.")
        return f"+237 {core_cmr[:3]} {core_cmr[3:6]} {core_cmr[6:]}"

    # 4. Cas International générique avec indicatif '+'
    if digits.startswith('+'):
        if len(clean_pure_digits) < 8 or len(clean_pure_digits) > 15:
            raise ValidationError("Numéro international invalide : doit comporter entre 8 et 15 chiffres selon la norme internationale.")
        match = re.match(r'(\+\d{1,3})(.*)', digits)
        if match:
            code, rest = match.groups()
            chunks = [rest[i:i+3] for i in range(0, len(rest), 3)]
            return f"{code} {' '.join(chunks)}"

    # Si 9 chiffres ont été saisis sans indicatif, orienter vers le format Cameroun
    if len(clean_pure_digits) < 9:
        raise ValidationError("Numéro de téléphone incomplet (au moins 9 chiffres requis).")
    
    raise ValidationError("Format de numéro non reconnu. Veuillez inclure l'indicatif (ex: +237 pour le Cameroun, +49 pour l'Allemagne).")


def validate_clean_email(email_raw):
    """
    Valide une adresse email et s'assure qu'elle est renseignée.
    """
    if not email_raw or not str(email_raw).strip():
        raise ValidationError("L'adresse email est obligatoire pour recevoir votre e-billet.")
    email = str(email_raw).strip().lower()
    django_validate_email(email)
    return email


def validate_identity_info(id_type, id_number):
    """
    Valide le type et le numéro de la pièce d'identité selon les normes des agences au Cameroun.
    """
    valid_types = ['CNI', 'PASSPORT', 'RECEIPT']
    if id_type not in valid_types:
        raise ValidationError("Type de pièce d'identité invalide. Choisissez CNI, Passeport ou Récépissé.")
        
    if not id_number or len(str(id_number).strip()) < 5:
        raise ValidationError("Le numéro de pièce d'identité est obligatoire et doit comporter au moins 5 caractères.")
        
    return id_type, str(id_number).strip().upper()
