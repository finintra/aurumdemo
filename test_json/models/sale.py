from odoo import api, models, fields


class SaleOrder(models.Model):
    _inherit = "sale.order"

    total_subtotal = fields.Monetary(compute="_compute_total_subtotal")

    @api.depends("order_line.subtotal")
    def _compute_total_subtotal(self):
        for record in self:
            record.total_subtotal = sum(record.order_line.mapped("subtotal"))

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_standard_price = fields.Float(related="product_id.standard_price")
    labor_hours = fields.Float()
    subtotal = fields.Monetary()
