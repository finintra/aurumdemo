import base64
import json

from odoo import _, models, fields
from odoo.exceptions import UserError


class UploadJson(models.TransientModel):
    _name = "upload.json"
    _description = "Wizard to upload JSON file"

    file = fields.Binary(required=True, store=True, attachment=False)
    filename = fields.Char()

    def _prepare_category(self, raw_data):
        categ_name = raw_data.get("Category")
        if not categ_name:
            return categ_name
        categ_id = self.env["product.category"].search([("name", "=", categ_name)])
        if not categ_id:
            categ_id = self.env["product.category"].create({"name": categ_name})

        subcategory_name = raw_data.get("Subcategory")
        if not subcategory_name:
            return categ_id

        subcateg_id = self.env["product.category"].search([("name", "=", subcategory_name)])
        if not subcateg_id:
            subcateg_id = self.env["product.category"].create({"name": subcategory_name, "parent_id": categ_id.id})
        return subcateg_id


    def _prepare_product(self, raw_data, product_type):
        mto_id = self.env.ref("stock.route_warehouse0_mto").id
        buy_id = self.env.ref("purchase_stock.route_warehouse0_buy").id
        manufact = raw_data.get('Manufacturer', '')
        model = raw_data.get('Model', '')
        product_name = f"{manufact}{':' if bool(model) and bool(manufact) else ''}{model}" if product_type == "consu" else raw_data.get("Phase")
        if not product_name:
            return product_name
        product_product_id = self.env["product.product"].search([("name", "=", product_name), ("type", "=", product_type)])
        if not product_product_id:
            if product_type == "consu":
                category_id = self._prepare_category(raw_data)
            else:
                category_id = self.env.ref("test_json.product_category_phase")
            if not category_id:
                return None

            product_data = {
                "name": product_name,
                "type": product_type,
                "categ_id": category_id.id,
                "standard_price": raw_data["UnitCost"] if product_type == "consu" else 0,
                "route_ids": [(4, mto_id), (4, buy_id)] if product_type == "consu" else []
            }

            if product_type == "consu":
                product_data["seller_ids"] = [(0, 0, {
                    "name": self.env.ref("test_json.test_vendor").id,
                    "price": 100.0,
                })]
            else:
                product_data["uom_id"] = self.env.ref("uom.product_uom_hour").id
                product_data["uom_po_id"] = self.env.ref("uom.product_uom_hour").id
                product_data["service_policy"] = "delivered_timesheet"
                product_data["service_tracking"] = "task_in_project"

            product_template_id = self.env["product.template"].create(product_data)
            product_product_id = self.env["product.product"].search([("product_tmpl_id", "=", product_template_id.id)])
        return product_product_id


    def action_upload(self):
        try:
            decoded_data = base64.b64decode(self.file).decode("ISO-8859-1")
            json_data = json.loads(decoded_data)
        except ValueError as e:
            raise UserError(_(f"Invalid file: {str(e)}"))

        sections = {}
        for item in json_data["Items"]:
            section_id = self._prepare_product(item, "service")
            if section_id and not section_id.name in sections:
                sections[section_id.name] = {"record": section_id, "items": {}, "hours": 0.0}
            product_id = self._prepare_product(item, "consu")
            if not product_id:
                continue
            if not product_id in sections[section_id.name]["items"]:
                sections[section_id.name]["items"][product_id] = {
                    "product_id": product_id.id,
                    "name": item["Description"] if item.get("Description") else "",
                    "product_uom_qty": item["Quantity"],
                    "price_unit": item["UnitPrice"],
                    "subtotal": item["InstallPrice"],
                    "labor_hours": item["LaborHours"],
                }
            else:
                sections[section_id.name]["items"][product_id]["product_uom_qty"] += item["Quantity"]
                sections[section_id.name]["items"][product_id]["subtotal"] += item["InstallPrice"]
                sections[section_id.name]["items"][product_id]["labor_hours"] += item["LaborHours"]
            if section_id:
                sections[section_id.name]["hours"] += item["LaborHours"]

        partner_id = self.env["res.partner"].search([("name", "=", json_data["Client"])])
        if not partner_id:
            partner_id = self.env["res.partner"].create({
                "name": json_data["Client"],
                "company_type": "person"
            })
        so_data = {
            "partner_id": partner_id.id,
            "order_line": []
        }
        for section in sections:
            so_data["order_line"].append((0, 0, {"name": section, "display_type": "line_section"}))
            for item in sections[section]["items"]:
                so_data["order_line"].append((0, 0, sections[section]["items"][item]))
        so_data["order_line"].append((0, 0, {"name": "Phases", "display_type": "line_section"}))
        for section in sections:
            so_data["order_line"].append((0, 0, {
                "product_id": sections[section]["record"].id,
                "name": section,
                "product_uom_qty": sections[section]["hours"],
                "price_unit": 100,
            }))
        self.env["sale.order"].create(so_data)