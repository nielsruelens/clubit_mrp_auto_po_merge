from openerp.osv import osv
from openerp import pooler
##############################################################################
#
#    procurement.order
#
#    This class extends the default procurement MRP scheduler behaviour
#    to automatically attempt to merge PO's created by the scheduler. They will
#    be merge according to the standard logic, with the addition of that they
#    also should be part of the same Sales Order.
#
##############################################################################

class procurement_order(osv.Model):
    _name = 'procurement.order'
    _inherit = 'procurement.order'


    def run_scheduler(self, cr, uid, automatic=False, use_new_cursor=False, context=None):
        ''' procurement.order:run_scheduler()
            ---------------------------------
            This method overwrites the standard OpenERP run_scheduler()
            method to make sure any created PO's are merged according to their
            respective Sales Orders.
            ------------------------------------------------------------------ '''
        if context: context['mrp_scheduler'] = True
        else: context = {'mrp_scheduler': True}
        result = super(procurement_order, self).run_scheduler(cr, uid, automatic, use_new_cursor, context)
        if use_new_cursor:
            use_new_cursor = cr.dbname
        cr = pooler.get_db(use_new_cursor).cursor()

        # Search for PO's in draft
        # ------------------------
        po_db = self.pool.get('purchase.order')
        so_db = self.pool.get('sale.order')
        proc_db = self.pool.get('procurement.order')
        pids = po_db.search(cr, uid, [('state', '=', 'draft')])

        # Find all individual PO origins
        # ------------------------------
        purchases = po_db.browse(cr, uid, pids, context=context)
        origins = [purchase.origin for purchase in purchases if purchase.origin]
        origins = list(set(origins))

        # Merge all PO's that have the same origin
        # ----------------------------------------
        for origin in origins:
            so_id = so_db.search(cr, uid, [('name', '=', origin)], context=context)
            ids = [purchase.id for purchase in purchases if purchase.origin == origin]
            if so_id:
                sale_order = so_db.browse(cr, uid, so_id, context=context)[0]
                if len(ids) > 1:
                    new_orders = po_db.do_merge(cr, uid, ids, context=context)
                    for new_order in new_orders:
                        po_db.write(cr, uid, [new_order], {'origin':origin, 'dest_address_id':sale_order.partner_shipping_id.id, 'partner_ref':sale_order.client_order_ref}, context=context)
                        proc_ids = proc_db.search(cr, uid, [('purchase_id', 'in', new_orders[new_order])], context=context)
                        for proc in proc_db.browse(cr, uid, proc_ids, context=context):
                            if proc.purchase_id:
                                proc_db.write(cr, uid, [proc.id], {'purchase_id': new_order}, context)
                elif len(ids) == 1:
                    po_db.write(cr, uid, ids, {'partner_ref':sale_order.client_order_ref})

        cr.commit()
        cr.close()
        return result

























