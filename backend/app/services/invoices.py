import uuid


def generate_invoice_number(tenant_id) -> str:
    tenant_prefix = str(tenant_id)[:6].upper()
    unique_suffix = uuid.uuid4().hex[:8].upper()
    return f"INV-{tenant_prefix}-{unique_suffix}"
