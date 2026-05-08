# app/routers/admin.py
@router.get("/super/stats")
def super_stats(db: Session = Depends(get_db)):
    total_tenants = db.query(Tenant).count()
    total_appointments = db.query(Appointment).count()
    total_leads = db.query(Lead).count()
    total_doctors = db.query(Doctor).count()
    return {
        "tenants": total_tenants,
        "appointments": total_appointments,
        "leads": total_leads,
        "doctors": total_doctors,
        "estimated_mrr": total_tenants * 3000
    }