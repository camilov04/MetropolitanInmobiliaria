def clean_text(value):
    return (value or "").strip()


def parse_price_value(raw_value):
    normalized = clean_text(raw_value).replace(",", ".")
    if not normalized:
        raise ValueError("El precio es obligatorio")

    value = float(normalized)
    if value < 0:
        raise ValueError("El precio no puede ser negativo")

    return value


def missing_required_fields(values, field_names):
    return [field_name for field_name in field_names if not clean_text(values.get(field_name))]


def parse_boolean_choice(raw_value):
    return clean_text(raw_value) == "1"
