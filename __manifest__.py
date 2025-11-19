{
    'name': 'Customer Payment Status Report',
    'version': '16.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Shows customer payment status with invoice clearance tracking',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/payment_status_wizard_view.xml',
        'report/payment_status_report.xml',
        'report/payment_status_template.xml',
    ],
    'installable': True,
    'application': False,
}