"""Small helpers shared by exchange files. (Leading _ = not an exchange.)"""


def to_float(value):
    """'7233411 INR' -> 7233411.0; '', None, junk -> None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().split(" ")[0].replace(",", "")
    try:
        return float(text)
    except ValueError:
        return None


def zero_to_none(row, fields):
    """Some exchanges send 0 or "" when they simply have no data."""
    for f in fields:
        v = to_float(row.get(f))
        row[f] = v if v else None
    return row
