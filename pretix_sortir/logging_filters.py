"""
Filtres de logs pour redaction des données sensibles (Sécurité PHASE 2 - Point 7)
"""

import logging
import re


class SensitiveDataFilter(logging.Filter):
    """
    Filtre pour masquer automatiquement les données sensibles dans les logs.

    Redacte :
    - Numéros de carte (10 chiffres consécutifs)
    - Tokens API (mots-clés: token, api_key, authorization)
    - Clés de service
    """

    # Pattern pour détecter les numéros de carte (10+ chiffres consécutifs)
    CARD_NUMBER_PATTERN = re.compile(r'\b\d{10,}\b')

    # Pattern pour détecter les tokens (après token=, api_key=, Authorization:, etc.)
    TOKEN_PATTERNS = [
        re.compile(r'(token[=:\s]+)[^\s,}]+', re.IGNORECASE),
        re.compile(r'(api_key[=:\s]+)[^\s,}]+', re.IGNORECASE),
        re.compile(r'(authorization[=:\s]+)[^\s,}]+', re.IGNORECASE),
        re.compile(r'(bearer\s+)[^\s,}]+', re.IGNORECASE),
        re.compile(r'(clé[=:\s]+)[^\s,}]+', re.IGNORECASE),
    ]

    def filter(self, record):
        """
        Filtre les données sensibles du message de log.

        Args:
            record: LogRecord Django à filtrer

        Returns:
            True pour garder le log (toujours True, on le modifie juste)
        """
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            # Redacte les numéros de carte (sauf 4 derniers chiffres)
            record.msg = self._redact_card_numbers(record.msg)

            # Redacte les tokens API
            record.msg = self._redact_tokens(record.msg)

        # Filtre aussi les arguments du log
        if hasattr(record, 'args') and record.args:
            if isinstance(record.args, dict):
                record.args = {k: self._redact_value(v) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self._redact_value(v) for v in record.args)

        return True

    def _redact_card_numbers(self, text):
        """
        Redacte les numéros de carte, ne garde que les 4 derniers chiffres.

        Exemple: "1234567890" -> "******7890"
        """
        def replace_card(match):
            card = match.group(0)
            if len(card) >= 10:
                # Garde les 4 derniers chiffres
                return '*' * (len(card) - 4) + card[-4:]
            return card

        return self.CARD_NUMBER_PATTERN.sub(replace_card, text)

    def _redact_tokens(self, text):
        """
        Redacte les tokens API, ne garde que les 10 premiers caractères.

        Exemple: "token=abc123def456ghi789" -> "token=abc123def4**********"
        """
        for pattern in self.TOKEN_PATTERNS:
            def replace_token(match):
                prefix = match.group(1)  # "token=", "Authorization:", etc.
                full_match = match.group(0)
                token_value = full_match[len(prefix):]

                # Garde les 10 premiers caractères du token
                if len(token_value) > 10:
                    redacted = token_value[:10] + '*' * 10
                else:
                    redacted = '*' * len(token_value)

                return prefix + redacted

            text = pattern.sub(replace_token, text)

        return text

    def _redact_value(self, value):
        """Redacte une valeur si c'est une chaîne contenant des données sensibles."""
        if isinstance(value, str):
            value = self._redact_card_numbers(value)
            value = self._redact_tokens(value)
        return value


class SortirSecurityFilter(logging.Filter):
    """
    Filtre spécifique pour les logs du plugin Sortir!

    Ajoute des informations de contexte de sécurité aux logs.
    """

    def filter(self, record):
        """Ajoute le prefix [SORTIR SECURITY] aux logs de sécurité."""
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            # Détecte les logs de sécurité (rate limit, validation, erreurs auth)
            security_keywords = ['rate limit', 'token', 'authentication', 'unauthorized', 'forbidden']

            if any(keyword in record.msg.lower() for keyword in security_keywords):
                record.msg = f"[SORTIR SECURITY] {record.msg}"

        return True
