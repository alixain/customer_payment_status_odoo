from odoo import models, fields, api

class PaymentStatusWizard(models.TransientModel):
    _name = 'payment.status.wizard'
    _description = 'Payment Status Report Wizard'

    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    date_to = fields.Date(string='As of Date', default=fields.Date.context_today)

    def action_print_report(self):
        return self.env.ref('customer_payment_status.action_payment_status_report').report_action(self)

    def action_view_report(self):
        lines = self._get_report_lines()
        return {
            'name': 'Payment Status Report',
            'type': 'ir.actions.act_window',
            'res_model': 'payment.status.line',
            'view_mode': 'tree',
            'views': [(self.env.ref('customer_payment_status.view_payment_status_line_tree').id, 'tree')],
            'domain': [('id', 'in', [l['id'] for l in lines])],
            'context': {'create': False, 'delete': False, 'edit': False}
        }

    def _get_report_lines(self):
        invoices = self.env['account.move'].search([
            ('partner_id', '=', self.partner_id.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('date', '<=', self.date_to)
        ], order='date asc, name asc')

        payments = self.env['account.payment'].search([
            ('partner_id', '=', self.partner_id.id),
            ('payment_type', '=', 'inbound'),
            ('state', '=', 'posted'),
            ('date', '<=', self.date_to)
        ], order='date asc')

        lines = []
        balance = 0.0
        remaining_payment = 0.0
        first_unpaid_found = False

        # Merge invoices and payments
        all_items = []
        for inv in invoices:
            all_items.append({'type': 'invoice', 'date': inv.date, 'record': inv})
        for pay in payments:
            all_items.append({'type': 'payment', 'date': pay.date, 'record': pay})
        
        all_items.sort(key=lambda x: (x['date'], x['type'] == 'payment'))

        for item in all_items:
            if item['type'] == 'invoice':
                inv = item['record']
                balance += inv.amount_total
                
                paid_amount = 0.0
                if remaining_payment > 0:
                    if remaining_payment >= inv.amount_total:
                        paid_amount = inv.amount_total
                        remaining_payment -= inv.amount_total
                        status = 'Paid'
                    else:
                        paid_amount = remaining_payment
                        remaining_payment = 0.0
                        status = 'Partial'
                else:
                    status = 'Unpaid'

                highlight = status in ['Unpaid', 'Partial']

                lines.append({
                    'date': inv.date,
                    'reference': inv.name,
                    'description': 'Invoice',
                    'debit': inv.amount_total,
                    'credit': 0.0,
                    'balance': balance - remaining_payment,
                    'status': status,
                    'highlight': highlight
                })
            else:
                pay = item['record']
                balance -= pay.amount
                remaining_payment += pay.amount
                
                lines.append({
                    'date': pay.date,
                    'reference': pay.name,
                    'description': 'Payment',
                    'debit': 0.0,
                    'credit': pay.amount,
                    'balance': balance - remaining_payment,
                    'status': '',
                    'highlight': False
                })

        return lines