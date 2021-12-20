{
    "name": "JSON Parser",
    "version": "14.0.0.0.0",
    "depends": ["contacts", "purchase", "purchase_stock", "sale_management", "stock", "sale_timesheet", "timesheet_grid", "uom"],
    "description": """
        JSON Parser module
    """,
    "data": [
        "security/ir.model.access.csv",
        "wizard/upload_json_views.xml",
        "views/sale_report_views.xml",
        "views/sale_views.xml",
        "data/product_category_data.xml",
    ],
    "application": True,
    "sequence": -100,
}
