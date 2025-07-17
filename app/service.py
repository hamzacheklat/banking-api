#!/usr/bin/python

import asyncio
import string
import random
import logging
from typing import Dict, List, Optional, Tuple
from functools import partial
from asgiref.sync import async_to_sync
from concurrent.futures import ThreadPoolExecutor

try:
    from ansible.module_utils import cyberark_client, robotic_helper, config
    from ansible.module_utils.cyberark_exceptions import (
        CyberArkException,
        CyberArkAPIError,
        CyberArkValidationError,
        cyberark_api_handler,
        ansible_module_handler
    )
except (ImportError, ModuleNotFoundError):
    from module_utils import cyberark_client, robotic_helper, config
    from module_utils.cyberark_exceptions import (
        CyberArkException,
        CyberArkAPIError,
        CyberArkValidationError,
        cyberark_api_handler,
        ansible_module_handler
    )


class CyberArkService:
    """High-level service for CyberArk operations with parallel processing and custom exception handling"""
    
    def __init__(self, cyberark_env: str, cert: str, key: str):
        """
        Initialize CyberArk service
        
        Args:
            cyberark_env: Environment (PRD, STG, DEV)
            cert: Path to certificate file
            key: Path to private key file
            
        Raises:
            CyberArkValidationError: If invalid parameters are provided
        """
        try:
            self.client = cyberark_client.CyberArkClient(
                env=cyberark_env,
                cert=cert,
                key=key
            )
            self.robotic_service = robotic_helper.RoboticHelper()
            self.executor = ThreadPoolExecutor(max_workers=10)
            self.logger = logging.getLogger(__name__)
            logging.basicConfig(
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                level=logging.INFO
            )
        except Exception as e:
            raise CyberArkValidationError(f"Initialization failed: {str(e)}")

    # Main public methods
    @ansible_module_handler
    def get_account(self, zone: str, safename: str, username: str, address: str) -> Dict:
        """Get account details (sync wrapper)"""
        return async_to_sync(self._async_get_account)(zone, safename, username, address)

    @ansible_module_handler
    def create_account(self, ecosystem: str, zone: str, address: str, env: str, 
                     port: str, database: str, techno: str,
                     list_schemas: List[str] = None, list_admin: List[str] = None) -> Dict:
        """Create accounts (sync wrapper)"""
        return async_to_sync(self._async_create_account)(
            ecosystem, zone, address, env, port, database, techno, list_schemas, list_admin
        )

    @ansible_module_handler
    def delete_accounts(self, account_ids: List[str]) -> Dict:
        """Delete multiple accounts in parallel (sync wrapper)"""
        return async_to_sync(self._async_delete_accounts)(account_ids)

    @ansible_module_handler
    def get_passwords(self, account_requests: List[Dict]) -> Dict:
        """Get multiple passwords in parallel (sync wrapper)"""
        return async_to_sync(self._async_get_passwords)(account_requests)

    # Async implementations with custom exception handling
    @cyberark_api_handler
    async def _async_get_account(self, zone: str, safename: str, 
                               username: str, address: str) -> Dict:
        """Actual async implementation of get_account"""
        account = await self.client.get_account(
            zone=zone,
            safe_name=safename,
            username=username,
            address=address
        )
        if not account:
            raise CyberArkAPIError(f"Account {username} not found in safe {safename}")
        return {"success": True, "account": account}

    @cyberark_api_handler
    async def _async_create_account(self, ecosystem: str, zone: str, 
                                  address: str, env: str, port: str, 
                                  database: str, techno: str,
                                  list_schemas: List[str] = None, 
                                  list_admin: List[str] = None) -> Dict:
        """Create accounts with parallel processing and error handling"""
        self._validate_inputs(ecosystem, zone, address, env, port, database, techno)
        
        accounts_to_create = self._prepare_accounts(
            ecosystem, zone, address, env, port, database, techno, 
            list_schemas, list_admin
        )
        
        tasks = [self._create_single_account(acc) for acc in accounts_to_create]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return self._format_bulk_results(results, accounts_to_create, "created")

    @cyberark_api_handler
    async def _async_delete_accounts(self, account_ids: List[str]) -> Dict:
        """Delete multiple accounts in parallel"""
        if not account_ids:
            raise CyberArkValidationError("No account IDs provided for deletion")
            
        tasks = [self.client.delete_account(acc_id) for acc_id in account_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return self._format_bulk_results(results, account_ids, "deleted")

    @cyberark_api_handler
    async def _async_get_passwords(self, account_requests: List[Dict]) -> Dict:
        """Get multiple passwords in parallel"""
        if not account_requests:
            raise CyberArkValidationError("No account requests provided")
            
        tasks = [
            self.client.get_password(
                zone=req["zone"],
                safe_name=req["safename"],
                user_name=req["username"],
                address=req["address"],
                database=req["database"]
            )
            for req in account_requests
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return self._format_bulk_results(results, account_requests, "retrieved")

    # Helper methods with error handling
    @cyberark_api_handler
    async def _create_single_account(self, account_data: Dict) -> Dict:
        """Create single account with error handling"""
        result = await self.client.create_account(**account_data)
        if "ErrorMessage" in result.get("Content", {}):
            raise CyberArkAPIError(result["Content"]["ErrorMessage"])
        return {
            "account_id": result.get("Content", {}).get("id"),
            "user_name": account_data["user_name"],
            "safe_name": account_data["safe_name"],
            "details": result
        }

    def _validate_inputs(self, ecosystem: str, zone: str, address: str,
                       env: str, port: str, database: str, techno: str) -> None:
        """Validate all input parameters"""
        if not all([ecosystem, zone, address, env, port, database, techno]):
            raise CyberArkValidationError("Missing required parameters")
        
        if env.upper() not in config.ACCOUNT_ENVIRONMENT_MAPPING:
            raise CyberArkValidationError(f"Invalid environment: {env}")
            
        if techno.lower() not in config.RECO_SAFE_TECHNO_MAPPING:
            raise CyberArkValidationError(f"Unsupported technology: {techno}")

    def _prepare_accounts(self, ecosystem: str, zone: str, address: str,
                        env: str, port: str, database: str, techno: str,
                        list_schemas: List[str], list_admin: List[str]) -> List[Dict]:
        """Prepare all account creation payloads"""
        try:
            safes = async_to_sync(self._get_safes)(ecosystem, zone, env)
            accounts = []
            
            accounts.extend(self._build_mandatory_accounts(
                ecosystem, database, address, techno, zone, env, safes
            ))
            
            if list_schemas:
                accounts.extend(self._build_schema_accounts(
                    list_schemas, safes["generic"], database, techno
                ))
            
            if list_admin:
                accounts.extend(self._build_admin_accounts(
                    list_admin, safes["service"], techno
                ))
            
            for acc in accounts:
                acc.update({
                    "zone": zone,
                    "address": address,
                    "env": env.upper(),
                    "password": self._generate_password(),
                    "env_letter": env[0].upper(),
                    "port": port,
                    "database": database,
                })
            
            return accounts
        except Exception as e:
            raise CyberArkAPIError(f"Failed to prepare accounts: {str(e)}")

    async def _get_safes(self, ecosystem: str, zone: str, env: str) -> Dict[str, str]:
        """Get safe names for the environment"""
        short_name = self.robotic_service.build_short_name_safe(
            ecosystem=ecosystem,
            region=zone
        )
        
        env_config = config.ACCOUNT_ENVIRONMENT_MAPPING.get(env.upper())
        if not env_config:
            raise CyberArkValidationError(f"Invalid environment: {env}")
            
        safe_gen = f"{short_name}--{env_config['GEN']}"
        safe_svc = f"{short_name}--{env_config['SERVICE']}"
        
        try:
            safe_exists = await self._check_safe_existence(safe_svc, zone)
            return {
                "generic": safe_gen,
                "service": safe_svc if safe_exists else safe_gen
            }
        except Exception as e:
            raise CyberArkAPIError(f"Safe check failed: {str(e)}")

    async def _check_safe_existence(self, safe_name: str, zone: str) -> bool:
        """Check if safe exists"""
        try:
            details = await self.client.get_safe_detail(
                safe_name=safe_name,
                zone=zone
            )
            return details is not None
        except Exception as e:
            self.logger.warning(f"Safe check failed for {safe_name}: {str(e)}")
            return False

    def _format_bulk_results(self, results: List, items: List, action: str) -> Dict:
        """Format results from bulk operations"""
        successes = []
        errors = []
        
        for result, item in zip(results, items):
            if isinstance(result, Exception):
                item_data = item if not isinstance(item, dict) else {
                    "user_name": item.get("user_name"),
                    "safe_name": item.get("safe_name")
                }
                errors.append({
                    "item": item_data,
                    "error": str(result)
                })
            else:
                successes.append(result)
        
        if errors:
            self.logger.error(f"Completed with {len(errors)} errors in {action} operation")
        
        return {
            f"{action}_items": successes,
            "failed_items": errors,
            "success_rate": f"{len(successes)}/{len(items)}",
            "success": len(errors) == 0
        }

    @staticmethod
    def _build_mandatory_accounts(ecosystem: str, database: str, address: str,
                                techno: str, zone: str, env: str, 
                                safes: Dict) -> List[Dict]:
        """Build mandatory accounts from config"""
        accounts = []
        
        for key, cfg in config.ACCOUNT_FUNC_CATEGORY_MAPPING.items():
            if key == "RECONCILE":
                safe_name = config.RECO_SAFE_TECHNO_MAPPING.get(techno.lower(), {}).get(zone)
                if not safe_name:
                    raise CyberArkValidationError(f"No reconcile safe mapping for {techno} in zone {zone}")
                username = f"{zone[-1]}CYBERARKRECO"
            else:
                safe_name = safes.get(cfg["policy"])
                if not safe_name:
                    raise CyberArkValidationError(f"No safe found for policy {cfg['policy']}")
                    
                short_name = "" if key == "MONITORING" else ecosystem.replace("-", "").replace("_", "")[:8]
                username = (
                    f"{config.USERNAME_PREFIX.get(cfg['policy'], '')}"
                    f"{zone[-1]}{techno[:2]}{cfg.get('code', '')}"
                    f"{short_name}{env[0].upper()}"
                )
            
            accounts.append({
                "safe_name": safe_name,
                "account_type": f"{techno.upper()}{config.ACCOUNT_TYPE_SUFFIX.get(cfg['policy'], '')}",
                "user_name": username,
                "role": cfg.get("role", ""),
                "comment": cfg.get("comment", ""),
            })
        
        return accounts

    @staticmethod
    def _build_schema_accounts(schemas: List[str], safe_name: str,
                             database: str, techno: str) -> List[Dict]:
        """Build schema account payloads"""
        if not schemas:
            return []
            
        techno_conf = config.SCHEMA_CONF.get(techno.upper())
        if not techno_conf:
            raise CyberArkValidationError(f"No schema config for technology {techno}")
            
        return [{
            "safe_name": safe_name,
            "account_type": f"{techno.upper()}{config.ACCOUNT_TYPE_SUFFIX.get('service', '')}",
            "user_name": schema,
            "role": techno_conf.get("role", ""),
            "comment": f"{techno_conf.get('comment', '')}{database}",
        } for schema in schemas]

    @staticmethod
    def _build_admin_accounts(admins: List[str], safe_name: str,
                            techno: str) -> List[Dict]:
        """Build admin account payloads"""
        if not admins:
            return []
            
        techno_conf = config.ADMIN_CONF.get(techno.upper())
        if not techno_conf:
            raise CyberArkValidationError(f"No admin config for technology {techno}")
            
        return [{
            "safe_name": safe_name,
            "account_type": f"{techno.upper()}{config.ACCOUNT_TYPE_SUFFIX.get('service', '')}",
            "user_name": admin,
            "role": techno_conf.get("role", ""),
            "comment": techno_conf.get("comment", ""),
        } for admin in admins]

    @staticmethod
    def _generate_password(length: int = 20) -> str:
        """Generate secure random password meeting complexity requirements"""
        try:
            char_sets = [
                string.ascii_uppercase,
                string.ascii_lowercase,
                string.digits,
                "!#%}"
            ]
            
            password = [random.choice(s) for s in char_sets]
            password.extend(random.choice(''.join(char_sets)) for _ in range(length - len(char_sets)))
            random.shuffle(password)
            return ''.join(password)
        except Exception as e:
            raise CyberArkException(f"Password generation failed: {str(e)}")
