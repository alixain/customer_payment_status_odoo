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

        # First pass: separate debits and credits, calculate total credits
        invoices = []
        total_credits = 0.0
        
        for item in all_items:
            if item['is_debit']:
                invoices.append(item)
            else:
                total_credits += item['credit']

        # Second pass: FIFO allocation to invoices
        remaining_credits = total_credits
        for invoice in invoices:
            if remaining_credits >= invoice['debit']:
                invoice['status'] = 'Paid'
                invoice['highlight'] = False
                remaining_credits -= invoice['debit']
            elif remaining_credits > 0:
                invoice['status'] = 'Partial'
                invoice['highlight'] = True
                remaining_credits = 0.0
            else:
                invoice['status'] = 'Unpaid'
                invoice['highlight'] = True

        # Third pass: build final lines with running balance
        lines = []
        balance = 0.0
        
        for item in all_items:
            balance += item['amount']
            
            # Find status for invoices
            status = ''
            highlight = False
            if item['is_debit']:
                for inv in invoices:
                    if inv['reference'] == item['reference'] and inv['date'] == item['date']:
                        status = inv['status']
                        highlight = inv['highlight']
                        break
            
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