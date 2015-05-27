# -*- coding: utf-8 -*-


from openerp import exceptions
from openerp.osv import orm
from openerp.tools.translate import _
import openerp.tests.common as common


class TestJobChannel(common.TransactionCase):

    def test_root_channel(self):
        QueueJobChannel = self.registry("queue.job.channel")
        cr, uid = self.cr, self.uid
        res = QueueJobChannel.search(cr, uid, [])
        self.assertEqual(1, len(res), 'One channel is created by default')
        root_id = res[0]
        channel_info = QueueJobChannel.browse(cr, uid, root_id)
        self.assertEqual(channel_info.id, self.ref('connector.channel_root'))
        self.assertEqual(channel_info.name, 'root')
        self.assertFalse(channel_info.parent_id)

        with self.assertRaises(exceptions.Warning) as ex:
            QueueJobChannel.write(cr, uid, root_id, {'name': 'toto'})
        self.assertEqual(str(ex.exception),
                         _('Cannot change the root channel'))

        with self.assertRaises(exceptions.Warning) as ex:
            QueueJobChannel.unlink(cr, uid, root_id)
        self.assertEqual(str(ex.exception),
                         _('Cannot remove the root channel'))

    def test_child_channel(self):
        QueueJobChannel = self.registry("queue.job.channel")
        cr, uid = self.cr, self.uid
        root_id = self.ref('connector.channel_root')
        with self.assertRaises(orm.except_orm) as ex:
            QueueJobChannel.create(cr, uid, {'name': 'child'})
        self.assertEqual(str(ex.exception.value),
                         'Error occurred while validating the field(s) '
                         'parent_id: Parent channel required.')
        child_id = QueueJobChannel.create(cr, uid, {'name': 'child',
                                                    'parent_id': root_id})
        channel_info = QueueJobChannel.browse(cr, uid, child_id)
        self.assertEqual(channel_info.name, 'child')
        self.assertEqual(channel_info.parent_id.id, root_id)
        self.assertEqual(channel_info.complete_name, 'root.child')
