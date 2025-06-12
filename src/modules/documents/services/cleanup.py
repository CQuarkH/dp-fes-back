import os
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from modules.documents.models.document import Document, DocumentStatus

def delete_rejected_documents(session: Session):
    cutoff_date = datetime.utcnow() - timedelta(days=30)

    documents = session.query(Document).filter(
        Document.status == DocumentStatus.REJECTED,
        Document.rejection_date <= cutoff_date
    ).all()

    for doc in documents:
        try:
            if os.path.exists(doc.file_path):
                os.remove(doc.file_path)
            session.delete(doc)
        except Exception as e:
            print(f"Error deleting {doc.file_path}: {e}")

    session.commit()
