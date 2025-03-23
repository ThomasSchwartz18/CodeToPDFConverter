from flask import Blueprint, jsonify
from app.services.counter_service import CounterService

api_bp = Blueprint('api', __name__)
counter_service = CounterService()

@api_bp.route("/pdf_count")
def pdf_count():
    """Get the current PDF conversion count."""
    current_count = counter_service.get_count()
    return jsonify({"count": current_count}) 