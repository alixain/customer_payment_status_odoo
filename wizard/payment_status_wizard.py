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
        
        # Create transient records for tree view
        line_ids = []
        PaymentLine = self.env['payment.status.line']
        for line in lines:
            record = PaymentLine.create({
                'date': line['date'],
                'reference': line['reference'],
                'description': line['description'],
                'debit': line['debit'],
                'credit': line['credit'],
                'balance': line['balance'],
                'status': line['status'],
                'highlight': line['highlight']
            })
            line_ids.append(record.id)
        
        return {
            'name': 'Payment Status Report',
            'type': 'ir.actions.act_window',
            'res_model': 'payment.status.line',
            'view_mode': 'tree',
            'views': [(self.env.ref('customer_payment_status.view_payment_status_line_tree').id, 'tree')],
            'domain': [('id', 'in', line_ids)],
            'context': {'create': False, 'delete': False, 'edit': False}
        }

    def _get_report_lines(self):
        # Get all account moves (invoices, credit notes, journal entries)
        moves = self.env['account.move'].search([
            ('partner_id', '=', self.partner_id.id),
            ('state', '=', 'posted'),
            ('date', '<=', self.date_to)
        ], order='date asc, name asc')

        all_items = []
        
        # Process all move lines affecting receivables
        for move in moves:
            for line in move.line_ids:
                if line.account_id.account_type == 'asset_receivable' and line.partner_id.id == self.partner_id.id:
                    amount = line.debit - line.credit
                    
                    if amount != 0:
                        move_type = dict(move._fields['move_type'].selection).get(move.move_type, 'Journal Entry')
                        
                        all_items.append({
                            'date': move.date,
                            'reference': move.name,
                            'description': move_type,
                            'debit': line.debit,
                            'credit': line.credit,
                            'amount': amount,
                            'is_debit': line.debit > 0
                        })

        # Sort by date
        all_items.sort(key=lambda x: x['date'])

        # FIFO payment allocation
        lines = []
        balance = 0.0
        available_credit = 0.0
        first_unpaid_found = False

        for item in all_items:
            balance += item['amount']
            
            status = ''
            highlight = False
            
            if item['is_debit']:  # Invoice or Debit entry
                invoice_amount = item['debit']
                
                # Apply available credits to this invoice
                if available_credit > 0:
                    if available_credit >= invoice_amount:
                        available_credit -= invoice_amount
                        status = 'Paid'
                    else:
                        available_credit = 0.0
                        status = 'Partial'
                else:
                    status = 'Unpaid'
                
                # Highlight unpaid and partial invoices
                highlight = status in ['Unpaid', 'Partial']
                    
            else:  # Payment or Credit entry
                available_credit += item['credit']
            
            lines.append({
                'date': item['date'],
                'reference': item['reference'],
                'description': item['description'],
                'debit': item['debit'],
                'credit': item['credit'],
                'balance': balance,
                'status': status,
                'highlight': highlight
            })

        return lines