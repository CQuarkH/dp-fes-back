from apscheduler.schedulers.background import BackgroundScheduler
from modules.documents.services.cleanup import delete_rejected_documents
from database import SessionLocal

def start_deletion_job():
    scheduler = BackgroundScheduler()

    def job():
        with SessionLocal() as session:
            delete_rejected_documents(session)

    scheduler.add_job(job, 'interval', days=1)  # cada 24 horas
    scheduler.start()
