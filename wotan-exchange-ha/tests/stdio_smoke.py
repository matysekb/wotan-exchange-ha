"""Actual stdio initialize + tools/list, without EWS or tunnel traffic."""
import json
import os
import subprocess
import sys

expected={'list_mail_folders','search_mail','read_mail','resolve_people','save_mail_draft','edit_mail_draft','continue_action','weekly_report','read_calendar','find_meeting_times','save_meeting','send_meeting_invitation'}
p=subprocess.Popen([sys.executable,'-m','exchange_ews_mcp','serve'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',env=os.environ.copy())
frames=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'offline-smoke','version':'1'}}},
        {'jsonrpc':'2.0','method':'notifications/initialized'},
        {'jsonrpc':'2.0','id':2,'method':'tools/list','params':{}}]
try:
 out,err=p.communicate('\n'.join(json.dumps(f) for f in frames)+'\n',timeout=30)
 responses=[json.loads(line) for line in out.splitlines() if line.strip()]
 assert any(f.get('id')==1 and 'result' in f for f in responses),responses
 result=next(f['result'] for f in responses if f.get('id')==2)
 assert {t['name'] for t in result['tools']}==expected
 assert len(result['tools'])==12
 print('PASS: real stdio initialize and tools/list; 12 production tools')
except BaseException:
 p.kill();p.communicate();raise
