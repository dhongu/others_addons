# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
from odoo import models


class DataQueueMixinEpt(models.AbstractModel):
    _name = 'data.queue.mixin.ept'
    _description = 'Data Queue Mixin'

    def delete_data_queue_ept(self, queue_detail=[], is_delete_queue=False):
        """  Uses to delete unused data of queues and log book. logbook deletes which created before 7 days ago.
            @param queue_detail: list of queue records, like product, order queue [['product_queue',
            'order_queue']]
            @param is_delete_queue: Identification to delete queue
            @author: Dipak Gogiya
            Migration done by Haresh Mori on September 2021
        """
        if queue_detail:
            try:
                queue_detail += ['common_log_book_ept']
                queue_detail = list(set(queue_detail))
                for tbl_name in queue_detail:
                    if is_delete_queue:
                        self._cr.execute("""delete from %s """ % str(tbl_name))
                        continue
                    self._cr.execute(
                        """delete from %s where cast(create_date as Date) <= current_date - %d""" % (str(tbl_name), 7))
            except Exception as error:
                return error
        return True
