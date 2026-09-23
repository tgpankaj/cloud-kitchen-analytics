"""
CSV Upload Routes
Handles order data ingestion.
"""
from flask import Blueprint, request, jsonify
from middleware.auth import token_required
from services.csv_processor import process_orders_csv, CSVValidationError
from db.connection import execute_query
import pandas as pd
import io

upload_bp = Blueprint('upload', __name__)


@upload_bp.route('/csv', methods=['POST'])
@token_required
def upload_csv():
    """
    Upload CSV file with order data.
    Expects: multipart/form-data with 'file' and 'kitchen_id'
    """
    # Check file present
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']

    if not file.filename:
        return jsonify({'error': 'Empty filename'}), 400

    if not file.filename.lower().endswith('.csv'):
        return jsonify({'error': 'Only .csv files are allowed'}), 400

    # Get kitchen_id (from form or use default)
    kitchen_id = request.form.get('kitchen_id')
    if not kitchen_id:
        # Fallback: get user's first kitchen
        kitchens = execute_query(
            "SELECT id FROM kitchens WHERE user_id = %s ORDER BY id LIMIT 1",
            (request.user_id,)
        )
        if not kitchens:
            return jsonify({'error': 'No kitchen found for user'}), 404
        kitchen_id = kitchens[0]['id']
    else:
        try:
            kitchen_id = int(kitchen_id)
        except ValueError:
            return jsonify({'error': 'Invalid kitchen_id'}), 400

    # Verify kitchen belongs to user
    kitchen = execute_query(
        "SELECT id FROM kitchens WHERE id = %s AND user_id = %s",
        (kitchen_id, request.user_id)
    )
    if not kitchen:
        return jsonify({'error': 'Kitchen not found or access denied'}), 403

    # Parse CSV
    try:
        content = file.read()

        # Try UTF-8 first
        try:
            text = content.decode('utf-8')
        except UnicodeDecodeError:
            # Try latin-1 fallback
            text = content.decode('latin-1')

        df = pd.read_csv(io.StringIO(text))

    except pd.errors.EmptyDataError:
        return jsonify({'error': 'CSV file is empty'}), 400
    except pd.errors.ParserError as e:
        return jsonify({'error': f'CSV parsing error: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to read CSV: {str(e)}'}), 400

    # Process
    try:
        stats = process_orders_csv(df, kitchen_id)
    except CSVValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

    return jsonify({
        'message': 'Upload successful',
        'kitchen_id': kitchen_id,
        'stats': stats
    }), 201


@upload_bp.route('/history', methods=['GET'])
@token_required
def upload_history():
    """Get upload history for user's kitchens."""
    uploads = execute_query("""
        SELECT u.id, u.filename, u.rows_inserted, u.rows_failed,
               u.uploaded_at, k.name AS kitchen_name
        FROM uploads u
        JOIN kitchens k ON k.id = u.kitchen_id
        WHERE k.user_id = %s
        ORDER BY u.uploaded_at DESC
        LIMIT 20
    """, (request.user_id,))

    return jsonify([dict(u) for u in uploads])


@upload_bp.route('/template', methods=['GET'])
def download_template():
    """Return CSV template as response."""
    template = (
        "order_date,order_time,platform,customer_phone,item_name,"
        "quantity,unit_price,commission_pct,prep_time,delivery_time,status\n"
        "2026-01-15,19:30,Swiggy,9876543210,Paneer Tikka,2,300,25,15,35,delivered\n"
        "2026-01-15,20:15,Zomato,9876543211,Chicken Biryani,1,350,28,20,40,delivered\n"
        "2026-01-15,21:00,Swiggy,9876543212,Dal Makhani,1,250,25,12,30,delivered\n"
    )

    return jsonify({
        'template': template,
        'columns': {
            'required': ['order_date', 'platform', 'item_name', 'quantity', 'unit_price'],
            'optional': ['order_time', 'customer_phone', 'commission_pct',
                         'prep_time', 'delivery_time', 'status']
        }
    })

