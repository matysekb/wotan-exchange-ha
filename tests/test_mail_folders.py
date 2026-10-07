"""Offline protocol and regression tests; no credentials or network needed."""
import unittest
from unittest.mock import Mock
from xml.etree import ElementTree as ET
from exchange_ews_mcp.config import AppConfig
from exchange_ews_mcp.ews import EwsClient, normalize_mail_folder
from exchange_ews_mcp.errors import EwsError
from exchange_ews_mcp.xml_builder import (q, MESSAGES_NS as M, TYPES_NS as T,
    build_find_folders_request, build_find_items_request, SearchCriteria)

def page(last=True, offset=100, name='Archiv', folder_id='A', klass='IPF.Note', parent='ROOT'):
    root=ET.Element('response')
    rf=ET.SubElement(root,q(M,'RootFolder'),IncludesLastItemInRange=str(last).lower(),IndexedPagingOffset=str(offset))
    folders=ET.SubElement(rf,q(T,'Folders'))
    f=ET.SubElement(folders,q(T,'Folder'))
    ET.SubElement(f,q(T,'FolderId'),Id=folder_id,ChangeKey='changes')
    ET.SubElement(f,q(T,'ParentFolderId'),Id=parent)
    ET.SubElement(f,q(T,'DisplayName')).text=name
    ET.SubElement(f,q(T,'FolderClass')).text=klass
    return root

class FolderTests(unittest.TestCase):
    def setUp(self):
        self.client=EwsClient(AppConfig(ews_url='https://mail.example.invalid/EWS/Exchange.asmx',username='TEST\\dummy'), 'dummy')
        self.client._post=Mock(return_value=b'not-used')
        self.client._parse_xml=Mock(return_value=page())
        self.client._raise_for_ews_error=Mock()

    def test_aliases_preserved(self):
        for name in ['inbox','sentitems','drafts','deleteditems','junkemail','outbox']:
            self.assertEqual(normalize_mail_folder(name),name)

    def test_primary_and_archive_xml(self):
        for scope,expected in [('primary','msgfolderroot'),('archive','archivemsgfolderroot')]:
            root=ET.fromstring(build_find_folders_request('Exchange2010_SP2',scope,100))
            self.assertEqual(root.find('.//'+q(T,'DistinguishedFolderId')).get('Id'),expected)
            self.assertEqual(root.find('.//'+q(M,'FindFolder')).get('Traversal'),'Deep')
            self.assertEqual(root.find('.//'+q(M,'IndexedPageFolderView')).get('Offset'),'100')

    def test_stable_reference_no_raw_ids_and_rename(self):
        result=self.client.list_mail_folders()
        ref=result['folders'][0]['folder_ref']
        self.assertTrue(result['complete'])
        self.assertTrue(result['folders'][0]['searchable'])
        self.client._parse_xml.return_value=page(name='Renamed')
        self.assertEqual(self.client.list_mail_folders()['folders'][0]['folder_ref'],ref)
        self.assertEqual(self.client.resolve_mail_folder(ref),'A')
        self.assertNotIn('id', result['folders'][0])
        self.assertNotEqual(self.client._folder_ref('archive','A'),ref)

    def test_foreign_reference_rejected(self):
        other=EwsClient(AppConfig(ews_url=self.client.config.ews_url,username='other'),'dummy')
        with self.assertRaises(ValueError):
            self.client.resolve_mail_folder(other._folder_ref('primary','A'))

    def test_nonmail_and_stale_rejected(self):
        ref=self.client._folder_ref('primary','A')
        self.client._parse_xml.return_value=page(klass='IPF.Appointment')
        with self.assertRaises(ValueError): self.client.resolve_mail_folder(ref)
        self.client._parse_xml.return_value=page(folder_id='B')
        with self.assertRaises(ValueError): self.client.resolve_mail_folder(ref)

    def test_parent_tree_and_duplicate_display_names(self):
        first=page(); container=first.find('.//'+q(T,'Folders'))
        container.append(page(folder_id='B',parent='A').find('.//'+q(T,'Folder')))
        self.client._parse_xml.return_value=first
        rows=self.client.list_mail_folders()['folders']
        self.assertEqual(rows[1]['parent_ref'],rows[0]['folder_ref'])
        self.assertNotEqual(rows[0]['folder_ref'],rows[1]['folder_ref'])

    def test_paging(self):
        self.client._parse_xml.side_effect=[page(last=False),page(folder_id='B')]
        self.assertEqual(len(self.client.list_mail_folders()['folders']),2)
        self.assertEqual(self.client._post.call_count,2)

    def test_bad_paging_fails_closed(self):
        self.client._parse_xml.return_value=page(last=False,offset=0)
        with self.assertRaises(EwsError): self.client.list_mail_folders()

    def test_archive_failure_is_not_empty_success(self):
        self.client._raise_for_ews_error.side_effect=EwsError('dummy-server-error')
        result=self.client.list_mail_folders(scope='archive')
        self.assertFalse(result['complete'])
        self.assertEqual(result['status'],'unavailable_or_error')
        with self.assertRaises(EwsError): self.client.list_mail_folders()

    def test_xml_escaping_and_standard_target(self):
        args=dict(exchange_version='Exchange2010_SP2',folder='inbox',limit=20,offset=0,criteria=SearchCriteria())
        root=ET.fromstring(build_find_items_request(**args,folder_id='A<&"'))
        self.assertEqual(root.find('.//'+q(T,'FolderId')).get('Id'),'A<&"')
        self.assertIsNone(root.find('.//'+q(T,'DistinguishedFolderId')))
        root=ET.fromstring(build_find_items_request(**args))
        self.assertEqual(root.find('.//'+q(T,'DistinguishedFolderId')).get('Id'),'inbox')

    def test_search_revalidates_reference(self):
        ref=self.client._folder_ref('primary','A')
        response=ET.Element('response'); rf=ET.SubElement(response,q(M,'RootFolder'),IncludesLastItemInRange='true'); ET.SubElement(rf,q(T,'Items'))
        self.client._parse_xml.side_effect=[page(),response]
        result=self.client.search_emails(folder=ref)
        self.assertEqual(result['folder'],ref)
        request=ET.fromstring(self.client._post.call_args.args[0])
        self.assertEqual(request.find('.//'+q(T,'FolderId')).get('Id'),'A')

    def test_invalid_inputs_no_network(self):
        for value in ['Archive', 'A', 'folder_v1_primary_bad', '<FolderId/>']:
            with self.assertRaises(ValueError): self.client.search_emails(folder=value)
        self.client._post.assert_not_called()

    def test_multiple_folders_deduplicated_and_bounded(self):
        self.client.search_emails=Mock(return_value=dict(items=[],returned=0,total_items_in_view=0))
        result=self.client.search_emails_multi_folder(folders=['inbox','inbox','sentitems'])
        self.assertEqual(result['folders'],['inbox','sentitems'])
        self.assertEqual(self.client.search_emails.call_count,2)
        refs=[self.client._folder_ref('primary',str(i)) for i in range(26)]
        with self.assertRaises(ValueError): self.client.search_emails_multi_folder(folders=refs)

    def test_discovery_bound(self):
        self.client._parse_xml.side_effect=[page(last=False,offset=(i+1)*100) for i in range(20)]
        with self.assertRaises(EwsError): self.client.list_mail_folders()

    def test_mixed_alias_and_ref_search(self):
        ref=self.client._folder_ref('primary','A')
        self.client.search_emails=Mock(return_value=dict(items=[],returned=0,total_items_in_view=0))
        result=self.client.search_emails_multi_folder(folders=['inbox',ref])
        self.assertEqual(result['folders'],['inbox',ref])

if __name__=='__main__': unittest.main()
