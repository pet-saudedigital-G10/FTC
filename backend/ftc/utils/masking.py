from __future__ import annotations

import re


def mask_name(value: str | None) -> str:
    if not isinstance(value, str):
        return ''

    partes = value.strip().split()
    if not partes:
        return ''

    resultado = [
        parte[0] + '*' * (len(parte) - 1)
        for parte in partes
    ]
    return ' '.join(resultado)


def mask_cpf(value: str | None) -> str:
    if not isinstance(value, str):
        return ''

    digits = re.sub(r'\D', '', value)
    if len(digits) != 11:
        return ''

    return f'***.***.***-{digits[-2:]}'


def mask_cns(value: str | None) -> str:
    if not isinstance(value, str):
        return ''

    digits = re.sub(r'\D', '', value)
    if len(digits) != 15:
        return ''

    return f"{'*' * 11}{digits[-4:]}"
