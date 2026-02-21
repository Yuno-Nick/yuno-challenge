"""Pipeline control API endpoints."""
from fastapi import APIRouter, BackgroundTasks
from app.simulator.stream import TransactionStream
from app.pipeline.processor import process_batch
from app.database import get_supabase, insert_transactions, insert_risk_assessments
import time
import threading

router = APIRouter()

# Pipeline state
_pipeline_running = False
_pipeline_thread = None
_stream = None
_stats = {
    "status": "stopped",
    "processed": 0,
    "total": 0,
    "batches": 0,
}


def _run_pipeline():
    """Background pipeline processing loop."""
    global _pipeline_running, _stream, _stats

    _stream = TransactionStream(batch_size=10)
    _stats["total"] = _stream.total_transactions
    _stats["status"] = "running"
    _stats["processed"] = 0
    _stats["batches"] = 0

    client = get_supabase()
    all_processed = []

    while _pipeline_running and not _stream.is_exhausted:
        batch = _stream.get_next_batch()
        if not batch:
            break

        # Insert transactions into DB
        try:
            txn_data = []
            for t in batch:
                txn_dict = dict(t)
                if "is_fraudulent" in txn_dict:
                    txn_dict["is_fraudulent"] = bool(txn_dict["is_fraudulent"])
                txn_data.append(txn_dict)
            insert_transactions(txn_data)
        except Exception as e:
            print(f"Error inserting transactions: {e}")

        # Process through fraud detection pipeline
        assessments = process_batch(batch, all_processed)

        # Store risk assessments
        try:
            assessment_data = []
            for a in assessments:
                a_dict = dict(a)
                if "triggered_rules" in a_dict and isinstance(a_dict["triggered_rules"], list):
                    a_dict["triggered_rules"] = a_dict["triggered_rules"]
                assessment_data.append(a_dict)
            insert_risk_assessments(assessment_data)
        except Exception as e:
            print(f"Error inserting assessments: {e}")

        all_processed.extend(batch)
        _stats["processed"] = len(all_processed)
        _stats["batches"] += 1

        time.sleep(3)  # Simulate real-time interval

    _stats["status"] = "completed" if _stream.is_exhausted else "stopped"
    _pipeline_running = False


@router.post("/start")
def start_pipeline():
    """Start the fraud detection pipeline."""
    global _pipeline_running, _pipeline_thread

    if _pipeline_running:
        return {"status": "already_running", "stats": _stats}

    _pipeline_running = True
    _pipeline_thread = threading.Thread(target=_run_pipeline, daemon=True)
    _pipeline_thread.start()

    return {"status": "started", "message": "Pipeline started processing transactions"}


@router.post("/stop")
def stop_pipeline():
    """Stop the pipeline."""
    global _pipeline_running
    _pipeline_running = False
    _stats["status"] = "stopped"
    return {"status": "stopped"}


@router.get("/status")
def pipeline_status():
    """Get pipeline status."""
    return {
        "status": _stats["status"],
        "processed": _stats["processed"],
        "total": _stats["total"],
        "batches": _stats["batches"],
        "progress": round(_stats["processed"] / _stats["total"] * 100, 1) if _stats["total"] > 0 else 0,
    }


@router.post("/reset")
def reset_pipeline():
    """Reset pipeline to process from beginning."""
    global _pipeline_running, _stream, _stats

    if _pipeline_running:
        _pipeline_running = False
        time.sleep(1)

    # Clear existing data
    client = get_supabase()
    try:
        client.table("risk_assessments").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        client.table("transactions").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    except Exception as e:
        print(f"Error clearing data: {e}")

    _stats = {"status": "stopped", "processed": 0, "total": 0, "batches": 0}
    _stream = None

    return {"status": "reset", "message": "Pipeline reset. Data cleared."}
