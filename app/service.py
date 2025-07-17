# cyberark_v3.py (module Ansible)
from ansible.module_utils.basic import AnsibleModule

def run_async(coroutine):
    """Run async coroutine from sync context"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coroutine)
    finally:
        loop.close()

def create_account(module: AnsibleModule) -> Dict:
    """Sync wrapper for Ansible"""
    service = CyberArkService(
        cyberark_env=module.params['cyberark_env'],
        cert=module.params['cyberark_cert'],
        key=module.params['cyberark_key']
    )
    
    try:
        success, result = run_async(service.create_account(
            ecosystem=module.params['ecosystem'],
            zone=module.params['zone'],
            address=module.params['address'],
            env=module.params['env'],
            port=module.params['port'],
            database=module.params['database'],
            techno=module.params['techno'],
            list_schemas=module.params.get('list_schemas'),
            list_admin=module.params.get('list_admin')
        ))
        
        if success:
            return {"changed": True, "accounts": result}
        else:
            module.fail_json(msg="Partial failure", accounts=result)
            
    except CyberArkException as e:
        module.fail_json(msg=str(e))
