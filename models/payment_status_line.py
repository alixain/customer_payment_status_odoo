from odoo import models, fields

class PaymentStatusLine(models.TransientModel):
    _name = 'payment.status.line'
    _description = 'Payment Status Line'

    date = fields.Date('Date')
    reference = fields.Char('Reference')
    description = fields.Char('Description')
    debit = fields.Float('Debit')
    credit = fields.Float('Credit')
    balance = fields.Float('Balance')
    status = fields.Char('Status')
    highlight = fields.Boolean('Highlight')